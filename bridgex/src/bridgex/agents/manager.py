"""
Agent Manager - Multi-agent coordination and lifecycle management.
Inspired by Microsoft Agent Framework and LangChain's agent architecture.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from bridgex.utils.exceptions import BridgeXError

logger = logging.getLogger(__name__)


class AgentCapability(BaseModel):
    """Capability of an agent."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    examples: List[Dict[str, Any]] = Field(default_factory=list)


class AgentDefinition(BaseModel):
    """Definition of an AI agent."""
    name: str
    description: str
    model: str = Field(default="gpt-4")
    capabilities: List[Union[str, AgentCapability]] = Field(default_factory=list)
    system_prompt: str = Field(default="")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)
    tools: List[str] = Field(default_factory=list)
    memory_enabled: bool = Field(default=True)
    max_memory_size: int = Field(default=10)
    requires_approval: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Get capabilities as AgentCapability list, converting strings if needed."""
        result = []
        for cap in self.capabilities:
            if isinstance(cap, str):
                result.append(AgentCapability(
                    name=cap,
                    description=f"Capability: {cap}",
                    input_schema={"type": "object", "properties": {}},
                    output_schema={"type": "object", "properties": {}}
                ))
            else:
                result.append(cap)
        return result


class AgentState(BaseModel):
    """Runtime state of an agent."""
    agent_name: str
    session_id: str
    status: str  # idle, busy, error, terminated
    current_task: Optional[str] = None
    memory: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: str(datetime.now().isoformat()))
    last_active: str = Field(default_factory=lambda: str(datetime.now().isoformat()))


class AgentExecutionResult(BaseModel):
    """Result of agent execution."""
    success: bool
    output: Any
    reasoning: Optional[str] = None
    steps_taken: int = 0
    tokens_used: int = 0
    duration_ms: int = 0
    error: Optional[str] = None


class AgentManager:
    """Manages multiple AI agents and their coordination.
    
    Features:
    - Agent lifecycle management
    - Multi-agent collaboration
    - Memory and context management
    - Load balancing and routing
    - Agent specialization
    """
    
    def __init__(self, max_agents: int = 10):
        """Initialize the agent manager.
        
        Args:
            max_agents: Maximum number of concurrent agents
        """
        self.max_agents = max_agents
        self.agent_definitions: Dict[str, AgentDefinition] = {}
        self.active_agents: Dict[str, AgentState] = {}
        self.agent_pools: Dict[str, List[AgentState]] = {}
        self.agent_instances: Dict[str, Any] = {}  # Actual agent instances
        
        # Agent types
        self.agent_types = {
            "generalist": "General purpose agent for diverse tasks",
            "specialist": "Domain-specific expert agent",
            "orchestrator": "Coordinates other agents",
            "verifier": "Validates outputs of other agents",
            "executor": "Focuses on action execution",
            "analyst": "Data analysis and insights",
            "communicator": "Handles external communication",
        }
        
        # Load default agents
        self._load_default_agents()
        
        logger.info(f"Agent Manager initialized (max agents: {max_agents})")
    
    async def initialize(self) -> None:
        """Initialize the agent manager."""
        # Initialize agent pools
        for agent_name in self.agent_definitions:
            self.agent_pools[agent_name] = []
        
        logger.info(f"Agent Manager initialized with {len(self.agent_definitions)} agent types")
    
    async def register_agent(self, agent_definition: AgentDefinition) -> str:
        """Register a new agent type.
        
        Args:
            agent_definition: Agent definition to register
            
        Returns:
            Agent name (used as ID)
        """
        agent_name = agent_definition.name
        self.agent_definitions[agent_name] = agent_definition
        
        if agent_name not in self.agent_pools:
            self.agent_pools[agent_name] = []
        
        logger.info(f"Agent registered: {agent_name}")
        return agent_name
    
    async def get_agent(self, agent_name: str) -> Optional[AgentDefinition]:
        """Get an agent definition by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent definition or None if not found
        """
        return self.agent_definitions.get(agent_name)
    
    async def list_agents(self) -> List[AgentDefinition]:
        """List all registered agent definitions.
        
        Returns:
            List of agent definitions with status
        """
        result = []
        for name, definition in self.agent_definitions.items():
            # Clone and add status
            agent_dict = definition.model_dump()
            agent_dict["status"] = "available" if name in self.agent_pools else "inactive"
            result.append(AgentDefinition(**agent_dict))
        return result
    
    async def execute_agent_task(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a task with a named agent.
        
        Args:
            agent_name: Name of the agent to execute
            task: Task description
            context: Additional context
            
        Returns:
            Task execution result
        """
        # Create agent instance
        agent_id = await self.create_agent(agent_name)
        
        try:
            # Execute the task
            result = await self.execute_agent(
                agent_id=agent_id,
                task=task,
                context=context,
            )
            
            return {
                "response": result.output if hasattr(result, 'output') else str(result),
                "success": result.success,
                "reasoning": result.reasoning,
                "steps_taken": result.steps_taken,
                "tokens_used": result.tokens_used,
                "duration_ms": result.duration_ms,
            }
        finally:
            # Clean up
            pass  # Agent stays in pool for reuse
    
    async def create_agent(
        self,
        agent_name: str,
        session_id: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new agent instance.
        
        Args:
            agent_name: Name of the agent type
            session_id: Optional session ID
            custom_config: Custom configuration
            
        Returns:
            Agent instance ID
            
        Raises:
            BridgeXError: If agent type not found or limit reached
        """
        if agent_name not in self.agent_definitions:
            raise BridgeXError(f"Agent type not found: {agent_name}")
        
        # Check agent limit
        if len(self.active_agents) >= self.max_agents:
            # Try to clean up idle agents
            await self._cleanup_idle_agents()
            
            if len(self.active_agents) >= self.max_agents:
                raise BridgeXError(f"Maximum agent limit reached: {self.max_agents}")
        
        # Create session ID if not provided
        if not session_id:
            session_id = f"{agent_name}_{int(datetime.now().timestamp())}"
        
        # Get agent definition
        definition = self.agent_definitions[agent_name]
        
        # Apply custom configuration
        if custom_config:
            definition = definition.copy(update=custom_config)
        
        # Create agent state
        state = AgentState(
            agent_name=agent_name,
            session_id=session_id,
            status="idle",
        )
        
        # Create actual agent instance
        agent_instance = await self._create_agent_instance(definition, state)
        
        # Store references
        self.active_agents[session_id] = state
        self.agent_instances[session_id] = agent_instance
        self.agent_pools[agent_name].append(state)
        
        logger.info(f"Agent created: {agent_name} (session: {session_id})")
        return session_id
    
    async def execute_agent(
        self,
        agent_id: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
    ) -> AgentExecutionResult:
        """Execute a task with an agent.
        
        Args:
            agent_id: Agent instance ID
            task: Task to execute
            context: Additional context
            max_steps: Maximum steps to take
            
        Returns:
            Execution result
        """
        if agent_id not in self.active_agents:
            raise BridgeXError(f"Agent not found: {agent_id}")
        
        state = self.active_agents[agent_id]
        agent_instance = self.agent_instances[agent_id]
        
        # Update state
        state.status = "busy"
        state.current_task = task
        state.last_active = str(datetime.now().isoformat())
        
        start_time = datetime.now()
        
        try:
            # Execute agent
            result = await agent_instance.execute(
                task=task,
                context=context or {},
                max_steps=max_steps,
            )
            
            # Update state
            state.status = "idle"
            state.current_task = None
            state.last_active = str(datetime.now().isoformat())
            
            # Update memory if enabled
            if state.agent_name in self.agent_definitions:
                definition = self.agent_definitions[state.agent_name]
                if definition.memory_enabled:
                    memory_entry = {
                        "task": task,
                        "result": result.output if hasattr(result, 'output') else result,
                        "timestamp": str(datetime.now().isoformat()),
                    }
                    state.memory.append(memory_entry)
                    
                    # Trim memory if needed
                    if len(state.memory) > definition.max_memory_size:
                        state.memory = state.memory[-definition.max_memory_size:]
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return AgentExecutionResult(
                success=True,
                output=result.output if hasattr(result, 'output') else result,
                reasoning=getattr(result, 'reasoning', None),
                steps_taken=getattr(result, 'steps_taken', 1),
                tokens_used=getattr(result, 'tokens_used', 0),
                duration_ms=int(duration),
            )
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            
            state.status = "error"
            state.current_task = None
            
            return AgentExecutionResult(
                success=False,
                output=None,
                error=str(e),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )
    
    async def coordinate_agents(
        self,
        task: str,
        agent_types: Optional[List[str]] = None,
        max_agents: int = 3,
    ) -> Dict[str, Any]:
        """Coordinate multiple agents to solve a complex task.
        
        Args:
            task: Complex task to solve
            agent_types: Specific agent types to use
            max_agents: Maximum number of agents to use
            
        Returns:
            Coordination result
        """
        # Select appropriate agents
        if not agent_types:
            agent_types = self._select_agents_for_task(task)
        
        # Limit number of agents
        agent_types = agent_types[:max_agents]
        
        # Create orchestrator agent
        orchestrator_id = await self.create_agent("orchestrator")
        
        try:
            # Create worker agents
            worker_agents = []
            for agent_type in agent_types:
                if agent_type != "orchestrator":
                    agent_id = await self.create_agent(agent_type)
                    worker_agents.append({
                        "id": agent_id,
                        "type": agent_type,
                    })
            
            # Execute with orchestrator
            context = {
                "task": task,
                "worker_agents": worker_agents,
                "agent_manager": self,
            }
            
            result = await self.execute_agent(
                agent_id=orchestrator_id,
                task=f"Coordinate the following agents to solve: {task}",
                context=context,
                max_steps=20,
            )
            
            return {
                "success": result.success,
                "output": result.output,
                "agents_used": len(worker_agents) + 1,  # +1 for orchestrator
                "agent_types": agent_types,
                "details": result.dict() if hasattr(result, 'dict') else result,
            }
            
        finally:
            # Clean up agents
            await self.terminate_agent(orchestrator_id)
            for worker in worker_agents:
                await self.terminate_agent(worker["id"])
    
    async def terminate_agent(self, agent_id: str) -> bool:
        """Terminate an agent instance.
        
        Args:
            agent_id: Agent instance ID
            
        Returns:
            True if terminated successfully
        """
        if agent_id not in self.active_agents:
            return False
        
        state = self.active_agents[agent_id]
        agent_name = state.agent_name
        
        # Clean up agent instance
        if agent_id in self.agent_instances:
            agent_instance = self.agent_instances[agent_id]
            if hasattr(agent_instance, 'cleanup'):
                await agent_instance.cleanup()
            del self.agent_instances[agent_id]
        
        # Remove from active agents
        del self.active_agents[agent_id]
        
        # Remove from pool
        if agent_name in self.agent_pools:
            self.agent_pools[agent_name] = [
                a for a in self.agent_pools[agent_name] if a.session_id != agent_id
            ]
        
        logger.info(f"Agent terminated: {agent_name} (session: {agent_id})")
        return True
    
    async def get_agent_status(self, agent_id: str) -> Optional[AgentState]:
        """Get the status of an agent.
        
        Args:
            agent_id: Agent instance ID
            
        Returns:
            Agent state or None if not found
        """
        return self.active_agents.get(agent_id)
    
    async def list_agents(self, agent_type: Optional[str] = None) -> List[AgentState]:
        """List all active agents.
        
        Args:
            agent_type: Filter by agent type
            
        Returns:
            List of agent states
        """
        if agent_type:
            return self.agent_pools.get(agent_type, [])
        return list(self.active_agents.values())
    
    def register_agent_type(self, definition: AgentDefinition) -> None:
        """Register a new agent type.
        
        Args:
            definition: Agent definition
            
        Raises:
            BridgeXError: If agent type already exists
        """
        if definition.name in self.agent_definitions:
            raise BridgeXError(f"Agent type already exists: {definition.name}")
        
        self.agent_definitions[definition.name] = definition
        self.agent_pools[definition.name] = []
        
        logger.info(f"Agent type registered: {definition.name}")
    
    def _select_agents_for_task(self, task: str) -> List[str]:
        """Select appropriate agent types for a task.
        
        Args:
            task: Task description
            
        Returns:
            List of agent types
        """
        task_lower = task.lower()
        selected = []
        
        # Simple keyword-based selection
        if any(word in task_lower for word in ["coordinate", "manage", "orchestrate"]):
            selected.append("orchestrator")
        
        if any(word in task_lower for word in ["verify", "check", "validate", "audit"]):
            selected.append("verifier")
        
        if any(word in task_lower for word in ["execute", "run", "perform", "do"]):
            selected.append("executor")
        
        if any(word in task_lower for word in ["analyze", "data", "statistics", "report"]):
            selected.append("analyst")
        
        if any(word in task_lower for word in ["communicate", "email", "message", "notify"]):
            selected.append("communicator")
        
        # Always include a generalist if no specialists selected
        if not selected:
            selected.append("generalist")
        
        return selected
    
    async def _create_agent_instance(
        self,
        definition: AgentDefinition,
        state: AgentState,
    ) -> Any:
        """Create an actual agent instance.
        
        Args:
            definition: Agent definition
            state: Agent state
            
        Returns:
            Agent instance
        """
        # This is a simplified implementation
        # In a real implementation, this would create LangChain agents, etc.
        
        class SimpleAgent:
            def __init__(self, definition: AgentDefinition, state: AgentState):
                self.definition = definition
                self.state = state
                self.step_count = 0
            
            async def execute(
                self,
                task: str,
                context: Dict[str, Any],
                max_steps: int = 10,
            ) -> Any:
                # Simulate agent execution
                self.step_count = 0
                
                # Simple task processing
                if "summarize" in task.lower():
                    return type('obj', (object,), {
                        'output': f"Summary: {task[:100]}...",
                        'reasoning': "Extracted key points from the task",
                        'steps_taken': 1,
                        'tokens_used': 50,
                    })()
                elif "analyze" in task.lower():
                    return type('obj', (object,), {
                        'output': f"Analysis complete for: {task}",
                        'reasoning': "Performed data analysis and pattern recognition",
                        'steps_taken': 3,
                        'tokens_used': 150,
                    })()
                else:
                    return type('obj', (object,), {
                        'output': f"Task completed: {task}",
                        'reasoning': "Executed the requested task",
                        'steps_taken': 1,
                        'tokens_used': 100,
                    })()
            
            async def cleanup(self):
                # Cleanup resources
                pass
        
        return SimpleAgent(definition, state)
    
    async def _cleanup_idle_agents(self) -> None:
        """Clean up idle agents that have been inactive for too long."""
        cutoff = datetime.now() - timedelta(minutes=30)  # 30 minutes idle
        
        to_remove = []
        for agent_id, state in self.active_agents.items():
            if state.status == "idle":
                last_active = datetime.fromisoformat(state.last_active)
                if last_active < cutoff:
                    to_remove.append(agent_id)
        
        for agent_id in to_remove:
            await self.terminate_agent(agent_id)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} idle agents")
    
    def _load_default_agents(self) -> None:
        """Load default agent definitions."""
        # Generalist Agent
        self.agent_definitions["generalist"] = AgentDefinition(
            name="generalist",
            description="General purpose AI agent for diverse tasks",
            model="gpt-4",
            system_prompt="You are a helpful AI assistant that can handle a wide variety of tasks.",
            capabilities=[
                AgentCapability(
                    name="general_reasoning",
                    description="General problem solving and reasoning",
                    input_schema={"task": "str"},
                    output_schema={"result": "str"},
                ),
            ],
        )
        
        # Orchestrator Agent
        self.agent_definitions["orchestrator"] = AgentDefinition(
            name="orchestrator",
            description="Coordinates multiple agents to solve complex tasks",
            model="gpt-4",
            system_prompt="You are an orchestrator agent. Your job is to break down complex tasks and coordinate specialized agents to solve them.",
            capabilities=[
                AgentCapability(
                    name="task_decomposition",
                    description="Break down complex tasks into subtasks",
                    input_schema={"complex_task": "str"},
                    output_schema={"subtasks": "list", "agent_assignments": "dict"},
                ),
                AgentCapability(
                    name="agent_coordination",
                    description="Coordinate multiple agents to work together",
                    input_schema={"subtasks": "list", "available_agents": "list"},
                    output_schema={"coordination_plan": "dict"},
                ),
            ],
            memory_enabled=True,
            max_memory_size=20,
        )
        
        # Verifier Agent
        self.agent_definitions["verifier"] = AgentDefinition(
            name="verifier",
            description="Validates and verifies outputs from other agents",
            model="gpt-4",
            system_prompt="You are a verifier agent. Your job is to check the correctness, safety, and quality of outputs from other agents.",
            capabilities=[
                AgentCapability(
                    name="output_validation",
                    description="Validate agent outputs against requirements",
                    input_schema={"output": "any", "requirements": "dict"},
                    output_schema={"valid": "bool", "issues": "list", "suggestions": "list"},
                ),
                AgentCapability(
                    name="safety_check",
                    description="Check for safety issues in agent outputs",
                    input_schema={"output": "any", "context": "dict"},
                    output_schema={"safe": "bool", "risks": "list", "recommendations": "list"},
                ),
            ],
            requires_approval=False,
        )
        
        # Executor Agent
        self.agent_definitions["executor"] = AgentDefinition(
            name="executor",
            description="Focuses on executing actions and tasks",
            model="gpt-4",
            system_prompt="You are an executor agent. Your job is to take action and get things done efficiently.",
            capabilities=[
                AgentCapability(
                    name="action_execution",
                    description="Execute specific actions and tasks",
                    input_schema={"action": "str", "parameters": "dict"},
                    output_schema={"result": "any", "status": "str"},
                ),
                AgentCapability(
                    name="task_completion",
                    description="Complete tasks from start to finish",
                    input_schema={"task": "str", "context": "dict"},
                    output_schema={"completed": "bool", "output": "any", "steps_taken": "int"},
                ),
            ],
        )
        
        # Analyst Agent
        self.agent_definitions["analyst"] = AgentDefinition(
            name="analyst",
            description="Data analysis and insights generation",
            model="gpt-4",
            system_prompt="You are an analyst agent. Your job is to analyze data, find patterns, and generate insights.",
            capabilities=[
                AgentCapability(
                    name="data_analysis",
                    description="Analyze data and extract insights",
                    input_schema={"data": "any", "analysis_type": "str"},
                    output_schema={"insights": "list", "summary": "str", "visualizations": "list"},
                ),
                AgentCapability(
                    name="pattern_recognition",
                    description="Recognize patterns in data",
                    input_schema={"data": "any", "pattern_type": "str"},
                    output_schema={"patterns": "list", "confidence": "float", "implications": "list"},
                ),
            ],
        )
        
        # Communicator Agent
        self.agent_definitions["communicator"] = AgentDefinition(
            name="communicator",
            description="Handles external communication and messaging",
            model="gpt-4",
            system_prompt="You are a communicator agent. Your job is to handle communication with external systems and users.",
            capabilities=[
                AgentCapability(
                    name="message_composition",
                    description="Compose messages for different channels",
                    input_schema={"content": "str", "channel": "str", "audience": "str"},
                    output_schema={"message": "str", "tone": "str", "format": "str"},
                ),
                AgentCapability(
                    name="communication_management",
                    description="Manage communication workflows",
                    input_schema={"workflow": "str", "recipients": "list", "content": "dict"},
                    output_schema={"status": "str", "sent": "int", "failed": "int"},
                ),
            ],
        )
    
    async def shutdown(self) -> None:
        """Shutdown the agent manager."""
        # Terminate all active agents
        agent_ids = list(self.active_agents.keys())
        termination_tasks = [self.terminate_agent(agent_id) for agent_id in agent_ids]
        
        await asyncio.gather(*termination_tasks, return_exceptions=True)
        
        logger.info("Agent Manager shutdown complete")


# Import here to avoid circular import
from datetime import datetime, timedelta