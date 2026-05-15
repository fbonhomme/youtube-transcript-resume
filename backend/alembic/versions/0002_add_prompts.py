"""add prompts table and prompt_id on summaries

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "prompts" not in existing_tables:
        op.create_table(
            "prompts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False, unique=True),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("system_prompt", sa.Text(), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    existing_cols = [c["name"] for c in inspector.get_columns("summaries")]
    if "prompt_id" not in existing_cols:
        with op.batch_alter_table("summaries") as batch_op:
            batch_op.add_column(sa.Column("prompt_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("summaries") as batch_op:
        batch_op.drop_column("prompt_id")
    op.drop_table("prompts")
