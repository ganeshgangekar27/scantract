"""create contracts and clauses tables

Revision ID: 001
Revises: 
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create contracts and clauses tables."""
    # Create contracts table
    op.create_table(
        'contracts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_type', sa.String(50), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contracts_id', 'contracts', ['id'])
    
    # Create clauses table
    op.create_table(
        'clauses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('clause_id', sa.String(50), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_clauses_id', 'clauses', ['id'])
    op.create_index('ix_clauses_contract_id', 'clauses', ['contract_id'])


def downgrade() -> None:
    """Drop contracts and clauses tables."""
    op.drop_index('ix_clauses_contract_id', table_name='clauses')
    op.drop_index('ix_clauses_id', table_name='clauses')
    op.drop_table('clauses')
    
    op.drop_index('ix_contracts_id', table_name='contracts')
    op.drop_table('contracts')
