import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.services import llm_service
from app.services.llm_service import (
    LLMAccesRefuse,
    LLMIndisponible,
    LLMNonConfigure,
    LLMReponseInvalide,
    LLMSature,
    LLMTimeout,
    appeler_llm,
)

CLE = "gsk_CLE_SECRETE_DE_TEST"
MESSAGES = [{"role": "user", "content": "Bonjour"}]


@pytest.fixture(autouse=True)
def configuration(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", SecretStr(CLE))
    monkeypatch.setattr(settings, "llm_base_url", "https://llm.exemple.test/v1")
    monkeypatch.setattr(settings, "llm_model", "modele-test")
    monkeypatch.setattr(settings, "llm_max_retries", 2)
    monkeypatch.setattr(llm_service.time, "sleep", lambda secondes: None)  # tests rapides


def client_simule(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def reponse_ok(texte="Bonjour !", finish="stop"):
    return httpx.Response(
        200,
        json={
            "model": "modele-test",
            "choices": [{"message": {"content": texte}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5},
        },
    )


def test_succes_et_contenu_de_la_requete():
    vues = []

    def handler(request):
        vues.append(request)
        return reponse_ok()

    resultat = appeler_llm(MESSAGES, http_client=client_simule(handler))

    assert resultat.texte == "Bonjour !"
    assert (resultat.tokens_entree, resultat.tokens_sortie) == (12, 5)
    assert resultat.tronquee is False
    requete = vues[0]
    assert str(requete.url) == "https://llm.exemple.test/v1/chat/completions"
    assert requete.headers["authorization"] == f"Bearer {CLE}"
    corps = requete.read().decode()
    assert '"model":"modele-test"' in corps.replace(" ", "") and '"max_tokens":1500' in corps.replace(" ", "")


def test_reponse_tronquee_signalee():
    resultat = appeler_llm(MESSAGES, http_client=client_simule(lambda r: reponse_ok("coupée", "length")))
    assert resultat.tronquee is True

def test_sans_cle_le_service_n_est_pas_configure(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", None)
    with pytest.raises(LLMNonConfigure) as erreur:
        appeler_llm(MESSAGES, http_client=client_simule(lambda r: reponse_ok()))
    assert erreur.value.status_code == 503


def test_ollama_local_sans_cle_autorise(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "llm_base_url", "http://localhost:11434/v1")
    assert appeler_llm(MESSAGES, http_client=client_simule(lambda r: reponse_ok())).texte == "Bonjour !"


def test_timeout_apres_les_nouvelles_tentatives():
    appels = []

    def handler(request):
        appels.append(1)
        raise httpx.ReadTimeout("trop lent", request=request)

    with pytest.raises(LLMTimeout) as erreur:
        appeler_llm(MESSAGES, http_client=client_simule(handler))
    assert erreur.value.status_code == 504
    assert len(appels) == 3  # 1 essai + 2 nouvelles tentatives


def test_erreur_reseau_devient_indisponible():
    def handler(request):
        raise httpx.ConnectError("connexion refusée", request=request)

    with pytest.raises(LLMIndisponible):
        appeler_llm(MESSAGES, http_client=client_simule(handler))


def test_erreur_serveur_puis_succes():
    reponses = iter([httpx.Response(503), httpx.Response(500), reponse_ok("enfin")])
    assert appeler_llm(MESSAGES, http_client=client_simule(lambda r: next(reponses))).texte == "enfin"


def test_cle_refusee_sans_nouvelle_tentative():
    appels = []

    def handler(request):
        appels.append(1)
        return httpx.Response(401, json={"error": "invalid api key"})

    with pytest.raises(LLMAccesRefuse) as erreur:
        appeler_llm(MESSAGES, http_client=client_simule(handler))
    assert len(appels) == 1
    assert CLE not in erreur.value.message and "invalid" not in erreur.value.message

def test_quota_epuise_echoue_vite():
    appels = []

    def handler(request):
        appels.append(1)
        return httpx.Response(429, headers={"retry-after": "3600"})

    with pytest.raises(LLMSature):
        appeler_llm(MESSAGES, http_client=client_simule(handler))
    assert len(appels) == 1  # inutile d'attendre une heure


def test_limite_courte_429_puis_succes():
    reponses = iter([httpx.Response(429, headers={"retry-after": "1"}), reponse_ok("ok")])
    assert appeler_llm(MESSAGES, http_client=client_simule(lambda r: next(reponses))).texte == "ok"


def test_reponse_vide_ou_illisible():
    with pytest.raises(LLMReponseInvalide):
        appeler_llm(MESSAGES, http_client=client_simule(lambda r: reponse_ok("   ")))
    with pytest.raises(LLMReponseInvalide):
        appeler_llm(MESSAGES, http_client=client_simule(lambda r: httpx.Response(200, text="pas du json")))
    with pytest.raises(LLMReponseInvalide):
        appeler_llm(MESSAGES, http_client=client_simule(lambda r: httpx.Response(200, json={"choices": []})))


def test_la_cle_n_apparait_jamais_dans_les_messages_ni_les_journaux(caplog):
    def handler(request):
        raise httpx.ConnectError(f"échec vers {request.url} avec {request.headers['authorization']}", request=request)

    with caplog.at_level("DEBUG"):
        with pytest.raises(LLMIndisponible) as erreur:
            appeler_llm(MESSAGES, http_client=client_simule(handler))
    assert CLE not in erreur.value.message
    assert CLE not in caplog.text and "llm.exemple.test" not in caplog.text


def test_la_cle_est_masquee_dans_la_configuration():
    assert CLE not in repr(settings) and CLE not in str(settings.llm_api_key)