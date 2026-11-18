
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mixins import TimestampMixin
from app.db.session import Base


STATUT = "statut_publication IN ('brouillon', 'publie', 'archive')"


class Etablissement(Base):
    __tablename__ = "etablissement"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    nom: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)


class Formation(TimestampMixin, Base):
    __tablename__ = "formation"

    __table_args__ = (
        CheckConstraint(
            "cycle IN ('licence', 'prepa', 'ingenieur', 'autre)",
            name="cycle",
        ),
        CheckConstraint(STATUT, name="statut_publication"),
        CheckConstraint(
            "duree_annees > 0",
            name="duree_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    etablissement_id: Mapped[int] = mapped_column(
        ForeignKey("etablissement.id", ondelete="RESTRICT"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(30), unique=True)
    nom: Mapped[str] = mapped_column(String(200))
    cycle: Mapped[str] = mapped_column(String(20))
    duree_annees: Mapped[int]
    modalites: Mapped[str | None] = mapped_column(String(100))
    langue: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    debouches: Mapped[str | None] = mapped_column(Text)
    statut_publication: Mapped[str] = mapped_column(
        String(20),
        server_default="brouillon",
    )


class Specialite(Base):
    __tablename__ = "specialite"

    id: Mapped[int] = mapped_column(primary_key=True)
    formation_id: Mapped[int] = mapped_column(
        ForeignKey("formation.id", ondelete="CASCADE"),
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)


class Programme(Base):
    __tablename__ = "programme"

    id: Mapped[int] = mapped_column(primary_key=True)
    formation_id: Mapped[int] = mapped_column(
        ForeignKey("formation.id", ondelete="CASCADE"),
        index=True,
    )
    specialite_id: Mapped[int | None] = mapped_column(
        ForeignKey("specialite.id", ondelete="SET NULL"),
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(200))
    annee_niveau: Mapped[int]
    description: Mapped[str | None] = mapped_column(Text)


class Matiere(Base):
    __tablename__ = "matiere"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    nom: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)


class ProgrammeMatiere(Base):
    __tablename__ = "programme_matiere"

    programme_id: Mapped[int] = mapped_column(
        ForeignKey("programme.id", ondelete="CASCADE"),
        primary_key=True,
    )
    matiere_id: Mapped[int] = mapped_column(
        ForeignKey("matiere.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    semestre: Mapped[int | None]
    credits: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    coefficient: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))


class ConditionAdmission(Base):
    __tablename__ = "condition_admission"

    __table_args__ = (
        CheckConstraint(
            "type IN ('diplome', 'moyenne', 'concours', 'dossier')",
            name="type",
        ),
        CheckConstraint(STATUT, name="statut_publication"),
        CheckConstraint(
            "valide_au IS NULL OR valide_du IS NULL OR valide_au >= valide_du",
            name="periode",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    formation_id: Mapped[int] = mapped_column(
        ForeignKey("formation.id", ondelete="CASCADE"),
        index=True,
    )
    type: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    valeur_min: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    niveau_requis: Mapped[str | None] = mapped_column(String(100))
    statut_publication: Mapped[str] = mapped_column(
        String(20),
        server_default="brouillon",
    )
    valide_du: Mapped[date | None] = mapped_column(Date)
    valide_au: Mapped[date | None] = mapped_column(Date)


class Tarif(Base):
    __tablename__ = "tarif"

    __table_args__ = (
        CheckConstraint(
            "frais_scolarite >= 0",
            name="frais_positifs",
        ),
        CheckConstraint(STATUT, name="statut_publication"),
        CheckConstraint(
            "valide_au IS NULL OR valide_du IS NULL OR valide_au >= valide_du",
            name="periode",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    formation_id: Mapped[int] = mapped_column(
        ForeignKey("formation.id", ondelete="CASCADE"),
        index=True,
    )

    frais_scolarite: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
    )

    devise: Mapped[str] = mapped_column(
        String(3),
        server_default="TND",
    )

    modalites_paiement: Mapped[str | None] = mapped_column(Text)

    statut_publication: Mapped[str] = mapped_column(
        String(20),
        server_default="brouillon",
    )

    valide_du: Mapped[date | None] = mapped_column(Date)

    valide_au: Mapped[date | None] = mapped_column(Date)


class Passerelle(Base):
    __tablename__ = "passerelle"

    __table_args__ = (
        CheckConstraint(STATUT, name="statut_publication"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    formation_id: Mapped[int] = mapped_column(
        ForeignKey("formation.id", ondelete="CASCADE"),
        index=True,
    )
    formation_cible: Mapped[str] = mapped_column(String(200))
    conditions: Mapped[str | None] = mapped_column(Text)
    statut_publication: Mapped[str] = mapped_column(
        String(20),
        server_default="brouillon",
    )
