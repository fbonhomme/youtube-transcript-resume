"""add summary feedback

Revision ID: 12712fa8d48e
Revises: 0003
Create Date: 2026-05-16 09:48:08.292184

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "12712fa8d48e"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("summaries") as batch_op:
        batch_op.add_column(sa.Column("feedback", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("summaries") as batch_op:
        batch_op.drop_column("feedback")
