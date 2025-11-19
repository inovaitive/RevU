"""Initial schema with organizations, users, feedback, and analysis

Revision ID: 001
Revises:
Create Date: 2025-11-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), unique=True, nullable=True),
        sa.Column('tier', sa.String(50), server_default='free'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), server_default='user'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('oauth_provider', sa.String(50), nullable=True),
        sa.Column('oauth_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_org', 'users', ['organization_id'])

    # Create feedback table
    op.create_table(
        'feedback',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('author_email', sa.String(255), nullable=True),
        sa.Column('rating', sa.DECIMAL(3, 2), nullable=True),
        sa.Column('feedback_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('raw_metadata', JSONB, nullable=True),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_feedback_org', 'feedback', ['organization_id'])
    op.create_index('idx_feedback_source', 'feedback', ['source'])
    op.create_index('idx_feedback_date', 'feedback', ['feedback_date'])

    # Create analysis table
    op.create_table(
        'analysis',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('feedback_id', UUID(as_uuid=True), sa.ForeignKey('feedback.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('sentiment', sa.String(50), nullable=True),
        sa.Column('sentiment_score', sa.DECIMAL(4, 3), nullable=True),
        sa.Column('categories', ARRAY(sa.String), nullable=True),
        sa.Column('themes', ARRAY(sa.String), nullable=True),
        sa.Column('priority_score', sa.Integer, nullable=True),
        sa.Column('urgency', sa.String(50), nullable=True),
        sa.Column('insights', JSONB, nullable=True),
        sa.Column('churn_risk', sa.Boolean, server_default='false'),
        sa.Column('competitor_mentions', ARRAY(sa.String), nullable=True),
        sa.Column('extracted_entities', JSONB, nullable=True),
        sa.Column('confidence_score', sa.DECIMAL(4, 3), nullable=True),
        sa.Column('requires_review', sa.Boolean, server_default='false'),
        sa.Column('reviewed_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ai_model_version', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_analysis_feedback', 'analysis', ['feedback_id'])
    op.create_index('idx_analysis_sentiment', 'analysis', ['sentiment'])
    op.create_index('idx_analysis_priority', 'analysis', ['priority_score'])
    op.create_index('idx_analysis_urgency', 'analysis', ['urgency'])
    op.create_index('idx_analysis_churn', 'analysis', ['churn_risk'], postgresql_where=sa.text('churn_risk = true'))


def downgrade() -> None:
    op.drop_table('analysis')
    op.drop_table('feedback')
    op.drop_table('users')
    op.drop_table('organizations')
