"""
AI Agents API Routes

FastAPI routes for AI agent capabilities.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ...capabilities.agents import get_agent, WorkflowStep, ActionType


router = APIRouter(prefix="/ai/agents", tags=["AI Agents"])


class WorkflowRequest(BaseModel):
    """Request to execute a workflow."""
    steps: List[Dict[str, Any]]  # Will be converted to WorkflowStep
    initial_context: Dict[str, Any] = {}


class BatchRequest(BaseModel):
    """Request for batch processing."""
    items: List[str]
    action: str
    batch_size: int = 5


class ChainRequest(BaseModel):
    """Request for action chaining."""
    input_text: str
    actions: List[str]


class SimpleAgentRequest(BaseModel):
    """Simple agent task request."""
    task: str
    context: Optional[str] = None


@router.post("/workflow")
async def execute_workflow(request: WorkflowRequest):
    """Execute a multi-step workflow."""
    try:
        agent = get_agent()
        
        # Convert dict steps to WorkflowStep
        steps = []
        for step_dict in request.steps:
            action = ActionType(step_dict.get("action", "generate"))
            steps.append(WorkflowStep(
                action=action,
                input_key=step_dict.get("input_key", "input"),
                output_key=step_dict.get("output_key", "output"),
                params=step_dict.get("params", {})
            ))
        
        result = await agent.execute_workflow(steps, request.initial_context)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_process(request: BatchRequest):
    """Process multiple items with the same action."""
    try:
        agent = get_agent()
        results = await agent.batch_process(
            items=request.items,
            action=request.action,
            batch_size=request.batch_size
        )
        return {"results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chain")
async def chain_actions(request: ChainRequest):
    """Chain multiple actions sequentially."""
    try:
        agent = get_agent()
        result = await agent.chain_actions(
            input_text=request.input_text,
            actions=request.actions
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def list_actions():
    """List available agent actions."""
    return {
        "workflow_actions": [a.value for a in ActionType],
        "batch_actions": [
            "summarize",
            "extract_key_points", 
            "classify",
            "sentiment",
            "translate_spanish",
            "improve"
        ]
    }


@router.post("/simple")
async def simple_agent_task(request: SimpleAgentRequest):
    """
    Execute a simple AI agent task.
    
    The agent will analyze the task and execute appropriate actions.
    """
    try:
        agent = get_agent()
        
        # Build context-aware prompt
        context_str = f"\nContext: {request.context}" if request.context else ""
        
        prompt = f"""You are an AI agent executing a task.

Task: {request.task}
{context_str}

Analyze this task and provide:
1. Your understanding of the task
2. The steps you would take
3. The result or output

Be concise and actionable."""

        from ...core import get_engine
        engine = get_engine()
        result = await engine.generate(prompt, temperature=0.5)
        
        return {
            "task": request.task,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
