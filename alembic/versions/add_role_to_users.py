"""add role to users

Revision ID: add_role_to_users
Revises: c95ebf097bed
Create Date: 2026-04-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_role_to_users'
down_revision: Union[str, Sequence[str], None] = 'c95ebf097bed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First, create the enum type (not strictly needed for SQLite, but good practice)
    role_enum = sa.Enum('admin', 'member', name='role')
    
    # Add the role column with a default value for existing records
    op.add_column(
        'users', 
        sa.Column(
            'role', 
            sa.String(length=10), 
            nullable=False, 
            server_default='member'
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role')