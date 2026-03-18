"""update genre taxonomy to Tripod Method and add register_id to recordings

Revision ID: 20260318_0001
Revises: 20260317_0001
Create Date: 2026-03-18

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260318_0001"
down_revision: str | None = "20260317_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Deterministic UUIDs for seed data (same namespace as original migration)
NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

NEW_GENRES = [
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-narrative-v2")),
        "name": "Narrative",
        "description": "Stories, accounts, and narrative forms of oral tradition",
        "icon": "book-open",
        "color": "#BE4A01",
        "sort_order": 1,
        "subcategories": [
            ("Historical Narrative", "historical_narrative", 1),
            ("Personal Account / Testimony", "personal_account", 2),
            ("Parable / Illustrative Story", "parable", 3),
            ("Origin / Creation Story", "origin_story", 4),
            ("Legend / Hero Story", "legend", 5),
            ("Vision or Dream Narrative", "vision_narrative", 6),
            ("Genealogy", "genealogy", 7),
            ("Recent Event Report", "event_report", 8),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-poetic-song-v2")),
        "name": "Poetic / Song",
        "description": "Musical and poetic oral traditions including hymns, laments, and wisdom poetry",
        "icon": "music",
        "color": "#89AAA3",
        "sort_order": 2,
        "subcategories": [
            ("Hymn / Worship Song", "hymn", 1),
            ("Lament", "lament", 2),
            ("Funeral Dirge", "funeral_dirge", 3),
            ("Victory / Celebration Song", "victory_song", 4),
            ("Love Song", "love_song", 5),
            ("Mocking / Taunt Song", "taunt_song", 6),
            ("Blessing", "blessing", 7),
            ("Curse", "curse", 8),
            ("Wisdom Poem / Proverb", "wisdom_poem", 9),
            ("Didactic Poetry", "didactic_poetry", 10),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-instructional-v2")),
        "name": "Instructional / Regulatory",
        "description": "Laws, rituals, procedures, and instructional forms",
        "icon": "clipboard-list",
        "color": "#C5C29F",
        "sort_order": 3,
        "subcategories": [
            ("Law / Legal Code", "legal_code", 1),
            ("Ritual / Liturgy", "ritual", 2),
            ("Procedure / Instruction", "procedure", 3),
            ("List / Inventory", "list_inventory", 4),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-oral-discourse-v2")),
        "name": "Oral Discourse",
        "description": "Speeches, teachings, prayers, and discursive oral forms",
        "icon": "message-circle",
        "color": "#777D45",
        "sort_order": 4,
        "subcategories": [
            ("Prophetic Oracle / Speech", "prophetic_oracle", 1),
            ("Exhortation / Sermon", "exhortation", 2),
            ("Wisdom Teaching", "wisdom_teaching", 3),
            ("Prayer", "prayer", 4),
            ("Dialogue", "dialogue", 5),
            ("Epistle / Letter", "epistle", 6),
            ("Apocalyptic Discourse", "apocalyptic_discourse", 7),
            ("Ceremonial Speech", "ceremonial_speech", 8),
            ("Community Memory", "community_memory", 9),
        ],
    },
]


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1. Add register_id column to oc_recordings (if not already present) ---
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("oc_recordings")]
    if "register_id" not in columns:
        op.add_column(
            "oc_recordings",
            sa.Column("register_id", sa.String(50), nullable=True),
        )

    # --- 2. Deactivate old genres and subcategories ---
    conn.execute(sa.text("UPDATE oc_subcategories SET is_active = false"))
    conn.execute(sa.text("UPDATE oc_genres SET is_active = false"))

    # --- 3. Seed new genre taxonomy ---
    for genre in NEW_GENRES:
        existing = conn.execute(
            sa.text("SELECT id FROM oc_genres WHERE id = :id"),
            {"id": genre["id"]},
        ).fetchone()
        if not existing:
            conn.execute(
                sa.text(
                    "INSERT INTO oc_genres (id, name, description, icon, color, sort_order, is_active) "
                    "VALUES (:id, :name, :description, :icon, :color, :sort_order, true)"
                ),
                {
                    "id": genre["id"],
                    "name": genre["name"],
                    "description": genre["description"],
                    "icon": genre["icon"],
                    "color": genre["color"],
                    "sort_order": genre["sort_order"],
                },
            )

        for sub_name, sub_slug, sub_order in genre["subcategories"]:
            sub_id = str(uuid.uuid5(NAMESPACE, f"oc-sub-v2-{sub_slug}"))
            existing_sub = conn.execute(
                sa.text("SELECT id FROM oc_subcategories WHERE id = :id"),
                {"id": sub_id},
            ).fetchone()
            if not existing_sub:
                conn.execute(
                    sa.text(
                        "INSERT INTO oc_subcategories (id, genre_id, name, description, sort_order, is_active) "
                        "VALUES (:id, :genre_id, :name, :description, :sort_order, true)"
                    ),
                    {
                        "id": sub_id,
                        "genre_id": genre["id"],
                        "name": sub_name,
                        "description": sub_slug,
                        "sort_order": sub_order,
                    },
                )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove new genres and subcategories
    for genre in NEW_GENRES:
        conn.execute(
            sa.text("DELETE FROM oc_subcategories WHERE genre_id = :genre_id"),
            {"genre_id": genre["id"]},
        )
        conn.execute(
            sa.text("DELETE FROM oc_genres WHERE id = :id"),
            {"id": genre["id"]},
        )

    # Reactivate old genres and subcategories
    conn.execute(sa.text("UPDATE oc_genres SET is_active = true"))
    conn.execute(sa.text("UPDATE oc_subcategories SET is_active = true"))

    # Remove register_id column
    op.drop_column("oc_recordings", "register_id")
