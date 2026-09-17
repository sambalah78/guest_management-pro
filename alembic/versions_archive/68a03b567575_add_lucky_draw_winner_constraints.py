"""add lucky draw winner constraints

Revision ID: 68a03b567575
Revises: bc77644dd2cf
Create Date: 2026-08-31 16:50:26.928559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "68a03b567575"
down_revision: Union[str, Sequence[str], None] = "bc77644dd2cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Lucky Draw winner integrity constraints."""

    with op.batch_alter_table("winners") as batch_op:
        batch_op.alter_column(
            "guest_id",
            existing_type=sa.VARCHAR(length=255),
            nullable=False,
        )

        batch_op.create_unique_constraint(
            "uq_winners_event_guest",
            ["event_id", "guest_id"],
        )


def downgrade() -> None:
    """Remove Lucky Draw winner integrity constraints."""

    with op.batch_alter_table("winners") as batch_op:
        batch_op.drop_constraint(
            "uq_winners_event_guest",
            type_="unique",
        )

        batch_op.alter_column(
            "guest_id",
            existing_type=sa.VARCHAR(length=255),
            nullable=True,
        )
