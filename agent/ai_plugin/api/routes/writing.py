"""
Writing AI API Routes

FastAPI routes for writing AI capabilities.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...capabilities.writing import get_writing_ai, Tone


router = APIRouter(prefix="/ai/writing", tags=["Writing AI"])


class TextRequest(BaseModel):
    """Base request with text."""
    text: str


class SummarizeRequest(BaseModel):
    """Request for summarization."""
    text: str
    style: str = "concise"
    max_sentences: int = 3


class ImproveRequest(BaseModel):
    """Request for writing improvement."""
    text: str
    focus: Optional[str] = None


class ToneRequest(BaseModel):
    """Request for tone change."""
    text: str
    tone: str  # Will be converted to Tone enum


class TranslateRequest(BaseModel):
    """Request for translation."""
    text: str
    target_language: str
    preserve_formatting: bool = True


class ExpandRequest(BaseModel):
    """Request for text expansion."""
    text: str
    style: str = "expand"


class CondenseRequest(BaseModel):
    """Request for text condensing."""
    text: str
    aggressive: bool = False


class ExplainRequest(BaseModel):
    """Request for explanation."""
    text: str
    audience: str = "general"


class ContinueRequest(BaseModel):
    """Request for writing continuation."""
    text: str
    style: Optional[str] = None
    length: str = "paragraph"


@router.post("/summarize")
async def summarize(request: SummarizeRequest):
    """Summarize text."""
    try:
        writing_ai = get_writing_ai()
        result = await writing_ai.summarize(
            text=request.text,
            style=request.style,
            max_sentences=request.max_sentences
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/improve")
async def improve_writing(request: ImproveRequest):
    """Improve writing quality."""
    try:
        writing_ai = get_writing_ai()
        result = await writing_ai.improve_writing(
            text=request.text,
            focus=request.focus
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix-grammar")
async def fix_grammar(request: TextRequest):
    """Fix grammar and spelling."""
    try:
        writing_ai = get_writing_ai()
        result = await writing_ai.fix_grammar(request.text)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/change-tone")
async def change_tone(request: ToneRequest):
    """Change text tone."""
    try:
        writing_ai = get_writing_ai()
        # Convert string to Tone enum
        try:
            tone = Tone(request.tone.lower())
        except ValueError:
            tone = Tone.PROFESSIONAL
        
        result = await writing_ai.change_tone(request.text, tone)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate")
async def translate(request: TranslateRequest):
    """Translate text."""
    try:
        writing_ai = get_writing_ai()
        result = await writing_ai.translate(
            text=request.text,
            target_language=request.target_language,
            preserve_formatting=request.preserve_formatting
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/make-longer")
async def make_longer(request: ExpandRequest):
    """Expand text with more detail."""
    try:
        writing_ai = get_writing_ai()
        result = await writing_ai.make_longer(
            text=request.text,
            style=request.style
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/make-shorter")
async def make_shorter(request: CondenseRequest):
    """Condense text to be shorter."""
    try:
        writing_ai = get_writing_ai()
        result = await writing_ai.make_shorter(
            text=request.text,
            aggressive=request.aggressive
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain")
async def explain(request: ExplainRequest):
    """Explain text in simpler terms."""
    try:
        writing_ai = get_writing_ai()
        result = await writing_ai.explain(
            text=request.text,
            audience=request.audience
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/continue")
async def continue_writing(request: ContinueRequest):
    """Continue writing from existing text."""
    try:
        writing_ai = get_writing_ai()
        result = await writing_ai.continue_writing(
            text=request.text,
            style=request.style,
            length=request.length
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tones")
async def list_tones():
    """List available tones."""
    return {"tones": [tone.value for tone in Tone]}
