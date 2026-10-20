"""
Meeting Notes and Transcription — Phase 6

AI capabilities for meeting transcription, summarization, and action item extraction:
- Audio transcription using Whisper
- Meeting summarization
- Action item and decision extraction
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

from ..core import get_engine

logger = logging.getLogger(__name__)


class Priority(str, Enum):
    """Priority levels for action items."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ActionItem:
    """An action item extracted from a meeting."""
    description: str
    assignee: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    due_date: Optional[str] = None


@dataclass
class Decision:
    """A decision made during a meeting."""
    statement: str
    context: Optional[str] = None
    confidence: float = 0.8


@dataclass
class MeetingResult:
    """Complete result of meeting processing."""
    transcript: str
    summary: str
    action_items: List[ActionItem]
    decisions: List[Decision]
    duration_seconds: int
    speaker_count: int


class MeetingNotesAI:
    """
    AI system for meeting transcription and notes.

    Provides:
    - Audio transcription (via Whisper)
    - Meeting summarization
    - Action item extraction
    - Decision tracking
    - Speaker detection (basic)
    """

    def __init__(self):
        """Initialize MeetingNotesAI."""
        self.engine = get_engine()
        self._whisper_available = self._check_whisper()

    def _check_whisper(self) -> bool:
        """Check if Whisper is available."""
        try:
            import whisper
            return True
        except ImportError:
            logger.warning("Whisper not installed. Install with: pip install openai-whisper")
            return False

    async def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (mp3, wav, m4a, etc.)

        Returns:
            Transcribed text

        Raises:
            RuntimeError: If Whisper is not available
        """
        if not self._whisper_available:
            raise RuntimeError(
                "Whisper is not installed. Install with: pip install openai-whisper"
            )

        try:
            import whisper

            logger.info(f"Transcribing audio file: {audio_path}")

            # Load model (base is good for most cases)
            model = whisper.load_model("base")

            # Transcribe
            result = model.transcribe(audio_path)
            transcript = result.get("text", "").strip()

            logger.info(f"Transcription complete. Length: {len(transcript)} chars")
            return transcript

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise

    async def summarize_meeting(self, transcript: str) -> str:
        """
        Generate a summary of the meeting from transcript.

        Args:
            transcript: Meeting transcript text

        Returns:
            Summary of the meeting
        """
        if not transcript.strip():
            logger.warning("Empty transcript provided for summarization")
            return ""

        prompt = f"""Summarize the following meeting transcript in 3-5 sentences.
Focus on the main topics discussed and key decisions made.

Transcript:
{transcript}

Summary:"""

        try:
            summary = await self.engine.generate(prompt, temperature=0.3, max_tokens=500)
            logger.info(f"Generated meeting summary ({len(summary)} chars)")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error summarizing meeting: {e}")
            raise

    async def extract_action_items(self, transcript: str) -> List[ActionItem]:
        """
        Extract action items from meeting transcript.

        Args:
            transcript: Meeting transcript text

        Returns:
            List of action items with assignees and priorities
        """
        if not transcript.strip():
            logger.warning("Empty transcript for action item extraction")
            return []

        prompt = f"""Extract all action items from the following meeting transcript.
For each action item, identify:
1. What needs to be done
2. Who is responsible (if mentioned)
3. Priority (high/medium/low)
4. Due date if mentioned

Format each action item as:
ACTION: [description]
ASSIGNEE: [person name or "Unassigned"]
PRIORITY: [high/medium/low]
DUE_DATE: [date or "Not specified"]

Transcript:
{transcript}

Action Items:"""

        try:
            response = await self.engine.generate(
                prompt, temperature=0.2, max_tokens=1000
            )

            items = []
            current_item = {}

            for line in response.strip().split("\n"):
                line = line.strip()
                if not line:
                    if current_item.get("ACTION"):
                        items.append(current_item)
                        current_item = {}
                    continue

                if line.startswith("ACTION:"):
                    current_item["ACTION"] = line.replace("ACTION:", "").strip()
                elif line.startswith("ASSIGNEE:"):
                    assignee = line.replace("ASSIGNEE:", "").strip()
                    current_item["ASSIGNEE"] = assignee if assignee.lower() != "unassigned" else None
                elif line.startswith("PRIORITY:"):
                    priority_str = line.replace("PRIORITY:", "").strip().lower()
                    try:
                        current_item["PRIORITY"] = Priority(priority_str)
                    except ValueError:
                        current_item["PRIORITY"] = Priority.MEDIUM
                elif line.startswith("DUE_DATE:"):
                    due_date = line.replace("DUE_DATE:", "").strip()
                    if due_date.lower() != "not specified":
                        current_item["DUE_DATE"] = due_date

            if current_item.get("ACTION"):
                items.append(current_item)

            # Convert to ActionItem objects
            action_items = [
                ActionItem(
                    description=item.get("ACTION", ""),
                    assignee=item.get("ASSIGNEE"),
                    priority=item.get("PRIORITY", Priority.MEDIUM),
                    due_date=item.get("DUE_DATE")
                )
                for item in items
                if item.get("ACTION")
            ]

            logger.info(f"Extracted {len(action_items)} action items")
            return action_items

        except Exception as e:
            logger.error(f"Error extracting action items: {e}")
            raise

    async def extract_decisions(self, transcript: str) -> List[Decision]:
        """
        Extract key decisions from meeting transcript.

        Args:
            transcript: Meeting transcript text

        Returns:
            List of decisions made
        """
        if not transcript.strip():
            logger.warning("Empty transcript for decision extraction")
            return []

        prompt = f"""Extract all key decisions made in the following meeting transcript.
For each decision, identify:
1. The decision statement
2. Context or reasoning if mentioned
3. Your confidence in this being a decision (0.0-1.0)

Format each decision as:
DECISION: [statement]
CONTEXT: [context or "Not specified"]
CONFIDENCE: [0.0-1.0]

Transcript:
{transcript}

Decisions:"""

        try:
            response = await self.engine.generate(
                prompt, temperature=0.2, max_tokens=1000
            )

            decisions = []
            current_decision = {}

            for line in response.strip().split("\n"):
                line = line.strip()
                if not line:
                    if current_decision.get("DECISION"):
                        decisions.append(current_decision)
                        current_decision = {}
                    continue

                if line.startswith("DECISION:"):
                    current_decision["DECISION"] = line.replace("DECISION:", "").strip()
                elif line.startswith("CONTEXT:"):
                    context = line.replace("CONTEXT:", "").strip()
                    current_decision["CONTEXT"] = context if context.lower() != "not specified" else None
                elif line.startswith("CONFIDENCE:"):
                    confidence_str = line.replace("CONFIDENCE:", "").strip()
                    try:
                        current_decision["CONFIDENCE"] = float(confidence_str)
                    except ValueError:
                        current_decision["CONFIDENCE"] = 0.8

            if current_decision.get("DECISION"):
                decisions.append(current_decision)

            # Convert to Decision objects
            decision_objs = [
                Decision(
                    statement=d.get("DECISION", ""),
                    context=d.get("CONTEXT"),
                    confidence=d.get("CONFIDENCE", 0.8)
                )
                for d in decisions
                if d.get("DECISION")
            ]

            logger.info(f"Extracted {len(decision_objs)} decisions")
            return decision_objs

        except Exception as e:
            logger.error(f"Error extracting decisions: {e}")
            raise

    async def create_meeting_notes(
        self,
        audio_path: str,
        title: str,
        meeting_type: str = "general"
    ) -> MeetingResult:
        """
        Create complete meeting notes from audio file.

        Full pipeline: transcribe → summarize → extract items → extract decisions

        Args:
            audio_path: Path to audio recording
            title: Meeting title
            meeting_type: Type of meeting (general, standup, planning, etc.)

        Returns:
            Complete MeetingResult with all extracted information
        """
        try:
            logger.info(f"Processing meeting: {title} ({meeting_type})")

            # Transcribe
            transcript = await self.transcribe(audio_path)

            # Summarize
            summary = await self.summarize_meeting(transcript)

            # Extract action items
            action_items = await self.extract_action_items(transcript)

            # Extract decisions
            decisions = await self.extract_decisions(transcript)

            # Estimate duration and speaker count from transcript
            words = transcript.split()
            estimated_duration = max(len(words) * 0.5, 60)  # ~2 words per second
            speaker_patterns = transcript.count(":")  # Rough estimate
            speaker_count = max(1, min(speaker_patterns // 10, 10))

            result = MeetingResult(
                transcript=transcript,
                summary=summary,
                action_items=action_items,
                decisions=decisions,
                duration_seconds=int(estimated_duration),
                speaker_count=speaker_count
            )

            logger.info(
                f"Meeting processing complete: {len(action_items)} actions, "
                f"{len(decisions)} decisions"
            )

            return result

        except Exception as e:
            logger.error(f"Error creating meeting notes: {e}")
            raise

    async def format_notes_markdown(self, meeting: MeetingResult) -> str:
        """
        Format meeting result as Markdown document.

        Args:
            meeting: MeetingResult object

        Returns:
            Markdown-formatted meeting notes
        """
        md_lines = [
            "# Meeting Notes",
            "",
            f"**Duration:** {meeting.duration_seconds // 60} min",
            f"**Speakers:** {meeting.speaker_count}",
            "",
            "## Summary",
            "",
            meeting.summary,
            "",
            "## Action Items",
            "",
        ]

        if meeting.action_items:
            for i, item in enumerate(meeting.action_items, 1):
                priority_emoji = {
                    Priority.HIGH: "🔴",
                    Priority.MEDIUM: "🟡",
                    Priority.LOW: "🟢"
                }.get(item.priority, "⚪")

                md_lines.append(
                    f"{i}. {priority_emoji} {item.description}"
                )
                if item.assignee:
                    md_lines.append(f"   - Assignee: {item.assignee}")
                if item.due_date:
                    md_lines.append(f"   - Due: {item.due_date}")
                md_lines.append("")
        else:
            md_lines.append("No action items identified.\n")

        md_lines.extend([
            "## Decisions",
            "",
        ])

        if meeting.decisions:
            for i, decision in enumerate(meeting.decisions, 1):
                md_lines.append(f"{i}. {decision.statement}")
                if decision.context:
                    md_lines.append(f"   - Context: {decision.context}")
                md_lines.append(f"   - Confidence: {decision.confidence:.0%}")
                md_lines.append("")
        else:
            md_lines.append("No decisions identified.\n")

        return "\n".join(md_lines)


# Singleton instance
_meeting_notes_ai: Optional[MeetingNotesAI] = None


def get_meeting_notes_ai() -> MeetingNotesAI:
    """Get MeetingNotesAI singleton."""
    global _meeting_notes_ai
    if _meeting_notes_ai is None:
        _meeting_notes_ai = MeetingNotesAI()
    return _meeting_notes_ai
