"""add pre draw prizes

Revision ID: c1f0d4b8e9a2
Revises: b9b51f43fdd1
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1f0d4b8e9a2"
down_revision: Union[str, Sequence[str], None] = "b9b51f43fdd1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pre_draw_prizes",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "event_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "value",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "image_url",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "winner_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "winner_count > 0",
            name="ck_pre_draw_prizes_winner_count_positive",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_pre_draw_prizes_sort_order_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'generated', 'archived')",
            name="ck_pre_draw_prizes_status",
        ),
    )

    op.create_index(
        "idx_pre_draw_prizes_event_order",
        "pre_draw_prizes",
        ["event_id", "sort_order", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_pre_draw_prizes_event_order",
        table_name="pre_draw_prizes",
    )

    op.drop_table("pre_draw_prizes")