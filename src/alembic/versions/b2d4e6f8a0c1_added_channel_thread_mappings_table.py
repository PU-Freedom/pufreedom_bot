"""added channel_thread_mappings table

Revision ID: b2d4e6f8a0c1
Revises: a1c3f9e2d4b7
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2d4e6f8a0c1'
down_revision: Union[str, None] = 'a1c3f9e2d4b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'channel_thread_mappings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('channelPostId', sa.BigInteger(), nullable=False),
        sa.Column('groupThreadId', sa.BigInteger(), nullable=False),
        sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channelPostId', name='uq_channel_thread_channelPostId')
    )
    with op.batch_alter_table('channel_thread_mappings', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_channel_thread_mappings_channelPostId'),
            ['channelPostId'],
            unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('channel_thread_mappings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_channel_thread_mappings_channelPostId'))
    op.drop_table('channel_thread_mappings')
