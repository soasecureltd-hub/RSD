"""Add owner (user_id) to assessments

Revision ID: 002
Revises: 001
Create Date: 2026-06-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("assessments") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_assessments_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_assessments_user_id_users", "users", ["user_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("assessments") as batch_op:
        batch_op.drop_constraint("fk_assessments_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_assessments_user_id")
        batch_op.drop_column("user_id")
