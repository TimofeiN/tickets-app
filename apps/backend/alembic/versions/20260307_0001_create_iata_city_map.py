"""create iata city map table

Revision ID: 20260307_0001
Revises:
Create Date: 2026-03-07 01:55:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260307_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iata_city_map",
        sa.Column("iata_code", sa.Text(), primary_key=True),
        sa.Column("city_code", sa.Text(), nullable=False),
        sa.Column("city_name", sa.Text(), nullable=False),
        sa.Column("airport_name", sa.Text(), nullable=True),
        sa.Column("country_code", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_iata_city_map_city_code", "iata_city_map", ["city_code"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_iata_city_map_city_code", table_name="iata_city_map")
    op.drop_table("iata_city_map")
