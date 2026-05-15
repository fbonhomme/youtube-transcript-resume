"""add input_tokens, output_tokens, cost_usd to summaries

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_cols = [c["name"] for c in inspector.get_columns("summaries")]
    cols_to_add = {
        "input_tokens": sa.Column("input_tokens", sa.Integer(), nullable=True),
        "output_tokens": sa.Column("output_tokens", sa.Integer(), nullable=True),
        "cost_usd": sa.Column("cost_usd", sa.Float(), nullable=True),
    }
    with op.batch_alter_table("summaries") as batch_op:
        for col_name, col_def in cols_to_add.items():
            if col_name not in existing_cols:
                batch_op.add_column(col_def)


def downgrade() -> None:
    with op.batch_alter_table("summaries") as batch_op:
        batch_op.drop_column("cost_usd")
        batch_op.drop_column("output_tokens")
        batch_op.drop_column("input_tokens")
