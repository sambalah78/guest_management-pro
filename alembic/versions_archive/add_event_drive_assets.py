"""Add Google Drive asset metadata to events.

Revision ID: add_event_drive_assets
Revises: 9ea7dd1fa8a3
Create Date: 2026-08-19

The existing legacy logo and wedding_invitation columns are intentionally
preserved.

This migration adds metadata columns used to reference files stored in
Google Drive.

The upgrade is intentionally idempotent because some development databases
may already contain one or more of these columns through an earlier schema
initialization.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ----------------------------------------------------------------------
# Revision identifiers
# ----------------------------------------------------------------------

revision: str = "add_event_drive_assets"

down_revision: Union[str, None] = "9ea7dd1fa8a3"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

EVENT_TABLE = "events"


def _existing_columns() -> set[str]:
    """Return the existing column names for the events table."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    return {
        column["name"]
        for column in inspector.get_columns(EVENT_TABLE)
    }


def _add_column_if_missing(
    column: sa.Column,
    existing_columns: set[str],
) -> None:
    """Add a column only when it does not already exist."""

    if column.name in existing_columns:
        return

    op.add_column(
        EVENT_TABLE,
        column,
    )


# ======================================================================
# UPGRADE
# ======================================================================

def upgrade() -> None:
    """Add Google Drive asset metadata columns to events."""

    existing_columns = _existing_columns()

    # ------------------------------------------------------------------
    # Event logo
    # ------------------------------------------------------------------

    _add_column_if_missing(
        sa.Column(
            "logo_drive_file_id",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
        existing_columns,
    )

    _add_column_if_missing(
        sa.Column(
            "logo_filename",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
        existing_columns,
    )

    _add_column_if_missing(
        sa.Column(
            "logo_mime_type",
            sa.String(length=100),
            nullable=False,
            server_default="",
        ),
        existing_columns,
    )

    # ------------------------------------------------------------------
    # Invitation card
    # ------------------------------------------------------------------

    _add_column_if_missing(
        sa.Column(
            "invitation_drive_file_id",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
        existing_columns,
    )

    _add_column_if_missing(
        sa.Column(
            "invitation_filename",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
        existing_columns,
    )

    _add_column_if_missing(
        sa.Column(
            "invitation_mime_type",
            sa.String(length=100),
            nullable=False,
            server_default="",
        ),
        existing_columns,
    )


# ======================================================================
# DOWNGRADE
# ======================================================================

def downgrade() -> None:
    """Remove Google Drive asset metadata columns from events."""

    existing_columns = _existing_columns()

    columns_to_remove = [
        "invitation_mime_type",
        "invitation_filename",
        "invitation_drive_file_id",
        "logo_mime_type",
        "logo_filename",
        "logo_drive_file_id",
    ]

    for column_name in columns_to_remove:
        if column_name in existing_columns:
            op.drop_column(
                EVENT_TABLE,
                column_name,
            )