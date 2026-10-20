"""
Workspace Q&A Engine — Phase 2

RAG-based question answering over workspace content:
- Semantic vector search via Qdrant
- Answer questions with source citations
- Page indexing and knowledge retrieval
- Workspace-wide search capability
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from ..core import get_engine
from ...db.vector_store import VectorStore
from ...db.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

WORKSPACE_QA_COLLECTION = "workspace_pages"


@dataclass
class Citation:
    """Source citation for Q&A answers."""
    page_title: str
    page_id: str
    relevance_score: float
    content_snippet: Optional[str] = None


@dataclass
class QAResult:
    """Result of a Q&A query."""
    answer: str
    citations: List[Citation]
    confidence: float


class WorkspaceQA:
    """
    RAG-based Q&A over workspace content using vector search.

    Provides:
    - Semantic indexing via Qdrant vector database
    - Question answering with source citations
    - Confidence scoring
    - Workspace page search
    """

    def __init__(self, vector_store: Optional[VectorStore] = None,
                 embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize WorkspaceQA engine.

        Args:
            vector_store: VectorStore instance (creates default if None)
            embedding_service: EmbeddingService instance (creates default if None)
        """
        self.vector_store = vector_store or VectorStore()
        self.embedding_service = embedding_service or EmbeddingService()
        self.llm = get_engine()

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensure Qdrant collection exists for workspace pages."""
        try:
            self.vector_store.ensure_collection(
                name=WORKSPACE_QA_COLLECTION,
                dimension=768  # nomic-embed-text
            )
        except Exception as e:
            logger.error(f"Error creating collection: {e}")

    async def index_page(
        self,
        page_id: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Index a single page into the workspace Q&A collection.

        Args:
            page_id: Unique identifier for the page
            title: Page title
            content: Full page content (text)
            metadata: Optional metadata (author, created_at, etc.)

        Returns:
            Point ID in Qdrant
        """
        try:
            # Generate embedding for page content
            embedding = await self.embedding_service.embed([content])
            if not embedding or not embedding[0]:
                logger.warning(f"Failed to embed page {page_id}")
                return None

            # Prepare metadata
            page_metadata = {
                "page_id": page_id,
                "title": title,
                "content": content,
                "type": "page",
                **(metadata or {})
            }

            # Add to Qdrant
            self.vector_store.add_record(
                record_id=f"page_{page_id}",
                text=content,
                embedding=embedding[0],
                metadata=page_metadata,
                collection_name=WORKSPACE_QA_COLLECTION
            )

            logger.info(f"Indexed page {page_id}: {title}")
            return f"page_{page_id}"

        except Exception as e:
            logger.error(f"Error indexing page {page_id}: {e}")
            raise

    async def index_all_pages(self, db_session: Session) -> int:
        """
        Index all pages from the database into Qdrant.

        Args:
            db_session: SQLAlchemy session

        Returns:
            Number of pages indexed
        """
        try:
            from ...db.models import Page

            pages = db_session.query(Page).all()
            indexed_count = 0

            for page in pages:
                try:
                    # Extract text content from page blocks
                    content = self._extract_text_from_page(page)

                    if content.strip():
                        await self.index_page(
                            page_id=str(page.id),
                            title=page.title,
                            content=content,
                            metadata={
                                "created_at": str(page.created_at),
                                "updated_at": str(page.updated_at),
                            }
                        )
                        indexed_count += 1

                except Exception as e:
                    logger.error(f"Error indexing page {page.id}: {e}")
                    continue

            logger.info(f"Indexed {indexed_count} pages total")
            return indexed_count

        except Exception as e:
            logger.error(f"Error during full page indexing: {e}")
            raise

    async def get_sources(
        self,
        question: str,
        top_k: int = 5
    ) -> List[Citation]:
        """
        Retrieve relevant source documents for a question.

        Args:
            question: User's question
            top_k: Number of top results to return

        Returns:
            List of source citations with relevance scores
        """
        try:
            # Embed the question
            question_embedding = await self.embedding_service.embed([question])
            if not question_embedding or not question_embedding[0]:
                logger.warning(f"Failed to embed question")
                return []

            # Search for relevant pages
            results = self.vector_store.search(
                query_embedding=question_embedding[0],
                top_k=top_k,
                collection_name=WORKSPACE_QA_COLLECTION
            )

            citations = []
            for result in results:
                payload = result.get("payload", {})
                citations.append(
                    Citation(
                        page_title=payload.get("title", "Unknown"),
                        page_id=payload.get("page_id", ""),
                        relevance_score=result.get("score", 0.0),
                        content_snippet=payload.get("content", "")[:300]
                    )
                )

            logger.info(f"Found {len(citations)} relevant sources")
            return citations

        except Exception as e:
            logger.error(f"Error retrieving sources: {e}")
            return []

    async def ask(
        self,
        question: str,
        top_k: int = 5,
        include_citations: bool = True
    ) -> QAResult:
        """
        Answer a natural language question about the workspace.

        Args:
            question: User's natural language question
            top_k: Number of source documents to retrieve
            include_citations: Whether to include source citations

        Returns:
            QAResult with answer text and citations
        """
        try:
            # Get relevant sources
            citations = await self.get_sources(question, top_k)

            if not citations:
                logger.warning("No relevant sources found")
                return QAResult(
                    answer="I couldn't find any relevant information in your workspace to answer this question.",
                    citations=[],
                    confidence=0.0
                )

            # Build context from retrieved sources
            context = self._build_context(citations)

            # Generate answer using LLM
            system_prompt = """You are a helpful assistant answering questions about the user's workspace.
Use the provided context to answer accurately. If information isn't available, say so explicitly."""

            answer_prompt = f"""Context from workspace pages:
{context}

Question: {question}

Please answer based on the context above:"""

            answer = await self.llm.generate(
                prompt=answer_prompt,
                temperature=0.3,
                max_tokens=1000
            )

            # Calculate confidence
            avg_score = sum(c.relevance_score for c in citations) / len(citations) if citations else 0.0
            confidence = min(avg_score, 1.0)

            logger.info(f"Generated answer with confidence {confidence:.2f}")

            return QAResult(
                answer=answer.strip(),
                citations=citations if include_citations else [],
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Error during Q&A: {e}")
            raise

    def _extract_text_from_page(self, page: Any) -> str:
        """Extract text from page object."""
        if hasattr(page, 'content'):
            content = page.content
            if isinstance(content, str):
                return content
            elif isinstance(content, dict):
                # Extract from block structure
                parts = []
                if "blocks" in content:
                    for block in content["blocks"]:
                        if isinstance(block, dict) and "content" in block:
                            parts.append(str(block["content"]))
                if parts:
                    return " ".join(parts)

        return getattr(page, 'title', '')

    def _build_context(self, citations: List[Citation]) -> str:
        """Build context string from citations."""
        context_parts = []
        for i, citation in enumerate(citations, 1):
            context_parts.append(
                f"[Source {i}: {citation.page_title}]\n{citation.content_snippet}\n"
            )
        return "\n".join(context_parts) if context_parts else "No context available"


# Singleton instance
_workspace_qa: Optional[WorkspaceQA] = None


def get_workspace_qa() -> WorkspaceQA:
    """Get WorkspaceQA singleton."""
    global _workspace_qa
    if _workspace_qa is None:
        _workspace_qa = WorkspaceQA()
    return _workspace_qa
