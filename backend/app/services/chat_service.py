"""Construction de la conversation envoyée au LLM (dialogue multi-tours)."""

from typing import Iterable, Protocol
from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT
from app.core.prompts import SYSTEM_PROMPT

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

def limiter_historique(
    historique: Iterable[MessageLike], budget_caracteres: int
) -> list[MessageLike]:
    """Garde les messages les plus récents dont le total tient dans le budget.

    Les plus anciens sont retirés en premier. Le message le plus récent est toujours
    conservé, même s'il dépasse seul le budget.
    """
    gardes: list[MessageLike] = []
    total = 0
    for message in reversed(list(historique)):
        taille = len(message.contenu)
        if gardes and total + taille > budget_caracteres:
            break
        gardes.append(message)
        total += taille
    gardes.reverse()
    return gardes


def construire_messages(
    question: str,
    historique: Iterable[MessageLike],
    memoire: dict | None = None,
    contexte_officiel: str | None = None,
    budget_caracteres: int | None = None,
) -> list[dict[str, str]]:
    """Liste de messages [{"role", "content"}] prête à être envoyée au LLM :

    1. consigne système, puis (si fournis) le contexte officiel et les informations
       déjà connues sur le visiteur ;
    2. derniers messages de la conversation, du plus ancien au plus récent, dans la
       limite d'un budget de caractères ;
    3. la nouvelle question.

    La question n'est pas encore enregistrée en base : elle ne doit pas figurer dans `historique`.
    `contexte_officiel` est le point d'accroche du futur RAG : seules les informations de ce
    bloc peuvent être présentées comme officielles (voir prompts.py).
    """
    systeme = SYSTEM_PROMPT

    contexte = (contexte_officiel or "").strip()
    if contexte:
        systeme += "\n\nCONTEXTE OFFICIEL (seule source des informations administratives) :\n" + contexte

    connu = texte_memoire(memoire or {})
    if connu:
        systeme += "\n\nInformations déjà connues sur l'étudiant (ne les redemande pas) :\n" + connu

    # le prompt système est déjà ajouté plus haut : on ne garde que les échanges user/assistant
    echanges = [m for m in historique if m.role in ("user", "assistant")]
    budget = (
        budget_caracteres
        if budget_caracteres is not None
        else settings.memoire_max_caracteres_contexte
    )

    messages = [{"role": "system", "content": systeme}]
    for message in limiter_historique(echanges, budget):
        messages.append({"role": message.role, "content": message.contenu})
    messages.append({"role": "user", "content": question})
    return messages