"""added comment_mappings table

Revision ID: a1c3f9e2d4b7
Revises: f3a9d1e2b7c8
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c3f9e2d4b7'
down_revision: Union[str, None] = 'f3a9d1e2b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comment_mappings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('userId', sa.BigInteger(), nullable=False),
        sa.Column('userChatId', sa.BigInteger(), nullable=False),
        sa.Column('userMessageId', sa.BigInteger(), nullable=False),
        sa.Column('groupChatId', sa.BigInteger(), nullable=False),
        sa.Column('groupMessageId', sa.BigInteger(), nullable=False),
        sa.Column('channelPostId', sa.BigInteger(), nullable=False),
        sa.Column('isDeleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['userId'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('comment_mappings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_comment_mappings_userId'), ['userId'], unique=False)
        batch_op.create_index(batch_op.f('ix_comment_mappings_userMessageId'), ['userMessageId'], unique=False)
        batch_op.create_index(batch_op.f('ix_comment_mappings_groupMessageId'), ['groupMessageId'], unique=False)
        batch_op.create_index(batch_op.f('ix_comment_mappings_channelPostId'), ['channelPostId'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('comment_mappings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_comment_mappings_channelPostId'))
        batch_op.drop_index(batch_op.f('ix_comment_mappings_groupMessageId'))
        batch_op.drop_index(batch_op.f('ix_comment_mappings_userMessageId'))
        batch_op.drop_index(batch_op.f('ix_comment_mappings_userId'))
    op.drop_table('comment_mappings')
