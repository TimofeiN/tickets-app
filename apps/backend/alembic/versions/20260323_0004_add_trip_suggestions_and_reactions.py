"""add trip suggestions and reactions

Revision ID: 20260323_0004
Revises: 20260317_0003
Create Date: 2026-03-23 10:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260323_0004"
down_revision: str | Sequence[str] | None = "20260317_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trip_suggestion",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("query_key", sa.Text(), nullable=False),
        sa.Column("origin_city", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("budget_usd", sa.Integer(), nullable=False),
        sa.Column("travelers_count", sa.Integer(), nullable=False),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column("option_id", sa.Text(), nullable=False),
        sa.Column("destination_city", sa.Text(), nullable=False),
        sa.Column("origin_airport", sa.Text(), nullable=False),
        sa.Column("destination_airport", sa.Text(), nullable=False),
        sa.Column("price_usd", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("trip_plan", sa.Text(), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dislikes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "query_key",
            "option_id",
            name="uq_trip_suggestion_query_option",
        ),
    )
    op.create_index("ix_trip_suggestion_query_key", "trip_suggestion", ["query_key"], unique=False)

    op.create_table(
        "trip_suggestion_reaction",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Text(),
            sa.ForeignKey("user_account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suggestion_id",
            sa.Text(),
            sa.ForeignKey("trip_suggestion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reaction", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "suggestion_id",
            name="uq_trip_suggestion_reaction_user_suggestion",
        ),
        sa.CheckConstraint(
            "reaction in ('like', 'dislike')",
            name="ck_trip_suggestion_reaction_value",
        ),
    )
    op.create_index(
        "ix_trip_suggestion_reaction_user_id",
        "trip_suggestion_reaction",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_trip_suggestion_reaction_suggestion_id",
        "trip_suggestion_reaction",
        ["suggestion_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trip_suggestion_reaction_suggestion_id",
        table_name="trip_suggestion_reaction",
    )
    op.drop_index(
        "ix_trip_suggestion_reaction_user_id",
        table_name="trip_suggestion_reaction",
    )
    op.drop_table("trip_suggestion_reaction")
    op.drop_index("ix_trip_suggestion_query_key", table_name="trip_suggestion")
    op.drop_table("trip_suggestion")
