"""Add session model

Revision ID: 001
Revises:
Create Date: 2025-11-06 04:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create sessions table"""
    op.create_table(
        'sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('notes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('crisis_level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('session_id')
    )

    # Create indexes for better query performance
    op.create_index('ix_sessions_conversation_id', 'sessions', ['conversation_id'])
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_started_at', 'sessions', ['started_at'])
    op.create_index('ix_sessions_is_deleted', 'sessions', ['is_deleted'])


def downgrade() -> None:
    """Drop sessions table"""
    op.drop_index('ix_sessions_is_deleted', table_name='sessions')
    op.drop_index('ix_sessions_started_at', table_name='sessions')
    op.drop_index('ix_sessions_user_id', table_name='sessions')
    op.drop_index('ix_sessions_conversation_id', table_name='sessions')
    op.drop_table('sessions')
