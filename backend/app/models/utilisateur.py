from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Numeric,
    String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

TZ = DateTime(timezone=True)


class Utilisateur(Base):
    __tablename__ = "utilisateur"
    __table_args__ = (
        CheckConstraint("role IN ('candidat','responsable')", name="role"),
        CheckConstraint(
            "role <> 'responsable' OR etablissement_id IS NOT NULL",
            name="responsable_etablissement",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    etablissement_id: Mapped[int | None] = mapped_column(
        ForeignKey("etablissement.id", ondelete="RESTRICT"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    telephone: Mapped[str | None] = mapped_column(String(30))
    consentement_rgpd: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    date_consentement: Mapped[datetime | None] = mapped_column(TZ)
    actif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    date_creation: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class SessionVisiteur(Base):
    __tablename__ = "session_visiteur"
    __table_args__ = (
        CheckConstraint("statut IN ('active','expiree','rattachee')", name="statut"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int | None] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="SET NULL"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    consentement_rattachement: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    statut: Mapped[str] = mapped_column(String(20), server_default="active")
    date_creation: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    date_expiration: Mapped[datetime] = mapped_column(TZ, index=True)


class Conversation(Base):
    __tablename__ = "conversation"
    __table_args__ = (
        CheckConstraint(
            "session_id IS NOT NULL OR utilisateur_id IS NOT NULL",
            name="proprietaire",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("session_visiteur.id", ondelete="CASCADE"), index=True
    )
    utilisateur_id: Mapped[int | None] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), index=True
    )
    langue_detectee: Mapped[str | None] = mapped_column(String(20))
    date_creation: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    date_cloture: Mapped[datetime | None] = mapped_column(TZ)
    # Informations utiles retenues sur le visiteur (niveau, intérêts, objectif...)
    memoire: Mapped[dict | None] = mapped_column(JSONB)


class Message(Base):
    __tablename__ = "message"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant','system')", name="role"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversation.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    contenu: Mapped[str] = mapped_column(Text)
    langue: Mapped[str | None] = mapped_column(String(20))
    date_creation: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    date_expiration: Mapped[datetime | None] = mapped_column(TZ, index=True)


class ProfilAcademique(Base):
    __tablename__ = "profil_academique"
    __table_args__ = (
        CheckConstraint("moyenne IS NULL OR (moyenne >= 0 AND moyenne <= 20)", name="moyenne"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), unique=True
    )
    niveau_scolaire: Mapped[str | None] = mapped_column(String(100))
    section_bac: Mapped[str | None] = mapped_column(String(100))
    moyenne: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    matieres_preferees: Mapped[list | None] = mapped_column(JSONB)
    centres_interet: Mapped[list | None] = mapped_column(JSONB)
    objectif_professionnel: Mapped[str | None] = mapped_column(Text)
    contraintes: Mapped[str | None] = mapped_column(Text)
    date_maj: Mapped[datetime] = mapped_column(TZ, server_default=func.now(), onupdate=func.now())


class Preinscription(Base):
    __tablename__ = "preinscription"
    __table_args__ = (
        CheckConstraint(
            "statut IN ('brouillon','soumise','en_cours','acceptee','refusee')",
            name="statut",
        ),
        UniqueConstraint("utilisateur_id", "formation_id", name="utilisateur_formation"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), index=True
    )
    formation_id: Mapped[int] = mapped_column(
        ForeignKey("formation.id", ondelete="RESTRICT"), index=True
    )
    statut: Mapped[str] = mapped_column(String(20), server_default="brouillon")
    consentement: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    date_creation: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class DemandeEquivalence(Base):
    __tablename__ = "demande_equivalence"
    __table_args__ = (
        CheckConstraint(
            "statut IN ('en_attente','en_cours','acceptee','refusee')",
            name="statut",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), index=True
    )
    formation_id: Mapped[int] = mapped_column(
        ForeignKey("formation.id", ondelete="RESTRICT"), index=True
    )
    diplome_origine: Mapped[str] = mapped_column(String(200))
    statut: Mapped[str] = mapped_column(String(20), server_default="en_attente")
    decision: Mapped[str | None] = mapped_column(Text)
    date_creation: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class RendezVous(Base):
    __tablename__ = "rendez_vous"
    __table_args__ = (
        CheckConstraint(
            "statut IN ('propose','confirme','annule','realise')",
            name="statut",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    preinscription_id: Mapped[int] = mapped_column(
        ForeignKey("preinscription.id", ondelete="CASCADE"), index=True
    )
    responsable_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="RESTRICT"), index=True
    )
    date_heure: Mapped[datetime] = mapped_column(TZ)
    statut: Mapped[str] = mapped_column(String(20), server_default="propose")
    lieu_ou_lien: Mapped[str | None] = mapped_column(String(255))


class Entretien(Base):
    __tablename__ = "entretien"
    __table_args__ = (
        CheckConstraint(
            "resultat IN ('favorable','defavorable','complement')",
            name="resultat",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    rendez_vous_id: Mapped[int] = mapped_column(
        ForeignKey("rendez_vous.id", ondelete="CASCADE"), unique=True
    )
    resultat: Mapped[str] = mapped_column(String(20))
    observations: Mapped[str | None] = mapped_column(Text)
    date_creation: Mapped[datetime] = mapped_column(TZ, server_default=func.now())