"""Construction de la conversation envoyée au LLM (dialogue multi-tours)."""

from typing import Iterable, Protocol

from sqlalchemy.orm import Session

from app.core.prompts import SYSTEM_PROMPT
from app.models.utilisateur import Conversation, Message, SessionVisiteur
from app.services import llm_service
from app.services.memoire_service import ajouter_message, get_historique, get_memoire
from app.services.quota_service import verifier_quota_messages

# champ de la mémoire -> libellé lisible par le modèle
LIBELLES_MEMOIRE = {
    "niveau_scolaire": "Niveau scolaire",
    "section_bac": "Section du bac",
    "moyenne": "Moyenne",
    "matieres_preferees": "Matières préférées",
    "centres_interet": "Centres d'intérêt",
    "objectif_professionnel": "Objectif professionnel",
    "contraintes": "Contraintes",
}


class MessageLike(Protocol):
    role: str
    contenu: str


def texte_memoire(memoire: dict) -> str:
    """Informations déjà connues sur le visiteur, en texte (vide s'il n'y en a pas)."""
    lignes = []
    for champ, libelle in LIBELLES_MEMOIRE.items():
        valeur = memoire.get(champ)
        if valeur in (None, "", []):
            continue
        if isinstance(valeur, list):
            valeur = ", ".join(str(v) for v in valeur)
        lignes.append(f"- {libelle} : {valeur}")
    return "\n".join(lignes)

def construire_messages(
    question: str, historique: Iterable[MessageLike], memoire: dict | None = None
) -> list[dict[str, str]]:
    """Liste de messages [{"role", "content"}] prête à être envoyée au LLM :

    1. consigne système (+ informations déjà connues sur le visiteur) ;
    2. derniers messages de la conversation, du plus ancien au plus récent ;
    3. la nouvelle question.

    La question n'est pas encore enregistrée en base : elle ne doit pas figurer dans `historique`.
    """
    systeme = SYSTEM_PROMPT
    connu = texte_memoire(memoire or {})
    if connu:
        systeme += "\n\nInformations déjà connues sur l'étudiant (ne les redemande pas) :\n" + connu

    messages = [{"role": "system", "content": systeme}]
    for message in historique:
        if message.role in ("user", "assistant"):  # le prompt système est déjà ajouté plus haut
            messages.append({"role": message.role, "content": message.contenu})
    messages.append({"role": "user", "content": question})
    return messages

def repondre(
    db: Session,
    conversation: Conversation,
    question: str,
    langue: str | None = None,
    session: SessionVisiteur | None = None,
) -> tuple[Message, llm_service.LLMReponse]:
    """Pose la question au LLM dans le contexte de la conversation et enregistre l'échange.

    `session` : visiteur anonyme (quota de session, messages temporaires) ;
    `None` : candidat connecté (messages permanents). Lève `LLMError` si le LLM échoue :
    dans ce cas, rien n'est enregistré.
    """
    if session is not None:
        verifier_quota_messages(db, session)  # avant l'appel (payant) au LLM
    messages = construire_messages(question, get_historique(db, conversation), get_memoire(conversation))
    resultat = llm_service.appeler_llm(messages)

    ajouter_message(db, session, conversation, "user", question, langue=langue)
    reponse = ajouter_message(db, session, conversation, "assistant", resultat.texte)
    return reponse, resultat