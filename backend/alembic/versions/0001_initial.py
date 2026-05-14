"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-14
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "themes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("youtube_url", sa.String(500), nullable=False),
        sa.Column("youtube_id", sa.String(20), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="fr"),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("summary_short", sa.Text(), nullable=False),
        sa.Column("summary_long", sa.Text(), nullable=False),
        sa.Column("key_points", sa.JSON(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("duration_read", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("theme_id", sa.Integer(), sa.ForeignKey("themes.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_summaries_theme_id", "summaries", ["theme_id"])
    op.create_index("ix_summaries_youtube_id", "summaries", ["youtube_id"])


def downgrade() -> None:
    op.drop_table("summaries")
    op.drop_table("themes")
