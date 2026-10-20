"""
Image Generation — Phase 4

AI image generation capabilities:
- DALL-E image generation from prompts
- Auto-prompt generation from page content
- Image style control
"""

from typing import Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
import base64
import os

from ..core import get_engine

logger = logging.getLogger(__name__)


class ImageSize(str, Enum):
    """Supported image sizes for DALL-E."""
    SMALL = "256x256"
    MEDIUM = "512x512"
    LARGE = "1024x1024"
    WIDESCREEN = "1792x1024"
    PORTRAIT = "1024x1792"


class ImageStyle(str, Enum):
    """Image style options."""
    NATURAL = "natural"
    PHOTOREALISTIC = "photorealistic"
    ARTISTIC = "artistic"
    CARTOON = "cartoon"
    SKETCH = "sketch"
    WATERCOLOR = "watercolor"
    OIL_PAINTING = "oil painting"
    ABSTRACT = "abstract"
    MINIMALIST = "minimalist"


@dataclass
class GeneratedImage:
    """Generated image result."""
    url: Optional[str] = None  # URL for web-hosted images
    base64: Optional[str] = None  # Base64 encoded image data
    prompt: str = ""
    revised_prompt: str = ""  # Prompt as revised by DALL-E
    size: str = "1024x1024"
    style: str = "natural"


class ImageGenerator:
    """
    AI image generation using DALL-E API.

    Provides:
    - Image generation from text prompts
    - Auto-prompt generation from content
    - Multiple style options
    - Size control
    """

    def __init__(self):
        """Initialize ImageGenerator."""
        self.engine = get_engine()
        self._openai_available = self._check_openai()
        self._api_key = os.getenv("OPENAI_API_KEY")

    def _check_openai(self) -> bool:
        """Check if OpenAI library is available."""
        try:
            import openai
            return True
        except ImportError:
            logger.warning("OpenAI not installed. Install with: pip install openai")
            return False

    async def generate(
        self,
        prompt: str,
        size: Union[str, ImageSize] = ImageSize.LARGE,
        style: Union[str, ImageStyle] = ImageStyle.NATURAL,
        quality: str = "standard"
    ) -> GeneratedImage:
        """
        Generate an image from a text prompt using DALL-E.

        Args:
            prompt: Text description of the image to generate
            size: Image size (256x256, 512x512, 1024x1024, etc.)
            style: Image style (natural, photorealistic, artistic, etc.)
            quality: Image quality (standard or hd)

        Returns:
            GeneratedImage with URL or base64 encoded image

        Raises:
            RuntimeError: If OpenAI not available or API key not set
        """
        if not self._openai_available:
            raise RuntimeError(
                "OpenAI not installed. Install with: pip install openai"
            )

        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable not set. "
                "Please set your OpenAI API key."
            )

        try:
            import openai

            # Normalize size enum
            if isinstance(size, ImageSize):
                size_str = size.value
            else:
                size_str = size

            # Build enhanced prompt with style
            if isinstance(style, ImageStyle):
                style_str = style.value
            else:
                style_str = style

            enhanced_prompt = f"{prompt}, {style_str} style"

            logger.info(f"Generating image: {enhanced_prompt}")

            # Call DALL-E API
            client = openai.OpenAI(api_key=self._api_key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size_str,
                quality=quality,
                n=1,
                response_format="url"
            )

            # Extract result
            image_data = response.data[0]

            result = GeneratedImage(
                url=image_data.url,
                prompt=prompt,
                revised_prompt=image_data.revised_prompt or prompt,
                size=size_str,
                style=style_str
            )

            logger.info(f"Image generated successfully: {result.url}")
            return result

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise

    async def generate_with_base64(
        self,
        prompt: str,
        size: Union[str, ImageSize] = ImageSize.LARGE,
        style: Union[str, ImageStyle] = ImageStyle.NATURAL
    ) -> GeneratedImage:
        """
        Generate image and return as base64 encoded data.

        Args:
            prompt: Text description
            size: Image size
            style: Image style

        Returns:
            GeneratedImage with base64 encoded image data
        """
        try:
            import openai
            import httpx

            if not self._api_key:
                raise RuntimeError("OPENAI_API_KEY not set")

            # Normalize inputs
            if isinstance(size, ImageSize):
                size_str = size.value
            else:
                size_str = size

            if isinstance(style, ImageStyle):
                style_str = style.value
            else:
                style_str = style

            enhanced_prompt = f"{prompt}, {style_str} style"

            logger.info(f"Generating image (base64): {enhanced_prompt}")

            # Generate image
            client = openai.OpenAI(api_key=self._api_key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size_str,
                n=1,
                response_format="url"
            )

            image_url = response.data[0].url

            # Download and convert to base64
            image_data = httpx.get(image_url).content
            base64_data = base64.b64encode(image_data).decode("utf-8")

            result = GeneratedImage(
                base64=base64_data,
                prompt=prompt,
                revised_prompt=response.data[0].revised_prompt or prompt,
                size=size_str,
                style=style_str
            )

            logger.info("Image generated and converted to base64")
            return result

        except Exception as e:
            logger.error(f"Error generating base64 image: {e}")
            raise

    async def generate_from_page(
        self,
        page_content: str,
        page_title: Optional[str] = None,
        style: Union[str, ImageStyle] = ImageStyle.NATURAL
    ) -> GeneratedImage:
        """
        Auto-generate an image based on page content.

        First generates a visual prompt from the content, then creates an image.

        Args:
            page_content: Page text content
            page_title: Optional page title
            style: Image style

        Returns:
            GeneratedImage
        """
        try:
            # Generate visual prompt from content
            visual_prompt = await self._generate_visual_prompt(
                page_content,
                page_title
            )

            logger.info(f"Auto-generated visual prompt: {visual_prompt}")

            # Generate image from prompt
            return await self.generate(visual_prompt, style=style)

        except Exception as e:
            logger.error(f"Error generating image from page: {e}")
            raise

    async def _generate_visual_prompt(
        self,
        content: str,
        title: Optional[str] = None
    ) -> str:
        """
        Generate a visual prompt from page content.

        Args:
            content: Page content
            title: Optional page title

        Returns:
            Visual prompt suitable for image generation
        """
        title_context = f"Page title: {title}\n" if title else ""

        prompt = f"""Generate a detailed visual prompt for creating an image that represents this content.
The prompt should be specific and evocative, suitable for DALL-E image generation.
Make it 2-3 sentences describing the key visual elements.

{title_context}Content (first 500 chars):
{content[:500]}

Visual prompt:"""

        try:
            visual_prompt = await self.engine.generate(
                prompt, temperature=0.7, max_tokens=200
            )

            return visual_prompt.strip()

        except Exception as e:
            logger.error(f"Error generating visual prompt: {e}")
            # Fallback to simple prompt
            return title or "Abstract representation of the content"

    async def generate_batch(
        self,
        prompts: list,
        size: Union[str, ImageSize] = ImageSize.LARGE,
        style: Union[str, ImageStyle] = ImageStyle.NATURAL
    ) -> list:
        """
        Generate multiple images from prompts.

        Args:
            prompts: List of text prompts
            size: Image size
            style: Image style

        Returns:
            List of GeneratedImage objects
        """
        import asyncio

        results = []

        # OpenAI rate limiting: 1 request per second recommended
        for prompt in prompts:
            try:
                image = await self.generate(prompt, size=size, style=style)
                results.append(image)

                # Rate limiting delay
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error generating image for prompt '{prompt}': {e}")
                results.append(None)

        return results

    async def get_image_url(self, image: GeneratedImage) -> Optional[str]:
        """
        Get the URL for an image.

        Args:
            image: GeneratedImage object

        Returns:
            Image URL if available, None otherwise
        """
        return image.url

    async def save_to_file(
        self,
        image: GeneratedImage,
        filepath: str
    ) -> bool:
        """
        Save generated image to file.

        Only works if image has base64 data. Otherwise, download from URL.

        Args:
            image: GeneratedImage object
            filepath: Path to save to

        Returns:
            True if successful
        """
        try:
            if image.base64:
                # Decode and write base64 image
                image_data = base64.b64decode(image.base64)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                logger.info(f"Saved image to: {filepath}")
                return True

            elif image.url:
                # Download from URL
                import httpx

                response = httpx.get(image.url)
                if response.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Downloaded and saved image to: {filepath}")
                    return True
                else:
                    logger.error(f"Failed to download image: {response.status_code}")
                    return False

            else:
                logger.warning("No image URL or base64 data available")
                return False

        except Exception as e:
            logger.error(f"Error saving image to file: {e}")
            return False


# Singleton instance
_image_generator: Optional[ImageGenerator] = None


def get_image_generator() -> ImageGenerator:
    """Get ImageGenerator singleton."""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
