"""merge_intelligence_decisions_documents

Revision ID: b1e2a3c4d5e6
Revises: 7aef0648394d
Create Date: 2026-10-03 11:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1e2a3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '7aef0648394d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add enriched columns to vendors
    op.add_column('vendors', sa.Column('tier', sa.String(length=50), server_default='TIER_2', nullable=False))
    op.add_column('vendors', sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False))
    op.add_column('vendors', sa.Column('certification_status', sa.String(length=50), server_default='GMP_CERTIFIED', nullable=False))
    op.add_column('vendors', sa.Column('delivery_reliability', sa.Float(), server_default='0.95', nullable=False))
    op.add_column('vendors', sa.Column('capacity', sa.Float(), server_default='100000.0', nullable=False))
    op.add_column('vendors', sa.Column('risk_score', sa.Float(), server_default='15.0', nullable=True))
    op.add_column('vendors', sa.Column('approval_rate', sa.Float(), server_default='0.95', nullable=True))
    op.add_column('vendors', sa.Column('quality_score', sa.Float(), server_default='98.0', nullable=True))

    # 2. Add analytical columns to raw_materials
    op.add_column('raw_materials', sa.Column('cas_number', sa.String(length=50), nullable=True))
    op.add_column('raw_materials', sa.Column('purity_min', sa.Float(), server_default='99.0', nullable=False))
    op.add_column('raw_materials', sa.Column('moisture_max', sa.Float(), server_default='1.0', nullable=False))
    op.add_column('raw_materials', sa.Column('heavy_metals_max_ppm', sa.Float(), server_default='10.0', nullable=False))
    op.add_column('raw_materials', sa.Column('microbial_limit_cfu_g', sa.Float(), server_default='100.0', nullable=False))
    op.add_column('raw_materials', sa.Column('storage_conditions', sa.String(length=255), server_default='Store below 25C in a dry, dark place', nullable=False))
    op.add_column('raw_materials', sa.Column('lead_time_days', sa.Float(), server_default='14.0', nullable=False))
    op.add_column('raw_materials', sa.Column('base_price', sa.Float(), server_default='100.0', nullable=False))

    # 3. Add reported columns to batches
    op.add_column('batches', sa.Column('purity_reported', sa.Float(), nullable=True))
    op.add_column('batches', sa.Column('lead_time_actual', sa.Float(), server_default='14.0', nullable=True))

    # 4. Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('vendor_id', sa.UUID(), nullable=True),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.UUID(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('extracted_data', sa.JSON(), nullable=True),
        sa.Column('extraction_error', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 5. Create batch_intelligence table
    op.create_table(
        'batch_intelligence',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('validation_result', sa.JSON(), nullable=True),
        sa.Column('vendor_history', sa.JSON(), nullable=True),
        sa.Column('ml_features', sa.JSON(), nullable=True),
        sa.Column('ml_prediction', sa.JSON(), nullable=True),
        sa.Column('kimi_analysis', sa.JSON(), nullable=True),
        sa.Column('kimi_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id'),
    )

    # 6. Create batch_decisions table
    op.create_table(
        'batch_decisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=32), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('recommended_actions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 7. Create email_events table
    op.create_table(
        'email_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.Column('vendor_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('decision_id', sa.UUID(), nullable=True),
        sa.Column('recipient_email', sa.String(length=320), nullable=False),
        sa.Column('subject', sa.String(length=998), nullable=False),
        sa.Column('email_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('html_content', sa.Text(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['decision_id'], ['batch_decisions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 8. Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.Column('vendor_id', sa.UUID(), nullable=True),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('email_events')
    op.drop_table('batch_decisions')
    op.drop_table('batch_intelligence')
    op.drop_table('documents')
    op.drop_column('batches', 'lead_time_actual')
    op.drop_column('batches', 'purity_reported')
    op.drop_column('raw_materials', 'base_price')
    op.drop_column('raw_materials', 'lead_time_days')
    op.drop_column('raw_materials', 'storage_conditions')
    op.drop_column('raw_materials', 'microbial_limit_cfu_g')
    op.drop_column('raw_materials', 'heavy_metals_max_ppm')
    op.drop_column('raw_materials', 'moisture_max')
    op.drop_column('raw_materials', 'purity_min')
    op.drop_column('raw_materials', 'cas_number')
    op.drop_column('vendors', 'quality_score')
    op.drop_column('vendors', 'approval_rate')
    op.drop_column('vendors', 'risk_score')
    op.drop_column('vendors', 'capacity')
    op.drop_column('vendors', 'delivery_reliability')
    op.drop_column('vendors', 'certification_status')
    op.drop_column('vendors', 'status')
    op.drop_column('vendors', 'tier')
