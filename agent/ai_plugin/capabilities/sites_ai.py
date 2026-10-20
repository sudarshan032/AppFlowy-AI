"""
Sites AI — Phase 6

AI capabilities for Notion Sites:
- SEO optimization (titles, descriptions, keywords)
- Content generation for pages and blogs
- Copy variations for A/B testing
- Audience-specific content adaptation
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

from ..core import get_engine

logger = logging.getLogger(__name__)


@dataclass
class SEOOptimization:
    """SEO optimization results."""
    title: str
    meta_description: str
    keywords: List[str]
    og_title: str
    og_description: str


@dataclass
class ContentPlan:
    """Content generation plan."""
    title: str
    sections: List[Dict[str, str]]  # List of {heading: str, content: str}
    summary: str
    call_to_action: str


class SitesAI:
    """
    AI capabilities for Notion Sites.

    Provides:
    - SEO optimization
    - Content generation
    - Copy variations
    - Audience adaptation
    """

    def __init__(self):
        """Initialize SitesAI."""
        self.engine = get_engine()

    async def generate_seo(
        self,
        title: str,
        content: str,
        target_audience: Optional[str] = None
    ) -> SEOOptimization:
        """
        Generate SEO-optimized metadata.

        Args:
            title: Page title
            content: Page content
            target_audience: Target audience description

        Returns:
            SEOOptimization object with optimized metadata
        """
        audience_context = ""
        if target_audience:
            audience_context = f"\nTarget audience: {target_audience}"

        prompt = f"""Generate SEO metadata for the following page.
Create optimized titles and descriptions for search engines and social media.

Page Title: {title}
Page Content (first 500 chars):
{content[:500]}
{audience_context}

Provide the following in this exact format:
SEO_TITLE: [optimized title, max 60 chars]
META_DESCRIPTION: [optimized description, max 160 chars]
KEYWORDS: [5-8 relevant keywords, comma-separated]
OG_TITLE: [Open Graph title for social media]
OG_DESCRIPTION: [Open Graph description for social media]"""

        try:
            response = await self.engine.generate(
                prompt, temperature=0.3, max_tokens=500
            )

            # Parse response
            seo_data = {}
            for line in response.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    seo_data[key.strip()] = value.strip()

            # Extract keywords
            keywords_str = seo_data.get("KEYWORDS", "")
            keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

            result = SEOOptimization(
                title=seo_data.get("SEO_TITLE", title),
                meta_description=seo_data.get("META_DESCRIPTION", ""),
                keywords=keywords,
                og_title=seo_data.get("OG_TITLE", title),
                og_description=seo_data.get("OG_DESCRIPTION", "")
            )

            logger.info(f"Generated SEO metadata for: {title}")
            return result

        except Exception as e:
            logger.error(f"Error generating SEO: {e}")
            raise

    async def generate_content(
        self,
        topic: str,
        audience: str,
        length: str = "medium",
        style: Optional[str] = None
    ) -> ContentPlan:
        """
        Generate structured content for a page.

        Args:
            topic: Main topic for the content
            audience: Target audience
            length: Length (short, medium, long)
            style: Writing style (professional, casual, technical, etc.)

        Returns:
            ContentPlan with title, sections, and call-to-action
        """
        length_guidance = {
            "short": "3-4 sections, each 2-3 paragraphs",
            "medium": "5-6 sections, each 3-4 paragraphs",
            "long": "8-10 sections, each 4-5 paragraphs"
        }.get(length, "5-6 sections, each 3-4 paragraphs")

        style_guidance = f"Style: {style}. " if style else ""

        prompt = f"""Create a comprehensive content plan for a Notion site page.

Topic: {topic}
Target Audience: {audience}
Length: {length} ({length_guidance})
{style_guidance}

Generate the following in this exact format:

TITLE: [Engaging page title]

SECTION_1_HEADING: [heading]
SECTION_1_CONTENT: [paragraph of content]

SECTION_2_HEADING: [heading]
SECTION_2_CONTENT: [paragraph of content]

[Continue for all sections]

SUMMARY: [2-3 sentence summary of the page]
CALL_TO_ACTION: [Suggested CTA for the page]

Make the content engaging, informative, and optimized for the target audience."""

        try:
            response = await self.engine.generate(
                prompt, temperature=0.7, max_tokens=2000
            )

            # Parse sections
            sections = []
            summary = ""
            cta = ""
            title = ""
            current_section = {}

            for line in response.strip().split("\n"):
                if line.startswith("TITLE:"):
                    title = line.replace("TITLE:", "").strip()
                elif line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                elif line.startswith("CALL_TO_ACTION:"):
                    cta = line.replace("CALL_TO_ACTION:", "").strip()
                elif line.startswith("SECTION_") and "_HEADING:" in line:
                    if current_section:
                        sections.append(current_section)
                    current_section = {"heading": line.split(":", 1)[1].strip()}
                elif line.startswith("SECTION_") and "_CONTENT:" in line:
                    if current_section:
                        current_section["content"] = line.split(":", 1)[1].strip()
                        sections.append(current_section)
                        current_section = {}

            if current_section:
                sections.append(current_section)

            result = ContentPlan(
                title=title or topic,
                sections=sections,
                summary=summary,
                call_to_action=cta
            )

            logger.info(f"Generated content plan with {len(sections)} sections")
            return result

        except Exception as e:
            logger.error(f"Error generating content: {e}")
            raise

    async def generate_copy_variations(
        self,
        text: str,
        count: int = 3,
        focus_areas: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate multiple variations of copy for A/B testing.

        Args:
            text: Original copy text
            count: Number of variations to generate
            focus_areas: List of areas to vary (tone, length, angle, etc.)

        Returns:
            List of copy variations
        """
        focus_text = ""
        if focus_areas:
            focus_text = f"\nVary these aspects: {', '.join(focus_areas)}"

        prompt = f"""Generate {count} variations of the following copy for A/B testing.
Each variation should be unique and compelling but convey the same core message.{focus_text}

Original copy:
{text}

Provide exactly {count} variations, each on a new line, numbered:
VARIATION_1: [copy variation]
VARIATION_2: [copy variation]
etc."""

        try:
            response = await self.engine.generate(
                prompt, temperature=0.8, max_tokens=1000
            )

            variations = []
            for line in response.strip().split("\n"):
                if ":" in line and line.startswith("VARIATION_"):
                    variation = line.split(":", 1)[1].strip()
                    if variation:
                        variations.append(variation)

            logger.info(f"Generated {len(variations)} copy variations")
            return variations

        except Exception as e:
            logger.error(f"Error generating copy variations: {e}")
            raise

    async def optimize_for_audience(
        self,
        text: str,
        target_audience: str,
        tone: Optional[str] = None
    ) -> str:
        """
        Rewrite text for a specific target audience.

        Args:
            text: Original text
            target_audience: Who this is for (e.g., "C-level executives", "beginners")
            tone: Optional tone to apply (professional, friendly, etc.)

        Returns:
            Rewritten text optimized for the audience
        """
        tone_instruction = ""
        if tone:
            tone_instruction = f"\nAdopt a {tone} tone."

        prompt = f"""Rewrite the following text to be optimized for this target audience.
Consider their knowledge level, interests, pain points, and communication preferences.{tone_instruction}

Target Audience: {target_audience}

Original text:
{text}

Optimized text:"""

        try:
            optimized = await self.engine.generate(
                prompt, temperature=0.6, max_tokens=1000
            )

            logger.info(f"Optimized text for audience: {target_audience}")
            return optimized.strip()

        except Exception as e:
            logger.error(f"Error optimizing for audience: {e}")
            raise

    async def generate_headline(
        self,
        topic: str,
        style: str = "engaging"
    ) -> List[str]:
        """
        Generate multiple headline options.

        Args:
            topic: Topic for the headline
            style: Headline style (engaging, curiosity, benefit, question, etc.)

        Returns:
            List of headline options
        """
        style_guidance = {
            "engaging": "Make it captivating and attention-grabbing",
            "curiosity": "Create curiosity gaps that make people want to read more",
            "benefit": "Focus on the benefit to the reader",
            "question": "Pose interesting questions",
            "list": "Use number lists (e.g., '5 Ways To...')",
            "how_to": "Structure as how-to headlines"
        }.get(style, "Make it captivating and attention-grabbing")

        prompt = f"""Generate 5 compelling headline options for this topic.
{style_guidance}

Topic: {topic}

Provide exactly 5 headlines, each on a new line, numbered:
HEADLINE_1: [headline]
HEADLINE_2: [headline]
etc."""

        try:
            response = await self.engine.generate(
                prompt, temperature=0.8, max_tokens=500
            )

            headlines = []
            for line in response.strip().split("\n"):
                if ":" in line and line.startswith("HEADLINE_"):
                    headline = line.split(":", 1)[1].strip()
                    if headline:
                        headlines.append(headline)

            logger.info(f"Generated {len(headlines)} headlines")
            return headlines

        except Exception as e:
            logger.error(f"Error generating headlines: {e}")
            raise

    async def generate_landing_page(
        self,
        product_name: str,
        value_proposition: str,
        target_audience: str,
        call_to_action: str
    ) -> ContentPlan:
        """
        Generate a complete landing page structure.

        Args:
            product_name: Name of the product/service
            value_proposition: Core value proposition
            target_audience: Target audience
            call_to_action: Desired action (signup, download, purchase, etc.)

        Returns:
            ContentPlan with landing page structure
        """
        prompt = f"""Design a high-converting landing page structure.

Product: {product_name}
Value Proposition: {value_proposition}
Target Audience: {target_audience}
Call to Action: {call_to_action}

Create sections in this format:

HERO_HEADING: [Main headline]
HERO_SUBHEADING: [Supporting subheading]

SECTION_1_HEADING: Problem
SECTION_1_CONTENT: [Describe the problem the audience faces]

SECTION_2_HEADING: Solution
SECTION_2_CONTENT: [Explain how the product solves it]

SECTION_3_HEADING: Key Benefits
SECTION_3_CONTENT: [List 3-5 key benefits]

SECTION_4_HEADING: Social Proof
SECTION_4_CONTENT: [How to build trust and credibility]

CTA_PRIMARY: [Primary call to action text]
CTA_SECONDARY: [Secondary call to action]"""

        try:
            response = await self.engine.generate(
                prompt, temperature=0.6, max_tokens=1500
            )

            sections = []
            title = f"{product_name} - Landing Page"
            summary = value_proposition

            for line in response.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    if key in ["HERO_HEADING", "HERO_SUBHEADING"]:
                        sections.append({
                            "heading": key.replace("_", " "),
                            "content": value
                        })
                    elif key.startswith("SECTION_") and "_HEADING:" in line:
                        sections.append({
                            "heading": value,
                            "content": ""
                        })
                    elif key.startswith("SECTION_") and "_CONTENT:" in line:
                        if sections:
                            sections[-1]["content"] = value

            return ContentPlan(
                title=title,
                sections=sections,
                summary=summary,
                call_to_action=call_to_action
            )

        except Exception as e:
            logger.error(f"Error generating landing page: {e}")
            raise


# Singleton instance
_sites_ai: Optional[SitesAI] = None


def get_sites_ai() -> SitesAI:
    """Get SitesAI singleton."""
    global _sites_ai
    if _sites_ai is None:
        _sites_ai = SitesAI()
    return _sites_ai
