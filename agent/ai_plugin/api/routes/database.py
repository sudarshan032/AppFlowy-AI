"""
Database AI API Routes

FastAPI routes for database AI capabilities.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

from ...capabilities.database_ai import get_database_ai


router = APIRouter(prefix="/ai/database", tags=["Database AI"])


class AutofillRequest(BaseModel):
    """Request for property autofill."""
    content: str
    property_name: str
    property_type: str = "text"
    existing_values: Optional[List[str]] = None
    context: Optional[str] = None


class AutofillResponse(BaseModel):
    """Response from autofill."""
    value: str
    property_name: str


class FormulaRequest(BaseModel):
    """Request for formula suggestion."""
    description: str
    columns: List[Dict[str, str]]
    database_context: Optional[str] = None


class FormulaResponse(BaseModel):
    """Response with suggested formula."""
    formula: str
    explanation: str


class CategorizeRequest(BaseModel):
    """Request for content categorization."""
    content: str
    categories: List[str]
    allow_new: bool = False


class ExtractRequest(BaseModel):
    """Request for key info extraction."""
    content: str
    fields: List[str]


class SummaryRequest(BaseModel):
    """Request for content summary."""
    content: str
    max_words: int = 50


@router.post("/autofill", response_model=AutofillResponse)
async def autofill_property(request: AutofillRequest):
    """Auto-generate a property value based on content."""
    try:
        db_ai = get_database_ai()
        value = await db_ai.autofill_property(
            content=request.content,
            property_name=request.property_name,
            property_type=request.property_type,
            existing_values=request.existing_values,
            context=request.context
        )
        return AutofillResponse(value=value, property_name=request.property_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/formula", response_model=FormulaResponse)
async def suggest_formula(request: FormulaRequest):
    """Suggest a formula from natural language description."""
    try:
        db_ai = get_database_ai()
        result = await db_ai.suggest_formula(
            description=request.description,
            columns=request.columns,
            database_context=request.database_context
        )
        return FormulaResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categorize")
async def categorize_content(request: CategorizeRequest):
    """Categorize content into a category."""
    try:
        db_ai = get_database_ai()
        category = await db_ai.categorize_content(
            content=request.content,
            categories=request.categories,
            allow_new=request.allow_new
        )
        return {"category": category}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract")
async def extract_key_info(request: ExtractRequest):
    """Extract key information from content."""
    try:
        db_ai = get_database_ai()
        extracted = await db_ai.extract_key_info(
            content=request.content,
            fields=request.fields
        )
        return {"extracted": extracted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summary")
async def generate_summary(request: SummaryRequest):
    """Generate a summary of content."""
    try:
        db_ai = get_database_ai()
        summary = await db_ai.generate_summary(
            content=request.content,
            max_words=request.max_words
        )
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
