"""Initial EventLah schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-13
"""
from alembic import op
from guest_management.database import metadata

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    metadata.create_all(bind=bind)

def downgrade():
    bind = op.get_bind()
    metadata.drop_all(bind=bind)
