#!/usr/bin/env python3
"""SA-18 - De l'extraction brute au catalogue validé (même format que seed/catalogue.json).

    python -m scripts.scrape.build_catalogue init     # crée/complète seed/real/curation.yaml
    (VALIDATION HUMAINE : relire curation.yaml, corriger, passer `valider: true`)
    python -m scripts.scrape.build_catalogue build    # produit seed/real/catalogue_reel.json

Seules les entrées marquées `valider: true` passent dans le catalogue : rien n'est importé sans relecture.
"""
import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import yaml

from scripts.scrape.scrape import EXTRACTED, REAL, load_sources, slugify

CURATION = REAL / "curation.yaml"
OUT = REAL / "catalogue_reel.json"
CYCLES = {"licence", "prepa", "ingenieur", "autre"}
STATUTS = {"brouillon", "publie", "archive"}
HEADER = """# SA-18 - Curation des formations collectées. À RELIRE ET CORRIGER À LA MAIN.
# - Mettez `valider: true` uniquement après avoir vérifié la page source (url) : seules ces entrées sont importées.
# - cycle : licence | prepa | ingenieur | autre (mastère, architecture, formation continue...)
# - parcours_de : code de la formation parente si la page est un PARCOURS/spécialité d'une autre formation.
# - Champs facultatifs de correction : nom, duree_annees, description, debouches, acces, frais_tnd, frais_periode,
#   tarif_valide_du, tarif_valide_au, langue, modalites, modules (false = ne pas importer les modules).
# - formations_virtuelles : formations sans page propre (ex. un menu « Licence en informatique » regroupant des parcours).
"""


def guess_cycle(url, titre):
    t = f"{url} {titre}".lower()
    if "prepa" in t or "préparatoire" in t:
        return "prepa"
    if "ingenieur" in t or "génie" in t or "genie" in t:
        return "ingenieur"
    if "licence" in t:
        return "licence"
    return "autre"


def matiere_code(nom, registry):
    base = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().upper()
    code = re.sub(r"[^A-Z0-9]+", "", base)[:20] or "MATIERE"
    while code in registry and registry[code] != nom:
        code = (code[:17] + "X" + str(len(registry) % 100))[:20]
    registry[code] = nom
    return code


def first_int(text, default):
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else default


def cmd_init(args):
    extracted = json.loads(EXTRACTED.read_text(encoding="utf-8"))
    cur = yaml.safe_load(CURATION.read_text(encoding="utf-8")) if CURATION.exists() else {}
    pages = cur.get("pages", [])
    known = {p["url"] for p in pages}
    added = 0
    for e in extracted:
        if e["type"] != "formation" or e["url"] in known:
            continue
        pages.append({
            "url": e["url"], "valider": False, "etablissement": e["etab"],
            "code": f"{e['etab']}-{slugify(e['titre']).upper()[:24]}", "nom": e["titre"],
            "cycle": guess_cycle(e["url"], e["titre"]), "parcours_de": None,
            "duree_annees": e["duree_annees"], "notes": " | ".join(e["alertes"]) or None,
        })
        added += 1
    virt = cur.get("formations_virtuelles") or [{
        "valider": False, "etablissement": "IIT", "code": "IIT-LIC-INFO", "nom": "Licence en informatique",
        "cycle": "licence", "duree_annees": 3, "description": "", "source_url": "https://iit.tn/licences/"}]
    CURATION.write_text(HEADER + yaml.safe_dump({"pages": pages, "formations_virtuelles": virt},
                                               allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"{added} entrée(s) ajoutée(s) -> {CURATION}\nRelisez-la, corrigez, puis mettez valider: true.")


def make_formation(p, e, today):
    f = {
        "etablissement": p["etablissement"], "code": p["code"], "nom": p.get("nom") or e["titre"],
        "cycle": p["cycle"], "duree_annees": p.get("duree_annees") or e.get("duree_annees"),
        "modalites": p.get("modalites"), "langue": p.get("langue"),
        "description": p.get("description") or e.get("intro"), "debouches": p.get("debouches") or e.get("debouches"),
        "statut_publication": p.get("statut_publication", "publie"),
        "source_url": p["url"], "date_collecte": e.get("date_collecte", today),
        "specialites": [], "programmes": [], "conditions": [], "tarifs": [], "passerelles": [],
    }
    acces = p.get("acces") or e.get("acces")
    if acces:
        f["conditions"].append({"type": "diplome", "description": acces, "niveau_requis": None,
                                "statut_publication": "publie"})
    fr = e.get("frais") or {}
    tnd = p.get("frais_tnd") or fr.get("tnd")
    if tnd:
        periode = p.get("frais_periode") or "période couverte non précisée sur le site"
        eur = f" (soit {fr['eur']:.0f} €)" if fr.get("eur") else ""
        f["tarifs"].append({
            "frais_scolarite": tnd, "devise": "TND",
            "modalites_paiement": f"Montant affiché sur le site : {fr.get('brut', tnd)}{eur} ; {periode}.",
            "statut_publication": "publie", "valide_du": p.get("tarif_valide_du"), "valide_au": p.get("tarif_valide_au")})
    return f


def add_programmes(f, e, p, registry, matieres, specialite=None):
    if p.get("modules") is False:
        return
    for i, g in enumerate(e.get("groupes_modules", []), 1):
        if INVALID_SECTION_RE.match(g["nom"].strip()):
            continue
        mods = []
        for nom in g["modules"]:
            if not is_valid_module_name(nom):
                continue
            code = matiere_code(nom, registry)
            matieres[code] = nom
            # Déduire le semestre si le titre de section contient "Semestre X"
            sem_m = re.search(r"semestre\s*(\d+)", g["nom"], re.I)
            sem = int(sem_m.group(1)) if sem_m else None
            mods.append({"code": code, "semestre": sem, "credits": None, "coefficient": None})
        if not mods:
            continue
        label = " - ".join(x for x in (f["nom"], specialite, g["nom"]) if x)
        # Calculer annee_niveau à partir du semestre (S1/S2 -> 1, S3/S4 -> 2, S5/S6 -> 3)
        sem_m = re.search(r"semestre\s*(\d+)", g["nom"], re.I)
        annee = (int(sem_m.group(1)) + 1) // 2 if sem_m else first_int(g["nom"], i)
        prog = {"nom": label, "annee_niveau": annee, "matieres": mods}
        if specialite:
            prog["specialite"] = specialite
        f["programmes"].append(prog)

INVALID_SECTION_RE = re.compile(
    r"^(employab|objectifs?|programmes?$|perspectives|débouchés|admission|brochure|actualités)",
    re.I,
)
INVALID_MODULE_RE = re.compile(
    r"^(\d+\s*%|1\s*er\s*ann|2\s*[ée]me\s*ann|3\s*[ée]me\s*ann|actualit[ée]s|admission|brochure|"
    r"espace\s+[ée]tudiant|vid[ée]oth[ée]que|visite\s+virtuelle|international|project$|"
    r"chef\s+d.entreprise|chef\s+des\s+op[ée]rations|consultant\s+en\s+gestion|gestionnaire|"
    r"op[ée]rateur\s+ind[ée]pendant|perspectives\s+professionnelles|voici\s+quelques)",
    re.I,
)


def is_valid_module_name(nom: str) -> bool:
    nom = nom.strip()
    if len(nom) < 3 or len(nom) > 75 or nom.endswith(":"):
        return False
    return not bool(INVALID_MODULE_RE.match(nom))

def validate(cat):
    errors, codes = [], set()
    etabs = {e["code"] for e in cat["etablissements"]}
    mats = {m["code"] for m in cat["matieres"]}
    for f in cat["formations"]:
        c = f["code"]
        if c in codes:
            errors.append(f"{c} : code en double")
        codes.add(c)
        if f["etablissement"] not in etabs:
            errors.append(f"{c} : établissement inconnu {f['etablissement']!r}")
        if f["cycle"] not in CYCLES:
            errors.append(f"{c} : cycle invalide {f['cycle']!r}")
        if not isinstance(f["duree_annees"], int) or f["duree_annees"] <= 0:
            errors.append(f"{c} : duree_annees manquante ou invalide (à renseigner dans curation.yaml)")
        if f["statut_publication"] not in STATUTS:
            errors.append(f"{c} : statut_publication invalide")
        specs = {s["nom"] for s in f["specialites"]}
        for pr in f["programmes"]:
            if pr.get("specialite") and pr["specialite"] not in specs:
                errors.append(f"{c} : spécialité inconnue {pr['specialite']!r}")
            for m in pr["matieres"]:
                if m["code"] not in mats:
                    errors.append(f"{c} : matière inconnue {m['code']}")
        for t in f["tarifs"]:
            if t["frais_scolarite"] < 0:
                errors.append(f"{c} : tarif négatif")
            if t.get("valide_du") and t.get("valide_au") and str(t["valide_au"]) < str(t["valide_du"]):
                errors.append(f"{c} : période de tarif incohérente")
    return errors


def cmd_build(args):
    if not CURATION.exists():
        sys.exit("curation.yaml introuvable : lancez d'abord `init`.")
    cur = yaml.safe_load(CURATION.read_text(encoding="utf-8"))
    extracted = {e["url"]: e for e in json.loads(EXTRACTED.read_text(encoding="utf-8"))}
    sources = load_sources(args.sources)["etablissements"]
    today = date.today().isoformat()
    registry, matieres, formations = {}, {}, {}

    for v in cur.get("formations_virtuelles") or []:
        if v.get("valider"):
            f = make_formation({**v, "url": v.get("source_url", "")}, {"titre": v["nom"], "date_collecte": today}, today)
            f["source_url"] = v.get("source_url")
            formations[f["code"]] = f
    valid = [p for p in cur["pages"] if p.get("valider")]
    for p in (x for x in valid if not x.get("parcours_de")):
        e = extracted.get(p["url"])
        if e is None:
            sys.exit(f"Page absente de extracted.json : {p['url']} (relancez crawl puis extract).")
        f = make_formation(p, e, today)
        add_programmes(f, e, p, registry, matieres)
        formations[f["code"]] = f
    for p in (x for x in valid if x.get("parcours_de")):
        e = extracted[p["url"]]
        parent = formations.get(p["parcours_de"])
        if parent is None:
            sys.exit(f"{p['code']} : formation parente {p['parcours_de']!r} absente ou non validée.")
        nom = p.get("nom") or e["titre"]
        parent["specialites"].append({"nom": nom, "description": p.get("description") or e.get("intro")})
        add_programmes(parent, e, p, registry, matieres, specialite=nom)

    used = {f["etablissement"] for f in formations.values()}
    cat = {
        "meta": {"genere_le": today, "sources": sorted({f["source_url"] for f in formations.values() if f["source_url"]}),
                 "avertissement": "Données collectées sur les sites publics puis validées manuellement."},
        "etablissements": [{"code": c, "nom": sources[c]["nom"],
                            "description": f"Données issues du site officiel ({sources[c]['base_url']})."}
                           for c in sources if c in used],
        "matieres": [{"code": c, "nom": n, "description": None} for c, n in sorted(matieres.items())],
        "formations": list(formations.values()),
    }
    errors = validate(cat)
    if errors:
        print("Erreurs de validation :")
        for er in errors:
            print("  -", er)
        sys.exit(1)
    OUT.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(cat['formations'])} formation(s), {sum(len(f['specialites']) for f in cat['formations'])} spécialité(s), "
          f"{sum(len(f['programmes']) for f in cat['formations'])} programme(s), {len(cat['matieres'])} matière(s), "
          f"{sum(len(f['tarifs']) for f in cat['formations'])} tarif(s) -> {OUT}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default=None)
    ap.add_argument("cmd", choices=["init", "build"])
    args = ap.parse_args()
    {"init": cmd_init, "build": cmd_build}[args.cmd](args)


if __name__ == "__main__":
    main()
