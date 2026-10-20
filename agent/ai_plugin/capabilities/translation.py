"""
Enhanced Translation — Phase 3

Advanced multi-language translation capabilities:
- Text translation to any language
- Language detection
- Batch translation
- Database column translation
- Formatting preservation
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

from ..core import get_engine

logger = logging.getLogger(__name__)

# Common languages mapping
LANGUAGES = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "japanese": "ja",
    "chinese": "zh",
    "korean": "ko",
    "arabic": "ar",
    "hindi": "hi",
    "dutch": "nl",
    "swedish": "sv",
    "polish": "pl",
}


class TranslationAI:
    """
    Advanced translation and language processing.

    Provides:
    - Translation to 50+ languages
    - Language detection
    - Batch translation
    - Database column translation
    - Formatting preservation
    """

    def __init__(self):
        """Initialize TranslationAI."""
        self.engine = get_engine()
        self._language_cache = {}

    async def detect_language(self, text: str) -> str:
        """
        Detect the language of given text.

        Args:
            text: Text to analyze

        Returns:
            Language name (e.g., "English", "Spanish")
        """
        if not text.strip():
            return "Unknown"

        prompt = f"""Identify the language of the following text.
Respond with ONLY the language name, nothing else.

Text: {text[:200]}

Language:"""

        try:
            language = await self.engine.generate(
                prompt, temperature=0.1, max_tokens=50
            )

            language = language.strip()
            logger.info(f"Detected language: {language}")
            return language

        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return "Unknown"

    async def translate(
        self,
        text: str,
        target_language: str,
        preserve_formatting: bool = True,
        context: Optional[str] = None
    ) -> str:
        """
        Translate text to target language.

        Args:
            text: Text to translate
            target_language: Target language (name or code)
            preserve_formatting: Whether to preserve markdown/formatting
            context: Optional context for better translation

        Returns:
            Translated text
        """
        if not text.strip():
            logger.warning("Empty text for translation")
            return ""

        # Normalize language name
        target_lang = self._normalize_language(target_language)

        formatting_instruction = ""
        if preserve_formatting:
            formatting_instruction = "\nPreserve any markdown formatting, bullet points, numbered lists, and structure."

        context_instruction = ""
        if context:
            context_instruction = f"\nContext: {context}"

        prompt = f"""Translate the following text to {target_lang}.
Maintain the original meaning and tone accurately.{formatting_instruction}{context_instruction}

Text to translate:
{text}

Translation:"""

        try:
            translated = await self.engine.generate(
                prompt, temperature=0.3, max_tokens=len(text) * 2
            )

            logger.info(f"Translated text to {target_lang}")
            return translated.strip()

        except Exception as e:
            logger.error(f"Error translating to {target_lang}: {e}")
            raise

    async def batch_translate(
        self,
        texts: List[str],
        target_language: str,
        preserve_formatting: bool = True
    ) -> List[str]:
        """
        Translate multiple texts to target language.

        Args:
            texts: List of texts to translate
            target_language: Target language
            preserve_formatting: Whether to preserve formatting

        Returns:
            List of translated texts
        """
        results = []

        for text in texts:
            try:
                translated = await self.translate(
                    text,
                    target_language,
                    preserve_formatting
                )
                results.append(translated)

            except Exception as e:
                logger.error(f"Error translating text: {e}")
                results.append("")  # Empty on error

        logger.info(f"Batch translated {len(results)} texts")
        return results

    async def translate_database_column(
        self,
        db_session: Session,
        db_id: int,
        source_property_name: str,
        target_language: str,
        target_property_name: Optional[str] = None
    ) -> int:
        """
        Translate an entire database column to target language.

        Creates a new column with translated content or updates existing column.

        Args:
            db_session: SQLAlchemy session
            db_id: Database ID
            source_property_name: Name of source property/column
            target_language: Target language for translation
            target_property_name: Optional name for target column

        Returns:
            Number of records translated
        """
        try:
            from ...db.models import Database, Record

            # Get database
            db = db_session.query(Database).filter_by(id=db_id).first()
            if not db:
                logger.error(f"Database {db_id} not found")
                return 0

            # Get target property name
            if not target_property_name:
                target_property_name = f"{source_property_name}_translation"

            # Ensure target property exists
            self._ensure_property_exists(
                db_session, db_id, target_property_name, "text"
            )

            # Get all records
            records = db_session.query(Record).filter_by(db_id=db_id).all()

            translated_count = 0

            for record in records:
                try:
                    # Extract source text from data
                    source_text = record.data.get(source_property_name, "")

                    if source_text and isinstance(source_text, str):
                        # Translate
                        translated = await self.translate(
                            source_text,
                            target_language,
                            preserve_formatting=True
                        )

                        # Update record
                        if translated:
                            record.data[target_property_name] = translated
                            translated_count += 1

                except Exception as e:
                    logger.error(
                        f"Error translating record {record.id}: {e}"
                    )
                    continue

            # Commit changes
            db_session.commit()
            logger.info(
                f"Translated {translated_count} records in {source_property_name}"
            )

            return translated_count

        except Exception as e:
            logger.error(f"Error translating database column: {e}")
            db_session.rollback()
            raise

    async def translate_multiple_languages(
        self,
        text: str,
        target_languages: List[str]
    ) -> Dict[str, str]:
        """
        Translate text to multiple languages at once.

        Args:
            text: Text to translate
            target_languages: List of target languages

        Returns:
            Dict mapping language to translated text
        """
        results = {}

        for language in target_languages:
            try:
                translated = await self.translate(text, language)
                results[language] = translated

            except Exception as e:
                logger.error(f"Error translating to {language}: {e}")
                results[language] = ""

        logger.info(f"Translated to {len(results)} languages")
        return results

    async def back_translate(
        self,
        text: str,
        intermediate_language: str,
        original_language: str = "English"
    ) -> str:
        """
        Back-translate: Original → Intermediate → Original.

        Useful for quality checking translations.

        Args:
            text: Original text
            intermediate_language: Language to translate through
            original_language: Original language

        Returns:
            Back-translated text (should be similar to original)
        """
        try:
            # Translate to intermediate language
            intermediate = await self.translate(text, intermediate_language)

            # Translate back to original
            back_translated = await self.translate(
                intermediate, original_language
            )

            logger.info(f"Back-translation complete: {original_language} → {intermediate_language} → {original_language}")
            return back_translated.strip()

        except Exception as e:
            logger.error(f"Error in back-translation: {e}")
            raise

    async def compare_translations(
        self,
        text: str,
        target_language: str,
        num_variations: int = 3
    ) -> List[str]:
        """
        Generate multiple translations for comparison.

        Useful for finding the best translation nuance.

        Args:
            text: Text to translate
            target_language: Target language
            num_variations: Number of translation variations

        Returns:
            List of different translations
        """
        variations = []

        for i in range(num_variations):
            try:
                # Vary temperature slightly for different outputs
                temperature = 0.2 + (i * 0.2)

                translated = await self.translate(text, target_language)
                variations.append(translated)

            except Exception as e:
                logger.error(f"Error generating translation variation {i + 1}: {e}")
                continue

        logger.info(f"Generated {len(variations)} translation variations")
        return variations

    async def translate_with_glossary(
        self,
        text: str,
        target_language: str,
        glossary: Dict[str, str]
    ) -> str:
        """
        Translate with a custom glossary of terms.

        Ensures consistent translation of key terms.

        Args:
            text: Text to translate
            target_language: Target language
            glossary: Dict mapping terms to their translations

        Returns:
            Translated text with glossary applied
        """
        if not glossary:
            return await self.translate(text, target_language)

        glossary_instruction = "\nUse these term translations:\n"
        for term, translation in glossary.items():
            glossary_instruction += f"- {term} = {translation}\n"

        target_lang = self._normalize_language(target_language)

        prompt = f"""Translate the following text to {target_lang}.
{glossary_instruction}
Maintain the original meaning and use the glossary terms consistently.

Text to translate:
{text}

Translation:"""

        try:
            translated = await self.engine.generate(
                prompt, temperature=0.3, max_tokens=len(text) * 2
            )

            logger.info(f"Translated with glossary to {target_lang}")
            return translated.strip()

        except Exception as e:
            logger.error(f"Error translating with glossary: {e}")
            raise

    def _normalize_language(self, language: str) -> str:
        """
        Normalize language name or code to full name.

        Args:
            language: Language name or code

        Returns:
            Full language name
        """
        lang_lower = language.lower()

        # Check if it's a code
        for name, code in LANGUAGES.items():
            if lang_lower == code or lang_lower == name:
                return name.capitalize()

        # Return as-is if not recognized
        return language

    def _ensure_property_exists(
        self,
        db_session: Session,
        db_id: int,
        property_name: str,
        property_type: str = "text"
    ) -> None:
        """
        Ensure a property exists in the database.

        Args:
            db_session: SQLAlchemy session
            db_id: Database ID
            property_name: Property name
            property_type: Property type
        """
        from ...db.models import Property

        existing = db_session.query(Property).filter_by(
            db_id=db_id,
            name=property_name
        ).first()

        if not existing:
            prop = Property(
                db_id=db_id,
                name=property_name,
                type=property_type
            )
            db_session.add(prop)
            db_session.commit()
            logger.info(f"Created property: {property_name}")

    async def estimate_translation_time(
        self,
        text_length: int,
        num_languages: int = 1
    ) -> Dict[str, Any]:
        """
        Estimate time and cost for translation.

        Args:
            text_length: Length of text in characters
            num_languages: Number of target languages

        Returns:
            Dict with time estimate and cost estimate
        """
        # Rough estimates based on OpenAI pricing
        tokens_estimate = text_length / 4  # ~4 chars per token
        time_per_translation = max(5, tokens_estimate / 100)  # seconds

        total_time = time_per_translation * num_languages
        cost_estimate = tokens_estimate * 0.000002 * num_languages  # rough USD estimate

        return {
            "estimated_time_seconds": int(total_time),
            "estimated_cost_usd": round(cost_estimate, 4),
            "tokens_estimate": int(tokens_estimate),
            "num_languages": num_languages
        }


# Singleton instance
_translation_ai: Optional[TranslationAI] = None


def get_translation_ai() -> TranslationAI:
    """Get TranslationAI singleton."""
    global _translation_ai
    if _translation_ai is None:
        _translation_ai = TranslationAI()
    return _translation_ai
