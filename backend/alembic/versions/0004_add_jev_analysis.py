"""add theme description and Jev analysis columns

Revision ID: 0004
Revises: 12712fa8d48e
Create Date: 2026-09-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "12712fa8d48e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    theme_cols = [c["name"] for c in inspector.get_columns("themes")]
    if "description" not in theme_cols:
        with op.batch_alter_table("themes") as batch_op:
            batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))

    summary_cols = [c["name"] for c in inspector.get_columns("summaries")]
    cols_to_add = {
        "scores": sa.JSON(),
        "theme_confidence": sa.Float(),
        "theme_suggestion_id": sa.Integer(),
    }
    missing = {name: type_ for name, type_ in cols_to_add.items() if name not in summary_cols}
    if missing:
        with op.batch_alter_table("summaries") as batch_op:
            for name, type_ in missing.items():
                batch_op.add_column(sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("summaries") as batch_op:
        batch_op.drop_column("theme_suggestion_id")
        batch_op.drop_column("theme_confidence")
        batch_op.drop_column("scores")
    with op.batch_alter_table("themes") as batch_op:
        batch_op.drop_column("description")
