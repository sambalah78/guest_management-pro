"""Add scanner station authentication credentials.

Revision ID: 0002_scanner_station_credentials
Revises: 0001_supabase_baseline
Create Date: 2026-09-16
"""

from alembic import op


revision = "0002_scanner_station_credentials"
down_revision = "0001_supabase_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.scanner_devices
        ADD COLUMN IF NOT EXISTS access_token_hash TEXT
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_scanner_devices_access_token_hash
        ON public.scanner_devices (access_token_hash)
        WHERE access_token_hash IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS
        public.idx_scanner_devices_access_token_hash
    """)

    op.execute("""
        ALTER TABLE public.scanner_devices
        DROP COLUMN IF EXISTS access_token_hash
    """)