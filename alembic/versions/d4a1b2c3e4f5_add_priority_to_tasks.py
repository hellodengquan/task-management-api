"""add priority to tasks

Revision ID: d4a1b2c3e4f5
Revises: c95ebf097bed
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4a1b2c3e4f5'
down_revision: Union[str, Sequence[str], None] = 'c95ebf097bed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    priority_enum = sa.Enum('high', 'medium', 'low', name='priority')
    priority_enum.create(op.get_bind(), checkfirst=True)
    
    op.add_column(
        'tasks',
        sa.Column(
            'priority',
            sa.Enum('high', 'medium', 'low', name='priority'),
            server_default='medium',
            nullable=False
        )
    )


def downgrade() -> None:
    op.drop_column('tasks', 'priority')
    sa.Enum(name='priority').drop(op.get_bind(), checkfirst=True)
