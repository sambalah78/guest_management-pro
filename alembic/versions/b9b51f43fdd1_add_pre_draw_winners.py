"""add pre draw winners

Revision ID: <KEEP_THE_GENERATED_REVISION_ID>
Revises: <KEEP_THE_GENERATED_DOWN_REVISION>
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9b51f43fdd1"
down_revision: Union[str, Sequence[str], None] = "b2cc9754243d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pre_draw_winners",
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
            "guest_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "prize_name",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "prize_value",
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
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "event_id",
            "guest_id",
            name="uq_pre_draw_winners_event_guest",
        ),
    )

    op.create_index(
        "idx_pre_draw_winners_event",
        "pre_draw_winners",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_pre_draw_winners_event",
        table_name="pre_draw_winners",
    )

    op.drop_table("pre_draw_winners")