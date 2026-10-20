"""
FastAPI router for external connectors (Slack, Google Drive, GitHub, etc).

Handles connector lifecycle: creation, authentication, indexing, and unified search.
"""

from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/connectors", tags=["connectors"])


class ConnectorCredentials(BaseModel):
    """Credentials for connector authentication."""
    token: Optional[str] = Field(None, description="API token or password")
    api_key: Optional[str] = Field(None, description="API key")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")
    base_url: Optional[str] = Field(None, description="Base URL for self-hosted services")
    custom_config: Optional[dict] = Field(None, description="Custom configuration")


class CreateConnectorRequest(BaseModel):
    """Request to create a new connector."""
    connector_type: str = Field(
        ...,
        description="Type of connector: slack, google_drive, github, jira, email, etc"
    )
    name: str = Field(..., description="User-friendly name for the connector")
    credentials: ConnectorCredentials = Field(..., description="Authentication credentials")
    auto_index: bool = Field(True, description="Automatically index on schedule")
    index_interval_minutes: int = Field(60, description="Index frequency in minutes")


class ConnectorInfo(BaseModel):
    """Information about a connector."""
    connector_id: str = Field(..., description="Unique connector ID")
    connector_type: str = Field(..., description="Type of connector")
    name: str = Field(..., description="User-friendly name")
    status: str = Field(..., description="Status: active, inactive, error")
    indexed_items: int = Field(0, description="Number of indexed items")
    last_indexed: Optional[str] = Field(None, description="Last indexing timestamp")
    created_at: str = Field(..., description="Creation timestamp")
    error_message: Optional[str] = Field(None, description="Last error if any")


class ConnectorListResponse(BaseModel):
    """Response containing list of connectors."""
    connectors: List[ConnectorInfo] = Field(..., description="List of configured connectors")
    total_count: int = Field(..., description="Total number of connectors")


class IndexConnectorRequest(BaseModel):
    """Request to index a connector."""
    connector_id: str = Field(..., description="Connector ID to index")
    full_index: bool = Field(False, description="Perform full reindex vs incremental")


class IndexConnectorResponse(BaseModel):
    """Response from connector indexing."""
    connector_id: str = Field(..., description="Connector ID")
    status: str = Field(..., description="Status: started, completed, failed")
    indexed_items: int = Field(..., description="Number of items indexed")
    duration_seconds: float = Field(..., description="Indexing duration")
    message: str = Field(..., description="Status message")


class SearchResult(BaseModel):
    """Single search result across connectors."""
    connector_id: str = Field(..., description="Source connector ID")
    connector_type: str = Field(..., description="Type of source connector")
    item_id: str = Field(..., description="ID within source system")
    title: str = Field(..., description="Result title")
    snippet: str = Field(..., description="Preview text snippet")
    source_url: str = Field(..., description="Link back to original")
    relevance_score: float = Field(..., description="Relevance score 0-1")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class UnifiedSearchRequest(BaseModel):
    """Request for unified search across connectors."""
    query: str = Field(..., description="Search query")
    connector_ids: Optional[List[str]] = Field(
        None,
        description="Specific connectors to search (None = all)"
    )
    limit: int = Field(10, description="Max results per connector")
    offset: int = Field(0, description="Results offset for pagination")


class UnifiedSearchResponse(BaseModel):
    """Response from unified search."""
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total results across all connectors")
    search_time_ms: float = Field(..., description="Query execution time")


class DeleteConnectorRequest(BaseModel):
    """Request to delete a connector."""
    connector_id: str = Field(..., description="Connector ID to delete")
    delete_indexed_data: bool = Field(
        True,
        description="Whether to delete indexed data from Qdrant"
    )


class DeleteConnectorResponse(BaseModel):
    """Response from connector deletion."""
    connector_id: str = Field(..., description="Deleted connector ID")
    status: str = Field(..., description="Status: deleted, error")
    message: str = Field(..., description="Status message")


# Import connector manager (lazy to avoid circular imports)
async def get_connector_manager():
    """Get connector manager singleton."""
    from ...capabilities.connectors import get_connector_manager as gcm
    return gcm()


@router.get("/", response_model=ConnectorListResponse)
async def list_connectors() -> ConnectorListResponse:
    """
    List all configured connectors.

    Returns:
        ConnectorListResponse with list of connectors and metadata

    Raises:
        HTTPException: If operation fails
    """
    try:
        manager = await get_connector_manager()
        connectors = await manager.list_connectors()

        return ConnectorListResponse(
            connectors=[
                ConnectorInfo(
                    connector_id=c.get("id"),
                    connector_type=c.get("type"),
                    name=c.get("name"),
                    status=c.get("status", "inactive"),
                    indexed_items=c.get("indexed_items", 0),
                    last_indexed=c.get("last_indexed"),
                    created_at=c.get("created_at"),
                    error_message=c.get("error")
                )
                for c in connectors
            ],
            total_count=len(connectors)
        )

    except Exception as e:
        logger.error(f"Failed to list connectors: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list connectors: {str(e)}"
        )


@router.post("/create", response_model=ConnectorInfo)
async def create_connector(
    request: CreateConnectorRequest
) -> ConnectorInfo:
    """
    Create a new connector.

    Args:
        request: CreateConnectorRequest with connector details

    Returns:
        ConnectorInfo for the created connector

    Raises:
        HTTPException: If creation fails
    """
    try:
        manager = await get_connector_manager()

        connector_id = await manager.create_connector(
            connector_type=request.connector_type,
            name=request.name,
            credentials=request.credentials.dict(),
            auto_index=request.auto_index,
            index_interval=request.index_interval_minutes
        )

        connector_data = await manager.get_connector(connector_id)

        return ConnectorInfo(
            connector_id=connector_id,
            connector_type=request.connector_type,
            name=request.name,
            status="inactive",
            indexed_items=0,
            created_at=connector_data.get("created_at", ""),
            error_message=None
        )

    except ValueError as e:
        logger.warning(f"Invalid connector request: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to create connector: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create connector: {str(e)}"
        )


@router.post("/{connector_id}/index", response_model=IndexConnectorResponse)
async def index_connector(
    connector_id: str,
    request: IndexConnectorRequest,
    background_tasks: BackgroundTasks
) -> IndexConnectorResponse:
    """
    Trigger indexing for a connector.

    Runs as background task to avoid timeout.

    Args:
        connector_id: Connector ID to index
        request: IndexConnectorRequest with indexing options
        background_tasks: FastAPI background task handler

    Returns:
        IndexConnectorResponse with indexing status

    Raises:
        HTTPException: If connector not found or indexing fails
    """
    try:
        manager = await get_connector_manager()

        # Verify connector exists
        connector = await manager.get_connector(connector_id)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"Connector {connector_id} not found"
            )

        # Start indexing in background
        async def run_indexing():
            try:
                result = await manager.index_connector(
                    connector_id,
                    full_index=request.full_index
                )
                logger.info(f"Indexed {connector_id}: {result}")
            except Exception as e:
                logger.error(f"Indexing failed for {connector_id}: {e}")

        background_tasks.add_task(run_indexing)

        return IndexConnectorResponse(
            connector_id=connector_id,
            status="started",
            indexed_items=0,
            duration_seconds=0,
            message="Indexing started in background"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start indexing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start indexing: {str(e)}"
        )


@router.post("/search", response_model=UnifiedSearchResponse)
async def unified_search(
    request: UnifiedSearchRequest
) -> UnifiedSearchResponse:
    """
    Search across all or specified connectors.

    Args:
        request: UnifiedSearchRequest with query and options

    Returns:
        UnifiedSearchResponse with results from all connectors

    Raises:
        HTTPException: If search fails
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="Search query cannot be empty"
            )

        manager = await get_connector_manager()

        import time
        start_time = time.time()

        results = await manager.search_connectors(
            query=request.query,
            connector_ids=request.connector_ids,
            limit=request.limit,
            offset=request.offset
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return UnifiedSearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    connector_id=r.get("connector_id"),
                    connector_type=r.get("connector_type"),
                    item_id=r.get("item_id"),
                    title=r.get("title"),
                    snippet=r.get("snippet"),
                    source_url=r.get("source_url"),
                    relevance_score=r.get("relevance_score", 0.5),
                    metadata=r.get("metadata")
                )
                for r in results
            ],
            total_count=len(results),
            search_time_ms=elapsed_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.delete("/{connector_id}", response_model=DeleteConnectorResponse)
async def delete_connector(
    connector_id: str,
    request: DeleteConnectorRequest
) -> DeleteConnectorResponse:
    """
    Delete a connector and optionally its indexed data.

    Args:
        connector_id: Connector ID to delete
        request: DeleteConnectorRequest with deletion options

    Returns:
        DeleteConnectorResponse with deletion status

    Raises:
        HTTPException: If connector not found
    """
    try:
        manager = await get_connector_manager()

        # Verify connector exists
        connector = await manager.get_connector(connector_id)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"Connector {connector_id} not found"
            )

        # Delete connector
        await manager.delete_connector(
            connector_id,
            delete_indexed_data=request.delete_indexed_data
        )

        return DeleteConnectorResponse(
            connector_id=connector_id,
            status="deleted",
            message=f"Connector {connector_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete connector {connector_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete connector: {str(e)}"
        )
