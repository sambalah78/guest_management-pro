"""Add Google Drive folder ID to events.

Revision ID: add_event_drive_folder
Revises: add_event_drive_assets
Create Date: 2026-08-20

Each EventLah event gets its own Google Drive folder.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_event_drive_folder"

down_revision: Union[str, None] = "add_event_drive_assets"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "event_drive_folder_id",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "events",
        "event_drive_folder_id",
    )