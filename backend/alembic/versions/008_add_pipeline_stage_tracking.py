"""add pipeline stage tracking

Revision ID: 008_pipeline_stage
Revises: 007_add_document_processing_fields
Create Date: 2026-09-15

Adds granular pipeline stage tracking to contracts table:
- pipeline_stage: current stage in processing pipeline
- failed_stage: stage where failure occurred (if any)

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_pipeline_stage'
down_revision = '007_doc_processing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add pipeline_stage and failed_stage columns.
    
    Pipeline stages:
    - 'uploaded': Contract uploaded, awaiting processing
    - 'extracting': Extracting text from PDF/DOCX
    - 'segmented': Text extracted and segmented into clauses
    - 'classifying': Running LLM clause classification
    - 'classified': All clauses classified
    - 'detecting_risks': Running risk detection
    - 'risks_detected': Risk findings generated
    - 'generating_explanations': Creating plain-language explanations
    - 'completed': Full pipeline completed successfully
    - 'failed': Pipeline failed (check failed_stage and error_message)
    """
    # Add pipeline_stage column
    op.add_column(
        'contracts',
        sa.Column(
            'pipeline_stage',
            sa.String(30),
            nullable=False,
            server_default='uploaded'
        )
    )
    
    # Add failed_stage column (nullable - only populated on failure)
    op.add_column(
        'contracts',
        sa.Column(
            'failed_stage',
            sa.String(30),
            nullable=True
        )
    )
    
    # Migrate existing data:
    # - processing_status='completed' -> pipeline_stage='segmented' (they stopped at Stage 2)
    # - processing_status='failed' -> pipeline_stage='failed', failed_stage='extracting'
    # - processing_status='uploaded' -> pipeline_stage='uploaded'
    # - processing_status='processing' -> pipeline_stage='extracting'
    
    op.execute("""
        UPDATE contracts 
        SET pipeline_stage = CASE processing_status
            WHEN 'completed' THEN 'segmented'
            WHEN 'failed' THEN 'failed'
            WHEN 'processing' THEN 'extracting'
            ELSE 'uploaded'
        END
    """)
    
    op.execute("""
        UPDATE contracts 
        SET failed_stage = 'extracting'
        WHERE processing_status = 'failed'
    """)
    
    # Create index for pipeline_stage queries
    op.create_index(
        'ix_contracts_pipeline_stage',
        'contracts',
        ['pipeline_stage']
    )


def downgrade() -> None:
    """Remove pipeline stage tracking columns."""
    op.drop_index('ix_contracts_pipeline_stage', table_name='contracts')
    op.drop_column('contracts', 'failed_stage')
    op.drop_column('contracts', 'pipeline_stage')
