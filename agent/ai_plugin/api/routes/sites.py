"""
FastAPI router for Notion Sites AI capabilities.

Handles SEO optimization, content generation, and copy variations for web content.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/sites", tags=["sites"])


class SEOMetadata(BaseModel):
    """SEO metadata for a page."""
    title: str = Field(..., description="SEO page title (50-60 chars)")
    description: str = Field(..., description="Meta description (150-160 chars)")
    keywords: List[str] = Field(..., description="SEO keywords")
    slug: str = Field(..., description="URL-friendly slug")
    og_title: Optional[str] = Field(None, description="Open Graph title")
    og_description: Optional[str] = Field(None, description="Open Graph description")
    og_image_alt: Optional[str] = Field(None, description="Image alt text for social sharing")


class GenerateSEORequest(BaseModel):
    """Request to generate SEO metadata."""
    page_title: str = Field(..., description="Page title or heading")
    page_content: str = Field(..., description="Page content for analysis")
    target_audience: Optional[str] = Field(
        None,
        description="Target audience (e.g., 'developers', 'small business owners')"
    )
    primary_keyword: Optional[str] = Field(
        None,
        description="Primary keyword to optimize for"
    )
    site_domain: Optional[str] = Field(None, description="Site domain for slug generation")


class GenerateSEOResponse(BaseModel):
    """Response with generated SEO metadata."""
    seo: SEOMetadata = Field(..., description="Generated SEO metadata")
    confidence: float = Field(..., description="Generation confidence (0-1)")
    recommendations: Optional[List[str]] = Field(
        None,
        description="Additional SEO recommendations"
    )


class ContentGenerationRequest(BaseModel):
    """Request to generate page content."""
    page_title: str = Field(..., description="Page title or topic")
    purpose: str = Field(
        ...,
        description="Purpose: blog_post, landing_page, product_description, about_page"
    )
    target_audience: Optional[str] = Field(None, description="Target audience")
    tone: str = Field(
        "professional",
        description="Content tone: professional, casual, friendly, technical"
    )
    length: str = Field(
        "medium",
        description="Content length: short (200 words), medium (500 words), long (1000+ words)"
    )
    keywords: Optional[List[str]] = Field(None, description="Keywords to include")


class GeneratedContent(BaseModel):
    """Generated content for a page."""
    title: str = Field(..., description="Page title")
    headline: str = Field(..., description="Main headline")
    subheadline: Optional[str] = Field(None, description="Subheadline")
    sections: List[dict] = Field(
        ...,
        description="Content sections with heading and body"
    )
    cta: Optional[str] = Field(None, description="Call-to-action text")
    word_count: int = Field(..., description="Total word count")


class GenerateContentResponse(BaseModel):
    """Response with generated content."""
    content: GeneratedContent = Field(..., description="Generated content")
    confidence: float = Field(..., description="Generation confidence (0-1)")


class CopyVariation(BaseModel):
    """Single variation of copy."""
    variation_number: int = Field(..., description="Variation number")
    text: str = Field(..., description="Copy text")
    style: str = Field(..., description="Style of this variation")
    focus: str = Field(..., description="What this variation focuses on")


class GenerateCopyVariationsRequest(BaseModel):
    """Request to generate copy variations."""
    original_copy: str = Field(..., description="Original copy to vary")
    element_type: str = Field(
        ...,
        description="Type: headline, subheadline, cta, body, meta_description"
    )
    target_variations: int = Field(
        3,
        description="Number of variations to generate",
        ge=1,
        le=10
    )
    styles: Optional[List[str]] = Field(
        None,
        description="Desired styles (e.g., 'persuasive', 'humorous', 'urgent', 'elegant')"
    )
    focus_points: Optional[List[str]] = Field(
        None,
        description="What to focus on in each variation (e.g., 'benefit', 'urgency', 'emotion')"
    )


class GenerateCopyVariationsResponse(BaseModel):
    """Response with copy variations."""
    original_copy: str = Field(..., description="Original copy")
    element_type: str = Field(..., description="Type of element")
    variations: List[CopyVariation] = Field(..., description="Generated variations")


class OptimizeContentRequest(BaseModel):
    """Request to optimize content for a target audience."""
    content: str = Field(..., description="Content to optimize")
    current_audience: Optional[str] = Field(None, description="Current target audience")
    target_audience: str = Field(..., description="New target audience")
    optimization_focus: str = Field(
        "engagement",
        description="Focus: engagement, conversion, clarity, retention"
    )


class OptimizedContent(BaseModel):
    """Optimized content."""
    original_content: str = Field(..., description="Original content")
    optimized_content: str = Field(..., description="Optimized content")
    changes_made: List[str] = Field(..., description="Summary of optimizations")
    estimated_improvement: float = Field(
        ...,
        description="Estimated improvement percentage (0-100)"
    )


class OptimizeContentResponse(BaseModel):
    """Response with optimized content."""
    result: OptimizedContent = Field(..., description="Optimization result")
    confidence: float = Field(..., description="Optimization confidence (0-1)")


# Import sites AI capability
async def get_sites_ai():
    """Get sites AI singleton."""
    from ...capabilities.sites_ai import get_sites_ai as gsa
    return gsa()


@router.post("/seo", response_model=GenerateSEOResponse)
async def generate_seo(
    request: GenerateSEORequest
) -> GenerateSEOResponse:
    """
    Generate SEO metadata for a page.

    Creates optimized title, meta description, keywords, and social sharing metadata.

    Args:
        request: GenerateSEORequest with page content

    Returns:
        GenerateSEOResponse with SEO metadata

    Raises:
        HTTPException: If generation fails
    """
    try:
        if not request.page_title or not request.page_content:
            raise HTTPException(
                status_code=400,
                detail="page_title and page_content are required"
            )

        sites_ai = await get_sites_ai()

        result = await sites_ai.generate_seo(
            page_title=request.page_title,
            page_content=request.page_content,
            target_audience=request.target_audience,
            primary_keyword=request.primary_keyword,
            site_domain=request.site_domain
        )

        seo_meta = SEOMetadata(
            title=result.get("title"),
            description=result.get("description"),
            keywords=result.get("keywords", []),
            slug=result.get("slug"),
            og_title=result.get("og_title"),
            og_description=result.get("og_description"),
            og_image_alt=result.get("og_image_alt")
        )

        return GenerateSEOResponse(
            seo=seo_meta,
            confidence=result.get("confidence", 0.95),
            recommendations=result.get("recommendations")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SEO generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"SEO generation failed: {str(e)}"
        )


@router.post("/content", response_model=GenerateContentResponse)
async def generate_content(
    request: ContentGenerationRequest
) -> GenerateContentResponse:
    """
    Generate page content for various purposes.

    Creates structured content with headlines, sections, and CTAs.

    Args:
        request: ContentGenerationRequest with content parameters

    Returns:
        GenerateContentResponse with generated content

    Raises:
        HTTPException: If generation fails
    """
    try:
        valid_purposes = [
            "blog_post", "landing_page", "product_description", "about_page"
        ]
        if request.purpose not in valid_purposes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid purpose. Must be one of: {valid_purposes}"
            )

        sites_ai = await get_sites_ai()

        result = await sites_ai.generate_content(
            page_title=request.page_title,
            purpose=request.purpose,
            target_audience=request.target_audience,
            tone=request.tone,
            length=request.length,
            keywords=request.keywords
        )

        content = GeneratedContent(
            title=result.get("title"),
            headline=result.get("headline"),
            subheadline=result.get("subheadline"),
            sections=result.get("sections", []),
            cta=result.get("cta"),
            word_count=result.get("word_count", 0)
        )

        return GenerateContentResponse(
            content=content,
            confidence=result.get("confidence", 0.95)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Content generation failed: {str(e)}"
        )


@router.post("/copy-variations", response_model=GenerateCopyVariationsResponse)
async def generate_copy_variations(
    request: GenerateCopyVariationsRequest
) -> GenerateCopyVariationsResponse:
    """
    Generate multiple variations of copy/text.

    Creates different styles and angles for headlines, CTAs, descriptions, etc.

    Args:
        request: GenerateCopyVariationsRequest with original copy

    Returns:
        GenerateCopyVariationsResponse with multiple variations

    Raises:
        HTTPException: If generation fails
    """
    try:
        if not request.original_copy or not request.original_copy.strip():
            raise HTTPException(
                status_code=400,
                detail="original_copy cannot be empty"
            )

        valid_types = [
            "headline", "subheadline", "cta", "body", "meta_description"
        ]
        if request.element_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid element_type. Must be one of: {valid_types}"
            )

        sites_ai = await get_sites_ai()

        result = await sites_ai.generate_copy_variations(
            original_copy=request.original_copy,
            element_type=request.element_type,
            num_variations=request.target_variations,
            styles=request.styles,
            focus_points=request.focus_points
        )

        variations = [
            CopyVariation(
                variation_number=v.get("number", i + 1),
                text=v.get("text"),
                style=v.get("style"),
                focus=v.get("focus")
            )
            for i, v in enumerate(result.get("variations", []))
        ]

        return GenerateCopyVariationsResponse(
            original_copy=request.original_copy,
            element_type=request.element_type,
            variations=variations
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copy variation generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Copy variation generation failed: {str(e)}"
        )


@router.post("/optimize", response_model=OptimizeContentResponse)
async def optimize_content(
    request: OptimizeContentRequest
) -> OptimizeContentResponse:
    """
    Optimize content for a specific target audience.

    Adjusts tone, language, and focus based on audience preferences.

    Args:
        request: OptimizeContentRequest with content and audience

    Returns:
        OptimizeContentResponse with optimized content

    Raises:
        HTTPException: If optimization fails
    """
    try:
        if not request.content or not request.content.strip():
            raise HTTPException(
                status_code=400,
                detail="content cannot be empty"
            )

        if not request.target_audience:
            raise HTTPException(
                status_code=400,
                detail="target_audience is required"
            )

        valid_focuses = ["engagement", "conversion", "clarity", "retention"]
        if request.optimization_focus not in valid_focuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid optimization_focus. Must be one of: {valid_focuses}"
            )

        sites_ai = await get_sites_ai()

        result = await sites_ai.optimize_content(
            content=request.content,
            current_audience=request.current_audience,
            target_audience=request.target_audience,
            optimization_focus=request.optimization_focus
        )

        optimized = OptimizedContent(
            original_content=request.content,
            optimized_content=result.get("optimized_content"),
            changes_made=result.get("changes_made", []),
            estimated_improvement=result.get("estimated_improvement", 0.0)
        )

        return OptimizeContentResponse(
            result=optimized,
            confidence=result.get("confidence", 0.95)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content optimization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Content optimization failed: {str(e)}"
        )
