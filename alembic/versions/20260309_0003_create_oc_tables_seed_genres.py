"""create oral collector tables and seed genre data

Revision ID: 20260309_0003
Revises: 20260309_0002
Create Date: 2026-03-09

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260309_0003"
down_revision: str | None = "20260309_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Deterministic UUIDs for seed data (UUID5 from DNS namespace + name)
NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

GENRES = [
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-narrative")),
        "name": "Narrative/Story",
        "description": "Oral narratives including personal stories, folk tales, and historical accounts",
        "icon": "book-open",
        "color": "#BE4A01",
        "sort_order": 1,
        "subcategories": [
            ("Personal Narrative", "First-person accounts of personal experiences"),
            ("Folk Tale", "Traditional stories passed down through generations"),
            ("Historical Account", "Oral recounting of historical events"),
            ("Legend/Myth", "Traditional stories explaining origins or supernatural events"),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-proverb")),
        "name": "Proverb/Wisdom",
        "description": "Wise sayings, proverbs, and riddles that encode cultural knowledge",
        "icon": "lightbulb",
        "color": "#3F3E20",
        "sort_order": 2,
        "subcategories": [
            ("Traditional Proverb", "Well-known sayings conveying cultural wisdom"),
            ("Riddle", "Traditional riddles and word puzzles"),
            ("Wise Saying", "Informal wisdom and life advice"),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-song")),
        "name": "Song/Poetry",
        "description": "Musical and poetic oral traditions",
        "icon": "music",
        "color": "#89AAA3",
        "sort_order": 3,
        "subcategories": [
            ("Traditional Song", "Songs from cultural heritage"),
            ("Poem/Verse", "Oral poetry and verse recitations"),
            ("Lullaby", "Songs for soothing children"),
            ("Work Song", "Songs sung during communal labor"),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-dialogue")),
        "name": "Dialogue/Conversation",
        "description": "Interactive speech between two or more participants",
        "icon": "message-circle",
        "color": "#777D45",
        "sort_order": 4,
        "subcategories": [
            ("Everyday Conversation", "Natural day-to-day dialogue"),
            ("Interview", "Structured question-and-answer sessions"),
            ("Debate/Discussion", "Formal or informal argumentative discourse"),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-instruction")),
        "name": "Instruction/Procedural",
        "description": "Step-by-step instructions and how-to explanations",
        "icon": "clipboard-list",
        "color": "#C5C29F",
        "sort_order": 5,
        "subcategories": [
            ("How-To", "General instructional explanations"),
            ("Recipe", "Food preparation instructions"),
            ("Craft Instructions", "Traditional craft and artisan techniques"),
            ("Agricultural Practice", "Farming and land management procedures"),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-prayer")),
        "name": "Prayer/Ceremonial",
        "description": "Religious prayers, blessings, and ceremonial speech",
        "icon": "heart",
        "color": "#BE4A01",
        "sort_order": 6,
        "subcategories": [
            ("Prayer", "Personal or communal prayers"),
            ("Blessing", "Formal blessings and benedictions"),
            ("Ceremony Speech", "Speeches delivered during ceremonies"),
            ("Ritual Chant", "Repetitive chants used in rituals"),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-description")),
        "name": "Description/Expository",
        "description": "Descriptive and explanatory oral texts",
        "icon": "file-text",
        "color": "#89AAA3",
        "sort_order": 7,
        "subcategories": [
            ("Place Description", "Descriptions of locations and environments"),
            ("Cultural Practice", "Explanations of customs and traditions"),
            ("Object Description", "Descriptions of tools, artifacts, or natural objects"),
        ],
    },
    {
        "id": str(uuid.uuid5(NAMESPACE, "oc-genre-hortatory")),
        "name": "Hortatory/Persuasion",
        "description": "Persuasive speech intended to motivate or warn",
        "icon": "megaphone",
        "color": "#3F3E20",
        "sort_order": 8,
        "subcategories": [
            ("Public Speech", "Speeches delivered to a public audience"),
            ("Moral Teaching", "Teachings aimed at shaping behavior"),
            ("Community Appeal", "Appeals for communal action or solidarity"),
            ("Warning", "Cautionary messages and admonitions"),
        ],
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # --- oc_genres ---
    if "oc_genres" not in existing_tables:
        op.create_table(
            "oc_genres",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("icon", sa.String(100), nullable=True),
            sa.Column("color", sa.String(20), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # --- oc_subcategories ---
    if "oc_subcategories" not in existing_tables:
        op.create_table(
            "oc_subcategories",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("genre_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["genre_id"], ["oc_genres.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_oc_subcategories_genre_id", "oc_subcategories", ["genre_id"])

    # --- oc_recordings ---
    if "oc_recordings" not in existing_tables:
        op.create_table(
            "oc_recordings",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("project_id", sa.String(36), nullable=False),
            sa.Column("genre_id", sa.String(36), nullable=False),
            sa.Column("subcategory_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("duration_seconds", sa.Float(), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("format", sa.String(20), nullable=False),
            sa.Column("gcs_url", sa.Text(), nullable=True),
            sa.Column("upload_status", sa.String(20), nullable=False, server_default="local"),
            sa.Column("cleaning_status", sa.String(20), nullable=False, server_default="none"),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["genre_id"], ["oc_genres.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["subcategory_id"], ["oc_subcategories.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_oc_recordings_project_id", "oc_recordings", ["project_id"])
        op.create_index("ix_oc_recordings_genre_id", "oc_recordings", ["genre_id"])
        op.create_index("ix_oc_recordings_subcategory_id", "oc_recordings", ["subcategory_id"])
        op.create_index("ix_oc_recordings_user_id", "oc_recordings", ["user_id"])

    # --- oc_project_users ---
    if "oc_project_users" not in existing_tables:
        op.create_table(
            "oc_project_users",
            sa.Column("project_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(30), nullable=False, server_default="user"),
            sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("invited_by", sa.String(36), nullable=True),
            sa.PrimaryKeyConstraint("project_id", "user_id"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        )

    # --- oc_project_invites ---
    if "oc_project_invites" not in existing_tables:
        op.create_table(
            "oc_project_invites",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("project_id", sa.String(36), nullable=False),
            sa.Column("email", sa.String(320), nullable=False),
            sa.Column("invited_by", sa.String(36), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("role", sa.String(30), nullable=False, server_default="user"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_oc_project_invites_project_id", "oc_project_invites", ["project_id"])
        op.create_index("ix_oc_project_invites_invited_by", "oc_project_invites", ["invited_by"])

    # --- Seed genre and subcategory data ---
    for genre in GENRES:
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

        for idx, (sub_name, sub_desc) in enumerate(genre["subcategories"], start=1):
            sub_id = str(uuid.uuid5(NAMESPACE, f"oc-sub-{genre['name']}-{sub_name}"))
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
                        "description": sub_desc,
                        "sort_order": idx,
                    },
                )


def downgrade() -> None:
    op.drop_table("oc_project_invites")
    op.drop_table("oc_project_users")
    op.drop_table("oc_recordings")
    op.drop_table("oc_subcategories")
    op.drop_table("oc_genres")
