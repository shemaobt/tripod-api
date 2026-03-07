import pytest

from app.services.book_context.generation.state import BCDGenerationState


def test_state_can_be_created_with_required_fields():
    state: BCDGenerationState = {
        "book_name": "Ruth",
        "book_id": "abc-123",
        "bcd_id": "bcd-456",
        "genre": "narrative",
        "chapter_count": 4,
    }
    assert state["book_name"] == "Ruth"
    assert state["chapter_count"] == 4


def test_state_accepts_all_fields():
    state: BCDGenerationState = {
        "book_name": "Ruth",
        "book_id": "abc-123",
        "bcd_id": "bcd-456",
        "genre": "narrative",
        "chapter_count": 4,
        "bhsa_summary": "summary text",
        "bhsa_entities": [{"name": "Ruth", "entry_verse": {"chapter": 1, "verse": 4}}],
        "structural_outline": {"book_arc": "test"},
        "participant_register": [{"name": "Naomi"}],
        "discourse_threads": [],
        "theological_spine": "spine text",
        "places": [],
        "objects": [],
        "institutions": [],
        "genre_context": {},
        "maintenance_notes": {},
    }
    assert state["bhsa_summary"] == "summary text"
    assert state["structural_outline"]["book_arc"] == "test"
    assert len(state["bhsa_entities"]) == 1


def test_bhsa_stream_generator_structure():
    from app.services.book_context.generation.bhsa_stream import stream_book_clauses

    assert callable(stream_book_clauses)


def test_schemas_validate():
    from app.services.book_context.generation.schemas import (
        ContextSectionsSchema,
        DiscourseThreadsSchema,
        GenreContextSchema,
        MaintenanceNotesSchema,
        ParticipantRegisterSchema,
        StructuralOutlineSchema,
    )

    outline = StructuralOutlineSchema(
        book_arc="The arc of Ruth",
        chapters=[],
        literary_structure="linear",
    )
    assert outline.book_arc == "The arc of Ruth"

    participants = ParticipantRegisterSchema(participants=[])
    assert len(participants.participants) == 0

    threads = DiscourseThreadsSchema(threads=[])
    assert len(threads.threads) == 0

    sections = ContextSectionsSchema(theological_spine="spine")
    assert sections.theological_spine == "spine"
    assert isinstance(sections.genre_context, GenreContextSchema)
    assert isinstance(sections.maintenance_notes, MaintenanceNotesSchema)

    genre = GenreContextSchema(primary_genre="narrative", sub_genres=["romance"])
    assert genre.primary_genre == "narrative"

    notes = MaintenanceNotesSchema(generation_notes="auto", known_limitations=["none"])
    assert notes.generation_notes == "auto"
