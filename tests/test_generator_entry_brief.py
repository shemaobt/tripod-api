from app.services.meaning_map.generator import _build_generation_prompt, _format_entry_brief


def test_format_entry_brief_with_established_items():
    brief = {
        "established_items": [
            {
                "category": "participant",
                "name": "Naomi",
                "description": "Naomi: wife and mother",
                "verse_reference": "1:2",
            },
        ],
        "participants": [
            {
                "name": "Naomi",
                "arc": [{"at": {"chapter": 1, "verse": 2}, "state": "wife and mother"}],
            },
        ],
        "active_threads": [
            {
                "label": "Will Naomi find security?",
                "question": "Will she return to Bethlehem?",
                "is_resolved_at_entry": False,
            },
        ],
    }
    result = _format_entry_brief(brief)
    assert "Naomi" in result
    assert "wife and mother" in result
    assert "Will Naomi find security?" in result
    assert "RESOLVED" not in result


def test_format_entry_brief_first_pericope():
    brief = {
        "established_items": [],
        "participants": [],
        "active_threads": [],
    }
    result = _format_entry_brief(brief)
    assert "opening of the book" in result


def test_format_entry_brief_resolved_thread():
    brief = {
        "established_items": [
            {
                "category": "event",
                "name": "Famine",
                "description": "A famine in the land",
                "verse_reference": "1:1",
            },
        ],
        "participants": [],
        "active_threads": [
            {
                "label": "Famine",
                "question": "Will the famine end?",
                "is_resolved_at_entry": True,
            },
        ],
    }
    result = _format_entry_brief(brief)
    assert "(RESOLVED)" in result


def test_build_prompt_includes_entry_brief():
    bhsa = {
        "clauses": [
            {
                "verse": 1,
                "clause_type": "Way0",
                "text": "test",
                "gloss": "test",
                "is_mainline": True,
                "chain_position": "initial",
            }
        ]
    }
    brief = {
        "established_items": [
            {
                "category": "participant",
                "name": "Ruth",
                "description": "Ruth: a Moabitess",
                "verse_reference": "1:4",
            },
        ],
        "participants": [],
        "active_threads": [],
    }
    result = _build_generation_prompt("Ruth 1:6-18", bhsa, "some rag", brief)
    assert "BOOK CONTEXT (Already Established)" in result
    assert "Ruth" in result


def test_build_prompt_without_entry_brief():
    result = _build_generation_prompt("Ruth 1:1-5", None, None, None)
    assert "BOOK CONTEXT" not in result
    assert "Ruth 1:1-5" in result
