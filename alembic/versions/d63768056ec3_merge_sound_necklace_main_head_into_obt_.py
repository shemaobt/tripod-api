"""merge sound_necklace main head into obt-200

Revision ID: d63768056ec3
Revises: 20260704_0004, 20260717_0003
Create Date: 2026-07-17 17:17:49.079330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd63768056ec3'
down_revision: Union[str, None] = ('20260704_0004', '20260717_0003')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
