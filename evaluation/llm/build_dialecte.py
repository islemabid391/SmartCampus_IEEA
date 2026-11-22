import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

fr = {q["id"]: q for q in json.loads((DATA / "questions_fr.json").read_text(encoding="utf-8"))}
src = json.loads((DATA / "dialecte_source.json").read_text(encoding="utf-8"))

ids = [s["id"] for s in src]
assert len(ids) == len(set(ids)), "ID dupliqué dans dialecte_source.json"

sortie = []
for s in src:
    assert s["variante_de"] in fr, f"{s['variante_de']} introuvable dans questions_fr.json"
    assert s["langue"] in {"tn_arabe", "arabizi", "code_switching"}, f"langue invalide : {s['langue']}"
    q = dict(fr[s["variante_de"]])          # copie contexte, mots_cles, etc.
    q.update(id=s["id"], langue=s["langue"], variante_de=s["variante_de"], question=s["question"])
    sortie.append(q)

(DATA / "questions_dialecte.json").write_text(
    json.dumps(sortie, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"{len(sortie)} questions générées")
print(Counter(q["langue"] for q in sortie))