"""add status, priority and assignee fields

Revision ID: d45e8f3c9b8a
Revises: c95ebf097bed
Create Date: 2026-04-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd45e8f3c9b8a'
down_revision: Union[str, Sequence[str], None] = 'c95ebf097bed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tasks', sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', name='taskstatus'), nullable=False, server_default='PENDING'))
    op.add_column('tasks', sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='taskpriority'), nullable=False, server_default='MEDIUM'))
    op.add_column('tasks', sa.Column('assignee_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_tasks_assignee_id_users', 'tasks', 'users', ['assignee_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_tasks_assignee_id_users', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'assignee_id')
    op.drop_column('tasks', 'priority')
    op.drop_column('tasks', 'status')
    op.execute('DROP TYPE IF EXISTS taskstatus')
    op.execute('DROP TYPE IF EXISTS taskpriority')