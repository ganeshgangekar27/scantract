"""add_explanation_caching

Revision ID: 006_add_explanation_caching
Revises: 005_create_risk_findings
Create Date: 2026-08-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_explanation_caching'
down_revision: Union[str, Sequence[str], None] = '005_create_risk_findings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add explanation caching columns to risk_findings table.
    
    Adds three nullable columns for caching generated explanations and
    formatted citations to avoid redundant LLM calls.
    """
    # Add explanation caching columns
    op.execute("""
        ALTER TABLE risk_findings 
        ADD COLUMN explanation TEXT,
        ADD COLUMN formatted_citation TEXT,
        ADD COLUMN explanation_generated_at TIMESTAMP WITH TIME ZONE
    """)
    
    # Index for finding findings without cached explanations (WHERE clause filters)
    op.execute("""
        CREATE INDEX idx_risk_findings_explanation_null 
        ON risk_findings(contract_id) 
        WHERE explanation IS NULL
    """)
    
    # Index for citation validation queries
    op.execute("""
        CREATE INDEX idx_risk_findings_citation 
        ON risk_findings(triggering_rule_or_corpus)
    """)


def downgrade() -> None:
    """
    Remove explanation caching columns and indexes from risk_findings table.
    """
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_risk_findings_citation")
    op.execute("DROP INDEX IF EXISTS idx_risk_findings_explanation_null")
    
    # Drop columns
    op.execute("""
        ALTER TABLE risk_findings 
        DROP COLUMN IF EXISTS explanation,
        DROP COLUMN IF EXISTS formatted_citation,
        DROP COLUMN IF EXISTS explanation_generated_at
    """)
