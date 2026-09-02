"""add google drive connections

Revision ID: <GENERATED_REVISION>
Revises: 68a03b567575
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "797a97b56652"
down_revision: Union[str, Sequence[str], None] = "68a03b567575"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_drive_connections",

        sa.Column(
            "id",
            sa.String(length=128),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.String(length=128),
            nullable=False,
        ),

        sa.Column(
            "google_email",
            sa.String(length=320),
            nullable=False,
        ),

        sa.Column(
            "encrypted_refresh_token",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "root_folder_id",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),

        sa.Column(
            "connection_role",
            sa.String(length=32),
            nullable=False,
            server_default="PRIMARY",
        ),

        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "last_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.UniqueConstraint(
            "user_id",
            "google_email",
            name="uq_drive_connection_user_email",
        ),
    )

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

    op.drop_table("google_drive_connections")