"""added alias to users

Revision ID: f3a9d1e2b7c8
Revises: 3b95be865b3c
Create Date: 2026-03-28 03:15:22.482917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f3a9d1e2b7c8'
down_revision: Union[str, None] = '828c363b0e62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('alias', sa.String(32), nullable=True))
        batch_op.create_unique_constraint('uq_users_alias', ['alias'])
        batch_op.create_index('ix_users_alias', ['alias'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_alias')
        batch_op.drop_constraint('uq_users_alias', type_='unique')
        batch_op.drop_column('alias')
