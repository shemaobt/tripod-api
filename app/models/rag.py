from enum import StrEnum

from pydantic import BaseModel, Field


class RagNamespace(StrEnum):
    MEANING_MAP_DOCS = "meaning-map-docs"


class SourceChunk(BaseModel):
    filename: str
    chunk_index: int
    text: str
    score: float


class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    namespace: str
    chunk_count: int


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    namespace: str
    chunk_count: int
    uploaded_at: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


class DeleteDocumentResponse(BaseModel):
    deleted_chunks: int
    doc_id: str
