"""add classification fields to clauses

Revision ID: 002
Revises: 001
Create Date: 2026-08-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add classification fields to clauses table."""
    # Add columns
    op.add_column('clauses', sa.Column('clause_type', sa.String(50), nullable=True))
    op.add_column('clauses', sa.Column('key_entities', JSONB, nullable=True))
    op.add_column('clauses', sa.Column('confidence', sa.Float, nullable=True))
    op.add_column('clauses', sa.Column('classification_error', sa.Text, nullable=True))
    op.add_column('clauses', sa.Column('classified_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes
    op.create_index('ix_clauses_clause_type', 'clauses', ['clause_type'])
    op.create_index('ix_clauses_confidence', 'clauses', ['confidence'])


def downgrade() -> None:
    """Remove classification fields from clauses table."""
    # Drop indexes
    op.drop_index('ix_clauses_confidence', table_name='clauses')
    op.drop_index('ix_clauses_clause_type', table_name='clauses')
    
    # Drop columns
    op.drop_column('clauses', 'classified_at')
    op.drop_column('clauses', 'classification_error')
    op.drop_column('clauses', 'confidence')
    op.drop_column('clauses', 'key_entities')
    op.drop_column('clauses', 'clause_type')
