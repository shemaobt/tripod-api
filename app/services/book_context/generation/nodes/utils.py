from __future__ import annotations

import json
from typing import Any


def summarize_participants(register: list[dict[str, Any]]) -> str:
    """Compact participant summary for use as LLM context in downstream steps.

    Only includes name, gloss, type, and role to avoid blowing input token
    limits on large books like Nehemiah (232+ participants).
    """
    summary = [
        {
            "name": p.get("name", ""),
            "english_gloss": p.get("english_gloss", ""),
            "type": p.get("type", ""),
            "role_in_book": p.get("role_in_book", ""),
        }
        for p in register
    ]
    return json.dumps(summary, indent=2)
