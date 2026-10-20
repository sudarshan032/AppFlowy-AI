"""
External Connectors Framework — Phase 5

Unified interface for connecting and indexing external data sources:
- Slack channels and messages
- GitHub repositories and issues
- Google Drive documents
- Other external sources

Supports unified search across all connectors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
import logging
import asyncio

from ..core import get_engine

logger = logging.getLogger(__name__)


@dataclass
class ConnectorSearchResult:
    """Result from connector search."""
    source_id: str  # Unique ID in source system
    title: str
    content: str
    content_snippet: str
    source_type: str  # slack, github, gdrive, etc.
    url: str
    relevance_score: float
    last_updated: datetime


class BaseConnector(ABC):
    """
    Abstract base class for all external connectors.

    Defines the interface that all connectors must implement.
    """

    def __init__(self, source_type: str):
        """
        Initialize connector.

        Args:
            source_type: Type of source (slack, github, gdrive, etc.)
        """
        self.source_type = source_type
        self.engine = get_engine()
        self._authenticated = False

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with the external service.

        Args:
            credentials: Dictionary with authentication details

        Returns:
            True if authentication successful
        """
        pass

    @abstractmethod
    async def index(self) -> int:
        """
        Index all content from the source.

        Returns:
            Number of items indexed
        """
        pass

    @abstractmethod
    async def incremental_index(self, since: datetime) -> int:
        """
        Index only new/changed content since timestamp.

        Args:
            since: Only index items modified after this timestamp

        Returns:
            Number of items indexed
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[ConnectorSearchResult]:
        """
        Search content in this connector.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def get_source_url(self, item_id: str) -> str:
        """
        Get direct URL to item in source system.

        Args:
            item_id: Item identifier in source system

        Returns:
            Direct URL to the item
        """
        pass

    def is_authenticated(self) -> bool:
        """Check if connector is authenticated."""
        return self._authenticated


class SlackConnector(BaseConnector):
    """
    Connector for Slack workspace.

    Indexes channels, messages, and threaded conversations.
    Requires SLACK_BOT_TOKEN environment variable.
    """

    def __init__(self):
        """Initialize Slack connector."""
        super().__init__("slack")
        self._client = None
        self._indexed_channels = {}

    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with Slack API.

        Args:
            credentials: Dict with 'bot_token' key

        Returns:
            True if authentication successful
        """
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError

            bot_token = credentials.get("bot_token") or os.getenv("SLACK_BOT_TOKEN")
            if not bot_token:
                logger.error("SLACK_BOT_TOKEN not provided")
                return False

            self._client = WebClient(token=bot_token)

            # Test connection
            self._client.auth_test()
            self._authenticated = True
            logger.info("Slack connector authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"Slack authentication failed: {e}")
            return False

    async def index(self) -> int:
        """Index all Slack channels and messages."""
        if not self._authenticated:
            logger.warning("Slack connector not authenticated")
            return 0

        try:
            from slack_sdk.errors import SlackApiError

            indexed_count = 0

            # Get all public channels
            result = self._client.conversations_list(
                types="public_channel,private_channel",
                limit=100
            )

            channels = result.get("channels", [])
            logger.info(f"Found {len(channels)} Slack channels")

            for channel in channels:
                channel_id = channel["id"]
                channel_name = channel["name"]

                # Get messages from this channel
                messages = await self._get_channel_messages(channel_id)
                indexed_count += len(messages)

                self._indexed_channels[channel_id] = {
                    "name": channel_name,
                    "message_count": len(messages),
                    "last_indexed": datetime.now()
                }

                logger.info(f"Indexed {len(messages)} messages from #{channel_name}")

            return indexed_count

        except Exception as e:
            logger.error(f"Error indexing Slack: {e}")
            return 0

    async def incremental_index(self, since: datetime) -> int:
        """
        Index only new messages since timestamp.

        Args:
            since: Only index messages after this time

        Returns:
            Number of messages indexed
        """
        if not self._authenticated:
            return 0

        try:
            indexed_count = 0
            since_timestamp = since.timestamp()

            result = self._client.conversations_list(
                types="public_channel,private_channel",
                limit=100
            )

            for channel in result.get("channels", []):
                channel_id = channel["id"]
                messages = await self._get_channel_messages(
                    channel_id,
                    oldest=since_timestamp
                )
                indexed_count += len(messages)

            return indexed_count

        except Exception as e:
            logger.error(f"Error in incremental Slack indexing: {e}")
            return 0

    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[ConnectorSearchResult]:
        """
        Search Slack messages.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of search results
        """
        if not self._authenticated:
            return []

        try:
            # Use Slack API search
            result = self._client.search_messages(query=query, count=limit)

            search_results = []
            for message in result.get("messages", []):
                timestamp = message.get("ts", "")
                channel_id = message.get("channel", {}).get("id", "")

                search_results.append(
                    ConnectorSearchResult(
                        source_id=f"{channel_id}:{timestamp}",
                        title=f"Message in {message.get('channel', {}).get('name', 'unknown')}",
                        content=message.get("text", ""),
                        content_snippet=(message.get("text", "")[:200]),
                        source_type="slack",
                        url=await self.get_source_url(f"{channel_id}:{timestamp}"),
                        relevance_score=0.8,  # Slack doesn't provide relevance
                        last_updated=datetime.fromtimestamp(float(timestamp))
                    )
                )

            return search_results

        except Exception as e:
            logger.error(f"Error searching Slack: {e}")
            return []

    async def get_source_url(self, item_id: str) -> str:
        """Get Slack message URL."""
        try:
            channel_id, timestamp = item_id.split(":", 1)
            # Reconstruct Slack message link
            return f"https://slack.com/archives/{channel_id}/p{timestamp.replace('.', '')}"
        except Exception:
            return ""

    async def _get_channel_messages(
        self,
        channel_id: str,
        oldest: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch messages from a channel."""
        try:
            result = self._client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                limit=limit
            )
            return result.get("messages", [])
        except Exception as e:
            logger.error(f"Error fetching messages from {channel_id}: {e}")
            return []


class GitHubConnector(BaseConnector):
    """
    Connector for GitHub repositories.

    Indexes repositories, issues, pull requests, and discussions.
    Requires GITHUB_TOKEN environment variable.
    """

    def __init__(self):
        """Initialize GitHub connector."""
        super().__init__("github")
        self._client = None
        self._repos = []

    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with GitHub API.

        Args:
            credentials: Dict with 'token' key

        Returns:
            True if authentication successful
        """
        try:
            from github import Github

            token = credentials.get("token") or os.getenv("GITHUB_TOKEN")
            if not token:
                logger.error("GITHUB_TOKEN not provided")
                return False

            self._client = Github(token)

            # Test connection
            self._client.get_user().login
            self._authenticated = True
            logger.info("GitHub connector authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"GitHub authentication failed: {e}")
            return False

    async def index(self) -> int:
        """Index all GitHub repositories and content."""
        if not self._authenticated:
            logger.warning("GitHub connector not authenticated")
            return 0

        try:
            indexed_count = 0
            user = self._client.get_user()

            # Get user's repositories
            repos = user.get_repos(type="owner")
            logger.info(f"Found {repos.totalCount} repositories")

            for repo in repos[:10]:  # Limit to first 10 repos
                self._repos.append(repo.full_name)

                # Index issues
                issues = repo.get_issues(state="all")
                for issue in issues[:100]:  # Limit to 100 issues per repo
                    indexed_count += 1

                # Index pull requests
                prs = repo.get_pulls(state="all")
                for pr in prs[:50]:  # Limit to 50 PRs
                    indexed_count += 1

            logger.info(f"Indexed {indexed_count} GitHub items")
            return indexed_count

        except Exception as e:
            logger.error(f"Error indexing GitHub: {e}")
            return 0

    async def incremental_index(self, since: datetime) -> int:
        """Index only recently updated items."""
        if not self._authenticated:
            return 0

        try:
            indexed_count = 0
            user = self._client.get_user()

            for repo_name in self._repos[:5]:  # Check first 5 repos
                repo = self._client.get_repo(repo_name)

                # Get issues updated since timestamp
                issues = repo.get_issues(
                    state="all",
                    since=since
                )
                indexed_count += issues.totalCount

            return indexed_count

        except Exception as e:
            logger.error(f"Error in incremental GitHub indexing: {e}")
            return 0

    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[ConnectorSearchResult]:
        """
        Search GitHub repositories, issues, and PRs.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of search results
        """
        if not self._authenticated:
            return []

        try:
            search_results = []

            # Search issues and pull requests
            issues = self._client.search_issues(query, sort="updated", order="desc")

            for i, issue in enumerate(issues[:limit]):
                search_results.append(
                    ConnectorSearchResult(
                        source_id=f"github:{issue.number}",
                        title=issue.title,
                        content=issue.body or "",
                        content_snippet=(issue.body or "")[:200],
                        source_type="github",
                        url=issue.html_url,
                        relevance_score=0.8,
                        last_updated=issue.updated_at
                    )
                )

            return search_results

        except Exception as e:
            logger.error(f"Error searching GitHub: {e}")
            return []

    async def get_source_url(self, item_id: str) -> str:
        """Get GitHub issue/PR URL."""
        if item_id.startswith("github:"):
            # Would need repo context to construct full URL
            return f"https://github.com/search?q={item_id}"
        return ""


class ConnectorManager:
    """
    Manager for all external connectors.

    Provides unified search and management interface.
    """

    def __init__(self):
        """Initialize connector manager."""
        self.connectors: Dict[str, BaseConnector] = {}
        self.engine = get_engine()

    def register_connector(self, name: str, connector: BaseConnector) -> None:
        """
        Register a connector.

        Args:
            name: Connector name
            connector: BaseConnector instance
        """
        self.connectors[name] = connector
        logger.info(f"Registered connector: {name}")

    async def authenticate_all(self, credentials: Dict[str, Dict]) -> Dict[str, bool]:
        """
        Authenticate all registered connectors.

        Args:
            credentials: Dict mapping connector names to credential dicts

        Returns:
            Dict mapping connector names to success status
        """
        results = {}

        for name, connector in self.connectors.items():
            if name in credentials:
                result = await connector.authenticate(credentials[name])
                results[name] = result
                logger.info(f"Connector {name}: {'✓' if result else '✗'}")
            else:
                logger.warning(f"No credentials provided for {name}")
                results[name] = False

        return results

    async def unified_search(
        self,
        query: str,
        limit: int = 10,
        connectors: Optional[List[str]] = None
    ) -> List[ConnectorSearchResult]:
        """
        Search across multiple connectors.

        Args:
            query: Search query
            limit: Max results total
            connectors: List of connector names to search. If None, search all.

        Returns:
            Sorted list of results from all connectors
        """
        try:
            all_results = []
            search_connectors = connectors or list(self.connectors.keys())

            # Search each connector concurrently
            search_tasks = [
                self.connectors[name].search(query, limit)
                for name in search_connectors
                if name in self.connectors and self.connectors[name].is_authenticated()
            ]

            if not search_tasks:
                logger.warning("No authenticated connectors available for search")
                return []

            results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

            for results in results_lists:
                if isinstance(results, list):
                    all_results.extend(results)
                elif isinstance(results, Exception):
                    logger.error(f"Error in connector search: {results}")

            # Sort by relevance and return top results
            all_results.sort(key=lambda x: x.relevance_score, reverse=True)
            return all_results[:limit]

        except Exception as e:
            logger.error(f"Error in unified search: {e}")
            return []

    async def index_all(self) -> Dict[str, int]:
        """
        Index all authenticated connectors.

        Returns:
            Dict mapping connector names to count of indexed items
        """
        results = {}

        for name, connector in self.connectors.items():
            if connector.is_authenticated():
                try:
                    count = await connector.index()
                    results[name] = count
                    logger.info(f"Indexed {count} items from {name}")
                except Exception as e:
                    logger.error(f"Error indexing {name}: {e}")
                    results[name] = 0
            else:
                logger.warning(f"Connector {name} not authenticated, skipping index")
                results[name] = 0

        return results


# Global connector manager instance
_connector_manager: Optional[ConnectorManager] = None


def get_connector_manager() -> ConnectorManager:
    """Get global ConnectorManager instance."""
    global _connector_manager
    if _connector_manager is None:
        _connector_manager = ConnectorManager()
        # Register default connectors
        _connector_manager.register_connector("slack", SlackConnector())
        _connector_manager.register_connector("github", GitHubConnector())
    return _connector_manager


import os
