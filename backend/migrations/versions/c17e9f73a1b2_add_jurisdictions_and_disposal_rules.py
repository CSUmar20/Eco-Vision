"""add jurisdictions and disposal rules

Revision ID: c17e9f73a1b2
Revises: ad961a824557
Create Date: 2026-08-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c17e9f73a1b2"
down_revision: str | Sequence[str] | None = "ad961a824557"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add source-backed recycling jurisdictions and rules."""
    op.create_table(
        "jurisdictions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("jurisdiction_type", sa.String(length=32), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("state_code", sa.String(length=3), nullable=True),
        sa.Column("county_name", sa.String(length=150), nullable=True),
        sa.Column("waste_provider", sa.String(length=255), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jurisdiction_type IN "
            "('state', 'county', 'municipality', 'waste_provider')",
            name="ck_jurisdictions_type",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["jurisdictions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_jurisdictions_slug"),
    )
    op.create_index(
        "ix_jurisdictions_display_name",
        "jurisdictions",
        ["display_name"],
        unique=False,
    )
    op.create_index(
        "ix_jurisdictions_state_code",
        "jurisdictions",
        ["state_code"],
        unique=False,
    )

    op.create_table(
        "jurisdiction_postal_codes",
        sa.Column("jurisdiction_id", sa.UUID(), nullable=False),
        sa.Column("postal_code", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdictions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("jurisdiction_id", "postal_code"),
    )
    op.create_index(
        "ix_jurisdiction_postal_codes_postal_code",
        "jurisdiction_postal_codes",
        ["postal_code"],
        unique=False,
    )

    op.create_table(
        "disposal_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("jurisdiction_id", sa.UUID(), nullable=False),
        sa.Column("material_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("source_title", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN "
            "('accepted_curbside', 'not_accepted_curbside', "
            "'drop_off_required', 'unavailable_or_unclear')",
            name="ck_disposal_rules_status",
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdictions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "jurisdiction_id",
            "material_key",
            name="uq_disposal_rules_jurisdiction_material",
        ),
    )
    op.create_index(
        "ix_disposal_rules_jurisdiction_id",
        "disposal_rules",
        ["jurisdiction_id"],
        unique=False,
    )

    op.add_column("scans", sa.Column("jurisdiction_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_scans_jurisdiction_id_jurisdictions",
        "scans",
        "jurisdictions",
        ["jurisdiction_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_scans_jurisdiction_id",
        "scans",
        ["jurisdiction_id"],
        unique=False,
    )
    op.drop_column("scans", "longitude")
    op.drop_column("scans", "latitude")


def downgrade() -> None:
    """Remove jurisdictions and restore the legacy coordinate columns."""
    op.add_column("scans", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("scans", sa.Column("longitude", sa.Float(), nullable=True))
    op.drop_index("ix_scans_jurisdiction_id", table_name="scans")
    op.drop_constraint(
        "fk_scans_jurisdiction_id_jurisdictions",
        "scans",
        type_="foreignkey",
    )
    op.drop_column("scans", "jurisdiction_id")

    op.drop_index("ix_disposal_rules_jurisdiction_id", table_name="disposal_rules")
    op.drop_table("disposal_rules")
    op.drop_index(
        "ix_jurisdiction_postal_codes_postal_code",
        table_name="jurisdiction_postal_codes",
    )
    op.drop_table("jurisdiction_postal_codes")
    op.drop_index("ix_jurisdictions_state_code", table_name="jurisdictions")
    op.drop_index("ix_jurisdictions_display_name", table_name="jurisdictions")
    op.drop_table("jurisdictions")
