"""merge event drive asset migrations

Revision ID: bc77644dd2cf
Revises: add_event_drive_folder, add_event_guest_list_asset
Create Date: 2026-08-20 19:08:53.846216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc77644dd2cf'
down_revision: Union[str, Sequence[str], None] = ('add_event_drive_folder', 'add_event_guest_list_asset')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
