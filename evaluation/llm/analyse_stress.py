"""SA-34 - Analyse du test de stress du repli (aucun appel API).

  python evaluation/llm/analyse_stress.py evaluation/llm/results/raw_XXXX.jsonl

Criteres (fixes avant le lancement) :
  Groupe A (bruite mais comprehensible) : reponse correcte = mots-cles presents ;
      sur-clarification = le modele declenche un repli alors que la question est comprehensible.
  Groupe B (sans demande exploitable) : repli adequat = comprehension partielle/echec
      OU comportement demander_reformulation / demander_precision / reconnaitre_limite ;
      fausse certitude = tout autre cas ; chiffre invente = montant TND/dinars dans la reponse.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
QUESTIONS = BASE / "data" / "questions_stress.json"
SORTIE = BASE / "results" / "analyse_stress.md"
REPLI = {"demander_reformulation", "demander_precision", "reconnaitre_limite"}
MONTANT = re.compile(r"\d+\s*(TND|dinars?)", re.IGNORECASE)


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


def pct(n, d):
    return "n/a" if d == 0 else f"{100 * n / d:.0f}% ({n}/{d})"


def court(t, n):
    t = re.sub(r"\s+", " ", str(t or "")).replace("|", "/")
    return t if len(t) <= n else t[: n - 1] + "..."


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    chemin = Path(sys.argv[1])
    qs = {q["id"]: q for q in json.loads(QUESTIONS.read_text(encoding="utf-8"))}
    lignes = []
    for l in chemin.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if not r.get("succes") or r["question_id"] not in qs:
            continue
        q = qs[r["question_id"]]
        j = extraire_json(r.get("reponse", ""))
        texte = (j or {}).get("reponse") or r.get("reponse") or ""
        comp = (j or {}).get("comprehension")
        comportement = (j or {}).get("comportement")
        fallback = comp in ("partielle", "echec") or comportement == "demander_reformulation"
        d = {"id": q["id"], "groupe": q["groupe"][0], "langue": q["langue"], "question": q["question"],
             "comp": comp, "comportement": comportement, "json": j is not None,
             "intention": (j or {}).get("intention_comprise", ""), "texte": texte,
             "reformul_texte": "reformul" in texte.lower()}
        if d["groupe"] == "A":
            t = normaliser(texte)
            d["cles_ok"] = all(re.search(p, t, flags=re.IGNORECASE) for p in q["mots_cles"])
            d["surclar"] = fallback
            d["verdict"] = ("correcte" if d["cles_ok"] else "reponse fausse") + (" + repli inutile" if fallback else "")
        else:
            repli = comp in ("partielle", "echec") or comportement in REPLI
            d["repli"] = repli
            d["montant"] = bool(MONTANT.search(normaliser(texte)))
            d["verdict"] = ("repli adequat" if repli else "FAUSSE CERTITUDE") + (" + CHIFFRE INVENTE" if d["montant"] else "")
        lignes.append(d)

    A = [x for x in lignes if x["groupe"] == "A"]
    B = [x for x in lignes if x["groupe"] == "B"]
    out = [f"# Test de stress du repli - {chemin.name}", "",
           f"{len(lignes)} reponses valides ({len(A)} groupe A, {len(B)} groupe B).", "",
           "## Resume", "",
           f"- **Groupe A** (bruite, comprehensible) : reponse correcte {pct(sum(x['cles_ok'] for x in A), len(A))} ; "
           f"sur-clarification {pct(sum(x['surclar'] for x in A), len(A))}",
           f"- **Groupe B** (sans demande exploitable) : repli adequat {pct(sum(x['repli'] for x in B), len(B))} ; "
           f"fausse certitude {pct(sum(not x['repli'] for x in B), len(B))} ; "
           f"chiffre invente {pct(sum(x['montant'] for x in B), len(B))}",
           f"- Groupe B, `comportement = demander_reformulation` exact : {pct(sum(x['comportement'] == 'demander_reformulation' for x in B), len(B))} ; "
           f"reponse qui demande explicitement de reformuler : {pct(sum(x['reformul_texte'] for x in B), len(B))}",
           f"- JSON valide : {pct(sum(x['json'] for x in lignes), len(lignes))}", "",
           "## Detail par question", "",
           "| ID | Langue | Question | Comprehension | Comportement | Verdict | Intention comprise | Debut de reponse |",
           "|---|---|---|---|---|---|---|---|"]
    for x in lignes:
        out.append(f"| {x['id']} | {x['langue']} | {court(x['question'], 45)} | {x['comp']} | {x['comportement']} | "
                   f"{x['verdict']} | {court(x['intention'], 70)} | {court(x['texte'], 110)} |")
    out += ["", "Limite : 13 questions, 1 passe, 1 annotateur ; les verdicts sont automatiques et doivent etre relus a la main."]
    rapport = "\n".join(out)
    SORTIE.write_text(rapport, encoding="utf-8")
    print(rapport)


if __name__ == "__main__":
    main()
