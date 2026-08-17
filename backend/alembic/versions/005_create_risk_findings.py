"""create_risk_findings

Revision ID: 005_create_risk_findings
Revises: 004_create_reference_clauses
Create Date: 2026-08-15 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, VARCHAR, TEXT, TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = '005_create_risk_findings'
down_revision: Union[str, Sequence[str], None] = '004_create_reference_clauses'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create risk_findings table for Stage 7 risk detection results.
    
    Stores both risky clauses and missing clauses with traceability requirements.
    Every finding MUST have a non-empty triggering_rule_or_corpus field.
    """
    op.execute("""
        CREATE TABLE risk_findings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            finding_type VARCHAR(20) NOT NULL,
            
            -- For risky clauses
            clause_id INTEGER REFERENCES clauses(id) ON DELETE SET NULL,
            
            -- For missing clauses
            expected_clause_type VARCHAR(100),
            
            -- Common fields
            reason TEXT NOT NULL,
            triggering_rule_or_corpus TEXT NOT NULL,
            severity VARCHAR(10) NOT NULL,
            
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            -- Constraints
            CONSTRAINT valid_finding_type CHECK (finding_type IN ('risky_clause', 'missing_clause')),
            CONSTRAINT valid_severity CHECK (severity IN ('low', 'medium', 'high')),
            CONSTRAINT risky_clause_has_id CHECK (
                finding_type = 'missing_clause' OR clause_id IS NOT NULL
            ),
            CONSTRAINT missing_clause_has_type CHECK (
                finding_type = 'risky_clause' OR expected_clause_type IS NOT NULL
            )
        )
    """)
    
    # Create indexes for common query patterns
    op.execute("""
        CREATE INDEX idx_risk_findings_contract ON risk_findings(contract_id)
    """)
    
    op.execute("""
        CREATE INDEX idx_risk_findings_severity ON risk_findings(severity)
    """)
    
    op.execute("""
        CREATE INDEX idx_risk_findings_type ON risk_findings(finding_type)
    """)
    
    op.execute("""
        CREATE INDEX idx_risk_findings_clause ON risk_findings(clause_id) 
        WHERE clause_id IS NOT NULL
    """)


def downgrade() -> None:
    """
    Drop risk_findings table.
    """
    op.execute("DROP TABLE IF EXISTS risk_findings")
