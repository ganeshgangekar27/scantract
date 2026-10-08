"""add_sample_contracts_flag

Revision ID: 010
Revises: 009
Create Date: 2026-10-08 12:04:36.839073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, Sequence[str], None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_sample column with default false
    op.add_column('contracts', sa.Column('is_sample', sa.Boolean(), nullable=False, server_default='false'))
    # Create index for faster filtering
    op.create_index('ix_contracts_is_sample', 'contracts', ['is_sample'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_contracts_is_sample', table_name='contracts')
    op.drop_column('contracts', 'is_sample')
