import csv, io, sys
from collections import Counter, defaultdict

chemin = sys.argv[1] if len(sys.argv) > 1 else r"evaluation\llm\results\dialecte_a_annoter_annote.csv"
texte = open(chemin, encoding="utf-8-sig").read()
entete = texte.splitlines()[0]
sep = ";" if entete.count(";") >= entete.count(",") else ","
rows = list(csv.DictReader(io.StringIO(texte), delimiter=sep))

I, J = "annot_intention_0_1_2", "annot_justesse_0_1_2"
H, F = "annot_hallucination_0_1", "annot_reponse_en_francais_0_1"
ann = [r for r in rows if (r.get(I) or "").strip() in ("0", "1", "2")]
print(f"Fichier : {chemin}\nSeparateur : {sep!r} | lignes : {len(rows)} | annotees : {len(ann)}\n")
if not ann:
    print("Aucune annotation lisible. Colonnes trouvees :", list(rows[0].keys()))
    sys.exit()

def pct(n, d):
    return "n/a" if d == 0 else f"{100 * n / d:.0f}% ({n}/{d})"

g = defaultdict(list)
for r in ann:
    g[r["langue"]].append(r)
    g["TOTAL"].append(r)
print("| Langue | N | Intention correcte (2) | Intention fausse (0) | Reponse juste (2) | Hallucination | Reponse en francais |")
print("|---|---|---|---|---|---|---|")
for lg in ["tn_arabe", "arabizi", "code_switching", "TOTAL"]:
    x = g.get(lg, [])
    n = len(x)
    print(f"| {lg} | {n} | {pct(sum(r[I].strip()=='2' for r in x), n)} | {pct(sum(r[I].strip()=='0' for r in x), n)} | "
          f"{pct(sum((r.get(J) or '').strip()=='2' for r in x), n)} | {pct(sum((r.get(H) or '').strip()=='1' for r in x), n)} | "
          f"{pct(sum((r.get(F) or '').strip()=='1' for r in x), n)} |")
err = Counter((r.get("type_erreur") or "").strip() for r in ann if (r.get("type_erreur") or "").strip())
print("\nTaxonomie des erreurs :", dict(err) or "aucune renseignee")
sil = [r for r in ann if r[I].strip() == "0" and r.get("comprehension") == "ok"]
print(f"Erreurs d'intention avec comprehension='ok' (silencieuses) : {len(sil)} -> {', '.join(r['id'] for r in sil) or 'aucune'}")
hal = [r["id"] for r in ann if (r.get(H) or "").strip() == "1"]
print(f"Hallucinations signalees : {len(hal)} -> {', '.join(hal) or 'aucune'}")
print("\nAttention : echantillon reduit, a presenter comme un ordre de grandeur.")