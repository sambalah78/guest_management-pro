"""add email delivery tracking

Revision ID: 9ea7dd1fa8a3
Revises: 0001_initial
Create Date: 2026-08-16 16:47:15.835318

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.



"""add email delivery tracking

Revision ID: add_email_delivery_tracking
Revises: PUT_PREVIOUS_REVISION_HERE
Create Date: 2026-08-16
"""



# IMPORTANT:
# Replace this with the revision ID shown by:
# alembic history

revision = "9ea7dd1fa8a3"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "email_jobs",
        sa.Column("provider_status", sa.String(length=64), nullable=True),
    )

    op.add_column(
        "email_jobs",
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "email_jobs",
        sa.Column("bounced_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "email_jobs",
        sa.Column("opened_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "email_jobs",
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("email_jobs", "clicked_at")
    op.drop_column("email_jobs", "opened_at")
    op.drop_column("email_jobs", "bounced_at")
    op.drop_column("email_jobs", "delivered_at")
    op.drop_column("email_jobs", "provider_status")