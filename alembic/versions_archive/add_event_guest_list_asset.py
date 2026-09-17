"""Add Google Drive guest-list metadata to events.

Revision ID: add_event_guest_list_asset
Revises: add_event_drive_assets
Create Date: 2026-08-19

The guest list remains stored in the database for live application
operations.

This migration only adds metadata pointing to the original uploaded
guest-list file stored in Google Drive.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ----------------------------------------------------------------------
# Revision identifiers
# ----------------------------------------------------------------------

revision: str = "add_event_guest_list_asset"

down_revision: Union[str, None] = "add_event_drive_assets"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ======================================================================
# UPGRADE
# ======================================================================

def upgrade() -> None:
    """Add Google Drive guest-list metadata to events."""

    op.add_column(
        "events",
        sa.Column(
            "guest_list_drive_file_id",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )

    op.add_column(
        "events",
        sa.Column(
            "guest_list_filename",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )

    op.add_column(
        "events",
        sa.Column(
            "guest_list_mime_type",
            sa.String(length=100),
            nullable=False,
            server_default="",
        ),
    )


# ======================================================================
# DOWNGRADE
# ======================================================================

def downgrade() -> None:
    """Remove Google Drive guest-list metadata from events."""

    op.drop_column(
        "events",
        "guest_list_mime_type",
    )

    op.drop_column(
        "events",
        "guest_list_filename",
    )

    op.drop_column(
        "events",
        "guest_list_drive_file_id",
    )