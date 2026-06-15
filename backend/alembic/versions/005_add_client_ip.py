"""add client_ip to tasks

Revision ID: 005
Revises: 004
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("client_ip", sa.String(45), nullable=True))
    op.create_index("idx_tasks_client_ip_created", "tasks", ["client_ip", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("idx_tasks_client_ip_created", table_name="tasks")
    op.drop_column("tasks", "client_ip")
