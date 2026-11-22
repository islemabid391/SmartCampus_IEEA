"""SA-34 - Analyse de la comprehension du dialecte tunisien / Arabizi.

Aucun appel API : lit les fichiers raw_*.jsonl deja produits par run_eval.py.

Usage (depuis la racine du repo) :
  python evaluation/llm/analyse_dialecte.py ^
      --fr evaluation/llm/results/raw_FR.jsonl ^
      --dialecte evaluation/llm/results/raw_DIALECTE.jsonl --passe 1

Sorties :
  results/analyse_dialecte.md        tableaux de resultats (a copier dans le rapport)
  results/dialecte_a_annoter.csv     grille d'annotation manuelle (ouvrir dans Excel)
"""
import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
RESULTS = BASE / "results"
REPONDRE = {"repondre", "repondre_et_preciser"}
LANGUES = ["tn_arabe", "arabizi", "code_switching"]


def extraire_json(texte):
    """Extrait l'objet JSON d'une reponse, meme entoure de ``` ou de texte."""
    if not texte:
        return None
    m = re.search(r"\{.*\}", texte, flags=re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def lire_questions(chemin):
    return {q["id"]: q for q in json.loads(chemin.read_text(encoding="utf-8"))}


def charger(chemin, passe):
    """Retourne (reponses reussies de la passe {question_id: record}, nb d'echecs API)."""
    ok, echecs = {}, 0
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        r = json.loads(ligne)
        if r.get("passe") != passe:
            continue
        if not r.get("succes"):
            echecs += 1
            continue
        r["json"] = extraire_json(r.get("reponse", ""))
        ok[r["question_id"]] = r
    return ok, echecs


def normaliser(texte):
    """'6 500' ou '6\u202f500' -> '6500' (sinon le regex des mots-cles rate les montants)."""
    texte = (texte or "").replace("\u00a0", " ").replace("\u202f", " ")
    return re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", texte)


def verifier(texte, item):
    texte = normaliser(texte)
    cles = item.get("mots_cles") or []
    interdits = item.get("mots_interdits") or []
    cles_ok = all(re.search(p, texte, flags=re.IGNORECASE) for p in cles) if cles else None
    faux = any(re.search(p, texte, flags=re.IGNORECASE) for p in interdits)
    return cles_ok, faux


def construire_lignes(records, questions, langue_fixe=None):
    """Une ligne de metriques par reponse."""
    lignes = []
    for qid, r in records.items():
        item = questions[qid]
        j = r["json"]
        texte = (j or {}).get("reponse") or r.get("reponse") or ""
        cles_ok, faux = verifier(texte, item)
        comp = (j or {}).get("comprehension")
        comportement = (j or {}).get("comportement")
        langue = langue_fixe or item.get("langue")
        lignes.append({
            "id": qid,
            "variante_de": item.get("variante_de"),
            "langue": langue,
            "json_ok": j is not None,
            "langue_detectee": (j or {}).get("langue_detectee"),
            "intention": (j or {}).get("intention_comprise", ""),
            "comp": comp,
            "comportement": comportement,
            "attendu": item.get("comportement_attendu"),
            "cles_ok": cles_ok,
            "faux": faux,
            "fallback": comp in ("partielle", "echec") or comportement == "demander_reformulation",
            "lat": r.get("latence_ms"),
            "tok": r.get("tokens_sortie"),
            "texte": texte,
            "question": item["question"],
            "reponse_attendue": item.get("reponse_attendue", ""),
        })
    return lignes


def pct(n, d):
    return "n/a" if d == 0 else f"{100 * n / d:.0f}% ({n}/{d})"


def med(vals):
    vals = [v for v in vals if v is not None]
    return "n/a" if not vals else f"{statistics.median(vals):.0f}"


def metriques(lignes):
    n = len(lignes)
    rep = [l for l in lignes if l["attendu"] in REPONDRE and l["cles_ok"] is not None]
    clairs = [l for l in lignes if l["attendu"] == "repondre"]
    return {
        "n": n,
        "json": pct(sum(l["json_ok"] for l in lignes), n),
        "comp_ok": pct(sum(l["comp"] == "ok" for l in lignes), n),
        "comp_part": pct(sum(l["comp"] == "partielle" for l in lignes), n),
        "comp_echec": pct(sum(l["comp"] == "echec" for l in lignes), n),
        "conforme": pct(sum(l["comportement"] == l["attendu"] for l in lignes), n),
        "cles": pct(sum(l["cles_ok"] for l in rep), len(rep)),
        "faux": pct(sum(l["faux"] for l in lignes), n),
        "surclar": pct(sum(l["fallback"] for l in clairs), len(clairs)),
        "lat": med([l["lat"] for l in lignes]),
        "tok": med([l["tok"] for l in lignes]),
    }


def tableau(titre, groupes):
    cols = [
        ("n", "N"), ("json", "JSON valide"), ("comp_ok", "Compris (ok)"),
        ("comp_part", "Partielle"), ("comp_echec", "Echec"),
        ("conforme", "Comportement conforme"), ("cles", "Mots-cles OK"),
        ("faux", "Fausse info"), ("surclar", "Repli sur q. claire"),
        ("lat", "Latence med. (ms)"), ("tok", "Tokens sortie med."),
    ]
    out = [f"### {titre}", "", "| Groupe | " + " | ".join(c[1] for c in cols) + " |",
           "|---|" + "---|" * len(cols)]
    for nom, lignes in groupes:
        m = metriques(lignes)
        out.append(f"| {nom} | " + " | ".join(str(m[c[0]]) for c in cols) + " |")
    return "\n".join(out)


def detection_langue(dial):
    out = ["### Detection de la langue (verite terrain = champ `langue` du jeu de test)", "",
           "| Langue reelle | N | Detectee correctement | Confusions (detectee -> nb) |", "|---|---|---|---|"]
    for lg in LANGUES:
        ls = [l for l in dial if l["langue"] == lg]
        bon = sum(l["langue_detectee"] == lg for l in ls)
        conf = defaultdict(int)
        for l in ls:
            if l["langue_detectee"] != lg:
                conf[str(l["langue_detectee"])] += 1
        out.append(f"| {lg} | {len(ls)} | {pct(bon, len(ls))} | {dict(conf) or '-'} |")
    return "\n".join(out)


def comparaison_appariee(dial, fr_par_id):
    out = ["### Comparaison appariee francais vs dialecte (mots-cles, questions avec reponse attendue)", "",
           "| Langue | Paires | Les deux OK | Regression (FR ok, dialecte KO) | Gain (FR KO, dialecte ok) | Les deux KO |",
           "|---|---|---|---|---|---|"]
    ids = {"reg": [], "ko": []}
    for lg in LANGUES + ["toutes"]:
        c = {"ok": 0, "reg": 0, "gain": 0, "ko": 0}
        for l in dial:
            if lg != "toutes" and l["langue"] != lg:
                continue
            f = fr_par_id.get(l["variante_de"])
            if f is None or l["attendu"] not in REPONDRE or l["cles_ok"] is None or f["cles_ok"] is None:
                continue
            if f["cles_ok"] and l["cles_ok"]:
                c["ok"] += 1
            elif f["cles_ok"]:
                c["reg"] += 1
                if lg == "toutes":
                    ids["reg"].append(l["id"])
            elif l["cles_ok"]:
                c["gain"] += 1
            else:
                c["ko"] += 1
                if lg == "toutes":
                    ids["ko"].append(l["id"])
        n = sum(c.values())
        out.append(f"| {lg} | {n} | {c['ok']} | {c['reg']} | {c['gain']} | {c['ko']} |")
    out += ["", f"- Regressions (a lire en priorite) : {', '.join(ids['reg']) or 'aucune'}",
            f"- Les deux KO (verifier si le controle automatique se trompe) : {', '.join(ids['ko']) or 'aucun'}"]
    return "\n".join(out)


def repli(dial):
    """Qualite du signal de repli. Verite terrain approchee : reponse jugee mauvaise
    = mots-cles manquants sur une question qui attend une reponse (proxy automatique)."""
    cand = [l for l in dial if l["attendu"] in REPONDRE and l["cles_ok"] is not None]
    mauvaise = [l for l in cand if not l["cles_ok"]]
    declenche = [l for l in cand if l["fallback"]]
    vrai_pos = [l for l in mauvaise if l["fallback"]]
    faux_neg = [l for l in mauvaise if not l["fallback"]]
    return "\n".join([
        "### Qualite du repli (proxy automatique, a affiner par l'annotation manuelle)", "",
        f"- Questions evaluees : {len(cand)} ; reponses jugees mauvaises (mots-cles absents) : {len(mauvaise)}",
        f"- Repli declenche : {len(declenche)}",
        f"- **Rappel** du repli (mauvaises reponses detectees) : {pct(len(vrai_pos), len(mauvaise))}",
        f"- **Precision** du repli (repli justifie par une mauvaise reponse) : {pct(len(vrai_pos), len(declenche))}",
        f"- Mauvaises reponses SANS repli (faux negatifs, cas dangereux) : {len(faux_neg)} -> "
        + (", ".join(l["id"] for l in faux_neg) or "aucun"),
    ])


def export_annotation(dial, chemin):
    entetes = ["id", "langue", "variante_de", "question", "intention_comprise", "comprehension",
               "comportement_attendu", "comportement", "reponse", "reponse_attendue",
               "annot_intention_0_1_2", "annot_justesse_0_1_2", "annot_hallucination_0_1",
               "annot_reponse_en_francais_0_1", "type_erreur", "commentaire"]
    with chemin.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(entetes)
        for l in dial:
            w.writerow([l["id"], l["langue"], l["variante_de"], l["question"], l["intention"],
                        l["comp"], l["attendu"], l["comportement"], l["texte"],
                        l["reponse_attendue"], "", "", "", "", "", ""])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fr", type=Path, required=True)
    ap.add_argument("--dialecte", type=Path, required=True)
    ap.add_argument("--passe", type=int, default=1)
    a = ap.parse_args()

    q_fr = lire_questions(DATA / "questions_fr.json")
    q_di = lire_questions(DATA / "questions_dialecte.json")
    rec_fr, ech_fr = charger(a.fr, a.passe)
    rec_di, ech_di = charger(a.dialecte, a.passe)

    fr = construire_lignes(rec_fr, q_fr, langue_fixe="fr")
    dial = construire_lignes(rec_di, q_di)
    fr_par_id = {l["id"]: l for l in fr}

    groupes = [("FR (40 q., reference)", fr)]
    groupes += [(lg, [l for l in dial if l["langue"] == lg]) for lg in LANGUES]
    groupes.append(("Dialecte (toutes)", dial))

    blocs = [
        f"# Analyse SA-34 - passe {a.passe}", "",
        f"Fichiers : FR `{a.fr.name}` ({len(fr)} reponses, {ech_fr} echecs API ignores) ; "
        f"dialecte `{a.dialecte.name}` ({len(dial)} reponses, {ech_di} echecs API ignores).",
        "",
        tableau("Resultats par groupe", groupes), "",
        detection_langue(dial), "",
        comparaison_appariee(dial, fr_par_id), "",
        repli(dial), "",
    ]
    rapport = "\n".join(blocs)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "analyse_dialecte.md").write_text(rapport, encoding="utf-8")
    export_annotation(dial, RESULTS / "dialecte_a_annoter.csv")
    print(rapport)
    print("\nEcrit : results/analyse_dialecte.md et results/dialecte_a_annoter.csv")


if __name__ == "__main__":
    main()