"""seed unclassified genre and subcategory for oral collector

Revision ID: 20260415_0001
Revises: 20260414_0001
Create Date: 2026-04-15

"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260415_0001"
down_revision: str | None = "20260414_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO oc_genres (id, name, description, icon, color, sort_order, is_active, created_at, updated_at)
        VALUES ('unclassified', 'Unclassified', 'Recordings pending classification',
                'tag', '#9CA3AF', 9999, true, now(), now())
        ON CONFLICT (id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO oc_subcategories (id, genre_id, name, description, sort_order, is_active, created_at, updated_at)
        VALUES ('unclassified', 'unclassified', 'Unclassified', 'Default subcategory for pending classification',
                9999, true, now(), now())
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM oc_subcategories WHERE id = 'unclassified';")
    op.execute("DELETE FROM oc_genres WHERE id = 'unclassified';")
