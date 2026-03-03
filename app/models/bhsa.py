from __future__ import annotations

from pydantic import BaseModel


class ClauseData(BaseModel):
    clause_id: int
    verse: int
    text: str
    gloss: str
    clause_type: str
    is_mainline: bool
    chain_position: str
    lemma: str | None = None
    lemma_ascii: str | None = None
    binyan: str | None = None
    tense: str | None = None
    subjects: list[str] = []
    objects: list[str] = []
    has_ki: bool = False
    names: list[str] = []


class PassageResponse(BaseModel):
    reference: str
    source_lang: str = "hbo"
    clauses: list[ClauseData]


class BHSAStatusResponse(BaseModel):
    status: str
    bhsa_loaded: bool
    message: str
