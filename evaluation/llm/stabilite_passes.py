"""SA-34 - Stabilite entre passes (aucun appel API).

  python evaluation/llm/stabilite_passes.py evaluation/llm/results/raw_XXXX.jsonl

Pour chaque question : les 3 passes donnent-elles la meme comprehension, le meme
comportement, le meme verdict mots-cles ? Suit aussi les cas d'erreur connus.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
QUESTIONS = BASE / "data" / "questions_dialecte.json"
CAS_CONNUS = ["TN-ADM-014", "TN-AMB-006"]


def extraire_json(t):
    m = re.search(r"\{.*\}", t or "", flags=re.DOTALL)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
        return o if isinstance(o, dict) else None
    except json.JSONDecodeError:
        return None


def normaliser(t):
    t = (t or "").replace("\u00a0", " ").replace("\u202f", " ")
    return re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", t)


def cles_ok(texte, item):
    cles = item.get("mots_cles") or []
    if not cles:
        return None
    texte = normaliser(texte)
    return all(re.search(p, texte, flags=re.IGNORECASE) for p in cles)


def pct(n, d):
    return "n/a" if d == 0 else f"{100 * n / d:.0f}% ({n}/{d})"


def main():
    chemin = Path(sys.argv[1])
    qs = {q["id"]: q for q in json.loads(QUESTIONS.read_text(encoding="utf-8"))}
    par_q = defaultdict(dict)
    echecs = 0
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        r = json.loads(ligne)
        if not r.get("succes"):
            echecs += 1
            continue
        j = extraire_json(r.get("reponse", ""))
        texte = (j or {}).get("reponse") or r.get("reponse") or ""
        par_q[r["question_id"]][r["passe"]] = {
            "comp": (j or {}).get("comprehension"),
            "comportement": (j or {}).get("comportement"),
            "cles": cles_ok(texte, qs[r["question_id"]]),
            "intention": (j or {}).get("intention_comprise", ""),
            "json": j is not None,
        }
    passes = sorted({p for d in par_q.values() for p in d})
    print(f"Fichier : {chemin.name} | echecs API : {echecs} | passes : {passes}\n")

    print("| Passe | N | JSON valide | Compris (ok) | Partielle | Echec | Mots-cles OK |")
    print("|---|---|---|---|---|---|---|")
    for p in passes:
        x = [d[p] for d in par_q.values() if p in d]
        c = [v for v in x if v["cles"] is not None]
        print(f"| {p} | {len(x)} | {pct(sum(v['json'] for v in x), len(x))} | "
              f"{pct(sum(v['comp'] == 'ok' for v in x), len(x))} | "
              f"{pct(sum(v['comp'] == 'partielle' for v in x), len(x))} | "
              f"{pct(sum(v['comp'] == 'echec' for v in x), len(x))} | "
              f"{pct(sum(v['cles'] for v in c), len(c))} |")

    completes = {q: d for q, d in par_q.items() if len(d) == len(passes)}
    print(f"\nQuestions avec toutes les passes valides : {len(completes)}/{len(qs)}")
    for champ, nom in (("comp", "comprehension"), ("comportement", "comportement"), ("cles", "verdict mots-cles")):
        cand = {q: d for q, d in completes.items() if all(v[champ] is not None for v in d.values())}
        stables = [q for q, d in cand.items() if len({v[champ] for v in d.values()}) == 1]
        print(f"- {nom} identique sur toutes les passes : {pct(len(stables), len(cand))}")
        if champ == "comp":
            instables = sorted(set(cand) - set(stables))
            print(f"  questions instables : {', '.join(instables) or 'aucune'}")

    print("\nSuivi des cas d'erreur connus :")
    for q in CAS_CONNUS:
        for p in passes:
            v = par_q.get(q, {}).get(p)
            if v:
                print(f"- {q} passe {p} : comprehension={v['comp']} | comportement={v['comportement']} | "
                      f"intention={v['intention'][:80]}")
    print("\nAttention : seule la passe 1 a ete annotee a la main ; les passes 2 et 3 servent a mesurer la stabilite.")


if __name__ == "__main__":
    main()
