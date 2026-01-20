from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, Optional

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
Allowed actions: create_db, create_record, edit_record, query_db, delete_record, add_property, apply_template, list_templates.

{context_str}

PROPERTY TYPES - Use these exact type values:
- "text" - DEFAULT for most fields (names, titles, descriptions, notes, lead, etc.)
- "number" - ONLY for numeric values (age, price, quantity, etc.)  
- "date" - ONLY for dates (deadline, birthday, created_at, etc.)
- "checkbox" - ONLY for true/false (is_complete, is_active, etc.)
- "select" - ONLY for single choice from options
- "url" - ONLY for web links

IMPORTANT: When in doubt, use "text" type. Fields like "lead", "name", "title", "description" are ALWAYS "text".

Example 1:
User: Create a database called Customers with name, lead and age properties
JSON:
{{
  "action": "create_db",
  "params": {{
    "name": "Customers", 
    "properties": [
        {{"name": "name", "type": "text"}}, 
        {{"name": "lead", "type": "text"}},
        {{"name": "age", "type": "number"}}
    ]
  }}
}}

Example 2:
User: Add a task "Buy milk" to Projects
JSON:
{{
  "action": "create_record",
  "params": {{
    "db_name": "Projects",
    "data": {{ "Name": "Buy milk" }}
  }}
}}

If the context contains a "db_name" and the user says "Add a record here", use that db_name.

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
