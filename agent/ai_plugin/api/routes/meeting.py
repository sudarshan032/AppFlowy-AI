"""
FastAPI router for meeting notes functionality.

Handles audio transcription, meeting summarization, action item extraction,
and persistent storage of meeting notes.
"""

import io
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel, Field
import logging

from ...capabilities.meeting_notes import get_meeting_notes_ai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/meeting", tags=["meeting"])


class TranscribeRequest(BaseModel):
    """Request model for audio transcription."""
    audio_file: Optional[bytes] = Field(None, description="Audio file bytes")
    language: str = Field("en", description="Language code for transcription")


class TranscribeResponse(BaseModel):
    """Response model for transcription results."""
    transcript: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., description="Confidence score (0-1)")
    duration_seconds: float = Field(..., description="Audio duration in seconds")


class SummarizeRequest(BaseModel):
    """Request model for meeting summarization."""
    transcript: str = Field(..., description="Meeting transcript text")
    focus_areas: Optional[list[str]] = Field(None, description="Topics to focus on")


class SummarizeResponse(BaseModel):
    """Response model for meeting summary."""
    summary: str = Field(..., description="Meeting summary")
    key_points: list[str] = Field(..., description="Key discussion points")
    decisions: list[str] = Field(..., description="Decisions made")


class ActionItemsRequest(BaseModel):
    """Request model for action item extraction."""
    transcript: str = Field(..., description="Meeting transcript")


class ActionItemsResponse(BaseModel):
    """Response model for action items."""
    action_items: list[dict] = Field(
        ...,
        description="List of action items with owner and deadline"
    )
    total_count: int = Field(..., description="Total number of action items")


class CreateMeetingRequest(BaseModel):
    """Request model for full meeting processing pipeline."""
    meeting_title: str = Field(..., description="Title of the meeting")
    audio_file: Optional[bytes] = Field(None, description="Audio file bytes")
    transcript: Optional[str] = Field(None, description="Pre-existing transcript")
    participants: Optional[list[str]] = Field(None, description="List of participants")


class CreateMeetingResponse(BaseModel):
    """Response model for created meeting."""
    meeting_id: str = Field(..., description="Unique meeting ID")
    title: str = Field(..., description="Meeting title")
    transcript: str = Field(..., description="Full transcript")
    summary: str = Field(..., description="Meeting summary")
    action_items: list[dict] = Field(..., description="Extracted action items")
    created_at: str = Field(..., description="Creation timestamp")


class GetMeetingResponse(BaseModel):
    """Response model for retrieving meeting notes."""
    meeting_id: str = Field(..., description="Meeting ID")
    title: str = Field(..., description="Meeting title")
    transcript: str = Field(..., description="Meeting transcript")
    summary: str = Field(..., description="Meeting summary")
    action_items: list[dict] = Field(..., description="Action items")
    participants: Optional[list[str]] = Field(None, description="Participants")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = "en"
) -> TranscribeResponse:
    """
    Transcribe audio file to text.

    Args:
        file: Audio file upload (WAV, MP3, M4A)
        language: Language code for transcription (default: 'en')

    Returns:
        TranscribeResponse with transcript and confidence score

    Raises:
        HTTPException: If transcription fails
    """
    try:
        meeting_ai = get_meeting_notes_ai()

        # Read file contents
        contents = await file.read()

        if not contents:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Transcribe
        result = await meeting_ai.transcribe(
            audio_bytes=contents,
            language=language
        )

        return TranscribeResponse(
            transcript=result["transcript"],
            confidence=result.get("confidence", 0.95),
            duration_seconds=result.get("duration", 0.0)
        )

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_meeting(
    request: SummarizeRequest
) -> SummarizeResponse:
    """
    Summarize meeting transcript.

    Args:
        request: SummarizeRequest with transcript

    Returns:
        SummarizeResponse with summary and key points

    Raises:
        HTTPException: If summarization fails
    """
    try:
        if not request.transcript or not request.transcript.strip():
            raise HTTPException(
                status_code=400,
                detail="Transcript cannot be empty"
            )

        meeting_ai = get_meeting_notes_ai()

        result = await meeting_ai.summarize(
            transcript=request.transcript,
            focus_areas=request.focus_areas
        )

        return SummarizeResponse(
            summary=result["summary"],
            key_points=result.get("key_points", []),
            decisions=result.get("decisions", [])
        )

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Summarization failed: {str(e)}"
        )


@router.post("/action-items", response_model=ActionItemsResponse)
async def extract_action_items(
    request: ActionItemsRequest
) -> ActionItemsResponse:
    """
    Extract action items from meeting transcript.

    Args:
        request: ActionItemsRequest with transcript

    Returns:
        ActionItemsResponse with list of action items

    Raises:
        HTTPException: If extraction fails
    """
    try:
        if not request.transcript or not request.transcript.strip():
            raise HTTPException(
                status_code=400,
                detail="Transcript cannot be empty"
            )

        meeting_ai = get_meeting_notes_ai()

        action_items = await meeting_ai.extract_action_items(
            transcript=request.transcript
        )

        return ActionItemsResponse(
            action_items=action_items,
            total_count=len(action_items)
        )

    except Exception as e:
        logger.error(f"Action item extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Action item extraction failed: {str(e)}"
        )


@router.post("/create", response_model=CreateMeetingResponse)
async def create_meeting(
    request: CreateMeetingRequest
) -> CreateMeetingResponse:
    """
    Full meeting processing pipeline: transcribe audio → summarize → extract items.

    Args:
        request: CreateMeetingRequest with audio or transcript

    Returns:
        CreateMeetingResponse with complete meeting data

    Raises:
        HTTPException: If processing fails
    """
    try:
        meeting_ai = get_meeting_notes_ai()

        # Get transcript (either from audio or provided)
        transcript = request.transcript
        if request.audio_file and not transcript:
            transcribe_result = await meeting_ai.transcribe(
                audio_bytes=request.audio_file
            )
            transcript = transcribe_result["transcript"]

        if not transcript:
            raise HTTPException(
                status_code=400,
                detail="Must provide either audio_file or transcript"
            )

        # Create meeting with full processing
        meeting_id = await meeting_ai.create_meeting(
            title=request.meeting_title,
            transcript=transcript,
            participants=request.participants
        )

        # Get summary
        summary_result = await meeting_ai.summarize(transcript)

        # Extract action items
        action_items = await meeting_ai.extract_action_items(transcript)

        return CreateMeetingResponse(
            meeting_id=meeting_id,
            title=request.meeting_title,
            transcript=transcript,
            summary=summary_result["summary"],
            action_items=action_items,
            created_at=await meeting_ai.get_created_timestamp(meeting_id)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Meeting creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Meeting creation failed: {str(e)}"
        )


@router.get("/{meeting_id}", response_model=GetMeetingResponse)
async def get_meeting(
    meeting_id: str
) -> GetMeetingResponse:
    """
    Retrieve meeting notes by ID from database.

    Args:
        meeting_id: Unique meeting identifier

    Returns:
        GetMeetingResponse with complete meeting data

    Raises:
        HTTPException: If meeting not found
    """
    try:
        meeting_ai = get_meeting_notes_ai()

        meeting_data = await meeting_ai.get_meeting(meeting_id)

        if not meeting_data:
            raise HTTPException(
                status_code=404,
                detail=f"Meeting {meeting_id} not found"
            )

        return GetMeetingResponse(
            meeting_id=meeting_id,
            title=meeting_data.get("title", ""),
            transcript=meeting_data.get("transcript", ""),
            summary=meeting_data.get("summary", ""),
            action_items=meeting_data.get("action_items", []),
            participants=meeting_data.get("participants"),
            created_at=meeting_data.get("created_at", ""),
            updated_at=meeting_data.get("updated_at", "")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve meeting {meeting_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve meeting: {str(e)}"
        )
