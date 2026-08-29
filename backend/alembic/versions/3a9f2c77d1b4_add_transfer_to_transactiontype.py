"""add transfer to transactiontype enum

Revision ID: 3a9f2c77d1b4
Revises: 2ffbf4af1389
Create Date: 2026-08-29 12:00:00.000000

Adds the 'transfer' value to the Postgres native enum `transactiontype`
so wallet-to-wallet transfers can be recorded in the ledger.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3a9f2c77d1b4'
down_revision: Union[str, None] = '2ffbf4af1389'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'transfer'")


def downgrade() -> None:
    # Postgres does not support removing an enum value directly; documented as no-op.
    pass
