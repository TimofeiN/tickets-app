"""add iata is_flightable flag

Revision ID: 20260317_0003
Revises: 20260316_0002
Create Date: 2026-03-17 02:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260317_0003"
down_revision: str | Sequence[str] | None = "20260316_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "iata_city_map",
        sa.Column(
            "is_flightable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("iata_city_map", "is_flightable", server_default=None)


def downgrade() -> None:
    op.drop_column("iata_city_map", "is_flightable")
