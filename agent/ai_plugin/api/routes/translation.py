"""
FastAPI router for translation capabilities.

Handles language detection and text translation to multiple target languages.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/translation", tags=["translation"])


class TranslateRequest(BaseModel):
    """Request to translate text."""
    text: str = Field(..., description="Text to translate", min_length=1)
    target_language: str = Field(
        ...,
        description="Target language code (e.g., 'en', 'es', 'fr', 'de', 'ja')"
    )
    source_language: Optional[str] = Field(
        None,
        description="Source language code (auto-detect if not provided)"
    )


class TranslateResponse(BaseModel):
    """Response with translated text."""
    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    source_language: str = Field(..., description="Detected or provided source language")
    target_language: str = Field(..., description="Target language")
    confidence: float = Field(..., description="Translation confidence (0-1)")


class DetectLanguageRequest(BaseModel):
    """Request to detect language of text."""
    text: str = Field(..., description="Text to analyze", min_length=1)


class DetectedLanguage(BaseModel):
    """Detected language information."""
    language_code: str = Field(..., description="Language code")
    language_name: str = Field(..., description="Full language name")
    confidence: float = Field(..., description="Detection confidence (0-1)")


class DetectLanguageResponse(BaseModel):
    """Response with language detection results."""
    text: str = Field(..., description="Analyzed text")
    detected_language: DetectedLanguage = Field(..., description="Primary detected language")
    alternatives: Optional[List[DetectedLanguage]] = Field(
        None,
        description="Alternative language possibilities"
    )


class BatchTranslateItem(BaseModel):
    """Single item in batch translation request."""
    text: str = Field(..., description="Text to translate")
    item_id: Optional[str] = Field(None, description="Optional identifier for tracking")


class BatchTranslateRequest(BaseModel):
    """Request to translate multiple texts."""
    items: List[BatchTranslateItem] = Field(..., description="Texts to translate")
    target_language: str = Field(..., description="Target language code")
    source_language: Optional[str] = Field(
        None,
        description="Source language (auto-detect if not provided)"
    )


class BatchTranslateResultItem(BaseModel):
    """Single result in batch translation response."""
    item_id: Optional[str] = Field(None, description="Item identifier if provided")
    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    confidence: float = Field(..., description="Translation confidence (0-1)")
    error: Optional[str] = Field(None, description="Error message if translation failed")


class BatchTranslateResponse(BaseModel):
    """Response with batch translation results."""
    target_language: str = Field(..., description="Target language")
    results: List[BatchTranslateResultItem] = Field(..., description="Translation results")
    successful_count: int = Field(..., description="Number of successful translations")
    failed_count: int = Field(..., description="Number of failed translations")
    total_time_ms: float = Field(..., description="Total processing time")


# Supported languages mapping
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
}


# Import translation AI
async def get_translation_ai():
    """Get translation AI singleton."""
    from ...capabilities.translation import get_translation_ai as gti
    return gti()


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(
    request: TranslateRequest
) -> TranslateResponse:
    """
    Translate text to target language.

    Args:
        request: TranslateRequest with text and target language

    Returns:
        TranslateResponse with translated text and metadata

    Raises:
        HTTPException: If translation fails or language not supported
    """
    try:
        # Validate languages
        if request.target_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Target language '{request.target_language}' not supported. "
                       f"Supported: {list(SUPPORTED_LANGUAGES.keys())}"
            )

        if request.source_language and request.source_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Source language '{request.source_language}' not supported."
            )

        translation_ai = await get_translation_ai()

        result = await translation_ai.translate(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language
        )

        return TranslateResponse(
            original_text=request.text,
            translated_text=result.get("translated_text"),
            source_language=result.get("source_language", request.source_language or "auto"),
            target_language=request.target_language,
            confidence=result.get("confidence", 0.95)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )


@router.post("/detect", response_model=DetectLanguageResponse)
async def detect_language(
    request: DetectLanguageRequest
) -> DetectLanguageResponse:
    """
    Detect the language of provided text.

    Args:
        request: DetectLanguageRequest with text

    Returns:
        DetectLanguageResponse with detected language and alternatives

    Raises:
        HTTPException: If detection fails
    """
    try:
        translation_ai = await get_translation_ai()

        result = await translation_ai.detect_language(request.text)

        detected_lang_code = result.get("language")
        detected_lang_name = SUPPORTED_LANGUAGES.get(detected_lang_code, detected_lang_code)

        detected = DetectedLanguage(
            language_code=detected_lang_code,
            language_name=detected_lang_name,
            confidence=result.get("confidence", 0.95)
        )

        alternatives = None
        if result.get("alternatives"):
            alternatives = [
                DetectedLanguage(
                    language_code=alt.get("language"),
                    language_name=SUPPORTED_LANGUAGES.get(
                        alt.get("language"),
                        alt.get("language")
                    ),
                    confidence=alt.get("confidence", 0.0)
                )
                for alt in result["alternatives"]
            ]

        return DetectLanguageResponse(
            text=request.text,
            detected_language=detected,
            alternatives=alternatives
        )

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Language detection failed: {str(e)}"
        )


@router.post("/batch", response_model=BatchTranslateResponse)
async def batch_translate(
    request: BatchTranslateRequest
) -> BatchTranslateResponse:
    """
    Translate multiple texts in a single request.

    Args:
        request: BatchTranslateRequest with list of texts

    Returns:
        BatchTranslateResponse with translation results for all items

    Raises:
        HTTPException: If batch processing fails
    """
    try:
        if not request.items:
            raise HTTPException(
                status_code=400,
                detail="Items list cannot be empty"
            )

        if len(request.items) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 items per batch translation"
            )

        # Validate target language
        if request.target_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Target language '{request.target_language}' not supported."
            )

        translation_ai = await get_translation_ai()

        import time
        start_time = time.time()

        results = []
        successful = 0
        failed = 0

        for item in request.items:
            try:
                result = await translation_ai.translate(
                    text=item.text,
                    target_language=request.target_language,
                    source_language=request.source_language
                )

                results.append(
                    BatchTranslateResultItem(
                        item_id=item.item_id,
                        original_text=item.text,
                        translated_text=result.get("translated_text"),
                        confidence=result.get("confidence", 0.95)
                    )
                )
                successful += 1

            except Exception as e:
                logger.warning(f"Failed to translate item {item.item_id}: {e}")
                results.append(
                    BatchTranslateResultItem(
                        item_id=item.item_id,
                        original_text=item.text,
                        translated_text="",
                        confidence=0.0,
                        error=str(e)
                    )
                )
                failed += 1

        elapsed_ms = (time.time() - start_time) * 1000

        return BatchTranslateResponse(
            target_language=request.target_language,
            results=results,
            successful_count=successful,
            failed_count=failed,
            total_time_ms=elapsed_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch translation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch translation failed: {str(e)}"
        )


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported languages.

    Returns:
        Dictionary mapping language codes to language names
    """
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "total_count": len(SUPPORTED_LANGUAGES)
    }
