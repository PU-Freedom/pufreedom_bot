"""base tables

users and message_mappings were originally created by Base.metadata.create_all,
so no migration created them and a fresh database couldn't be migrated.
schema as it was before the later migrations (isAdmin, userLastEditMessageId, alias)

Revision ID: 9a1b2c3d4e5f
Revises:
Create Date: 2026-11-23 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9a1b2c3d4e5f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('telegramId', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('firstName', sa.String(255), nullable=False),
        sa.Column('lastName', sa.String(255), nullable=True),
        sa.Column('isBanned', sa.Boolean(), nullable=False),
        sa.Column('lastActiveAt', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_telegramId', 'users', ['telegramId'], unique=True)

    op.create_table(
        'message_mappings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('userId', sa.BigInteger(), nullable=False),
        sa.Column('userChatId', sa.BigInteger(), nullable=False),
        sa.Column('userMessageId', sa.BigInteger(), nullable=False),
        sa.Column('channelChatId', sa.BigInteger(), nullable=False),
        sa.Column('channelMessageId', sa.BigInteger(), nullable=False),
        sa.Column('isDeleted', sa.Boolean(), nullable=False),
        sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['userId'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_message_mappings_userId', 'message_mappings', ['userId'])
    op.create_index('ix_message_mappings_userMessageId', 'message_mappings', ['userMessageId'])
    op.create_index('ix_message_mappings_channelMessageId', 'message_mappings', ['channelMessageId'])


def downgrade() -> None:
    # recreated by cb49abf9ff8b's downgrade and references users
    op.execute('DROP TABLE IF EXISTS rate_limit_logs')
    op.drop_table('message_mappings')
    op.drop_table('users')
