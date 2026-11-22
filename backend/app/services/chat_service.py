"""Construction de la conversation envoyée au LLM (dialogue multi-tours)."""

from typing import Iterable, Protocol

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