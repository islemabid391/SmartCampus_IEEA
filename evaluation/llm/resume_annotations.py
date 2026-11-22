"""SA-34 - Echantillon d'annotation + agregation des annotations manuelles.

  python evaluation/llm/resume_annotations.py --tirage      # liste les IDs a annoter
  python evaluation/llm/resume_annotations.py               # agrege le CSV annote

Grille (colonnes du CSV results/dialecte_a_annoter.csv) :
  annot_intention_0_1_2        0 = intention fausse, 1 = partielle, 2 = correcte
  annot_justesse_0_1_2         0 = faux, 1 = partiellement juste, 2 = juste (par rapport a reponse_attendue)
  annot_hallucination_0_1      1 = le modele invente un fait/document/demarche absent du contexte
  annot_reponse_en_francais_0_1  1 = reponse entierement en francais
  type_erreur                  libre : ex. polysemie, mot_inconnu, hallucination, code_switching, autre
"""
import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent / "results" / "dialecte_a_annoter.csv"
COL_INT = "annot_intention_0_1_2"
COL_JUS = "annot_justesse_0_1_2"
COL_HAL = "annot_hallucination_0_1"
COL_FR = "annot_reponse_en_francais_0_1"
FORCES = ["TN-ADM-001", "TN-ADM-014", "TN-AMB-006", "TN-ADM-007", "TN-ADM-018"]  # cas deja identifies


def lire():
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def tirage(lignes, par_langue=6, graine=42):
    rnd = random.Random(graine)
    tires = []
    for lg in ["tn_arabe", "arabizi", "code_switching"]:
        ids = sorted(l["id"] for l in lignes if l["langue"] == lg and l["id"] not in FORCES)
        tires += rnd.sample(ids, min(par_langue, len(ids)))
    return FORCES + tires


def num(v):
    v = (v or "").strip()
    return int(v) if v in {"0", "1", "2"} else None


def pct(n, d):
    return "n/a" if d == 0 else f"{100 * n / d:.0f}% ({n}/{d})"


def agreger(lignes):
    annotees = [l for l in lignes if num(l[COL_INT]) is not None]
    if not annotees:
        print("Aucune ligne annotee.")
        return
    print(f"Lignes annotees : {len(annotees)}\n")
    print("| Langue | N | Intention correcte (2) | Intention fausse (0) | Reponse juste (2) | Hallucination | Reponse en francais |")
    print("|---|---|---|---|---|---|---|")
    groupes = defaultdict(list)
    for l in annotees:
        groupes[l["langue"]].append(l)
        groupes["TOTAL"].append(l)
    for lg in ["tn_arabe", "arabizi", "code_switching", "TOTAL"]:
        g = groupes.get(lg, [])
        n = len(g)
        print(f"| {lg} | {n} | {pct(sum(num(x[COL_INT]) == 2 for x in g), n)} | "
              f"{pct(sum(num(x[COL_INT]) == 0 for x in g), n)} | "
              f"{pct(sum(num(x[COL_JUS]) == 2 for x in g), n)} | "
              f"{pct(sum((x[COL_HAL] or '').strip() == '1' for x in g), n)} | "
              f"{pct(sum((x[COL_FR] or '').strip() == '1' for x in g), n)} |")
    erreurs = Counter(l["type_erreur"].strip() for l in annotees if l["type_erreur"].strip())
    print("\nTaxonomie des erreurs :", dict(erreurs) or "aucune renseignee")
    surs = [l for l in annotees if num(l[COL_INT]) == 0 and l["comprehension"] == "ok"]
    print(f"\nErreurs d'intention avec comprehension='ok' (erreurs silencieuses) : {len(surs)} -> "
          + (", ".join(l["id"] for l in surs) or "aucune"))
    print("\nAttention : echantillon de petite taille, non representatif des cas rares.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tirage", action="store_true")
    a = ap.parse_args()
    lignes = lire()
    if a.tirage:
        print("A annoter (", len(tirage(lignes)), "lignes ) :")
        print(", ".join(tirage(lignes)))
    else:
        agreger(lignes)
