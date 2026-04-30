from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.book_context.generation.bhsa_stream import stream_book_clauses
from app.services.book_context.generation.types import (
    BHSAEntity,
    BHSAEntryRef,
    ClauseExtract,
    CollectBHSAOutput,
    CommonNounCandidate,
)

_PERSON_TYPES = frozenset({"pers", "ppde", "pers,gens", "pers,god"})
_PLACE_TYPES = frozenset({"topo", "gens,topo"})
_SKIP_TYPES = frozenset({"mens"})

_TOP_N = 250
_MIN_APPEARANCES = 2
_NOMINAL_FUNCTIONS = frozenset({"Subj", "Objc", "Cmpl", "PreC"})
_SAMPLE_LIMIT = 8


def _classify_nametype(nametype: str) -> str:
    if nametype in _PERSON_TYPES:
        return "person"
    if nametype in _PLACE_TYPES:
        return "place"
    if nametype in _SKIP_TYPES:
        return "skip"
    if "pers" in nametype:
        return "person"
    if "topo" in nametype:
        return "place"
    return "ambiguous"


class BHSASummaryBuilder:
    """Aggregates per-chapter narrative summary lines from clauses."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._current_ch: int | None = None
        self._clause_count: int = 0
        self._all_names: set[str] = set()
        self._verbs: list[str] = []
        self._verse_summaries: dict[int, list[str]] = {}

    def _flush_chapter(self) -> None:
        if self._current_ch is None:
            return
        self._lines.append(f"\n=== Chapter {self._current_ch} ({self._clause_count} clauses) ===")
        if self._all_names:
            self._lines.append(f"  Names: {', '.join(sorted(self._all_names))}")
        if self._verbs:
            self._lines.append(f"  Key verbs: {', '.join(self._verbs[:20])}")
        for v in sorted(self._verse_summaries.keys()):
            combined = " | ".join(self._verse_summaries[v][:3])
            self._lines.append(f"  v{v}: {combined[:200]}")

    def start_chapter(self, ch: int) -> None:
        self._flush_chapter()
        self._current_ch = ch
        self._clause_count = 0
        self._all_names = set()
        self._verbs = []
        self._verse_summaries = {}

    def consume(self, ch: int, clause: ClauseExtract) -> None:
        self._clause_count += 1
        v = clause["verse"]
        if v not in self._verse_summaries:
            self._verse_summaries[v] = []
        gloss = clause.get("gloss", "")
        if gloss:
            self._verse_summaries[v].append(gloss[:120])
        for name in clause.get("names", []):
            self._all_names.add(name)
        if clause.get("lemma"):
            self._verbs.append(
                f"{clause['lemma']} ({clause.get('binyan', '?')}/{clause.get('tense', '?')})"
            )

    def build(self) -> str:
        self._flush_chapter()
        return "\n".join(self._lines)


class BHSAEntitiesBuilder:
    """Aggregates proper-noun entities (names) across the book."""

    def __init__(self) -> None:
        self._appearances: dict[str, list[BHSAEntryRef]] = {}
        self._first: dict[str, BHSAEntryRef] = {}
        self._last: dict[str, BHSAEntryRef] = {}
        self._glosses: dict[str, str] = {}
        self._types: dict[str, str] = {}

    def consume(self, ch: int, clause: ClauseExtract) -> None:
        v = clause["verse"]
        ref: BHSAEntryRef = {"chapter": ch, "verse": v}

        for name in clause.get("names", []):
            if name not in self._appearances:
                self._appearances[name] = []
                self._first[name] = ref
            if not self._appearances[name] or self._appearances[name][-1] != ref:
                self._appearances[name].append(ref)
            self._last[name] = ref

        for heb_name, gloss in clause.get("name_glosses", {}).items():
            if heb_name not in self._glosses and gloss:
                self._glosses[heb_name] = gloss

        for heb_name, nt in clause.get("name_types", {}).items():
            if heb_name not in self._types and nt:
                self._types[heb_name] = nt

    def build(self) -> list[BHSAEntity]:
        entities: list[BHSAEntity] = []
        for name in sorted(self._appearances.keys()):
            raw_nametype = self._types.get(name, "")
            entity_type = _classify_nametype(raw_nametype) if raw_nametype else "ambiguous"
            if entity_type == "skip":
                continue
            entities.append(
                {
                    "name": name,
                    "english_gloss": self._glosses.get(name, ""),
                    "entity_type": entity_type,
                    "entry_verse": self._first[name],
                    "exit_verse": self._last[name],
                    "appears_in": self._appearances[name],
                    "appearance_count": len(self._appearances[name]),
                }
            )
        return entities


class BHSACommonNounsBuilder:
    """Aggregates common-noun / verb / adjective lemma candidates across the book."""

    def __init__(self) -> None:
        self._aggregates: dict[tuple[str, str], dict[str, Any]] = {}

    def consume(self, ch: int, clause: ClauseExtract) -> None:
        v = clause["verse"]
        ref: BHSAEntryRef = {"chapter": ch, "verse": v}
        for cw in clause.get("content_words", []):
            key_lex = cw.get("lex_utf8") or cw.get("lex")
            sp = cw.get("sp")
            if not key_lex or not sp:
                continue
            key = (key_lex, sp)

            bucket = self._aggregates.get(key)
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
                self._aggregates[key] = bucket

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

    def build(self) -> list[CommonNounCandidate]:
        candidates: list[CommonNounCandidate] = []
        for bucket in self._aggregates.values():
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
        return candidates[:_TOP_N]


def collect_bhsa_data(tf_api: Any, book_name: str, chapter_count: int) -> CollectBHSAOutput:
    """Single-pass BHSA collection: streams clauses once and feeds three builders."""

    summary_b = BHSASummaryBuilder()
    entities_b = BHSAEntitiesBuilder()
    common_b = BHSACommonNounsBuilder()

    for chapter_data in stream_book_clauses(tf_api, book_name, chapter_count):
        ch = chapter_data["chapter"]
        summary_b.start_chapter(ch)
        for clause in chapter_data["clauses"]:
            summary_b.consume(ch, clause)
            entities_b.consume(ch, clause)
            common_b.consume(ch, clause)

    return {
        "bhsa_summary": summary_b.build(),
        "bhsa_entities": entities_b.build(),
        "bhsa_common_nouns": common_b.build(),
    }
