from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.book_context.generation.bhsa_stream import stream_book_clauses

_TOP_N = 250
_MIN_APPEARANCES = 2
_NOMINAL_FUNCTIONS = frozenset({"Subj", "Objc", "Cmpl", "PreC"})
_SAMPLE_LIMIT = 8


def extract_common_noun_candidates(
    tf_api: Any, book_name: str, chapter_count: int
) -> dict[str, Any]:
    aggregates: dict[tuple[str, str], dict[str, Any]] = {}

    for chapter_data in stream_book_clauses(tf_api, book_name, chapter_count):
        ch = chapter_data["chapter"]
        for clause in chapter_data["clauses"]:
            v = clause["verse"]
            ref = {"chapter": ch, "verse": v}
            for cw in clause.get("content_words", []):
                key_lex = cw.get("lex_utf8") or cw.get("lex")
                sp = cw.get("sp")
                if not key_lex or not sp:
                    continue
                key = (key_lex, sp)

                bucket = aggregates.get(key)
                if bucket is None:
                    bucket = {
                        "lex_utf8": cw.get("lex_utf8"),
                        "lex": cw.get("lex"),
                        "sp": sp,
                        "english_gloss": cw.get("gloss") or "",
                        "first_appears": ref,
                        "appears_in": [],
                        "function_counter": Counter(),
                        "binyan_counter": Counter(),
                    }
                    aggregates[key] = bucket

                if not bucket["english_gloss"] and cw.get("gloss"):
                    bucket["english_gloss"] = cw["gloss"]

                if not bucket["appears_in"] or bucket["appears_in"][-1] != ref:
                    bucket["appears_in"].append(ref)

                func = cw.get("function")
                if func:
                    bucket["function_counter"][func] += 1
                binyan = cw.get("binyan")
                if binyan:
                    bucket["binyan_counter"][binyan] += 1

    candidates: list[dict[str, Any]] = []
    for bucket in aggregates.values():
        appearance_count = len(bucket["appears_in"])
        if appearance_count < _MIN_APPEARANCES:
            continue

        sp = bucket["sp"]
        function_counter: Counter = bucket["function_counter"]

        if sp in ("subs", "adjv") and not (set(function_counter.keys()) & _NOMINAL_FUNCTIONS):
            continue

        candidates.append(
            {
                "lemma": bucket["lex_utf8"],
                "lemma_ascii": bucket["lex"],
                "english_gloss": bucket["english_gloss"],
                "sp": sp,
                "appearance_count": appearance_count,
                "top_functions": [f for f, _ in function_counter.most_common(3)],
                "top_binyans": [b for b, _ in bucket["binyan_counter"].most_common(3)],
                "first_appears": bucket["first_appears"],
                "sample_appears_in": bucket["appears_in"][:_SAMPLE_LIMIT],
            }
        )

    candidates.sort(key=lambda c: c["appearance_count"], reverse=True)
    return {"bhsa_common_nouns": candidates[:_TOP_N]}
