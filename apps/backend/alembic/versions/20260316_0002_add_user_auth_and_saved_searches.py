"""add user auth and saved searches

Revision ID: 20260316_0002
Revises: 20260307_0001
Create Date: 2026-03-16 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260316_0002"
down_revision: str | Sequence[str] | None = "20260307_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_account",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_user_account_email", "user_account", ["email"], unique=True)

    op.create_table(
        "user_session",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Text(),
            sa.ForeignKey("user_account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_user_session_token_hash", "user_session", ["token_hash"], unique=True)
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"], unique=False)

    op.create_table(
        "saved_search",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Text(),
            sa.ForeignKey("user_account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("origin_city", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("budget_usd", sa.Integer(), nullable=False),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column("summary_destination", sa.Text(), nullable=True),
        sa.Column("summary_price_usd", sa.Integer(), nullable=True),
        sa.Column("options_count", sa.Integer(), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_saved_search_user_id", "saved_search", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_saved_search_user_id", table_name="saved_search")
    op.drop_table("saved_search")
    op.drop_index("ix_user_session_user_id", table_name="user_session")
    op.drop_index("ix_user_session_token_hash", table_name="user_session")
    op.drop_table("user_session")
    op.drop_index("ix_user_account_email", table_name="user_account")
    op.drop_table("user_account")
