"""Mémoire temporaire des conversations : messages conservés, fenêtre de contexte, expiration."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.utilisateur import Conversation, Message, SessionVisiteur
from app.services.quota_service import verifier_quota_conversations, verifier_quota_messages


def creer_conversation(
    db: Session, session: SessionVisiteur, langue: str | None = None
) -> Conversation:
    """Ouvre une conversation dans la session (429 si la limite de conversations est atteinte)."""
    verifier_quota_conversations(db, session)
    conversation = Conversation(session_id=session.id, langue_detectee=langue)
    try:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    except Exception:
        db.rollback()
        raise
    return conversation


def get_conversation_de_session(
    db: Session, session: SessionVisiteur, conversation_id: int
) -> Conversation | None:
    """Retourne la conversation seulement si elle appartient à cette session."""
    return db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.session_id == session.id,
        )
    )


def ajouter_message(
    db: Session,
    session: SessionVisiteur | None,
    conversation: Conversation,
    role: str,
    contenu: str,
    langue: str | None = None,
) -> Message:
    """Enregistre un message avec sa date d'expiration et applique les limites.

    - le contenu est tronqué à `memoire_max_caracteres` ;
    - un message visiteur ('user') respecte le quota de la session (429) ;
    - le message expire après `memoire_ttl_minutes`, sans dépasser l'expiration de la session ;
    - au-delà de `memoire_max_messages_stockes`, les plus anciens messages sont supprimés.
    """
    contenu = contenu.strip()[: settings.memoire_max_caracteres]
    if not contenu:
        raise ValueError("Le message est vide.")
    if session is not None and role == "user":
        verifier_quota_messages(db, session)

    expiration = None if session is None else min(
        session.date_expiration,
        datetime.now(timezone.utc) + timedelta(minutes=settings.memoire_ttl_minutes),
    )
    message = Message(
        conversation_id=conversation.id,
        role=role,
        contenu=contenu,
        langue=langue,
        date_expiration=expiration,
    )
    try:
        db.add(message)
        db.flush()
        if session is not None:
            _limiter_stockage(db, conversation)
        db.commit()
        db.refresh(message)
    except Exception:
        db.rollback()
        raise
    return message


def _limiter_stockage(db: Session, conversation: Conversation) -> None:
    """Supprime les plus anciens messages au-delà de la limite de stockage."""
    trop_anciens = db.scalars(
        select(Message.id)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
        .offset(settings.memoire_max_messages_stockes)
    ).all()
    if trop_anciens:
        db.execute(delete(Message).where(Message.id.in_(trop_anciens)))


def get_historique(
    db: Session, conversation: Conversation, limite: int | None = None
) -> list[Message]:
    """Derniers messages non expirés, du plus ancien au plus récent (fenêtre de contexte)."""
    limite = limite or settings.memoire_fenetre_messages
    recents = db.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            or_(
                Message.date_expiration.is_(None),
                Message.date_expiration > datetime.now(timezone.utc),
            ),
        )
        .order_by(Message.id.desc())
        .limit(limite)
    ).all()
    return list(reversed(recents))


def historique_pour_llm(messages: list[Message]) -> list[dict[str, str]]:
    """Format attendu par un LLM : [{"role": ..., "content": ...}, ...]."""
    return [{"role": m.role, "content": m.contenu} for m in messages]

# ---------------------------------------------------------------------------
# Informations utiles retenues sur le visiteur (évite de reposer les mêmes questions)
# ---------------------------------------------------------------------------

# champ -> taille maximale (texte) ; les listes gardent au plus MAX_ELEMENTS éléments
CHAMPS_TEXTE = {
    "niveau_scolaire": 100,
    "section_bac": 100,
    "objectif_professionnel": 300,
    "contraintes": 300,
}
CHAMPS_LISTE = ("matieres_preferees", "centres_interet")
CHAMP_MOYENNE = "moyenne"
MAX_ELEMENTS = 10
MAX_ELEMENT_CARACTERES = 50
CHAMPS_PROFIL = [*CHAMPS_TEXTE, CHAMP_MOYENNE, *CHAMPS_LISTE]


def _nettoyer_infos(infos: dict) -> dict:
    """Garde uniquement les champs autorisés, avec des valeurs valides et de taille limitée."""
    propre: dict = {}
    for champ, taille in CHAMPS_TEXTE.items():
        valeur = infos.get(champ)
        if isinstance(valeur, str) and valeur.strip():
            propre[champ] = valeur.strip()[:taille]

    moyenne = infos.get(CHAMP_MOYENNE)
    if isinstance(moyenne, (int, float)) and not isinstance(moyenne, bool) and 0 <= moyenne <= 20:
        propre[CHAMP_MOYENNE] = float(moyenne)

    for champ in CHAMPS_LISTE:
        valeurs = infos.get(champ)
        if isinstance(valeurs, list):
            elements = [
                v.strip()[:MAX_ELEMENT_CARACTERES]
                for v in valeurs
                if isinstance(v, str) and v.strip()
            ]
            if elements:
                propre[champ] = elements
    return propre


def get_memoire(conversation: Conversation) -> dict:
    """Informations retenues jusqu'ici (dictionnaire vide s'il n'y en a pas)."""
    return dict(conversation.memoire or {})


def mettre_a_jour_memoire(db: Session, conversation: Conversation, infos: dict) -> dict:
    """Fusionne de nouvelles informations avec celles déjà connues.

    - champs inconnus ou valeurs invalides : ignorés ;
    - texte et moyenne : la valeur la plus récente remplace l'ancienne ;
    - listes : fusionnées sans doublon, limitées à MAX_ELEMENTS éléments.
    """
    nouvelles = _nettoyer_infos(infos)
    fusion = get_memoire(conversation)
    for champ, valeur in nouvelles.items():
        if champ in CHAMPS_LISTE:
            existants = fusion.get(champ, [])
            ajoutes = [v for v in valeur if v.lower() not in {e.lower() for e in existants}]
            fusion[champ] = (existants + ajoutes)[:MAX_ELEMENTS]
        else:
            fusion[champ] = valeur

    conversation.memoire = fusion  # nouvel objet : SQLAlchemy détecte le changement
    try:
        db.commit()
        db.refresh(conversation)
    except Exception:
        db.rollback()
        raise
    return get_memoire(conversation)


def infos_manquantes(conversation: Conversation) -> list[str]:
    """Champs du profil encore inconnus : ce que l'agent peut encore demander."""
    connu = get_memoire(conversation)
    return [champ for champ in CHAMPS_PROFIL if not connu.get(champ)]


def effacer_memoire(db: Session, conversation: Conversation) -> None:
    """Droit à l'oubli : supprime les messages et les informations retenues."""
    try:
        db.execute(delete(Message).where(Message.conversation_id == conversation.id))
        conversation.memoire = None
        db.commit()
    except Exception:
        db.rollback()
        raise
