RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based ONLY on the "
    "following context extracted from documents. If the context does not contain "
    "enough information to answer, say so clearly."
)

NO_CONTEXT_ANSWER = (
    "I don't have enough information in the provided documents to answer this question."
)

CONTEXT_SEPARATOR = "\n\n---\n\n"


def build_rag_prompt(context_parts: list[str], question: str) -> str:
    """Build the RAG prompt from retrieved context chunks and a user question."""
    context = CONTEXT_SEPARATOR.join(context_parts)
    return f"{RAG_SYSTEM_PROMPT}\n\n## Context\n\n{context}\n\n## Question\n\n{question}"
