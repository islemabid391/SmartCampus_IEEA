import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
GROUPES = {"A_bruite_comprehensible": "repondre", "B_incomprehensible": "demander_reformulation"}
LANGUES = {"tn_arabe", "arabizi", "code_switching"}
MONTANT = r"\d+\s*(TND|dinars?)"  # un montant dans une reponse du groupe B = chiffre invente

fr = {q["id"]: q for q in json.loads((DATA / "questions_fr.json").read_text(encoding="utf-8"))}
src = json.loads((DATA / "stress_source.json").read_text(encoding="utf-8"))

ids = [s["id"] for s in src]
assert len(ids) == len(set(ids)), "ID duplique dans stress_source.json"

sortie = []
for s in src:
    sid = s["id"]
    assert s["groupe"] in GROUPES, f"{sid} : groupe invalide {s['groupe']}"
    assert s["langue"] in LANGUES, f"{sid} : langue invalide {s['langue']}"
    assert s["question"].strip(), f"{sid} : question vide"
    ctx = None
    if s.get("contexte_de"):
        assert s["contexte_de"] in fr, f"{sid} : {s['contexte_de']} introuvable dans questions_fr.json"
        ctx = fr[s["contexte_de"]]["contexte"]
    if s["groupe"].startswith("A"):
        assert ctx, f"{sid} : un cas du groupe A doit avoir un contexte_de"
        assert s.get("mots_cles"), f"{sid} : un cas du groupe A doit avoir des mots_cles"
    sortie.append(
        {
            "id": sid,
            "categorie": "stress",
            "groupe": s["groupe"],
            "langue": s["langue"],
            "difficulte": "difficile",
            "question": s["question"],
            "contexte": ctx,
            "reponse_attendue": s["reponse_attendue"],
            "comportement_attendu": GROUPES[s["groupe"]],
            "mots_cles": s.get("mots_cles", []),
            "mots_interdits": [MONTANT] if s["groupe"].startswith("B") else [],
        }
    )

(DATA / "questions_stress.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(sortie)} questions generees")
print(Counter(q["groupe"] for q in sortie))
print(Counter(q["langue"] for q in sortie))
