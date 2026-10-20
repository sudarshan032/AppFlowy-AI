"""
AI Agents Capability

Multi-step autonomous task execution:
- Workflow orchestration
- Batch processing
- Action chaining
"""

from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from pydantic import BaseModel
import asyncio

from ..core import get_engine


class ActionType(str, Enum):
    """Types of agent actions."""
    GENERATE = "generate"       # Generate text
    SUMMARIZE = "summarize"     # Summarize content
    EXTRACT = "extract"         # Extract information
    TRANSFORM = "transform"     # Transform content
    DECIDE = "decide"           # Make a decision
    ITERATE = "iterate"         # Process multiple items


class WorkflowStep(BaseModel):
    """A single step in a workflow."""
    action: ActionType
    input_key: str = "input"       # Key to get input from context
    output_key: str = "output"     # Key to store output in context
    params: Dict[str, Any] = {}    # Additional parameters
    
    
class WorkflowResult(BaseModel):
    """Result of workflow execution."""
    success: bool
    steps_completed: int
    context: Dict[str, Any]
    errors: List[str] = []


class AIAgent:
    """
    AI Agent for multi-step autonomous task execution.
    
    Provides:
    - Sequential workflow execution
    - Batch processing
    - Conditional logic
    - Context passing between steps
    """
    
    def __init__(self):
        self.engine = get_engine()
        
    async def execute_workflow(
        self,
        steps: List[WorkflowStep],
        initial_context: Dict[str, Any]
    ) -> WorkflowResult:
        """
        Execute a multi-step workflow.
        
        Args:
            steps: List of workflow steps to execute
            initial_context: Initial context/variables
            
        Returns:
            WorkflowResult with final context and status
        """
        context = initial_context.copy()
        errors = []
        steps_completed = 0
        
        for i, step in enumerate(steps):
            try:
                result = await self._execute_step(step, context)
                context[step.output_key] = result
                steps_completed += 1
            except Exception as e:
                errors.append(f"Step {i} ({step.action}): {str(e)}")
                break
        
        return WorkflowResult(
            success=len(errors) == 0,
            steps_completed=steps_completed,
            context=context,
            errors=errors
        )
    
    async def _execute_step(
        self, 
        step: WorkflowStep, 
        context: Dict[str, Any]
    ) -> Any:
        """Execute a single workflow step."""
        input_data = context.get(step.input_key, "")
        
        if step.action == ActionType.GENERATE:
            prompt = step.params.get("prompt", "{input}")
            formatted_prompt = prompt.format(input=input_data, **context)
            return await self.engine.generate(formatted_prompt)
        
        elif step.action == ActionType.SUMMARIZE:
            max_words = step.params.get("max_words", 50)
            prompt = f"Summarize the following in {max_words} words or less:\n\n{input_data}"
            return await self.engine.generate(prompt, temperature=0.3)
        
        elif step.action == ActionType.EXTRACT:
            fields = step.params.get("fields", [])
            fields_str = ", ".join(fields)
            prompt = f"Extract the following fields from the text: {fields_str}\n\nText: {input_data}\n\nRespond in JSON format."
            return await self.engine.generate(prompt, temperature=0.2)
        
        elif step.action == ActionType.TRANSFORM:
            transformation = step.params.get("transformation", "improve")
            prompt = f"{transformation}:\n\n{input_data}"
            return await self.engine.generate(prompt)
        
        elif step.action == ActionType.DECIDE:
            question = step.params.get("question", "What should be done next?")
            options = step.params.get("options", [])
            options_str = "\n".join([f"- {opt}" for opt in options]) if options else ""
            
            prompt = f"""Based on this context:
{input_data}

Question: {question}
{f"Options:{chr(10)}{options_str}" if options_str else ""}

Respond with your decision and brief reasoning."""
            return await self.engine.generate(prompt, temperature=0.3)
        
        elif step.action == ActionType.ITERATE:
            # Process list of items
            items = input_data if isinstance(input_data, list) else [input_data]
            template = step.params.get("template", "Process: {item}")
            results = []
            
            for item in items:
                prompt = template.format(item=item, **context)
                result = await self.engine.generate(prompt)
                results.append(result)
            
            return results
        
        else:
            raise ValueError(f"Unknown action type: {step.action}")
    
    async def batch_process(
        self,
        items: List[str],
        action: str,
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple items with the same action.
        
        Args:
            items: List of items to process
            action: Action to apply (summarize, extract, transform, etc.)
            batch_size: How many to process concurrently
            
        Returns:
            List of results
        """
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_tasks = [
                self._process_single_item(item, action) 
                for item in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "input": batch[j],
                        "success": False,
                        "error": str(result)
                    })
                else:
                    results.append({
                        "input": batch[j],
                        "success": True,
                        "output": result
                    })
        
        return results
    
    async def _process_single_item(self, item: str, action: str) -> str:
        """Process a single item with given action."""
        prompts = {
            "summarize": f"Summarize in one sentence:\n{item}",
            "extract_key_points": f"Extract 3 key points:\n{item}",
            "classify": f"Classify this content into a category:\n{item}",
            "sentiment": f"Analyze the sentiment (positive/negative/neutral):\n{item}",
            "translate_spanish": f"Translate to Spanish:\n{item}",
            "improve": f"Improve this text:\n{item}",
        }
        
        prompt = prompts.get(action, f"{action}:\n{item}")
        return await self.engine.generate(prompt, temperature=0.3)
    
    async def chain_actions(
        self,
        input_text: str,
        actions: List[str]
    ) -> Dict[str, Any]:
        """
        Chain multiple actions sequentially.
        
        Args:
            input_text: Initial input
            actions: List of actions to chain
            
        Returns:
            Dict with intermediate and final results
        """
        current = input_text
        history = [{"step": 0, "action": "input", "result": input_text}]
        
        for i, action in enumerate(actions, 1):
            try:
                current = await self._process_single_item(current, action)
                history.append({
                    "step": i,
                    "action": action,
                    "result": current
                })
            except Exception as e:
                history.append({
                    "step": i,
                    "action": action,
                    "error": str(e)
                })
                break
        
        return {
            "final_result": current,
            "history": history,
            "success": len(history) == len(actions) + 1
        }


# Singleton instance
_agent: Optional[AIAgent] = None


def get_agent() -> AIAgent:
    """Get AIAgent singleton."""
    global _agent
    if _agent is None:
        _agent = AIAgent()
    return _agent
