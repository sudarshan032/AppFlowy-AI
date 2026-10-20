"""
Database AI Capabilities — Phase 2

Notion-style AI features for database operations:
- Autofill property values using AI
- AI property creation and auto-update
- Summary, key info, and translation properties
- Formula suggestions from natural language
- Batch autofill operations
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from ..core import get_engine

logger = logging.getLogger(__name__)


class AIPropertyType(str, Enum):
    """Types of AI-powered database properties."""
    SUMMARY = "ai_summary"          # Auto-summarize content
    KEY_INFO = "ai_key_info"        # Extract key data points
    TRANSLATION = "ai_translation"  # Auto-translate content
    CUSTOM = "ai_custom"            # User-defined AI prompt


@dataclass
class AIPropertyConfig:
    """Configuration for an AI property."""
    property_id: int
    property_name: str
    ai_type: AIPropertyType
    source_properties: List[str]  # Which properties to use as input
    prompt_template: Optional[str] = None  # For CUSTOM type
    target_language: Optional[str] = None  # For TRANSLATION type
    auto_update: bool = False  # Auto-update when source changes


class DatabaseAI:
    """
    AI capabilities for database operations.

    Provides Notion-like AI features:
    - Auto-generate property values
    - AI-powered properties (summary, key info, translation)
    - Suggest formulas from descriptions
    - Categorize content
    - Extract key information
    """

    def __init__(self):
        """Initialize DatabaseAI."""
        self.engine = get_engine()

    async def autofill_property(
        self,
        content: str,
        property_name: str,
        property_type: str = "text",
        existing_values: Optional[List[str]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a value for a property based on content.

        Args:
            content: The page/row content to analyze
            property_name: Name of the property to fill
            property_type: Type of property (text, number, date, select, etc.)
            existing_values: For select types, existing options
            context: Additional context about the database

        Returns:
            Generated property value
        """
        examples = ""
        if existing_values:
            examples = f"\nExisting values for reference: {', '.join(existing_values[:10])}"

        context_str = f"\nContext: {context}" if context else ""

        prompt = f"""You are an AI assistant that fills in database property values.

Analyze the following content and generate an appropriate value for the property.

Content:
{content}

Property to fill:
- Name: {property_name}
- Type: {property_type}
{examples}{context_str}

Instructions:
- For 'text' type: Generate a concise, relevant value
- For 'number' type: Extract or estimate a numeric value
- For 'date' type: Extract or suggest a date in YYYY-MM-DD format
- For 'select' type: Choose from existing values or suggest a new category
- For 'checkbox' type: Respond with 'true' or 'false'

Respond with ONLY the property value, nothing else."""

        return await self.engine.generate(prompt, temperature=0.3)

    async def create_ai_property(
        self,
        db_session: Session,
        db_id: int,
        property_name: str,
        ai_type: AIPropertyType,
        source_properties: List[str],
        prompt_template: Optional[str] = None,
        target_language: Optional[str] = None,
        auto_update: bool = False
    ) -> AIPropertyConfig:
        """
        Create a new AI-powered property in a database.

        Args:
            db_session: SQLAlchemy session
            db_id: Database ID
            property_name: Name for the new property
            ai_type: Type of AI property (summary, key_info, etc.)
            source_properties: Which properties to use as input
            prompt_template: For CUSTOM type, the prompt template
            target_language: For TRANSLATION type, target language
            auto_update: Whether to auto-update when source changes

        Returns:
            AIPropertyConfig object
        """
        try:
            from ...db.models import Property

            # Create the property in database
            prop = Property(
                db_id=db_id,
                name=property_name,
                type=ai_type.value,
                options={
                    "source_properties": source_properties,
                    "prompt_template": prompt_template,
                    "target_language": target_language,
                    "auto_update": auto_update
                }
            )

            db_session.add(prop)
            db_session.commit()

            config = AIPropertyConfig(
                property_id=prop.id,
                property_name=property_name,
                ai_type=ai_type,
                source_properties=source_properties,
                prompt_template=prompt_template,
                target_language=target_language,
                auto_update=auto_update
            )

            logger.info(f"Created AI property: {property_name} ({ai_type.value})")
            return config

        except Exception as e:
            logger.error(f"Error creating AI property: {e}")
            db_session.rollback()
            raise

    async def compute_ai_property(
        self,
        ai_property: AIPropertyConfig,
        record_data: Dict[str, Any]
    ) -> str:
        """
        Compute the AI value for a single record.

        Args:
            ai_property: AIPropertyConfig for the property
            record_data: Record data dictionary

        Returns:
            Computed property value
        """
        try:
            # Extract source content
            source_content = self._extract_source_content(
                record_data, ai_property.source_properties
            )

            if not source_content.strip():
                logger.warning(f"No source content for property {ai_property.property_name}")
                return ""

            # Generate value based on type
            if ai_property.ai_type == AIPropertyType.SUMMARY:
                return await self._generate_summary(source_content)

            elif ai_property.ai_type == AIPropertyType.KEY_INFO:
                return await self._extract_key_info(source_content)

            elif ai_property.ai_type == AIPropertyType.TRANSLATION:
                return await self._translate_content(
                    source_content, ai_property.target_language
                )

            elif ai_property.ai_type == AIPropertyType.CUSTOM:
                return await self._generate_custom(
                    source_content, ai_property.prompt_template
                )

            else:
                logger.warning(f"Unknown AI property type: {ai_property.ai_type}")
                return ""

        except Exception as e:
            logger.error(f"Error computing AI property: {e}")
            raise

    async def autofill_column(
        self,
        db_session: Session,
        ai_property_id: int
    ) -> int:
        """
        Autofill all records in database for an AI property.

        Args:
            db_session: SQLAlchemy session
            ai_property_id: AI property ID

        Returns:
            Number of records filled
        """
        try:
            from ...db.models import Property, Record, Database

            # Get property
            prop = db_session.query(Property).filter_by(id=ai_property_id).first()
            if not prop:
                logger.error(f"Property {ai_property_id} not found")
                return 0

            # Build config
            config = AIPropertyConfig(
                property_id=prop.id,
                property_name=prop.name,
                ai_type=AIPropertyType(prop.type),
                source_properties=prop.options.get("source_properties", []),
                prompt_template=prop.options.get("prompt_template"),
                target_language=prop.options.get("target_language"),
                auto_update=prop.options.get("auto_update", False)
            )

            # Get all records in database
            records = db_session.query(Record).filter_by(db_id=prop.db_id).all()
            filled_count = 0

            for record in records:
                try:
                    # Compute value
                    value = await self.compute_ai_property(config, record.data)

                    # Update record
                    if value:
                        record.data[prop.name] = value
                        filled_count += 1

                except Exception as e:
                    logger.error(f"Error filling record {record.id}: {e}")
                    continue

            db_session.commit()
            logger.info(f"Autofilled {filled_count} records for property {prop.name}")
            return filled_count

        except Exception as e:
            logger.error(f"Error autofilling column: {e}")
            db_session.rollback()
            raise

    async def batch_autofill(
        self,
        db_session: Session,
        db_id: int
    ) -> Dict[str, int]:
        """
        Autofill all AI properties for a database.

        Args:
            db_session: SQLAlchemy session
            db_id: Database ID

        Returns:
            Dict mapping property names to count filled
        """
        try:
            from ...db.models import Property

            # Get all AI properties for this database
            ai_props = db_session.query(Property).filter_by(
                db_id=db_id
            ).filter(
                Property.type.in_([t.value for t in AIPropertyType])
            ).all()

            results = {}

            for prop in ai_props:
                try:
                    count = await self.autofill_column(db_session, prop.id)
                    results[prop.name] = count
                except Exception as e:
                    logger.error(f"Error autofilling {prop.name}: {e}")
                    results[prop.name] = 0

            logger.info(f"Batch autofill complete for database {db_id}")
            return results

        except Exception as e:
            logger.error(f"Error in batch autofill: {e}")
            raise

    async def suggest_formula(
        self,
        description: str,
        columns: List[Dict[str, str]],
        database_context: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Suggest a formula based on natural language description.

        Args:
            description: What the formula should do
            columns: Available columns with names and types
            database_context: What the database is about

        Returns:
            Dict with 'formula' and 'explanation'
        """
        columns_str = "\n".join([f"- {col['name']} ({col['type']})" for col in columns])
        context_str = f"\nDatabase context: {database_context}" if database_context else ""

        prompt = f"""You are an AI that generates formulas for databases.

Available columns:
{columns_str}
{context_str}

User wants: {description}

Generate a formula that accomplishes this. Use a syntax similar to spreadsheets or Notion formulas.

Respond in this exact format:
FORMULA: <the formula>
EXPLANATION: <brief explanation of how it works>"""

        result = await self.engine.generate(prompt, temperature=0.2)

        # Parse response
        formula = ""
        explanation = ""

        for line in result.strip().split("\n"):
            if line.startswith("FORMULA:"):
                formula = line.replace("FORMULA:", "").strip()
            elif line.startswith("EXPLANATION:"):
                explanation = line.replace("EXPLANATION:", "").strip()

        return {"formula": formula, "explanation": explanation}

    async def categorize_content(
        self,
        content: str,
        categories: List[str],
        allow_new: bool = False
    ) -> str:
        """
        Categorize content into one of the given categories.

        Args:
            content: Text to categorize
            categories: Available categories
            allow_new: Whether to allow suggesting new categories

        Returns:
            The chosen category
        """
        new_category_instruction = ""
        if allow_new:
            new_category_instruction = "\nIf none of the categories fit well, you may suggest a new one."

        prompt = f"""Categorize the following content into one of these categories:
{', '.join(categories)}
{new_category_instruction}

Content:
{content}

Respond with ONLY the category name, nothing else."""

        result = await self.engine.generate(prompt, temperature=0.1)

        result = result.strip()

        if not allow_new and result not in categories:
            result_lower = result.lower()
            for cat in categories:
                if cat.lower() == result_lower or result_lower in cat.lower():
                    return cat
            return categories[0] if categories else result

        return result

    async def extract_key_info(
        self,
        content: str,
        fields: List[str]
    ) -> Dict[str, str]:
        """
        Extract key information from content.

        Args:
            content: Text to analyze
            fields: List of fields to extract

        Returns:
            Dict mapping field names to extracted values
        """
        fields_str = "\n".join([f"- {field}" for field in fields])

        prompt = f"""Extract the following information from the content below.

Fields to extract:
{fields_str}

Content:
{content}

Respond in this format (one per line):
FIELD_NAME: extracted value
(Use "N/A" if not found)"""

        result = await self.engine.generate(prompt, temperature=0.2)

        extracted = {}
        for line in result.strip().split("\n"):
            if ":" in line:
                parts = line.split(":", 1)
                field = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else "N/A"
                for requested_field in fields:
                    if field.lower() == requested_field.lower():
                        extracted[requested_field] = value
                        break

        for field in fields:
            if field not in extracted:
                extracted[field] = "N/A"

        return extracted

    # Private helper methods

    def _extract_source_content(
        self,
        record_data: Dict[str, Any],
        source_properties: List[str]
    ) -> str:
        """Extract and combine content from source properties."""
        parts = []
        for prop in source_properties:
            value = record_data.get(prop, "")
            if value:
                parts.append(str(value))
        return " ".join(parts)

    async def _generate_summary(self, content: str) -> str:
        """Generate a summary of content."""
        prompt = f"""Summarize the following content concisely in 1-2 sentences.

Content:
{content}

Summary:"""
        return await self.engine.generate(prompt, temperature=0.3, max_tokens=200)

    async def _extract_key_info(self, content: str) -> str:
        """Extract key information points."""
        prompt = f"""Extract 3-5 key information points from the following content.
Format as a bullet list.

Content:
{content}

Key points:"""
        return await self.engine.generate(prompt, temperature=0.3, max_tokens=300)

    async def _translate_content(
        self,
        content: str,
        target_language: str
    ) -> str:
        """Translate content to target language."""
        prompt = f"""Translate the following content to {target_language}.

Content:
{content}

Translation:"""
        return await self.engine.generate(prompt, temperature=0.3, max_tokens=len(content) * 2)

    async def _generate_custom(
        self,
        content: str,
        prompt_template: str
    ) -> str:
        """Generate value using custom prompt template."""
        # Replace {content} placeholder
        prompt = prompt_template.replace("{content}", content)
        return await self.engine.generate(prompt, temperature=0.5, max_tokens=500)


# Singleton instance
_database_ai: Optional[DatabaseAI] = None


def get_database_ai() -> DatabaseAI:
    """Get DatabaseAI singleton."""
    global _database_ai
    if _database_ai is None:
        _database_ai = DatabaseAI()
    return _database_ai
