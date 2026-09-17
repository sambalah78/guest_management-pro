"""add google drive connection indexes

Revision ID: <YOUR_GENERATED_REVISION>
Revises: 797a97b56652
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b2cc9754243d"
down_revision: Union[str, Sequence[str], None] = "797a97b56652"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_drive_connections_user",
        "google_drive_connections",
        ["user_id"],
    )

    op.create_index(
        "idx_drive_connections_active",
        "google_drive_connections",
        ["is_active"],
    )

    op.create_index(
        "idx_drive_connections_primary",
        "google_drive_connections",
        ["user_id", "is_primary"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_drive_connections_primary",
        table_name="google_drive_connections",
    )

    op.drop_index(
        "idx_drive_connections_active",
        table_name="google_drive_connections",
    )

    op.drop_index(
        "idx_drive_connections_user",
        table_name="google_drive_connections",
    )