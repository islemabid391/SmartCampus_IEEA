import argparse
import csv
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config" / "models.yaml"
RESULTS_DIR = BASE_DIR / "results"


def charger_jsonl(path: Path) -> list[dict]:
    lignes = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                lignes.append(json.loads(line))
    return lignes


def percentile_95(valeurs: list[float]) -> float:
    if not valeurs:
        return 0.0
    triees = sorted(valeurs)
    idx = math.ceil(0.95 * len(triees)) - 1
    return triees[max(0, min(idx, len(triees) - 1))]


def generer_feuille_notation(raw_path: Path, passe_cible: int = 1):
    enregistrements = [r for r in charger_jsonl(raw_path) if r["passe"] == passe_cible]
    random.seed(42)
    random.shuffle(enregistrements)

    a_noter_path = RESULTS_DIR / "a_noter.csv"
    mapping_path = RESULTS_DIR / "mapping.csv"

    with a_noter_path.open("w", encoding="utf-8-sig", newline="") as f_notes, \
         mapping_path.open("w", encoding="utf-8-sig", newline="") as f_map:

        writer_notes = csv.writer(f_notes, delimiter=";")
        writer_map = csv.writer(f_map, delimiter=";")

        writer_notes.writerow([
            "eval_id",
            "categorie",
            "question",
            "contexte",
            "comportement_attendu",
            "reponse_attendue",
            "reponse_modele",
            "justesse",
            "pertinence",
            "qualite_francais",
            "commentaire",
        ])
        writer_map.writerow(["eval_id", "question_id", "modele_id", "modele_nom"])

        for i, rec in enumerate(enregistrements, start=1):
            eval_id = f"EVAL-{i:03d}"
            writer_notes.writerow([
                eval_id,
                rec["categorie"],
                rec["question"],
                rec["contexte"] or "(Aucun contexte)",
                rec["comportement_attendu"],
                rec["reponse_attendue"],
                rec["reponse"],
                "",
                "",
                "",
                "",
            ])
            writer_map.writerow([eval_id, rec["question_id"], rec["modele_id"], rec["modele_nom"]])

    print(f"Feuille de notation en aveugle générée : {a_noter_path} ({len(enregistrements)} lignes)")
    print(f"Fichier de correspondance (ne pas ouvrir avant la fin) : {mapping_path}")


def charger_notes_humaines(notes_path: Path, mapping_path: Path) -> dict:
    mapping = {}
    with mapping_path.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            mapping[row["eval_id"]] = (row["modele_id"], row["question_id"])

    notes_par_modele = defaultdict(list)
    notes_par_modele_cat = defaultdict(list)

    with notes_path.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            eval_id = row["eval_id"]
            if eval_id not in mapping:
                continue
            modele_id, _ = mapping[eval_id]
            try:
                j = float(row["justesse"])
                p = float(row["pertinence"])
                qf = float(row["qualite_francais"])
            except (ValueError, TypeError):
                continue
            moyenne_item = (j + p + qf) / 3.0
            notes_par_modele[modele_id].append(moyenne_item)
            notes_par_modele_cat[(modele_id, row["categorie"])].append(moyenne_item)

    return {"par_modele": notes_par_modele, "par_cat": notes_par_modele_cat}


def generer_resume(raw_path: Path, notes_path: Path | None, config_path: Path):
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    poids = config.get("ponderation_score", {"qualite": 0.5, "latence": 0.2, "cout": 0.2, "erreurs": 0.1})

    enregistrements = charger_jsonl(raw_path)
    par_modele = defaultdict(list)
    for r in enregistrements:
        par_modele[r["modele_id"]].append(r)

    notes_humaines = {"par_modele": {}, "par_cat": {}}
    mapping_path = RESULTS_DIR / "mapping.csv"
    if notes_path and notes_path.exists() and mapping_path.exists():
        notes_humaines = charger_notes_humaines(notes_path, mapping_path)

    stats_modeles = []
    for modele_id, items in par_modele.items():
        nom = items[0]["modele_nom"]
        nb_total = len(items)
        nb_erreurs = sum(1 for x in items if not x["succes"])
        nb_reprises = sum(x["reprises"] for x in items)
        nb_fausses_infos = sum(1 for x in items if x["verif_auto"]["fausse_info_detectee"])

        latences = [x["latence_ms"] for x in items if x["succes"]]
        lat_med = statistics.median(latences) if latences else 0.0
        lat_p95 = percentile_95(latences)

        cout_moyen_req = statistics.mean(x["cout_usd"] for x in items)
        cout_1000 = cout_moyen_req * 1000.0

        ratio_cles = statistics.mean(x["verif_auto"]["ratio_mots_cles"] for x in items)

        # Cohérence des reformulations (passe 1)
        groupes = defaultdict(list)
        for x in items:
            if x["passe"] == 1 and x.get("groupe"):
                groupes[x["groupe"]].append(x["verif_auto"]["mots_cles_ok"])
        coherence_ref = (
            statistics.mean(1.0 if all(v) or not any(v) else 0.0 for v in groupes.values())
            if groupes
            else 1.0
        )

        liste_notes = notes_humaines["par_modele"].get(modele_id, [])
        note_humaine_moy = statistics.mean(liste_notes) if liste_notes else None

        stats_modeles.append({
            "modele_id": modele_id,
            "nom": nom,
            "nb_req": nb_total,
            "taux_erreurs": round((nb_erreurs / nb_total) * 100, 1),
            "reprises": nb_reprises,
            "lat_med_ms": round(lat_med, 1),
            "lat_p95_ms": round(lat_p95, 1),
            "cout_1000_usd": round(cout_1000, 4),
            "ratio_cles_pct": round(ratio_cles * 100, 1),
            "fausses_infos": nb_fausses_infos,
            "coherence_ref_pct": round(coherence_ref * 100, 1),
            "note_humaine_2": round(note_humaine_moy, 2) if note_humaine_moy is not None else None,
        })

    # Calcul du score global normalisé (0 à 100)
    max_lat = max((s["lat_med_ms"] for s in stats_modeles), default=1.0) or 1.0
    max_cout = max((s["cout_1000_usd"] for s in stats_modeles), default=1.0) or 1.0

    for s in stats_modeles:
        score_qual = (
            (s["note_humaine_2"] / 2.0)
            if s["note_humaine_2"] is not None
            else (s["ratio_cles_pct"] / 100.0)
        )
        score_lat = max(0.0, 1.0 - (s["lat_med_ms"] / (max_lat * 1.2)))
        score_cout = max(0.0, 1.0 - (s["cout_1000_usd"] / (max_cout * 1.2))) if max_cout > 0 else 1.0
        score_err = max(0.0, 1.0 - (s["taux_erreurs"] / 100.0))

        global_100 = 100.0 * (
            poids["qualite"] * score_qual
            + poids["latence"] * score_lat
            + poids["cout"] * score_cout
            + poids["erreurs"] * score_err
        )
        s["score_global"] = round(global_100, 1)

    stats_modeles.sort(key=lambda x: x["score_global"], reverse=True)

    resume_md = RESULTS_DIR / "resume.md"
    resume_csv = RESULTS_DIR / "resume.csv"

    lignes_md = [
        "# Résumé comparatif des modèles LLM (SA-33)\n",
        "| Modèle | Note humaine (/2) | Mots-clés (%) | Fausses infos | Cohérence reform. (%) | Latence méd. (ms) | Latence p95 (ms) | Coût / 1000 req ($) | Erreurs (%) | Score global (/100) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in stats_modeles:
        nh = f"{s['note_humaine_2']:.2f}" if s["note_humaine_2"] is not None else "N/A"
        lignes_md.append(
            f"| {s['nom']} (`{s['modele_id']}`) | {nh} | {s['ratio_cles_pct']}% | "
            f"{s['fausses_infos']} | {s['coherence_ref_pct']}% | {s['lat_med_ms']} | "
            f"{s['lat_p95_ms']} | ${s['cout_1000_usd']:.4f} | {s['taux_erreurs']}% | **{s['score_global']}** |"
        )

    resume_md.write_text("\n".join(lignes_md) + "\n", encoding="utf-8")

    with resume_csv.open("w", encoding="utf-8-sig", newline="") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=list(stats_modeles[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(stats_modeles)

    print(f"Tableau comparatif généré : {resume_md} et {resume_csv}")


def main():
    parser = argparse.ArgumentParser(description="Analyse et notation des résultats SA-33")
    sub = parser.add_subparsers(dest="commande", required=True)

    p_feuille = sub.add_parser("feuille", help="Génère results/a_noter.csv pour notation en aveugle")
    p_feuille.add_argument("--raw", type=Path, required=True)
    p_feuille.add_argument("--passe", type=int, default=1)

    p_resume = sub.add_parser("resume", help="Calcule les métriques et génère resume.md")
    p_resume.add_argument("--raw", type=Path, required=True)
    p_resume.add_argument("--notes", type=Path, default=None)
    p_resume.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    args = parser.parse_args()
    if args.commande == "feuille":
        generer_feuille_notation(args.raw, args.passe)
    elif args.commande == "resume":
        generer_resume(args.raw, args.notes, args.config)


if __name__ == "__main__":
    main()