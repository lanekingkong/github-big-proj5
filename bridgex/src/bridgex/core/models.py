"""
Core Data Models - Workflow definitions and execution models.
Separated to avoid circular imports between engine and orchestrator.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    """A single step in a workflow."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str = Field(..., description="Type of step: skill, agent, condition, loop")
    name: str = Field(..., description="Human-readable name of the step")
    skill: Optional[str] = Field(None, description="Skill name for skill steps")
    agent: Optional[str] = Field(None, description="Agent name for agent steps")
    params: Dict[str, Any] = Field(default_factory=dict, description="Step parameters")
    condition: Optional[str] = Field(None, description="Condition expression for conditional steps")
    on_success: Optional[str] = Field(None, description="Next step on success")
    on_failure: Optional[str] = Field(None, description="Next step on failure")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    retry_delay: int = Field(default=1, description="Delay between retries in seconds")


class WorkflowDefinition(BaseModel):
    """Complete workflow definition."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Workflow name")
    version: str = Field("1.0.0", description="Workflow version")
    description: Optional[str] = Field(None, description="Workflow description")
    steps: List[WorkflowStep] = Field(..., description="Workflow steps")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Workflow variables")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class WorkflowStatus(BaseModel):
    """Status of a workflow execution."""
    
    workflow_id: str
    execution_id: str
    status: str = Field(default="pending")
    current_step: Optional[str] = None
    step_progress: Dict[str, str] = Field(default_factory=dict)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def get_status_choices(cls) -> list[str]:
        """Get available status choices."""
        return ["pending", "running", "completed", "failed", "cancelled", "paused"]


class AgentDefinition(BaseModel):
    """Definition of an agent."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Agent name")
    type: str = Field(..., description="Agent type: assistant, executor, reviewer, coordinator")
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    llm_provider: str = Field(default="openai")
    llm_model: str = Field(default="gpt-4")
    system_prompt: Optional[str] = None
    max_iterations: int = Field(default=10)
    temperature: float = Field(default=0.7, ge=0, le=2)
    tools: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SkillDefinition(BaseModel):
    """Definition of a skill."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Skill name")
    version: str = Field(default="1.0.0")
    description: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    risk_level: str = Field(default="low", description="Risk level: low, medium, high, critical")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "WorkflowStep",
    "WorkflowDefinition",
    "WorkflowStatus",
    "AgentDefinition",
    "SkillDefinition",
]