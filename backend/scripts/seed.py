"""Alimente la base avec les données du catalogue (réelles NAPU ou démo) et les comptes démo (idempotent).

Usage (depuis le dossier backend/) :
    python -m scripts.seed --source real
    python -m scripts.seed --source demo

Variable optionnelle : SEED_DEMO_PASSWORD (mot de passe des comptes de démo).
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import bcrypt
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.catalogue import (
    ConditionAdmission, Etablissement, Formation, Matiere, Passerelle,
    Programme, ProgrammeMatiere, Specialite, Tarif,
)
from app.models.utilisateur import Utilisateur

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
REAL_CATALOGUE_PATH = SEED_DIR / "real" / "catalogue_reel.json"
DEFAULT_DEMO_PASSWORD = "DemoSmartCampus2026!"


def load(name: str):
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def to_date(value):
    return date.fromisoformat(value) if value else None


def to_decimal(value):
    return None if value is None else Decimal(str(value))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def upsert(db, model, lookup: dict, values: dict | None = None):
    """Retrouve la ligne par sa clé naturelle ; la crée ou la met à jour."""
    values = values or {}
    obj = db.execute(select(model).filter_by(**lookup)).scalar_one_or_none()
    if obj is None:
        obj = model(**lookup, **values)
        db.add(obj)
    else:
        for key, val in values.items():
            setattr(obj, key, val)
    db.flush()
    return obj


def seed_matieres_from_list(db, items: list[dict]):
    for m in items:
        upsert(
            db, Matiere, {"code": m["code"]},
            {"nom": m["nom"], "description": m.get("description")},
        )


def seed_matieres(db, source: str, data: dict):
    if "matieres" in data and isinstance(data["matieres"], list):
        seed_matieres_from_list(db, data["matieres"])
    elif (SEED_DIR / "matieres.json").exists():
        seed_matieres_from_list(db, load("matieres.json"))


def seed_catalogue(db, data: dict):
    etablissements = {}
    for e in data["etablissements"]:
        etablissements[e["code"]] = upsert(
            db, Etablissement, {"code": e["code"]},
            {"nom": e["nom"], "description": e.get("description")},
        )

    matieres = {m.code: m for m in db.scalars(select(Matiere))}

    for f in data["formations"]:
        formation = upsert(db, Formation, {"code": f["code"]}, {
            "etablissement_id": etablissements[f["etablissement"]].id,
            "nom": f["nom"], "cycle": f["cycle"], "duree_annees": f["duree_annees"],
            "modalites": f.get("modalites"), "langue": f.get("langue"),
            "description": f.get("description"), "debouches": f.get("debouches"),
            "statut_publication": f["statut_publication"],
            "source_url": f.get("source_url"),
            "date_collecte": to_datetime(f.get("date_collecte")),
        })

        specialites = {}
        for s in f.get("specialites", []):
            specialites[s["nom"]] = upsert(
                db, Specialite, {"formation_id": formation.id, "nom": s["nom"]},
                {"description": s.get("description")},
            )

        for p in f.get("programmes", []):
            spec = specialites[p["specialite"]] if p.get("specialite") else None
            programme = upsert(
                db, Programme, {"formation_id": formation.id, "nom": p["nom"]},
                {"specialite_id": spec.id if spec else None,
                 "annee_niveau": p["annee_niveau"], "description": p.get("description")},
            )
            for pm in p.get("matieres", []):
                matiere = matieres.get(pm["code"])
                if matiere is None:
                    raise ValueError(f"Matière inconnue dans le seed : {pm['code']}")
                upsert(
                    db, ProgrammeMatiere,
                    {"programme_id": programme.id, "matiere_id": matiere.id},
                    {"semestre": pm.get("semestre"),
                     "credits": to_decimal(pm.get("credits")),
                     "coefficient": to_decimal(pm.get("coefficient"))},
                )

        for c in f.get("conditions", []):
            upsert(
                db, ConditionAdmission,
                {"formation_id": formation.id, "type": c["type"], "description": c["description"]},
                {"valeur_min": to_decimal(c.get("valeur_min")),
                 "niveau_requis": c.get("niveau_requis"),
                 "statut_publication": c.get("statut_publication", "publie"),
                 "valide_du": to_date(c.get("valide_du")),
                 "valide_au": to_date(c.get("valide_au"))},
            )

        for t in f.get("tarifs", []):
            devise = t.get("devise", "TND")
            upsert(
                db, Tarif,
                {"formation_id": formation.id, "devise": devise, "valide_du": to_date(t.get("valide_du"))},
                {"frais_scolarite": to_decimal(t["frais_scolarite"]),
                 "modalites_paiement": t.get("modalites_paiement"),
                 "statut_publication": t.get("statut_publication", "publie"),
                 "valide_au": to_date(t.get("valide_au"))},
            )

        for pg in f.get("passerelles", []):
            upsert(
                db, Passerelle,
                {"formation_id": formation.id, "formation_cible": pg["formation_cible"]},
                {"conditions": pg.get("conditions"),
                 "statut_publication": pg.get("statut_publication", "publie")},
            )


def seed_utilisateurs(db):
    if not (SEED_DIR / "users_demo.json").exists():
        return
    password = os.environ.get("SEED_DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)
    etablissements = {e.code: e for e in db.scalars(select(Etablissement))}

    for u in load("users_demo.json"):
        etab = etablissements[u["etablissement"]] if u.get("etablissement") else None
        values = {
            "etablissement_id": etab.id if etab else None,
            "role": u["role"], "nom": u["nom"], "prenom": u["prenom"],
            "telephone": u.get("telephone"), "actif": True,
            "consentement_rgpd": u.get("consentement_rgpd", False),
        }
        existing = db.execute(
            select(Utilisateur).where(Utilisateur.email == u["email"])
        ).scalar_one_or_none()

        if existing is None:
            if values["consentement_rgpd"]:
                values["date_consentement"] = datetime.now(timezone.utc)
            db.add(Utilisateur(email=u["email"],
                               mot_de_passe_hash=hash_password(password), **values))
        else:
            for key, val in values.items():
                setattr(existing, key, val)
        db.flush()


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=["real", "demo"], default="demo")
    return ap.parse_args()

def to_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)

def main():
    args = parse_args()
    env = getattr(settings, "APP_ENV", "development")
    if env == "production":
        sys.exit("Refus : le seed est interdit en production.")

    if args.source == "real":
        if not REAL_CATALOGUE_PATH.exists():
            sys.exit(f"Fichier introuvable : {REAL_CATALOGUE_PATH}")
        data = json.loads(REAL_CATALOGUE_PATH.read_text(encoding="utf-8"))
        label = "données réelles NAPU (catalogue_reel.json)"
    else:
        data = load("catalogue.json")
        label = "données de démonstration (catalogue.json)"

    with SessionLocal() as db:
        try:
            seed_matieres(db, args.source, data)
            seed_catalogue(db, data)
            seed_utilisateurs(db)
            db.commit()
        except Exception:
            db.rollback()
            raise

        print(f"Seed terminé ({label}) :")
        for model in (Etablissement, Formation, Specialite, Programme, Matiere,
                      ProgrammeMatiere, ConditionAdmission, Tarif, Passerelle, Utilisateur):
            n = db.scalar(select(func.count()).select_from(model))
            print(f"  {model.__tablename__:<20} {n}")


if __name__ == "__main__":
    main()