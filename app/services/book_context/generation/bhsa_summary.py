from __future__ import annotations

from typing import Any

from app.services.book_context.generation.bhsa_stream import stream_book_clauses


def build_bhsa_summary(tf_api: Any, book_name: str, chapter_count: int) -> str:
    lines: list[str] = []

    for chapter_data in stream_book_clauses(tf_api, book_name, chapter_count):
        ch = chapter_data["chapter"]
        clauses = chapter_data["clauses"]

        lines.append(f"\n=== Chapter {ch} ({len(clauses)} clauses) ===")

        all_names: set[str] = set()
        verbs: list[str] = []
        verse_summaries: dict[int, list[str]] = {}

        for c in clauses:
            v = c["verse"]
            if v not in verse_summaries:
                verse_summaries[v] = []

            gloss = c.get("gloss", "")
            if gloss:
                verse_summaries[v].append(gloss[:120])

            for name in c.get("names", []):
                all_names.add(name)

            if c.get("lemma"):
                verbs.append(f"{c['lemma']} ({c.get('binyan', '?')}/{c.get('tense', '?')})")

        if all_names:
            lines.append(f"  Names: {', '.join(sorted(all_names))}")
        if verbs:
            lines.append(f"  Key verbs: {', '.join(verbs[:20])}")

        for v in sorted(verse_summaries.keys()):
            combined = " | ".join(verse_summaries[v][:3])
            lines.append(f"  v{v}: {combined[:200]}")

    return "\n".join(lines)
