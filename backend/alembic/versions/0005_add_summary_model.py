"""add summaries.model (modèle ayant généré la synthèse)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_cols = [c["name"] for c in inspector.get_columns("summaries")]
    if "model" not in existing_cols:
        with op.batch_alter_table("summaries") as batch_op:
            batch_op.add_column(sa.Column("model", sa.String(100), nullable=True))
    # Jusqu'ici toutes les synthèses étaient générées par Claude Opus 4.7.
    op.execute("UPDATE summaries SET model = 'claude-opus-4-7' WHERE model IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("summaries") as batch_op:
        batch_op.drop_column("model")
