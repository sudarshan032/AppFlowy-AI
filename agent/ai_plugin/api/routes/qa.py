"""
Workspace Q&A API Routes

FastAPI routes for RAG-based workspace Q&A.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ...capabilities.workspace_qa import get_workspace_qa, Document


router = APIRouter(prefix="/ai/qa", tags=["Workspace Q&A"])


class DocumentInput(BaseModel):
    """Input for indexing a document."""
    id: Optional[str] = None
    title: str
    content: str
    metadata: Dict[str, Any] = {}


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str
    top_k: int = 5


class AskRequest(BaseModel):
    """Request for Q&A."""
    question: str
    context_docs: Optional[List[str]] = None


@router.post("/index")
async def index_document(doc: DocumentInput):
    """Index a document for Q&A."""
    try:
        qa = get_workspace_qa()
        doc_id = qa.index_document(Document(
            id=doc.id or "",
            title=doc.title,
            content=doc.content,
            metadata=doc.metadata
        ))
        return {"success": True, "document_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index-batch")
async def index_documents(docs: List[DocumentInput]):
    """Index multiple documents."""
    try:
        qa = get_workspace_qa()
        documents = [
            Document(
                id=doc.id or "",
                title=doc.title,
                content=doc.content,
                metadata=doc.metadata
            )
            for doc in docs
        ]
        doc_ids = qa.index_documents(documents)
        return {"success": True, "document_ids": doc_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{doc_id}")
async def remove_document(doc_id: str):
    """Remove a document from the index."""
    qa = get_workspace_qa()
    removed = qa.remove_document(doc_id)
    return {"success": removed}


@router.get("/documents")
async def list_documents():
    """List all indexed documents."""
    qa = get_workspace_qa()
    return {"documents": qa.list_documents()}


@router.post("/search")
async def search(request: SearchRequest):
    """Search documents for relevant content."""
    try:
        qa = get_workspace_qa()
        results = await qa.search(request.query, request.top_k)
        return {"results": [r.model_dump() for r in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def ask(request: AskRequest):
    """Ask a question about the workspace."""
    try:
        qa = get_workspace_qa()
        response = await qa.ask(request.question, request.context_docs)
        return response.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def summarize_workspace():
    """Get a summary of the workspace."""
    try:
        qa = get_workspace_qa()
        summary = await qa.summarize_workspace()
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
