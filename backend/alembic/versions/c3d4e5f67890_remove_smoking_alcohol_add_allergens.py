"""remove smoking_alcohol from medical_cards, add allergens table

Revision ID: c3d4e5f67890
Revises: b2c3d4e5f678
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c3d4e5f67890'
down_revision: Union[str, None] = 'b2c3d4e5f678'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove smoking_status and alcohol_status from medical_cards
    op.drop_column('medical_cards', 'alcohol_status')
    op.execute("DROP TYPE IF EXISTS alcoholstatus")

    # smoking_status was added in initial migration — check and drop
    op.drop_column('medical_cards', 'smoking_status')
    op.execute("DROP TYPE IF EXISTS smokingstatus")

    # Create allergens reference table
    op.create_table(
        'allergens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(20), nullable=False, unique=True),
        sa.Column('name_ua', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('international_name', sa.String(255), nullable=True),
        sa.Column('component', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.create_index('ix_allergens_code', 'allergens', ['code'])
    op.create_index('ix_allergens_name_ua', 'allergens', ['name_ua'])


def downgrade() -> None:
    op.drop_index('ix_allergens_name_ua', 'allergens')
    op.drop_index('ix_allergens_code', 'allergens')
    op.drop_table('allergens')

    op.execute("CREATE TYPE smokingstatus AS ENUM ('NEVER', 'FORMER', 'CURRENT', 'UNKNOWN')")
    op.add_column('medical_cards', sa.Column(
        'smoking_status',
        sa.Enum('NEVER', 'FORMER', 'CURRENT', 'UNKNOWN', name='smokingstatus'),
        nullable=False,
        server_default='UNKNOWN',
    ))
    op.execute("CREATE TYPE alcoholstatus AS ENUM ('NEVER', 'FORMER', 'CURRENT', 'UNKNOWN')")
    op.add_column('medical_cards', sa.Column(
        'alcohol_status',
        sa.Enum('NEVER', 'FORMER', 'CURRENT', 'UNKNOWN', name='alcoholstatus'),
        nullable=False,
        server_default='UNKNOWN',
    ))