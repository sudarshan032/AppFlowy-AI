"""
AI Plugin Capabilities Module.

Exports all AI capability classes and singleton getter functions for the AppFlowy AI system.

Available capabilities:
- WritingAI: Text writing improvements and transformations
- WorkspaceQA: Natural language Q&A over workspace content
- DatabaseAI: AI-powered database operations and autofill
- AgentExecutor: Autonomous AI agent execution
- MeetingNotesAI: Meeting transcription and summarization
- ConnectorManager: External connector management and unified search
- SitesAI: Notion Sites AI (SEO, content generation)
- ImageGenerator: AI image generation capabilities
- TranslationAI: Multi-language text translation
"""

# Import capability classes and getters
from .writing import WritingAI, get_writing_ai
from .workspace_qa import WorkspaceQA, get_workspace_qa
from .database_ai import DatabaseAI, get_database_ai
from .agents import AgentExecutor, get_agent_executor
from .meeting_notes import MeetingNotesAI, get_meeting_notes_ai
from .connectors import ConnectorManager, get_connector_manager
from .sites_ai import SitesAI, get_sites_ai
from .image_gen import ImageGenerator, get_image_generator
from .translation import TranslationAI, get_translation_ai

__all__ = [
    # Writing capabilities
    "WritingAI",
    "get_writing_ai",
    # Workspace Q&A
    "WorkspaceQA",
    "get_workspace_qa",
    # Database AI
    "DatabaseAI",
    "get_database_ai",
    # Agents
    "AgentExecutor",
    "get_agent_executor",
    # Meeting notes
    "MeetingNotesAI",
    "get_meeting_notes_ai",
    # Connectors
    "ConnectorManager",
    "get_connector_manager",
    # Sites AI
    "SitesAI",
    "get_sites_ai",
    # Image generation
    "ImageGenerator",
    "get_image_generator",
    # Translation
    "TranslationAI",
    "get_translation_ai",
]
