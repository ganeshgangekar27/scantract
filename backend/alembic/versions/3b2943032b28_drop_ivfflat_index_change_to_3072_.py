"""drop_ivfflat_index_change_to_3072_dimensions

Revision ID: 3b2943032b28
Revises: c9f165806a4d
Create Date: 2026-08-14 12:57:45.672511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b2943032b28'
down_revision: Union[str, Sequence[str], None] = 'c9f165806a4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop IVFFlat index and change embedding dimension from 768 to 3072.
    
    IVFFlat index cannot support >2000 dimensions, so we drop it entirely
    and rely on pgvector's exact (brute-force) cosine distance search.
    For small datasets (20-30 rows), there is no meaningful performance difference.
    """
    # Delete all existing rules (sample data only, safe to drop)
    op.execute("DELETE FROM legal_rules")
    
    # Drop the IVFFlat index
    op.execute("DROP INDEX IF EXISTS ix_legal_rules_embedding_ivfflat")
    
    # Alter embedding column dimensions from 768 to 3072
    op.execute("ALTER TABLE legal_rules ALTER COLUMN embedding TYPE vector(3072)")


def downgrade() -> None:
    """
    Revert to 768 dimensions and recreate IVFFlat index.
    """
    # Delete all existing rules
    op.execute("DELETE FROM legal_rules")
    
    # Revert embedding column dimensions from 3072 to 768
    op.execute("ALTER TABLE legal_rules ALTER COLUMN embedding TYPE vector(768)")
    
    # Recreate IVFFlat index
    op.execute(
        "CREATE INDEX ix_legal_rules_embedding_ivfflat "
        "ON legal_rules USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )
