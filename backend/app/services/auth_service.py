from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.roles import Role
from app.core.security import hash_password, verify_password
from app.models.utilisateur import Utilisateur
from app.schemas.auth import RegisterRequest

# Hash factice : on fait toujours un calcul bcrypt, même si l'email n'existe pas
_FAUX_HASH = hash_password("mot-de-passe-factice")


def get_user_par_email(db: Session, email: str) -> Utilisateur | None:
    return db.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == email.lower()))


def creer_candidat(db: Session, data: RegisterRequest) -> Utilisateur:
    """Crée un compte candidat. Les responsables ne s'inscrivent jamais seuls."""
    if not data.consentement_rgpd:
        raise ValueError("Le consentement RGPD est obligatoire.")
    if get_user_par_email(db, data.email) is not None:
        raise LookupError("Un compte existe déjà avec cet email.")
    user = Utilisateur(
        email=data.email.lower(),
        mot_de_passe_hash=hash_password(data.mot_de_passe),
        role=Role.CANDIDAT,
        nom=data.nom.strip(),
        prenom=data.prenom.strip(),
        telephone=data.telephone,
        consentement_rgpd=True,
        date_consentement=datetime.now(timezone.utc),
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user


def authentifier(db: Session, email: str, mot_de_passe: str) -> Utilisateur | None:
    user = get_user_par_email(db, email)
    hash_a_verifier = user.mot_de_passe_hash if user else _FAUX_HASH
    ok = verify_password(mot_de_passe, hash_a_verifier)
    if user is None or not ok or not user.actif:
        return None
    return user