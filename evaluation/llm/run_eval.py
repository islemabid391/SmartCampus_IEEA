import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import APIError, APITimeoutError, OpenAI, RateLimitError

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_QUESTIONS = BASE_DIR / "data" / "questions_fr.json"
DEFAULT_CONFIG = BASE_DIR / "config" / "models.yaml"
RESULTS_DIR = BASE_DIR / "results"


def construire_prompt_utilisateur(item: dict) -> str:
    contexte = item.get("contexte")
    question = item["question"].strip()
    if contexte:
        return (
            f"Contexte officiel :\n{contexte.strip()}\n\n"
            f"Question de l'étudiant :\n{question}"
        )
    return (
        "Contexte officiel :\nAucun document officiel disponible pour cette demande.\n\n"
        f"Question de l'étudiant :\n{question}"
    )


def verifier_automatiquement(reponse: str, item: dict) -> dict:
    texte = reponse or ""
    mots_cles = item.get("mots_cles") or []
    mots_interdits = item.get("mots_interdits") or []

    cles_trouvees = [
        pat for pat in mots_cles if re.search(pat, texte, flags=re.IGNORECASE)
    ]
    interdits_trouves = [
        pat for pat in mots_interdits if re.search(pat, texte, flags=re.IGNORECASE)
    ]

    score_cles = (len(cles_trouvees) / len(mots_cles)) if mots_cles else 1.0
    a_fausse_info = len(interdits_trouves) > 0

    return {
        "mots_cles_ok": len(cles_trouvees) == len(mots_cles),
        "ratio_mots_cles": round(score_cles, 3),
        "mots_interdits_trouves": interdits_trouves,
        "fausse_info_detectee": a_fausse_info,
    }


def appeler_modele_avec_reprise(
    client: OpenAI,
    model_id: str,
    prompt_systeme: str,
    prompt_user: str,
    temperature: float,
    max_tokens: int,
    timeout_s: float,
    max_retries: int,
) -> dict:
    reprises = 0
    dernier_err = None

    for tentative in range(max_retries + 1):
        debut = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": prompt_systeme},
                    {"role": "user", "content": prompt_user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout_s,
            )
            latence_ms = (time.perf_counter() - debut) * 1000.0
            choice = resp.choices[0]
            contenu = (choice.message.content or "").strip()
            finish_reason = choice.finish_reason

            usage = resp.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0

            erreur_type = None
            if not contenu:
                erreur_type = "reponse_vide"
            elif finish_reason == "length":
                erreur_type = "reponse_tronquee"

            return {
                "succes": erreur_type is None,
                "erreur_type": erreur_type,
                "erreur_detail": None,
                "reponse": contenu,
                "finish_reason": finish_reason,
                "latence_ms": round(latence_ms, 2),
                "tokens_entree": tokens_in,
                "tokens_sortie": tokens_out,
                "reprises": reprises,
            }

        except RateLimitError as e:
            dernier_err = f"rate_limit: {e}"
            if tentative < max_retries:
                reprises += 1
                time.sleep(2 ** tentative)
                continue
            return {
                "succes": False,
                "erreur_type": "rate_limit_429",
                "erreur_detail": dernier_err,
                "reponse": "",
                "finish_reason": None,
                "latence_ms": round((time.perf_counter() - debut) * 1000.0, 2),
                "tokens_entree": 0,
                "tokens_sortie": 0,
                "reprises": reprises,
            }
        except APITimeoutError as e:
            dernier_err = f"timeout: {e}"
            if tentative < max_retries:
                reprises += 1
                continue
            return {
                "succes": False,
                "erreur_type": "timeout",
                "erreur_detail": dernier_err,
                "reponse": "",
                "finish_reason": None,
                "latence_ms": round((time.perf_counter() - debut) * 1000.0, 2),
                "tokens_entree": 0,
                "tokens_sortie": 0,
                "reprises": reprises,
            }
        except APIError as e:
            dernier_err = f"api_error_{getattr(e, 'status_code', 'unknown')}: {e}"
            if tentative < max_retries and getattr(e, "status_code", 500) >= 500:
                reprises += 1
                time.sleep(1.5 * (tentative + 1))
                continue
            return {
                "succes": False,
                "erreur_type": "erreur_http",
                "erreur_detail": dernier_err,
                "reponse": "",
                "finish_reason": None,
                "latence_ms": round((time.perf_counter() - debut) * 1000.0, 2),
                "tokens_entree": 0,
                "tokens_sortie": 0,
                "reprises": reprises,
            }
        except Exception as e:
            return {
                "succes": False,
                "erreur_type": "erreur_inattendue",
                "erreur_detail": str(e),
                "reponse": "",
                "finish_reason": None,
                "latence_ms": round((time.perf_counter() - debut) * 1000.0, 2),
                "tokens_entree": 0,
                "tokens_sortie": 0,
                "reprises": reprises,
            }


def main():
    parser = argparse.ArgumentParser(description="Évaluation multi-LLM SmartCampus AI (SA-33)")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--limit", type=int, default=None, help="Limiter aux N premières questions")
    parser.add_argument("--repeats", type=int, default=None, help="Nombre de passes (défaut: config)")
    parser.add_argument("--pause", type=float, default=0.0, help="Pause en secondes entre chaque requête")
    parser.add_argument("--dry-run", action="store_true", help="Vérifie la config sans appeler les API")
    parser.add_argument("--models", type=str, default=None,help="IDs des modèles à tester, séparés par des virgules")
    parser.add_argument("--max-tokens", type=int, default=None,help="Remplace max_tokens du fichier de config")
    parser.add_argument("--prompt-file", type=Path, default=None,
                        help="Fichier texte remplaçant le prompt système du fichier de config")
    parser.add_argument("--reprendre", type=Path, default=None,
                        help="Ancien raw_*.jsonl : conserve les réussites, ne relance que les échecs")
    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    params = config["parametres"]
    if args.max_tokens:
        params["max_tokens"] = args.max_tokens
    prompt_systeme = config["prompt_systeme"].strip()
    if args.prompt_file:
        prompt_systeme = args.prompt_file.read_text(encoding="utf-8").strip()
    modeles = config["modeles"]
    if args.models:
        ids_demandes = [x.strip() for x in args.models.split(",")]
        modeles = [m for m in modeles if m["id"] in ids_demandes]
        inconnus = set(ids_demandes) - {m["id"] for m in modeles}
        if inconnus:
            raise SystemExit(f"Modèle(s) inconnu(s) dans models.yaml : {inconnus}")

    questions_brutes = args.questions.read_text(encoding="utf-8")
    empreinte_questions = hashlib.sha256(questions_brutes.encode("utf-8")).hexdigest()[:16]
    questions = json.loads(questions_brutes)
    if args.limit:
        questions = questions[: args.limit]

    passes = args.repeats if args.repeats is not None else params.get("passes", 3)
    total_requetes = len(modeles) * len(questions) * passes

    if args.dry_run:
        print("=== MODE DRY-RUN (0 requête envoyée) ===")
        print(f"Questions chargées : {len(questions)} (empreinte SHA256: {empreinte_questions})")
        print(f"Passes par modèle  : {passes}")
        print(f"Modèles configurés : {[m['id'] for m in modeles]}")
        print(f"Total requêtes     : {total_requetes}")
        print("\n--- Prompt système ---")
        print(prompt_systeme)
        print("\n--- Exemple prompt utilisateur (Q1) ---")
        print(construire_prompt_utilisateur(questions[0]))
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_path = RESULTS_DIR / f"raw_{horodatage}.jsonl"
    meta_path = RESULTS_DIR / f"meta_{horodatage}.json"

    meta = {
        "date_utc": horodatage,
        "empreinte_questions": empreinte_questions,
        "nb_questions": len(questions),
        "passes": passes,
        "parametres": params,
        "modeles": modeles,
        "prompt_file": str(args.prompt_file) if args.prompt_file else None,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    clients = {}
    for m in modeles:
        cle = os.getenv(m["api_key_env"])
        if not cle:
            raise RuntimeError(
                f"Variable d'environnement manquante : {m['api_key_env']} pour le modèle {m['id']}"
            )
        clients[m["id"]] = OpenAI(api_key=cle, base_url=m["base_url"])
    deja_faits = {}
    if args.reprendre:
        for ligne in args.reprendre.read_text(encoding="utf-8").splitlines():
            if ligne.strip():
                r = json.loads(ligne)
                if r.get("succes"):
                    deja_faits[(r["passe"], r["modele_id"], r["question_id"])] = r
        print(f"Reprise : {len(deja_faits)} réponses réussies conservées")
    compteur = 0
    with raw_path.open("w", encoding="utf-8") as f_out:
        for passe in range(1, passes + 1):
            for m in modeles:
                client = clients[m["id"]]
                for idx, item in enumerate(questions, start=1):
                    compteur += 1
                    q_id = item.get("id", f"Q{idx:02d}")
                    cle_reprise = (passe, m["id"], q_id)
                    if cle_reprise in deja_faits:
                        f_out.write(json.dumps(deja_faits[cle_reprise], ensure_ascii=False) + "\n")
                        f_out.flush()
                        continue
                    prompt_user = construire_prompt_utilisateur(item)

                    res = appeler_modele_avec_reprise(
                        client=client,
                        model_id=m["id"],
                        prompt_systeme=prompt_systeme,
                        prompt_user=prompt_user,
                        temperature=params["temperature"],
                        max_tokens=params["max_tokens"],
                        timeout_s=params["timeout_secondes"],
                        max_retries=params.get("max_retries", 3),
                    )

                    cout_usd = (
                        res["tokens_entree"] * m["prix_entree_1m"]
                        + res["tokens_sortie"] * m["prix_sortie_1m"]
                    ) / 1_000_000.0

                    verif_auto = verifier_automatiquement(res["reponse"], item)

                    enregistrement = {
                        "passe": passe,
                        "modele_id": m["id"],
                        "modele_nom": m["nom_affiche"],
                        "fournisseur": m["fournisseur"],
                        "question_id": q_id,
                        "categorie": item.get("categorie", "inconnue"),
                        "groupe": item.get("groupe"),
                        "question": item["question"],
                        "contexte": item.get("contexte"),
                        "reponse_attendue": item.get("reponse_attendue", ""),
                        "comportement_attendu": item.get("comportement_attendu", ""),
                        "cout_usd": round(cout_usd, 8),
                        "verif_auto": verif_auto,
                        **res,
                    }
                    f_out.write(json.dumps(enregistrement, ensure_ascii=False) + "\n")
                    f_out.flush()

                    statut = "OK" if res["succes"] else f"ERR({res['erreur_type']})"
                    print(
                        f"[{compteur}/{total_requetes}] Passe {passe} | {m['id']} | {q_id} -> "
                        f"{statut} ({res['latence_ms']} ms)"
                    )

                    if args.pause > 0:
                        time.sleep(args.pause)

    print(f"\nTerminé ! Résultats bruts : {raw_path}")
    print(f"Métadonnées : {meta_path}")


if __name__ == "__main__":
    main()