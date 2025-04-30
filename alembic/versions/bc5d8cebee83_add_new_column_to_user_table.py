"""Add new column to User table

Revision ID: bc5d8cebee83
Revises: 9f4c9c6ca7bb
Create Date: 2025-04-14 12:56:21.109380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc5d8cebee83'
down_revision: Union[str, None] = '9f4c9c6ca7bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
