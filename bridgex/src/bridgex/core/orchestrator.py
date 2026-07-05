"""
Orchestrator - Central coordination layer for workflow execution.
Inspired by LangChain's execution patterns and enhanced with BridgeX's trust-first approach.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from bridgex.core.models import WorkflowDefinition, WorkflowStep
from bridgex.utils.exceptions import BridgeXError

logger = logging.getLogger(__name__)


class ExecutionContext(BaseModel):
    """Execution context for a workflow run."""
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str = Field(...)
    variables: Dict[str, Any] = Field(default_factory=dict)
    step_outputs: Dict[str, Any] = Field(default_factory=dict)
    completed_steps: Set[str] = Field(default_factory=set)
    failed_steps: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    start_time: datetime = Field(default_factory=datetime.now)
    max_retries: int = Field(default=3)
    timeout: Optional[int] = Field(default=600)  # 10 minutes default


class OrchestrationResult(BaseModel):
    """Result of orchestration execution."""
    execution_id: str
    status: str
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Orchestrator:
    """Central orchestrator that manages workflow execution flow."""
    
    def __init__(self):
        self.active_contexts: Dict[str, ExecutionContext] = {}
    
    async def execute(
        self,
        workflow: WorkflowDefinition,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        engine: "BridgeEngine",
    ) -> OrchestrationResult:
        """Execute a workflow through the orchestrator.
        
        Args:
            workflow: Workflow definition to execute
            input_data: Input data for the workflow
            context: Execution context
            engine: Reference to the BridgeEngine
            
        Returns:
            Orchestration result
        """
        # Create execution context
        exec_context = ExecutionContext(
            workflow_id=workflow.id,
            variables={**workflow.variables, **input_data},
            metadata=context,
        )
        
        self.active_contexts[exec_context.execution_id] = exec_context
        
        try:
            # Build dependency graph
            dependency_graph = self._build_dependency_graph(workflow.steps)
            
            # Find initial steps (no dependencies)
            initial_steps = self._find_initial_steps(workflow.steps, dependency_graph)
            
            # Execute workflow
            results = await self._execute_steps(
                steps=workflow.steps,
                initial_steps=initial_steps,
                dependency_graph=dependency_graph,
                exec_context=exec_context,
                engine=engine,
            )
            
            # Calculate metrics
            duration = (datetime.now() - exec_context.start_time).total_seconds()
            
            return OrchestrationResult(
                execution_id=exec_context.execution_id,
                status="completed",
                results=results,
                metrics={
                    "duration": duration,
                    "total_steps": len(workflow.steps),
                    "completed_steps": len(exec_context.completed_steps),
                    "failed_steps": len(exec_context.failed_steps),
                },
            )
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            raise
        
        finally:
            # Clean up context
            self.active_contexts.pop(exec_context.execution_id, None)
    
    def _build_dependency_graph(
        self, steps: List[WorkflowStep]
    ) -> Dict[str, List[str]]:
        """Build a dependency graph from workflow steps.
        
        Args:
            steps: List of workflow steps
            
        Returns:
            Dependency graph mapping step_id -> [dependent_step_ids]
        """
        graph: Dict[str, List[str]] = {step.id: [] for step in steps}
        
        for step in steps:
            if step.on_success:
                graph[step.on_success].append(step.id)
            if step.on_failure:
                graph[step.on_failure].append(step.id)
        
        return graph
    
    def _find_initial_steps(
        self,
        steps: List[WorkflowStep],
        dependency_graph: Dict[str, List[str]],
    ) -> List[str]:
        """Find steps that have no incoming dependencies.
        
        Args:
            steps: List of workflow steps
            dependency_graph: Dependency graph
            
        Returns:
            List of initial step IDs
        """
        referenced = set()
        for step in steps:
            if step.on_success:
                referenced.add(step.on_success)
            if step.on_failure:
                referenced.add(step.on_failure)
        
        return [step.id for step in steps if step.id not in referenced]
    
    async def _execute_steps(
        self,
        steps: List[WorkflowStep],
        initial_steps: List[str],
        dependency_graph: Dict[str, List[str]],
        exec_context: ExecutionContext,
        engine: "BridgeEngine",
    ) -> Dict[str, Any]:
        """Execute workflow steps respecting dependencies.
        
        Used with topological execution pattern (inspired by Haystack pipeline execution).
        
        Args:
            steps: List of workflow steps
            initial_steps: Initial step IDs
            dependency_graph: Dependency graph
            exec_context: Execution context
            engine: BridgeEngine reference
            
        Returns:
            Dict of step outputs
        """
        step_map = {step.id: step for step in steps}
        results: Dict[str, Any] = {}
        executed: Set[str] = set()
        queue: List[str] = list(initial_steps)
        
        while queue:
            # Execute steps that are ready in parallel
            ready_steps = [step_id for step_id in queue if step_id not in executed]
            
            if not ready_steps:
                # Check for deadlock
                remaining = set(step_map.keys()) - executed
                if remaining:
                    raise BridgeXError(
                        f"Workflow deadlock detected. Remaining steps: {remaining}"
                    )
                break
            
            # Execute ready steps
            tasks = []
            for step_id in ready_steps:
                task = self._execute_single_step(
                    step_id=step_id,
                    step=step_map[step_id],
                    context=exec_context,
                    engine=engine,
                )
                tasks.append(task)
            
            step_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            new_ready = []
            for i, result in enumerate(step_results):
                step_id = ready_steps[i]
                executed.add(step_id)
                
                if isinstance(result, Exception):
                    logger.error(f"Step {step_id} failed: {result}")
                    exec_context.failed_steps.append(step_id)
                    results[step_id] = {"error": str(result)}
                    
                    # Follow failure path
                    step = step_map[step_id]
                    if step.on_failure and step.on_failure not in executed:
                        new_ready.append(step.on_failure)
                else:
                    exec_context.completed_steps.add(step_id)
                    exec_context.step_outputs[step_id] = result
                    results[step_id] = result
                    
                    # Follow success path
                    step = step_map[step_id]
                    if step.on_success and step.on_success not in executed:
                        new_ready.append(step.on_success)
            
            # Add newly ready steps to queue
            queue = new_ready
        
        return results
    
    async def _execute_single_step(
        self,
        step_id: str,
        step: WorkflowStep,
        context: ExecutionContext,
        engine: "BridgeEngine",
    ) -> Any:
        """Execute a single workflow step with retry logic.
        
        Args:
            step_id: Step ID
            step: Step definition
            context: Execution context
            engine: BridgeEngine reference
            
        Returns:
            Step execution result
        """
        last_error = None
        
        for attempt in range(step.retry_count):
            try:
                # Resolve template variables in params
                resolved_params = self._resolve_template_vars(
                    step.params, context
                )
                
                # Execute based on step type
                if step.type == "skill":
                    result = await engine.execute_skill(
                        skill_name=step.skill,
                        params=resolved_params,
                        context={
                            "execution_id": context.execution_id,
                            "step_id": step_id,
                            "attempt": attempt + 1,
                        },
                    )
                    return result
                
                elif step.type == "agent":
                    result = await engine.agent_manager.execute_agent(
                        agent_name=step.agent,
                        params=resolved_params,
                    )
                    return result
                
                elif step.type == "condition":
                    result = self._evaluate_condition(
                        step.condition,
                        context,
                    )
                    return result
                
                else:
                    raise BridgeXError(f"Unknown step type: {step.type}")
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Step {step_id} attempt {attempt + 1}/{step.retry_count} failed: {e}"
                )
                
                if attempt < step.retry_count - 1:
                    await asyncio.sleep(step.retry_delay)
        
        raise last_error if last_error else BridgeXError(f"Step {step_id} failed after {step.retry_count} attempts")
    
    def _resolve_params(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Resolve parameters with template variables and step outputs.
        
        Args:
            params: Parameters to resolve
            context: Execution context
            
        Returns:
            Resolved parameters
        """
        return self._resolve_template_vars(params, context)
    
    def _resolve_template_vars(
        self,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Resolve template variables in parameters.
        
        Uses {{variable}} syntax, inspired by workflow engines.
        
        Args:
            params: Parameters with potential template variables
            context: Execution context with variable values
            
        Returns:
            Parameters with resolved variables
        """
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and "{{" in value:
                # Simple template resolution
                resolved_value = value
                import re
                
                pattern = r'\{\{(\w+(?:\.\w+)*)\}\}'
                
                def replace_var(match):
                    var_path = match.group(1)
                    parts = var_path.split(".")
                    
                    # Start with variables
                    result = context.variables
                    for part in parts:
                        if isinstance(result, dict):
                            result = result.get(part, match.group(0))
                        else:
                            return match.group(0)
                    
                    return str(result) if result is not None else match.group(0)
                
                resolved_value = re.sub(pattern, replace_var, resolved_value)
                resolved[key] = resolved_value
            else:
                resolved[key] = value
        
        return resolved
    
    def _evaluate_condition(
        self,
        condition: Optional[str],
        context: ExecutionContext,
    ) -> bool:
        """Evaluate a condition expression.
        
        Args:
            condition: Condition expression string
            context: Execution context
            
        Returns:
            Boolean result of condition evaluation
        """
        if not condition:
            return True
        
        # Safe condition evaluation using restricted environment
        safe_vars = {
            "results": context.step_outputs,
            "variables": context.variables,
            "completed": context.completed_steps,
            "failed": context.failed_steps,
        }
        
        try:
            # Use Python's eval with restricted globals
            result = eval(condition, {"__builtins__": {}}, safe_vars)
            return bool(result)
        except Exception as e:
            logger.error(f"Condition evaluation failed: {condition} - {e}")
            return False
    
    def get_execution_status(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get the status of an active execution.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution context or None if not found
        """
        return self.active_contexts.get(execution_id)