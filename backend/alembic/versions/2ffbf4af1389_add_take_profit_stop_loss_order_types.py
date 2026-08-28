"""add take_profit stop_loss order types

Revision ID: 2ffbf4af1389
Revises: f534bdc35207
Create Date: 2026-08-28 13:12:00.225371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ffbf4af1389'
down_revision: Union[str, None] = 'f534bdc35207'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE ordertype ADD VALUE IF NOT EXISTS 'take_profit'")
    op.execute("ALTER TYPE ordertype ADD VALUE IF NOT EXISTS 'stop_loss'")


def downgrade() -> None:
    # PostgreSQL has no enum value removal; rebuild the type without the new values.
    op.execute("ALTER TABLE orders ALTER COLUMN type TYPE VARCHAR(32) USING type::text")
    op.execute("DROP TYPE ordertype")
    op.execute("CREATE TYPE ordertype AS ENUM ('market', 'limit')")
    op.execute("ALTER TABLE orders ALTER COLUMN type TYPE ordertype USING type::ordertype")
