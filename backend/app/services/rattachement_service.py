"""Rattachement d'une session visiteur (et de ses conversations) à un compte candidat."""

from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.utilisateur import (
    Conversation,
    Message,
    ProfilAcademique,
    SessionVisiteur,
    Utilisateur,
)
from app.services.memoire_service import CHAMPS_PROFIL, get_memoire


class ConsentementRequis(Exception):
    """Le candidat n'a pas donné son accord explicite."""


class RattachementImpossible(Exception):
    """Session déjà rattachée, expirée ou sans conversation."""


def apercu_rattachement(db: Session, session: SessionVisiteur) -> dict:
    """Ce que le candidat s'apprête à associer à son compte (pour l'afficher avant l'accord)."""
    nb_conversations = db.scalar(
        select(func.count(Conversation.id)).where(Conversation.session_id == session.id)
    ) or 0
    nb_messages = db.scalar(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.session_id == session.id)
    ) or 0
    return {
        "rattachable": (
            session.statut == "active"
            and session.utilisateur_id is None
            and nb_conversations > 0
        ),
        "nb_conversations": nb_conversations,
        "nb_messages": nb_messages,
    }


def _copier_memoire_vers_profil(
    db: Session, utilisateur: Utilisateur, conversations: list[Conversation]
) -> None:
    """Pré-remplit le profil académique sans écraser ce que le candidat a déjà saisi."""
    infos: dict = {}
    for conversation in sorted(conversations, key=lambda c: c.id):
        infos.update(get_memoire(conversation))  # la plus récente l'emporte
    if not infos:
        return

    profil = db.scalar(
        select(ProfilAcademique).where(ProfilAcademique.utilisateur_id == utilisateur.id)
    )
    if profil is None:
        profil = ProfilAcademique(utilisateur_id=utilisateur.id)
        db.add(profil)

    for champ in CHAMPS_PROFIL:
        if champ not in infos:
            continue
        if getattr(profil, champ) not in (None, "", []):
            continue  # déjà renseigné par le candidat : on ne touche pas
        valeur = infos[champ]
        if champ == "moyenne":
            valeur = Decimal(str(valeur))
        setattr(profil, champ, valeur)


def rattacher_session(
    db: Session,
    session: SessionVisiteur,
    utilisateur: Utilisateur,
    consentement: bool,
) -> int:
    """Rattache la session et ses conversations au candidat. Retourne le nombre de conversations."""
    if not consentement:
        raise ConsentementRequis("Votre accord explicite est nécessaire pour associer la conversation.")

    try:
        # Verrou de ligne : deux rattachements simultanés de la même session sont impossibles.
        # populate_existing : on relit l'état réel en base, pas une copie en mémoire.
        verrouillee = db.scalar(
            select(SessionVisiteur)
            .where(SessionVisiteur.id == session.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            verrouillee is None
            or verrouillee.statut != "active"
            or verrouillee.utilisateur_id is not None
        ):
            raise RattachementImpossible("Cette session ne peut plus être rattachée.")

        conversations = list(
            db.scalars(select(Conversation).where(Conversation.session_id == verrouillee.id))
        )
        if not conversations:
            raise RattachementImpossible("Aucune conversation à rattacher.")

        ids = [c.id for c in conversations]
        for conversation in conversations:
            conversation.utilisateur_id = utilisateur.id
            conversation.session_id = None  # la conversation appartient désormais au compte

        # Les messages d'un compte ne sont plus temporaires : on retire leur date d'expiration.
        db.execute(
            update(Message)
            .where(Message.conversation_id.in_(ids))
            .values(date_expiration=None)
        )

        _copier_memoire_vers_profil(db, utilisateur, conversations)

        verrouillee.utilisateur_id = utilisateur.id
        verrouillee.consentement_rattachement = True
        verrouillee.statut = "rattachee"

        db.commit()
        return len(conversations)
    except Exception:
        db.rollback()
        raise