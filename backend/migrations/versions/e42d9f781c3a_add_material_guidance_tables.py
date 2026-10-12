"""add material guidance tables

Revision ID: e42d9f781c3a
Revises: c17e9f73a1b2
Create Date: 2026-10-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e42d9f781c3a"
down_revision: str | Sequence[str] | None = "c17e9f73a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add canonical materials, aliases, and general disposal guidance."""
    op.create_table(
        "materials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_materials_key"),
    )
    op.create_index(
        "ix_materials_display_name",
        "materials",
        ["display_name"],
        unique=False,
    )

    op.create_table(
        "material_aliases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("material_id", sa.UUID(), nullable=False),
        sa.Column("alias", sa.String(length=150), nullable=False),
        sa.Column("normalized_alias", sa.String(length=150), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "normalized_alias",
            name="uq_material_aliases_normalized_alias",
        ),
    )
    op.create_index(
        "ix_material_aliases_material_id",
        "material_aliases",
        ["material_id"],
        unique=False,
    )

    op.create_table(
        "general_disposal_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("material_id", sa.UUID(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("preparation", sa.Text(), nullable=True),
        sa.Column("warning", sa.Text(), nullable=True),
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
            "action IN "
            "('reuse_or_donate', 'recycle', 'compost', "
            "'special_drop_off', 'trash', 'check_locally')",
            name="ck_general_disposal_rules_action",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_id",
            "country_code",
            name="uq_general_disposal_rules_material_country",
        ),
    )


def downgrade() -> None:
    """Remove general disposal guidance and its material taxonomy."""
    op.drop_table("general_disposal_rules")
    op.drop_index(
        "ix_material_aliases_material_id",
        table_name="material_aliases",
    )
    op.drop_table("material_aliases")
    op.drop_index("ix_materials_display_name", table_name="materials")
    op.drop_table("materials")
