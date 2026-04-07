"""Add brand trust assessment module

Tables: brand_industries, brand_trust_questions, brand_trust_assessments,
        brand_trust_answers

Revision ID: 031_add_brand_trust_module
Revises: 030_add_destinations_module
Create Date: 2026-03-20 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = '031_add_brand_trust_module'
down_revision = '030_add_destinations_module'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if tables already exist
    inspector = inspect(op.get_bind())
    
    # ── brand_industries ──────────────────────────────────────────────────────
    if not inspector.has_table('brand_industries'):
        op.create_table(
        'brand_industries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )

    # ── brand_trust_questions ─────────────────────────────────────────────────
    if not inspector.has_table('brand_trust_questions'):
        op.create_table(
            'brand_trust_questions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text('gen_random_uuid()')),
            sa.Column('industry_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('brand_industries.id'), nullable=True,
                      comment='NULL = applies to all industries'),
            sa.Column('section', sa.String(100), nullable=False,
                      comment='Grouping label, e.g. Product Quality, Customer Trust'),
            sa.Column('question_text', sa.Text, nullable=False),
            sa.Column('question_type', sa.String(20), nullable=False,
                      server_default='rating',
                      comment='rating | yes_no | text | multiple_choice'),
            sa.Column('options', postgresql.JSONB, nullable=True,
                      comment='For multiple_choice: list of option strings'),
            sa.Column('weight', sa.Numeric(4, 2), server_default='1.0',
                      comment='Scoring weight for this question'),
            sa.Column('order_index', sa.Integer, server_default='0'),
            sa.Column('is_active', sa.Boolean, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True),
                      server_default=sa.text('now()')),
        )
        op.create_index('idx_btq_industry', 'brand_trust_questions', ['industry_id'])
        op.create_index('idx_btq_section', 'brand_trust_questions', ['section'])

    # ── brand_trust_assessments ───────────────────────────────────────────────
    if not inspector.has_table('brand_trust_assessments'):
        op.create_table(
            'brand_trust_assessments',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text('gen_random_uuid()')),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('industry_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('brand_industries.id'), nullable=True),
            sa.Column('started_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('status', sa.String(20), server_default='in_progress',
                      comment='in_progress | submitted | scored'),
            sa.Column('overall_score', sa.Numeric(5, 2), nullable=True,
                      comment='Computed 0-100 score after submission'),
            sa.Column('score_breakdown', postgresql.JSONB, nullable=True,
                      comment='Per-section scores'),
            sa.Column('report_url', sa.Text, nullable=True),
            sa.Column('notes', sa.Text, nullable=True),
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True),
                      server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True),
                      server_default=sa.text('now()')),
        )
        op.create_index('idx_bta_org', 'brand_trust_assessments', ['organization_id'])
        op.create_index('idx_bta_status', 'brand_trust_assessments', ['status'])

    # ── brand_trust_answers ───────────────────────────────────────────────────
    if not inspector.has_table('brand_trust_answers'):
        op.create_table(
            'brand_trust_answers',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text('gen_random_uuid()')),
            sa.Column('assessment_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('brand_trust_assessments.id', ondelete='CASCADE'),
                      nullable=False),
            sa.Column('question_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('brand_trust_questions.id'), nullable=False),
            sa.Column('answer_value', sa.Text, nullable=True,
                      comment='Rating as string, yes/no, free text, or selected option'),
            sa.Column('answered_at', sa.DateTime(timezone=True),
                      server_default=sa.text('now()')),
        )
        op.create_index('idx_bta_answers_assessment', 'brand_trust_answers', ['assessment_id'])


def downgrade() -> None:
    op.drop_table('brand_trust_answers')
    op.drop_table('brand_trust_assessments')
    op.drop_table('brand_trust_questions')
    op.drop_table('brand_industries')
