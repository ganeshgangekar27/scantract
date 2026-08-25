"""Add document processing fields to contracts table

Revision ID: 007_doc_processing
Revises: 006_add_explanation_caching
Create Date: 2026-08-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_doc_processing'
down_revision = '006_add_explanation_caching'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('contracts', sa.Column('file_path', sa.String(512), nullable=True))
    op.add_column('contracts', sa.Column('full_text', sa.Text(), nullable=True))
    op.add_column('contracts', sa.Column('processing_status', sa.String(20), nullable=False, server_default='uploaded'))
    op.add_column('contracts', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('contracts', sa.Column('page_count', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('contracts', 'page_count')
    op.drop_column('contracts', 'error_message')
    op.drop_column('contracts', 'processing_status')
    op.drop_column('contracts', 'full_text')
    op.drop_column('contracts', 'file_path')
