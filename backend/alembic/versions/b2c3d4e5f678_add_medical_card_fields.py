"""add alcohol_status and disability_group to medical_cards

Revision ID: b2c3d4e5f678
Revises: 87b0ee71440f
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f678'
down_revision: Union[str, None] = '87b0ee71440f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE alcoholstatus AS ENUM ('NEVER', 'FORMER', 'CURRENT', 'UNKNOWN')")
    op.add_column('medical_cards', sa.Column(
        'alcohol_status',
        sa.Enum('NEVER', 'FORMER', 'CURRENT', 'UNKNOWN', name='alcoholstatus'),
        nullable=False,
        server_default='UNKNOWN',
    ))
    op.add_column('medical_cards', sa.Column(
        'disability_group',
        sa.String(length=50),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_column('medical_cards', 'disability_group')
    op.drop_column('medical_cards', 'alcohol_status')
    op.execute("DROP TYPE alcoholstatus")
