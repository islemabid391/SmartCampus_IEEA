"""Client du modèle de langage (API compatible OpenAI : Groq, OpenRouter, Ollama...).

- la clé d'accès vient uniquement de la configuration (LLM_API_KEY) et n'est jamais journalisée ;
- chaque erreur est convertie en `LLMError` avec un message sûr pour l'utilisateur
  (jamais de clé, d'URL interne ni de détail du fournisseur) ;
- délai maximal et nouvelles tentatives limitées pour ne pas bloquer l'API.
"""

import logging
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

HOTES_LOCAUX = {"localhost", "127.0.0.1", "::1"}
ATTENTE_MAX_RETRY_AFTER = 5  # secondes : au-delà, on n'attend pas (quota épuisé)


class LLMError(Exception):
    """Erreur d'appel au LLM. `status_code` est le code HTTP à renvoyer au client."""

    status_code = 502
    message_par_defaut = "Le service d'IA a rencontré une erreur."

    def __init__(self, message: str | None = None):
        self.message = message or self.message_par_defaut
        super().__init__(self.message)


class LLMNonConfigure(LLMError):
    status_code = 503
    message_par_defaut = "Le service d'IA n'est pas configuré."


class LLMTimeout(LLMError):
    status_code = 504
    message_par_defaut = "Le service d'IA a mis trop de temps à répondre. Réessayez dans un instant."


class LLMIndisponible(LLMError):
    status_code = 503
    message_par_defaut = "Le service d'IA est momentanément indisponible. Réessayez dans un instant."


class LLMSature(LLMError):
    status_code = 503
    message_par_defaut = "Le service d'IA est saturé (limite d'utilisation atteinte). Réessayez plus tard."


class LLMAccesRefuse(LLMError):
    status_code = 503
    # Message volontairement vague : la cause (clé invalide) est dans les journaux du serveur.
    message_par_defaut = "Le service d'IA n'est pas accessible pour le moment."


class LLMReponseInvalide(LLMError):
    status_code = 502
    message_par_defaut = "Le service d'IA a renvoyé une réponse inexploitable."


@dataclass
class LLMReponse:
    texte: str
    modele: str
    finish_reason: str | None
    tokens_entree: int | None
    tokens_sortie: int | None
    duree_ms: int

    @property
    def tronquee(self) -> bool:
        """True si la réponse a été coupée par la limite max_tokens."""
        return self.finish_reason == "length"

def appeler_llm(messages: list[dict[str, str]], http_client: httpx.Client | None = None) -> LLMReponse:
    """Envoie la conversation au LLM et retourne sa réponse.

    `messages` : [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
    Lève une sous-classe de `LLMError` en cas de problème.
    """
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    cle = settings.llm_api_key.get_secret_value() if settings.llm_api_key else ""
    if not cle and urlparse(url).hostname not in HOTES_LOCAUX:
        raise LLMNonConfigure()

    en_tetes = {"Authorization": f"Bearer {cle}"} if cle else {}
    corps = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }

    client = http_client or httpx.Client(timeout=httpx.Timeout(settings.llm_timeout_secondes))
    try:
        debut = time.monotonic()
        reponse = _envoyer_avec_reessais(client, url, en_tetes, corps)
        duree_ms = int((time.monotonic() - debut) * 1000)
    finally:
        if http_client is None:
            client.close()
    return _lire_reponse(reponse, duree_ms)

def _envoyer_avec_reessais(
    client: httpx.Client, url: str, en_tetes: dict, corps: dict
) -> httpx.Response:
    tentatives = 1 + max(0, settings.llm_max_retries)
    derniere_erreur: LLMError = LLMIndisponible()

    for numero in range(tentatives):
        try:
            reponse = client.post(url, headers=en_tetes, json=corps)
        except httpx.TimeoutException:
            logger.warning("LLM : délai dépassé (tentative %s/%s)", numero + 1, tentatives)
            derniere_erreur = LLMTimeout()
        except httpx.TransportError as erreur:
            # on journalise le type d'erreur seulement (pas le message, qui peut contenir l'URL)
            logger.warning("LLM : erreur réseau %s (tentative %s/%s)", type(erreur).__name__, numero + 1, tentatives)
            derniere_erreur = LLMIndisponible()
        else:
            code = reponse.status_code
            if code < 400:
                return reponse
            logger.warning("LLM : réponse HTTP %s (tentative %s/%s)", code, numero + 1, tentatives)
            if code in (401, 403):
                logger.error("LLM : accès refusé par le fournisseur (clé invalide ou sans droit)")
                raise LLMAccesRefuse()
            if code == 429:
                attente = _attente_retry_after(reponse)
                if attente is None or numero == tentatives - 1:
                    raise LLMSature()  # quota épuisé : inutile d'insister
                time.sleep(attente)
                derniere_erreur = LLMSature()
                continue
            if code >= 500:
                derniere_erreur = LLMIndisponible()
            else:
                raise LLMError()  # autre erreur 4xx (requête ou modèle invalide) : pas de nouvelle tentative

        if numero < tentatives - 1:
            time.sleep(0.5 * (2**numero))  # 0,5 s puis 1 s...

    raise derniere_erreur

def _attente_retry_after(reponse: httpx.Response) -> float | None:
    """Délai demandé par le fournisseur s'il est court, sinon None."""
    try:
        attente = float(reponse.headers.get("retry-after", ""))
    except ValueError:
        return None
    return attente if 0 <= attente <= ATTENTE_MAX_RETRY_AFTER else None


def _lire_reponse(reponse: httpx.Response, duree_ms: int) -> LLMReponse:
    try:
        donnees = reponse.json()
        choix = donnees["choices"][0]
        texte = (choix["message"]["content"] or "").strip()
    except (ValueError, KeyError, IndexError, TypeError):
        raise LLMReponseInvalide()

    if not texte:
        # arrive quand le budget de tokens est consommé avant la réponse (observé en SA-33)
        raise LLMReponseInvalide("Le service d'IA n'a pas produit de réponse. Reformulez votre question.")

    usage = donnees.get("usage") or {}
    return LLMReponse(
        texte=texte,
        modele=donnees.get("model") or settings.llm_model,
        finish_reason=choix.get("finish_reason"),
        tokens_entree=usage.get("prompt_tokens"),
        tokens_sortie=usage.get("completion_tokens"),
        duree_ms=duree_ms,
    )