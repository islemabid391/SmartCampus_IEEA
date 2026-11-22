from types import SimpleNamespace

from app.core.prompts import SYSTEM_PROMPT
from app.services.chat_service import construire_messages, texte_memoire


def msg(role, contenu):
    return SimpleNamespace(role=role, contenu=contenu)


def test_ordre_systeme_historique_question():
    historique = [msg("user", "Bonjour"), msg("assistant", "Bonjour, que voulez-vous savoir ?")]
    messages = construire_messages("Quels sont les frais ?", historique)

    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert messages[1]["content"] == "Bonjour"
    assert messages[-1] == {"role": "user", "content": "Quels sont les frais ?"}


def test_informations_connues_ajoutees_au_prompt_systeme():
    memoire = {
        "niveau_scolaire": "Bac 2024",
        "matieres_preferees": ["Maths", "Info"],
        "moyenne": 14.5,
        "champ_inconnu": "ignoré",
        "contraintes": "",
    }
    systeme = construire_messages("Salut", [], memoire)[0]["content"]

    assert "Niveau scolaire : Bac 2024" in systeme
    assert "Matières préférées : Maths, Info" in systeme
    assert "Moyenne : 14.5" in systeme
    assert "ignoré" not in systeme and "Contraintes" not in systeme


def test_sans_memoire_le_prompt_systeme_reste_identique():
    assert construire_messages("Salut", [], {})[0]["content"] == SYSTEM_PROMPT
    assert construire_messages("Salut", [])[0]["content"] == SYSTEM_PROMPT
    assert texte_memoire({}) == ""


def test_les_messages_system_de_l_historique_sont_ignores():
    historique = [msg("system", "ancienne consigne"), msg("user", "Bonjour")]
    messages = construire_messages("Suite", historique)
    assert all("ancienne consigne" not in m["content"] for m in messages)
    assert [m["role"] for m in messages] == ["system", "user", "user"]