"""merge sound_necklace main head into obt-242

Revision ID: 38994e1b98e9
Revises: 20260714_0102, 20260717_0003
Create Date: 2026-07-17 17:40:17.966311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38994e1b98e9'
down_revision: Union[str, None] = ('20260714_0102', '20260717_0003')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
