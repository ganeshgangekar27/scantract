"""Create legal_rules table with pgvector support

Revision ID: 003
Revises: 002
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create legal_rules table
    op.create_table(
        'legal_rules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('act_name', sa.String(length=255), nullable=False),
        sa.Column('section_reference', sa.String(length=100), nullable=False),
        sa.Column('rule_text', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add UNIQUE constraint on (act_name, section_reference, state)
    op.create_unique_constraint(
        'uq_legal_rule',
        'legal_rules',
        ['act_name', 'section_reference', 'state']
    )
    
    # Create indexes
    op.create_index('ix_legal_rules_state', 'legal_rules', ['state'])
    op.create_index('ix_legal_rules_act_name', 'legal_rules', ['act_name'])
    
    # Create IVFFlat index on embedding column for cosine similarity search
    op.execute('''
        CREATE INDEX ix_legal_rules_embedding_ivfflat 
        ON legal_rules 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    ''')


def downgrade() -> None:
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS ix_legal_rules_embedding_ivfflat')
    op.drop_index('ix_legal_rules_act_name', 'legal_rules')
    op.drop_index('ix_legal_rules_state', 'legal_rules')
    
    # Drop unique constraint
    op.drop_constraint('uq_legal_rule', 'legal_rules', type_='unique')
    
    # Drop table
    op.drop_table('legal_rules')
    
    # Note: Not dropping vector extension as it may be used by other tables
