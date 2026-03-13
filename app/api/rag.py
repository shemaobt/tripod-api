from fastapi import APIRouter, Depends, UploadFile, status

from app.core.access_control import require_app_access, require_role
from app.core.auth_middleware import get_current_user
from app.core.exceptions import ValidationError
from app.core.qdrant import get_qdrant_client
from app.db.models.auth import User
from app.models.rag import (
    DeleteDocumentResponse,
    DocumentInfo,
    DocumentUploadResponse,
    QueryRequest,
    QueryResponse,
    RagNamespace,
)
from app.services import rag_service

router = APIRouter()
_mm_access = require_app_access("meaning-map-generator")
_mm_admin = require_role("meaning-map-generator", "admin")


@router.post(
    "/{namespace}/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    namespace: RagNamespace,
    file: UploadFile,
    _: User = _mm_admin,
) -> DocumentUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise ValidationError("Only .md files are supported")

    content = (await file.read()).decode("utf-8")
    client = get_qdrant_client()
    return await rag_service.upload_document(client, namespace, file.filename, content)


@router.post("/{namespace}/query", response_model=QueryResponse, dependencies=[_mm_access])
async def query_documents(
    namespace: RagNamespace,
    payload: QueryRequest,
    _: User = Depends(get_current_user),
) -> QueryResponse:
    client = get_qdrant_client()
    return await rag_service.query(client, namespace, payload.question, payload.top_k)


@router.get("/{namespace}/documents", response_model=list[DocumentInfo], dependencies=[_mm_access])
async def list_documents(
    namespace: RagNamespace,
    _: User = Depends(get_current_user),
) -> list[DocumentInfo]:
    client = get_qdrant_client()
    return await rag_service.list_documents(client, namespace)


@router.delete(
    "/{namespace}/documents/{doc_id}",
    response_model=DeleteDocumentResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_document(
    namespace: RagNamespace,
    doc_id: str,
    _: User = _mm_admin,
) -> DeleteDocumentResponse:
    client = get_qdrant_client()
    deleted = await rag_service.delete_document(client, namespace, doc_id)
    return DeleteDocumentResponse(deleted_chunks=deleted, doc_id=doc_id)
