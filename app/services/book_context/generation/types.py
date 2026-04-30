from __future__ import annotations

from typing import NotRequired, TypedDict


class BHSAEntryRef(TypedDict):
    chapter: int
    verse: int


class ContentWordEntry(TypedDict):
    lex_utf8: str | None
    lex: str | None
    sp: str
    gloss: str
    pdp: str | None
    function: str | None
    binyan: NotRequired[str | None]
    tense: NotRequired[str | None]


class ClauseExtract(TypedDict):
    clause_id: int
    verse: int
    text: str
    gloss: str
    clause_type: str
    is_mainline: bool
    chain_position: str
    lemma: str | None
    lemma_ascii: str | None
    binyan: str | None
    tense: str | None
    subjects: list[str]
    objects: list[str]
    has_ki: bool
    names: list[str]
    name_glosses: dict[str, str]
    name_types: dict[str, str]
    content_words: list[ContentWordEntry]


class BHSAEntity(TypedDict):
    name: str
    english_gloss: str
    entity_type: str
    entry_verse: BHSAEntryRef
    exit_verse: BHSAEntryRef
    appears_in: list[BHSAEntryRef]
    appearance_count: int


class CommonNounCandidate(TypedDict):
    lemma: str | None
    lemma_ascii: str | None
    english_gloss: str
    sp: str
    appearance_count: int
    top_functions: list[str]
    top_binyans: list[str]
    first_appears: BHSAEntryRef
    sample_appears_in: list[BHSAEntryRef]


class CollectBHSAOutput(TypedDict):
    bhsa_summary: str
    bhsa_entities: list[BHSAEntity]
    bhsa_common_nouns: list[CommonNounCandidate]
