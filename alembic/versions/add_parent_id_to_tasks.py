"""add parent_id to tasks

Revision ID: add_parent_id_to_tasks
Revises: c95ebf097bed
Create Date: 2026-04-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_parent_id_to_tasks'
down_revision: Union[str, Sequence[str], None] = 'c95ebf097bed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tasks',
        sa.Column('parent_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_tasks_parent_id_tasks',
        'tasks',
        'tasks',
        ['parent_id'],
        ['id']
    )
    op.create_index(
        op.f('ix_tasks_parent_id'),
        'tasks',
        ['parent_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_tasks_parent_id'), table_name='tasks')
    op.drop_constraint('fk_tasks_parent_id_tasks', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'parent_id')
