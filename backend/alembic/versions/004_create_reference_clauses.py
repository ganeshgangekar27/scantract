"""create_reference_clauses

Revision ID: 004_create_reference_clauses
Revises: 3b2943032b28
Create Date: 2026-08-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import VARCHAR, TEXT, TIMESTAMP
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '004_create_reference_clauses'
down_revision: Union[str, Sequence[str], None] = '3b2943032b28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create reference_clauses table for Stage 5B reference corpus.
    
    CRITICAL: Uses VECTOR(3072) for Gemini embeddings, NO IVFFlat index.
    Exact/brute-force search only, matching Stage 5A approach.
    """
    # Create reference_clauses table
    op.execute("""
        CREATE TABLE reference_clauses (
            id SERIAL PRIMARY KEY,
            contract_type VARCHAR(50) NOT NULL,
            clause_category VARCHAR(100) NOT NULL,
            clause_text TEXT NOT NULL,
            source_label VARCHAR(200) NOT NULL,
            embedding VECTOR(3072) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)
    
    # Create unique index using MD5 hash (PostgreSQL doesn't allow functions in UNIQUE constraints directly)
    op.execute("""
        CREATE UNIQUE INDEX unique_reference_clause_idx 
        ON reference_clauses (contract_type, clause_category, MD5(clause_text))
    """)
    
    # NO IVFFlat index - using exact search only
    # For small datasets (28 sample clauses), exact search is sufficient
    # and avoids IVFFlat's >2000 dimension limitation


def downgrade() -> None:
    """
    Drop reference_clauses table.
    """
    op.execute("DROP TABLE IF EXISTS reference_clauses")
