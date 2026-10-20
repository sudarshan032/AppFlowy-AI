"""
Writing Capabilities

Notion-style AI writing tools:
- Summarize text
- Improve writing
- Change tone
- Translate content
- Make longer/shorter
"""

from typing import Optional, List
from enum import Enum
from ..core import get_engine


class Tone(str, Enum):
    """Available writing tones."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CONFIDENT = "confident"
    EMPATHETIC = "empathetic"
    PERSUASIVE = "persuasive"


class WritingAI:
    """
    AI capabilities for writing enhancement.
    
    Provides Notion-like writing tools:
    - Summarize
    - Improve writing
    - Fix grammar
    - Change tone
    - Translate
    - Make longer/shorter
    - Explain
    - Continue writing
    """
    
    def __init__(self):
        self.engine = get_engine()
    
    async def summarize(
        self,
        text: str,
        style: str = "concise",
        max_sentences: int = 3
    ) -> str:
        """
        Summarize text into key points.
        
        Args:
            text: Text to summarize
            style: Summary style (concise, detailed, bullet_points)
            max_sentences: Maximum sentences for the summary
            
        Returns:
            Summarized text
        """
        style_instruction = {
            "concise": f"Provide a {max_sentences}-sentence summary.",
            "detailed": "Provide a comprehensive summary covering all main points.",
            "bullet_points": "Provide the summary as bullet points."
        }.get(style, f"Provide a {max_sentences}-sentence summary.")
        
        prompt = f"""Summarize the following text.
{style_instruction}

Text:
{text}

Summary:"""

        return await self.engine.generate(prompt, temperature=0.3)
    
    async def improve_writing(
        self,
        text: str,
        focus: Optional[str] = None
    ) -> str:
        """
        Improve the quality of writing.
        
        Args:
            text: Text to improve
            focus: Optional focus area (clarity, flow, engagement, etc.)
            
        Returns:
            Improved text
        """
        focus_instruction = ""
        if focus:
            focus_instruction = f"\nFocus especially on improving: {focus}"
        
        prompt = f"""Improve the following text. Make it clearer, more engaging, and better structured.
{focus_instruction}

Original text:
{text}

Improved text:"""

        return await self.engine.generate(prompt, temperature=0.5)
    
    async def fix_grammar(self, text: str) -> str:
        """
        Fix grammar and spelling errors.
        
        Args:
            text: Text to fix
            
        Returns:
            Corrected text
        """
        prompt = f"""Fix any grammar, spelling, and punctuation errors in the following text.
Keep the original meaning and style intact.

Text:
{text}

Corrected text:"""

        return await self.engine.generate(prompt, temperature=0.1)
    
    async def change_tone(
        self,
        text: str,
        target_tone: Tone
    ) -> str:
        """
        Change the tone of the text.
        
        Args:
            text: Text to modify
            target_tone: Desired tone
            
        Returns:
            Text with new tone
        """
        prompt = f"""Rewrite the following text in a {target_tone.value} tone.
Maintain the core message while adjusting the style and word choice.

Original text:
{text}

{target_tone.value.capitalize()} version:"""

        return await self.engine.generate(prompt, temperature=0.6)
    
    async def translate(
        self,
        text: str,
        target_language: str,
        preserve_formatting: bool = True
    ) -> str:
        """
        Translate text to another language.
        
        Args:
            text: Text to translate
            target_language: Target language (e.g., "Spanish", "French")
            preserve_formatting: Whether to preserve markdown/formatting
            
        Returns:
            Translated text
        """
        formatting_instruction = ""
        if preserve_formatting:
            formatting_instruction = "\nPreserve any markdown formatting, bullet points, or structure."
        
        prompt = f"""Translate the following text to {target_language}.
{formatting_instruction}

Text:
{text}

Translation:"""

        return await self.engine.generate(prompt, temperature=0.3)
    
    async def make_longer(
        self,
        text: str,
        style: str = "expand"
    ) -> str:
        """
        Expand the text with more detail.
        
        Args:
            text: Text to expand
            style: Expansion style (expand, elaborate, examples)
            
        Returns:
            Longer text
        """
        style_instructions = {
            "expand": "Add more details and elaboration",
            "elaborate": "Provide deeper explanation of concepts",
            "examples": "Add relevant examples to illustrate points"
        }.get(style, "Add more details and elaboration")
        
        prompt = f"""Make the following text longer. {style_instructions}.
Keep the original meaning and key points.

Original text:
{text}

Expanded text:"""

        return await self.engine.generate(prompt, temperature=0.7)
    
    async def make_shorter(
        self,
        text: str,
        aggressive: bool = False
    ) -> str:
        """
        Condense the text to be shorter.
        
        Args:
            text: Text to condense
            aggressive: If True, make it much shorter
            
        Returns:
            Shorter text
        """
        instruction = "Make it significantly shorter" if aggressive else "Condense it while keeping key points"
        
        prompt = f"""Make the following text shorter. {instruction}.
Remove redundancy while preserving the core message.

Original text:
{text}

Shorter text:"""

        return await self.engine.generate(prompt, temperature=0.3)
    
    async def explain(
        self,
        text: str,
        audience: str = "general"
    ) -> str:
        """
        Explain the text in simpler terms.
        
        Args:
            text: Text to explain
            audience: Target audience level (general, beginner, expert)
            
        Returns:
            Explanation
        """
        audience_instruction = {
            "general": "for a general audience",
            "beginner": "in very simple terms, as if explaining to a beginner",
            "expert": "with technical depth for an expert audience"
        }.get(audience, "for a general audience")
        
        prompt = f"""Explain the following text {audience_instruction}.

Text:
{text}

Explanation:"""

        return await self.engine.generate(prompt, temperature=0.5)
    
    async def continue_writing(
        self,
        text: str,
        style: Optional[str] = None,
        length: str = "paragraph"
    ) -> str:
        """
        Continue writing based on existing text.
        
        Args:
            text: Existing text to continue from
            style: Optional style guidance
            length: How much to write (sentence, paragraph, section)
            
        Returns:
            Continuation
        """
        length_instruction = {
            "sentence": "Write one or two more sentences",
            "paragraph": "Write a paragraph continuation",
            "section": "Write a full section continuation"
        }.get(length, "Write a paragraph continuation")
        
        style_instruction = f"\nMaintain this style: {style}" if style else ""
        
        prompt = f"""Continue writing based on the following text. {length_instruction}.
Match the tone, style, and flow of the original.{style_instruction}

Text so far:
{text}

Continuation:"""

        return await self.engine.generate(prompt, temperature=0.8)


# Singleton instance
_writing_ai: Optional[WritingAI] = None


def get_writing_ai() -> WritingAI:
    """Get WritingAI singleton."""
    global _writing_ai
    if _writing_ai is None:
        _writing_ai = WritingAI()
    return _writing_ai
