"""add task status column

Revision ID: add_task_status_column
Revises: c95ebf097bed
Create Date: 2026-04-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_task_status_column'
down_revision: Union[str, Sequence[str], None] = 'c95ebf097bed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'tasks',
        sa.Column('status', sa.String(20), nullable=True)
    )
    
    op.execute(
        "UPDATE tasks SET status = 'completed' WHERE completed = 1"
    )
    op.execute(
        "UPDATE tasks SET status = 'pending' WHERE completed = 0 OR status IS NULL"
    )
    
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.String(20),
            nullable=False,
            server_default='pending'
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tasks', 'status')
