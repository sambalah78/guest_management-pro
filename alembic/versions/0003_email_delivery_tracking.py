"""Add SendGrid delivery tracking fields to email_jobs.

Revision ID: 0003_email_delivery_tracking
Revises: 0002_scanner_station_credentials
"""

from alembic import op


revision = "0003_email_delivery_tracking"
down_revision = "0002_scanner_station_credentials"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.email_jobs
        ADD COLUMN IF NOT EXISTS provider_status TEXT
    """)

    op.execute("""
        ALTER TABLE public.email_jobs
        ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ
    """)

    op.execute("""
        ALTER TABLE public.email_jobs
        ADD COLUMN IF NOT EXISTS bounced_at TIMESTAMPTZ
    """)

    op.execute("""
        ALTER TABLE public.email_jobs
        ADD COLUMN IF NOT EXISTS opened_at TIMESTAMPTZ
    """)

    op.execute("""
        ALTER TABLE public.email_jobs
        ADD COLUMN IF NOT EXISTS clicked_at TIMESTAMPTZ
    """)


def downgrade():
    op.execute("""
        ALTER TABLE public.email_jobs
        DROP COLUMN IF EXISTS clicked_at
    """)

    op.execute("""
        ALTER TABLE public.email_jobs
        DROP COLUMN IF EXISTS opened_at
    """)

    op.execute("""
        ALTER TABLE public.email_jobs
        DROP COLUMN IF EXISTS bounced_at
    """)

    op.execute("""
        ALTER TABLE public.email_jobs
        DROP COLUMN IF EXISTS delivered_at
    """)

    op.execute("""
        ALTER TABLE public.email_jobs
        DROP COLUMN IF EXISTS provider_status
    """)