"""
Celery application and task definitions for AppFlowy AI.

Handles asynchronous background tasks including:
- Workspace indexing for Q&A
- Database property autofill
- Connector indexing
- Meeting audio processing
- Log cleanup
"""

import os
import logging
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
celery_app = Celery("appflowy_ai", broker=REDIS_URL, backend=REDIS_URL)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,
    task_time_limit=20 * 60,  # Hard time limit: 20 minutes
    task_soft_time_limit=19 * 60,  # Soft time limit: 19 minutes
)

# Celery Beat Schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    "index-workspace-pages": {
        "task": "agent.tasks.celery_app.index_workspace_pages",
        "schedule": 30 * 60,  # Every 30 minutes
        "options": {"queue": "default"}
    },
    "cleanup-old-logs": {
        "task": "agent.tasks.celery_app.cleanup_old_logs",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM UTC
        "options": {"queue": "default"}
    },
    "update-connector-indexes": {
        "task": "agent.tasks.celery_app.update_connector_indexes",
        "schedule": 60 * 60,  # Every hour
        "options": {"queue": "default"}
    },
}


# ============================================================================
# TASK DEFINITIONS
# ============================================================================


@celery_app.task(name="agent.tasks.celery_app.index_workspace_pages", bind=True)
def index_workspace_pages(self):
    """
    Index all workspace pages into Qdrant for Q&A search.

    This is a periodic task that runs every 30 minutes to keep the vector
    database updated with the latest workspace content.

    Returns:
        Dictionary with indexing results
    """
    try:
        logger.info("Starting workspace page indexing task")

        from agent.db.service import DatabaseService
        from agent.ai_plugin.capabilities.workspace_qa import get_workspace_qa

        # Get all pages from database
        db_service = DatabaseService()
        pages = db_service.get_all_pages()

        if not pages:
            logger.info("No pages to index")
            return {"status": "success", "indexed_count": 0}

        # Index pages into Qdrant
        qa_engine = get_workspace_qa()
        indexed_count = 0

        for page in pages:
            try:
                qa_engine.index_page(page)
                indexed_count += 1
            except Exception as e:
                logger.error(f"Failed to index page {page.id}: {e}")
                continue

        logger.info(f"Successfully indexed {indexed_count} pages")
        return {
            "status": "success",
            "indexed_count": indexed_count,
            "total_pages": len(pages)
        }

    except Exception as e:
        logger.error(f"Workspace indexing task failed: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
        return {"status": "error", "error": str(e)}


@celery_app.task(
    name="agent.tasks.celery_app.autofill_database_properties",
    bind=True,
    time_limit=10 * 60  # 10 minute timeout for this task
)
def autofill_database_properties(self, database_id: str, property_id: str):
    """
    Run AI autofill for a specific database property across all records.

    This task processes all records in a database and populates an AI
    autofill property with generated content.

    Args:
        database_id: ID of the database
        property_id: ID of the AI property to autofill

    Returns:
        Dictionary with autofill results
    """
    try:
        logger.info(f"Starting autofill for database {database_id}, property {property_id}")

        from agent.db.service import DatabaseService
        from agent.ai_plugin.capabilities.database_ai import get_database_ai

        db_service = DatabaseService()
        ai_service = get_database_ai()

        # Get database and property
        database = db_service.get_database(database_id)
        if not database:
            raise ValueError(f"Database {database_id} not found")

        # Get all records
        records = db_service.get_records(database_id)

        if not records:
            logger.info(f"No records to autofill in database {database_id}")
            return {"status": "success", "filled_count": 0}

        # Autofill each record
        filled_count = 0
        for record in records:
            try:
                ai_service.autofill_record_property(
                    database_id=database_id,
                    record_id=record.id,
                    property_id=property_id
                )
                filled_count += 1

                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={"current": filled_count, "total": len(records)}
                )

            except Exception as e:
                logger.error(f"Failed to autofill record {record.id}: {e}")
                continue

        logger.info(f"Autofilled {filled_count} records")
        return {
            "status": "success",
            "filled_count": filled_count,
            "total_records": len(records)
        }

    except Exception as e:
        logger.error(f"Autofill task failed: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
        return {"status": "error", "error": str(e)}


@celery_app.task(name="agent.tasks.celery_app.index_connector", bind=True)
def index_connector(self, connector_id: str, full_index: bool = False):
    """
    Index a specific external connector (Slack, Google Drive, GitHub, etc).

    Args:
        connector_id: ID of the connector to index
        full_index: Whether to perform full reindex vs incremental

    Returns:
        Dictionary with indexing results
    """
    try:
        logger.info(
            f"Starting connector indexing: {connector_id} (full={full_index})"
        )

        from agent.ai_plugin.capabilities.connectors import get_connector_manager

        manager = get_connector_manager()

        # Get connector
        connector = manager.get_connector(connector_id)
        if not connector:
            raise ValueError(f"Connector {connector_id} not found")

        # Index connector
        result = manager.index_connector(
            connector_id,
            full_index=full_index
        )

        logger.info(f"Connector {connector_id} indexed: {result}")
        return {
            "status": "success",
            "connector_id": connector_id,
            "indexed_items": result.get("indexed_items", 0),
            "duration_seconds": result.get("duration", 0)
        }

    except Exception as e:
        logger.error(f"Connector indexing failed: {e}")
        self.retry(exc=e, countdown=120, max_retries=3)
        return {"status": "error", "connector_id": connector_id, "error": str(e)}


@celery_app.task(
    name="agent.tasks.celery_app.process_meeting_audio",
    bind=True,
    time_limit=30 * 60  # 30 minute timeout
)
def process_meeting_audio(self, meeting_id: str, audio_file_path: str):
    """
    Transcribe and process meeting audio file.

    Runs transcription, generates summary, and extracts action items.

    Args:
        meeting_id: ID of the meeting
        audio_file_path: Path to audio file

    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Starting meeting audio processing: {meeting_id}")

        from agent.ai_plugin.capabilities.meeting_notes import get_meeting_notes_ai
        from agent.db.service import DatabaseService
        import os

        # Verify file exists
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Read audio file
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()

        meeting_ai = get_meeting_notes_ai()
        db_service = DatabaseService()

        # Transcribe
        transcribe_result = meeting_ai.transcribe(audio_bytes)
        transcript = transcribe_result.get("transcript")

        # Summarize
        summary_result = meeting_ai.summarize(transcript)
        summary = summary_result.get("summary")

        # Extract action items
        action_items = meeting_ai.extract_action_items(transcript)

        # Save to database
        db_service.update_meeting(
            meeting_id,
            transcript=transcript,
            summary=summary,
            action_items=action_items
        )

        logger.info(f"Meeting {meeting_id} processed successfully")
        return {
            "status": "success",
            "meeting_id": meeting_id,
            "transcript_length": len(transcript),
            "action_items_count": len(action_items)
        }

    except Exception as e:
        logger.error(f"Meeting audio processing failed: {e}")
        self.retry(exc=e, countdown=60, max_retries=2)
        return {"status": "error", "meeting_id": meeting_id, "error": str(e)}


@celery_app.task(name="agent.tasks.celery_app.cleanup_old_logs")
def cleanup_old_logs():
    """
    Remove old AI usage logs from database.

    Runs daily to clean up logs older than 90 days.

    Returns:
        Dictionary with cleanup results
    """
    try:
        logger.info("Starting cleanup of old AI usage logs")

        from agent.db.service import DatabaseService

        db_service = DatabaseService()

        # Calculate cutoff date (90 days ago)
        cutoff_date = datetime.utcnow() - timedelta(days=90)

        # Delete old logs
        deleted_count = db_service.delete_old_ai_logs(cutoff_date)

        logger.info(f"Deleted {deleted_count} old AI usage logs")
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }

    except Exception as e:
        logger.error(f"Log cleanup failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="agent.tasks.celery_app.update_connector_indexes")
def update_connector_indexes():
    """
    Perform incremental indexing for all active connectors.

    Runs hourly to keep external connector indexes up-to-date.

    Returns:
        Dictionary with update results
    """
    try:
        logger.info("Starting connector incremental indexing")

        from agent.ai_plugin.capabilities.connectors import get_connector_manager

        manager = get_connector_manager()

        # Get all active connectors
        connectors = manager.list_connectors()
        active_connectors = [
            c for c in connectors
            if c.get("status") == "active" and c.get("auto_index", False)
        ]

        if not active_connectors:
            logger.info("No active connectors to update")
            return {"status": "success", "updated_count": 0}

        # Index each connector incrementally
        updated_count = 0
        for connector in active_connectors:
            try:
                manager.index_connector(
                    connector["id"],
                    full_index=False  # Incremental only
                )
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update connector {connector['id']}: {e}")
                continue

        logger.info(f"Updated {updated_count} connectors")
        return {
            "status": "success",
            "updated_count": updated_count,
            "total_connectors": len(active_connectors)
        }

    except Exception as e:
        logger.error(f"Connector update failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="agent.tasks.celery_app.generate_ai_report")
def generate_ai_report(start_date: str, end_date: str):
    """
    Generate AI usage report for a date range.

    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format

    Returns:
        Dictionary with report data
    """
    try:
        logger.info(f"Generating AI usage report: {start_date} to {end_date}")

        from agent.db.service import DatabaseService
        from datetime import datetime

        db_service = DatabaseService()

        # Parse dates
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        # Get usage data
        usage_data = db_service.get_ai_usage_stats(start, end)

        logger.info("AI usage report generated")
        return {
            "status": "success",
            "start_date": start_date,
            "end_date": end_date,
            "data": usage_data
        }

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def schedule_connector_index(connector_id: str, delay_seconds: int = 0):
    """
    Schedule a connector indexing task.

    Args:
        connector_id: Connector to index
        delay_seconds: Delay before starting (optional)
    """
    if delay_seconds > 0:
        index_connector.apply_async(
            args=[connector_id, False],
            countdown=delay_seconds
        )
    else:
        index_connector.delay(connector_id, False)


def schedule_database_autofill(
    database_id: str,
    property_id: str,
    delay_seconds: int = 0
):
    """
    Schedule a database property autofill task.

    Args:
        database_id: Database to autofill
        property_id: Property to autofill
        delay_seconds: Delay before starting (optional)
    """
    if delay_seconds > 0:
        autofill_database_properties.apply_async(
            args=[database_id, property_id],
            countdown=delay_seconds
        )
    else:
        autofill_database_properties.delay(database_id, property_id)


def schedule_meeting_processing(meeting_id: str, audio_file_path: str):
    """
    Schedule meeting audio processing task.

    Args:
        meeting_id: Meeting to process
        audio_file_path: Path to audio file
    """
    process_meeting_audio.delay(meeting_id, audio_file_path)
