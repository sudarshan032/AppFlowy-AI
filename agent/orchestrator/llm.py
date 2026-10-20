from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, Optional, List
import json

class LLMService:
    def __init__(self, model_name: str = "gpt-oss:20b", base_url: str = "http://localhost:11434"):
        self.llm = ChatOllama(model=model_name, base_url=base_url, temperature=0)

    def generate_text(self, prompt: str) -> str:
        return self.llm.invoke(prompt).content

    def parse_action(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parses user input into a structured action JSON.
        """
        context_str = ""
        if context:
            context_str = f"\nCURRENT CONTEXT:\n{context}\n"
            
        # Use a raw/regular string to avoid f-string escaping nightmare
        # LangChain uses {variable} for its own templates.
        system_prompt = """You are an agent that acts on a database. 
You MUST respond in strict JSON format with keys: "action" (string) and "params" (object).
Allowed actions: create_db, create_record, edit_record, query_db, delete_record, delete_database, add_property, drop_property, rename_property, list_properties, apply_template, list_templates, create_page, summarize, improve_writing, explain, continue_writing, none.

{context_str}

PROPERTY TYPES - Use these exact type values:
- "text" - DEFAULT for most fields (names, titles, descriptions, notes, lead, etc.)
- "number" - ONLY for numeric values (age, price, quantity, etc.)  
- "date" - ONLY for dates (deadline, birthday, created_at, etc.)
- "checkbox" - ONLY for true/false (is_complete, is_active, etc.)
- "select" - ONLY for single choice from options
- "url" - ONLY for web links

IMPORTANT: When in doubt, use "text" type. Fields like "lead", "name", "title", "description" are ALWAYS "text".

When creating databases or pages, always suggest a relevant emoji icon in the "icon" field.

Example 1 - Create database:
User: Create a database called Customers with name, lead and age properties
JSON:
{{
  "action": "create_db",
  "params": {{
    "name": "Customers",
    "icon": "👥",
    "properties": [
        {{"name": "name", "type": "text"}},
        {{"name": "lead", "type": "text"}},
        {{"name": "age", "type": "number"}}
    ]
  }}
}}

Example 2 - Add record:
User: Add a task "Buy milk" to Projects
JSON:
{{
  "action": "create_record",
  "params": {{
    "db_name": "Projects",
    "data": {{ "Name": "Buy milk" }}
  }}
}}

Example 3 - Drop column/property:
User: Drop the deal_value column from CRM
JSON:
{{
  "action": "drop_property",
  "params": {{
    "db_name": "CRM",
    "property_name": "deal_value"
  }}
}}

Example 4 - Add column/property:
User: Add a column called value_adds_for_company as number to CRM
JSON:
{{
  "action": "add_property",
  "params": {{
    "db_name": "CRM",
    "property_name": "value_adds_for_company",
    "property_type": "number"
  }}
}}

Example 5 - Rename column/property:
User: Rename the deal_value column to company_value in CRM
JSON:
{{
  "action": "rename_property",
  "params": {{
    "db_name": "CRM",
    "old_name": "deal_value",
    "new_name": "company_value"
  }}
}}

Example 6 - List columns/properties:
User: What columns does the CRM database have?
JSON:
{{
  "action": "list_properties",
  "params": {{
    "db_name": "CRM"
  }}
}}

Example 7 - Edit record:
User: Update record abc-123 in CRM, set Status to Active
JSON:
{{
  "action": "edit_record",
  "params": {{
    "db_name": "CRM",
    "record_id": "abc-123",
    "data": {{ "Status": "Active" }}
  }}
}}

Example 8 - Delete record:
User: Delete record abc-123 from CRM
JSON:
{{
  "action": "delete_record",
  "params": {{
    "db_name": "CRM",
    "record_id": "abc-123"
  }}
}}

Example 9 - Delete database:
User: Delete the CRM database
JSON:
{{
  "action": "delete_database",
  "params": {{
    "db_name": "CRM"
  }}
}}

Example 10 - Create page:
User: Create a meeting notes page for Q4 planning
JSON:
{{
  "action": "create_page",
  "params": {{
    "title": "Q4 Planning Meeting Notes",
    "description": "Meeting notes for Q4 planning session",
    "icon": "📝"
  }}
}}

Example 11 - Continue writing:
User: Continue writing this paragraph about machine learning
JSON:
{{
  "action": "continue_writing",
  "params": {{
    "text": "this paragraph about machine learning"
  }}
}}

Example 12 - Explain:
User: Explain this in simple terms: Machine learning uses gradient descent to minimize loss functions
JSON:
{{
  "action": "explain",
  "params": {{
    "text": "Machine learning uses gradient descent to minimize loss functions"
  }}
}}

Example 13 - Summarize:
User: Summarize this: The quarterly report shows a 15% increase in revenue driven by new product launches.
JSON:
{{
  "action": "summarize",
  "params": {{
    "text": "The quarterly report shows a 15% increase in revenue driven by new product launches."
  }}
}}

Use "none" when the request is not a database/schema/writing/page operation (e.g. greetings, off-topic questions).

WRITING ACTIONS - These are writing/text operations, NOT general questions:
When user says "explain", "explain this", "explain in simple terms", or asks for explanation of provided text, use the "explain" action.
When user says "summarize", "summarize this", or asks for a summary of provided text, use the "summarize" action.
When user says "improve", "improve writing", "rewrite", or asks to improve provided text, use the "improve_writing" action.
When user says "continue writing", "continue this", or asks to extend provided text, use the "continue_writing" action.

If the context contains a "db_name" and the user says "Add a record here", use that db_name.
When user says "drop column", "remove column", "delete column", or similar, use drop_property action.
When user says "add column", "add property", or similar, use add_property action.
When user says "delete database", "remove database", "drop database", use delete_database action.
When user says "create a page", "make a page", "new page", use create_page action.

Do NOT output any markdown code fences or extra text. JUST valid JSON.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])
        
        chain = prompt | self.llm | JsonOutputParser()
        
        try:
            return chain.invoke({"input": user_input, "context_str": context_str})
        except Exception as e:
            # Fallback for malformed JSON
            print(f"Error parsing LLM output: {e}")
            return {"action": "error", "params": {"error": str(e)}}

    def generate_page_content(self, title: str, description: str = "") -> Dict[str, Any]:
        """Generate structured page content blocks from a title and description."""
        system_prompt = """You generate structured page content as JSON.
Return a JSON object with a "blocks" array. Each block has a "type" and type-specific fields.

Supported block types:
- {"type": "heading", "level": 1, "text": "..."}
- {"type": "heading", "level": 2, "text": "..."}
- {"type": "paragraph", "text": "..."}
- {"type": "bullet_list", "items": ["...", "..."]}
- {"type": "todo", "text": "...", "checked": false}

Generate 5-15 blocks that make a useful page. Include a level-1 heading matching the title, then relevant sections, bullet lists, and todo items.

Return ONLY valid JSON. No markdown fences or extra text."""

        user_prompt = f"Create page content for: {title}"
        if description:
            user_prompt += f"\nDescription: {description}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])

        chain = prompt | self.llm | JsonOutputParser()

        try:
            result = chain.invoke({"input": user_prompt})
            if isinstance(result, dict) and "blocks" in result:
                return result
            return {"blocks": [
                {"type": "heading", "level": 1, "text": title},
                {"type": "paragraph", "text": description or ""}
            ]}
        except Exception as e:
            print(f"Error generating page content: {e}")
            return {"blocks": [
                {"type": "heading", "level": 1, "text": title},
                {"type": "paragraph", "text": description or ""}
            ]}
