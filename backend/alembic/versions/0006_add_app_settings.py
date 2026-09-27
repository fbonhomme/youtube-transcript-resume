"""add app_settings (clés API saisies dans l'administration, chiffrées)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("app_settings"):
        op.create_table(
            "app_settings",
            sa.Column("key", sa.String(100), primary_key=True),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("app_settings")
