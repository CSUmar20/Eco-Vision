import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

JURISDICTION_TYPES = (
    "state",
    "county",
    "municipality",
    "waste_provider",
)

DISPOSAL_STATUSES = (
    "accepted_curbside",
    "not_accepted_curbside",
    "drop_off_required",
    "unavailable_or_unclear",
)

GENERAL_DISPOSAL_ACTIONS = (
    "reuse_or_donate",
    "recycle",
    "compost",
    "special_drop_off",
    "trash",
    "check_locally",
)


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        UniqueConstraint("key", name="uq_materials_key"),
        Index("ix_materials_display_name", "display_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    aliases: Mapped[list["MaterialAlias"]] = relationship(
        back_populates="material",
        cascade="all, delete-orphan",
        order_by="MaterialAlias.normalized_alias",
    )
    general_disposal_rules: Mapped[list["GeneralDisposalRule"]] = relationship(
        back_populates="material",
        cascade="all, delete-orphan",
        order_by="GeneralDisposalRule.country_code",
    )


class MaterialAlias(Base):
    __tablename__ = "material_aliases"
    __table_args__ = (
        UniqueConstraint(
            "normalized_alias",
            name="uq_material_aliases_normalized_alias",
        ),
        Index("ix_material_aliases_material_id", "material_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    material: Mapped[Material] = relationship(back_populates="aliases")


class GeneralDisposalRule(Base):
    __tablename__ = "general_disposal_rules"
    __table_args__ = (
        CheckConstraint(
            f"action IN {GENERAL_DISPOSAL_ACTIONS}",
            name="ck_general_disposal_rules_action",
        ),
        UniqueConstraint(
            "material_id",
            "country_code",
            name="uq_general_disposal_rules_material_country",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    preparation: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    material: Mapped[Material] = relationship(back_populates="general_disposal_rules")


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"
    __table_args__ = (
        CheckConstraint(
            f"jurisdiction_type IN {JURISDICTION_TYPES}",
            name="ck_jurisdictions_type",
        ),
        UniqueConstraint("slug", name="uq_jurisdictions_slug"),
        Index("ix_jurisdictions_state_code", "state_code"),
        Index("ix_jurisdictions_display_name", "display_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    state_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    county_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    waste_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id", ondelete="SET NULL"),
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    postal_codes: Mapped[list["JurisdictionPostalCode"]] = relationship(
        back_populates="jurisdiction",
        cascade="all, delete-orphan",
        order_by="JurisdictionPostalCode.postal_code",
    )
    rules: Mapped[list["DisposalRule"]] = relationship(
        back_populates="jurisdiction",
        cascade="all, delete-orphan",
    )


class JurisdictionPostalCode(Base):
    __tablename__ = "jurisdiction_postal_codes"
    __table_args__ = (Index("ix_jurisdiction_postal_codes_postal_code", "postal_code"),)

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    postal_code: Mapped[str] = mapped_column(String(16), primary_key=True)

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="postal_codes")


class DisposalRule(Base):
    __tablename__ = "disposal_rules"
    __table_args__ = (
        CheckConstraint(
            f"status IN {DISPOSAL_STATUSES}",
            name="ck_disposal_rules_status",
        ),
        UniqueConstraint(
            "jurisdiction_id",
            "material_key",
            name="uq_disposal_rules_jurisdiction_material",
        ),
        Index("ix_disposal_rules_jurisdiction_id", "jurisdiction_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="rules")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    model_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    top_label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    predictions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )

    confirmed_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    jurisdiction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id", ondelete="SET NULL"),
        nullable=True,
    )
