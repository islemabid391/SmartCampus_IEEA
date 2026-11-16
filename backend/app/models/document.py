from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

TZ = DateTime(timezone=True)


class Document(Base):
    __tablename__ = "document"
    __table_args__ = (
        CheckConstraint(
            "type_document IN ('brochure','faq','reglement','tarifs','autre')",
            name="type_document",
        ),
        CheckConstraint("statut IN ('actif','archive','supprime')", name="statut"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    etablissement_id: Mapped[int] = mapped_column(
        ForeignKey("etablissement.id", ondelete="RESTRICT"), index=True
    )
    formation_id: Mapped[int | None] = mapped_column(
        ForeignKey("formation.id", ondelete="SET NULL"), index=True
    )
    titre: Mapped[str] = mapped_column(String(255))
    type_document: Mapped[str] = mapped_column(String(30))
    langue: Mapped[str | None] = mapped_column(String(20))
    statut: Mapped[str] = mapped_column(String(20), server_default="actif")
    date_creation: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    date_maj: Mapped[datetime] = mapped_column(TZ, server_default=func.now(), onupdate=func.now())


class VersionDocument(Base):
    __tablename__ = "version_document"
    __table_args__ = (
        UniqueConstraint("document_id", "numero_version", name="document_numero"),
        CheckConstraint("numero_version >= 1", name="numero_positif"),
        CheckConstraint("taille_octets >= 0", name="taille_positive"),
        # une seule version courante par document
        Index(
            "uq_version_courante", "document_id",
            unique=True, postgresql_where=text("est_courante"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), index=True
    )
    importee_par_id: Mapped[int | None] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="SET NULL"), index=True
    )
    numero_version: Mapped[int] = mapped_column(Integer)
    nom_fichier: Mapped[str] = mapped_column(String(255))
    url_fichier: Mapped[str] = mapped_column(String(500))
    format: Mapped[str] = mapped_column(String(20))
    taille_octets: Mapped[int] = mapped_column(BigInteger)
    empreinte: Mapped[str] = mapped_column(String(64))
    est_courante: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    commentaire: Mapped[str | None] = mapped_column(Text)
    date_import: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class ChunkDocument(Base):
    """Passage de texte d'une version. La colonne `vecteur` (pgvector) sera
    ajoutée par une migration dédiée quand le modèle d'embedding sera choisi."""
    __tablename__ = "chunk_document"
    __table_args__ = (
        UniqueConstraint("version_id", "ordre", name="version_ordre"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("version_document.id", ondelete="CASCADE"), index=True
    )
    ordre: Mapped[int] = mapped_column(Integer)
    numero_page: Mapped[int | None] = mapped_column(Integer)
    texte: Mapped[str] = mapped_column(Text)


class TacheSynchronisation(Base):
    __tablename__ = "tache_synchronisation"
    __table_args__ = (
        CheckConstraint(
            "type_operation IN ('ajout','modification','suppression')",
            name="type_operation",
        ),
        CheckConstraint(
            "statut IN ('en_attente','en_cours','termine','echec')",
            name="statut",
        ),
        CheckConstraint("nb_chunks >= 0 AND nb_tentatives >= 0", name="compteurs_positifs"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), index=True
    )
    version_id: Mapped[int | None] = mapped_column(
        ForeignKey("version_document.id", ondelete="SET NULL"), index=True
    )
    type_operation: Mapped[str] = mapped_column(String(20))
    statut: Mapped[str] = mapped_column(String(20), server_default="en_attente")
    nb_chunks: Mapped[int] = mapped_column(Integer, server_default="0")
    nb_tentatives: Mapped[int] = mapped_column(Integer, server_default="0")
    message_erreur: Mapped[str | None] = mapped_column(Text)
    date_debut: Mapped[datetime | None] = mapped_column(TZ)
    date_fin: Mapped[datetime | None] = mapped_column(TZ)