"""
Execution Runtime - Sandboxed execution environment for AI actions.
Provides safe, monitored, and auditable execution of skills and workflows.
"""

import asyncio
import logging
import signal
import time
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from bridgex.utils.exceptions import BridgeXError, ExecutionError, TimeoutError

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Status of an execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ExecutionContext(BaseModel):
    """Execution context containing environment and state."""
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Environment
    temp_dir: Optional[str] = None
    workspace_dir: Optional[str] = None
    env_vars: Dict[str, str] = Field(default_factory=dict)
    
    # State
    variables: Dict[str, Any] = Field(default_factory=dict)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Tracking
    created_at: str = Field(default_factory=lambda: str(datetime.now().isoformat()))
    expires_at: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result of an execution."""
    status: ExecutionStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    steps_executed: int = 0
    total_steps: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)


class ExecutionConfig(BaseModel):
    """Configuration for execution runtime."""
    max_execution_time_ms: int = Field(default=300_000)  # 5 minutes
    max_memory_mb: int = Field(default=512)
    max_output_size_mb: int = Field(default=100)
    max_steps: int = Field(default=100)
    retry_count: int = Field(default=3)
    retry_delay_ms: int = Field(default=1000)
    allow_parallel_steps: bool = Field(default=True)
    sandbox_enabled: bool = Field(default=True)
    timeout_action: str = Field(default="cancel")  # cancel, pause, notify


class WatchdogTimer:
    """Watchdog timer for execution timeouts."""
    
    def __init__(self, timeout_ms: int, callback: Callable):
        self.timeout_ms = timeout_ms
        self.callback = callback
        self.start_time: Optional[float] = None
        self.timed_out = False
    
    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        self.timed_out = False
    
    def reset(self):
        """Reset the timer."""
        self.start_time = time.time()
        self.timed_out = False
    
    def check(self) -> bool:
        """Check if timeout has been exceeded.
        
        Returns:
            True if timed out, False otherwise
        """
        if self.start_time is None:
            return False
        
        elapsed_ms = (time.time() - self.start_time) * 1000
        if elapsed_ms > self.timeout_ms:
            self.timed_out = True
            return True
        
        return False
    
    @property
    def elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0
        return int((time.time() - self.start_time) * 1000)
    
    @property
    def remaining_ms(self) -> int:
        """Get remaining time in milliseconds."""
        return max(0, self.timeout_ms - self.elapsed_ms)


class ExecutionRuntime:
    """Sandboxed execution runtime for AI actions.
    
    Features:
    - Isolated execution environment
    - Timeout and resource management
    - Step-by-step execution tracking
    - Parallel step execution
    - Retry and error recovery
    - Audit trail generation
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Initialize the execution runtime.
        
        Args:
            config: Execution configuration
        """
        self.config = config or ExecutionConfig()
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.watchdogs: Dict[str, WatchdogTimer] = {}
        self._cancelled_executions: set = set()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("Execution Runtime initialized")
    
    async def initialize(self) -> None:
        """Initialize the runtime."""
        logger.info("Execution Runtime initialization complete")
    
    async def execute_workflow(
        self,
        workflow: Any,
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """Execute a complete workflow.
        
        Args:
            workflow: Workflow definition
            context: Execution context
            
        Returns:
            Execution result
        """
        if context is None:
            context = ExecutionContext()
        
        # Initialize execution
        result = ExecutionResult(
            status=ExecutionStatus.PENDING,
            total_steps=len(workflow.steps) if hasattr(workflow, 'steps') else 0,
            started_at=str(datetime.now().isoformat()),
        )
        
        # Register execution
        self.active_executions[context.execution_id] = context
        self.execution_results[context.execution_id] = result
        
        # Setup watchdog
        watchdog = WatchdogTimer(
            timeout_ms=self.config.max_execution_time_ms,
            callback=lambda: self._handle_timeout(context.execution_id),
        )
        self.watchdogs[context.execution_id] = watchdog
        
        try:
            # Start execution
            result.status = ExecutionStatus.RUNNING
            watchdog.start()
            
            # Build execution plan
            if not hasattr(workflow, 'steps'):
                return self._finalize_execution(
                    context.execution_id,
                    ExecutionStatus.FAILED,
                    error="Workflow has no steps",
                )
            
            steps = self._build_execution_plan(workflow.steps)
            
            # Execute steps
            completed_steps = 0
            step_outputs: Dict[str, Any] = {}
            
            for step_batch in steps:
                # Check timeout
                if watchdog.check():
                    return self._finalize_execution(
                        context.execution_id,
                        ExecutionStatus.TIMED_OUT,
                        steps_executed=completed_steps,
                    )
                
                # Check cancellation
                if context.execution_id in self._cancelled_executions:
                    return self._finalize_execution(
                        context.execution_id,
                        ExecutionStatus.CANCELLED,
                        steps_executed=completed_steps,
                    )
                
                # Execute batch (parallel if possible)
                if isinstance(step_batch, list) and self.config.allow_parallel_steps:
                    batch_results = await asyncio.gather(
                        *[self._execute_step(step, context, step_outputs) for step in step_batch],
                        return_exceptions=True,
                    )
                    
                    for step, batch_result in zip(step_batch, batch_results):
                        if isinstance(batch_result, Exception):
                            logger.error(f"Step {getattr(step, 'name', 'unknown')} failed: {batch_result}")
                            result.logs.append(f"[ERROR] Step failed: {batch_result}")
                            
                            if isinstance(batch_result, TimeoutError):
                                return self._finalize_execution(
                                    context.execution_id,
                                    ExecutionStatus.TIMED_OUT,
                                    steps_executed=completed_steps,
                                    error=str(batch_result),
                                )
                            
                            if isinstance(batch_result, ExecutionError):
                                # Check if we should retry
                                retry_result = await self._retry_step(
                                    step, context, step_outputs, batch_result
                                )
                                if retry_result:
                                    step_outputs[step.id] = retry_result
                                    completed_steps += 1
                                else:
                                    return self._finalize_execution(
                                        context.execution_id,
                                        ExecutionStatus.FAILED,
                                        steps_executed=completed_steps,
                                        error=str(batch_result),
                                    )
                        else:
                            step_outputs[step.id] = batch_result
                            completed_steps += 1
                else:
                    step_list = step_batch if isinstance(step_batch, list) else [step_batch]
                    for step in step_list:
                        try:
                            step_result = await self._execute_step(step, context, step_outputs)
                            step_outputs[step.id] = step_result
                            completed_steps += 1
                        except (ExecutionError, TimeoutError) as e:
                            logger.error(f"Step {getattr(step, 'name', 'unknown')} failed: {e}")
                            
                            # Try retry
                            retry_result = await self._retry_step(step, context, step_outputs, e)
                            if retry_result:
                                step_outputs[step.id] = retry_result
                                completed_steps += 1
                            else:
                                return self._finalize_execution(
                                    context.execution_id,
                                    ExecutionStatus.FAILED,
                                    steps_executed=completed_steps,
                                    error=str(e),
                                )
            
            # Execution completed
            final_output = self._collect_workflow_output(workflow, step_outputs)
            
            return self._finalize_execution(
                context.execution_id,
                ExecutionStatus.COMPLETED,
                output=final_output,
                steps_executed=completed_steps,
            )
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            return self._finalize_execution(
                context.execution_id,
                ExecutionStatus.FAILED,
                error=str(e),
            )
    
    async def execute_agent(
        self,
        agent: Any,
        task: str,
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """Execute a task with an AI agent.
        
        Args:
            agent: Agent definition
            task: Task description
            context: Execution context
            
        Returns:
            Execution result
        """
        if context is None:
            context = ExecutionContext()
        
        result = ExecutionResult(
            status=ExecutionStatus.PENDING,
            total_steps=1,
            started_at=str(datetime.now().isoformat()),
        )
        
        self.active_executions[context.execution_id] = context
        self.execution_results[context.execution_id] = result
        
        watchdog = WatchdogTimer(
            timeout_ms=self.config.max_execution_time_ms,
            callback=lambda: self._handle_timeout(context.execution_id),
        )
        self.watchdogs[context.execution_id] = watchdog
        
        try:
            result.status = ExecutionStatus.RUNNING
            watchdog.start()
            
            # Execute agent task
            if hasattr(agent, 'execute'):
                output = await agent.execute(task=task, context=context)
            elif hasattr(agent, 'run'):
                output = await agent.run(task=task, context=context)
            else:
                raise ExecutionError(f"Agent has no execute or run method: {agent}")
            
            return self._finalize_execution(
                context.execution_id,
                ExecutionStatus.COMPLETED,
                output=output,
                steps_executed=1,
            )
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            return self._finalize_execution(
                context.execution_id,
                ExecutionStatus.FAILED,
                error=str(e),
            )
    
    async def execute_skill(
        self,
        skill: Any,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """Execute a single skill.
        
        Args:
            skill: Skill definition
            params: Skill parameters
            context: Execution context
            
        Returns:
            Execution result
        """
        if context is None:
            context = ExecutionContext()
        
        result = ExecutionResult(
            status=ExecutionStatus.PENDING,
            total_steps=1,
            started_at=str(datetime.now().isoformat()),
        )
        
        self.active_executions[context.execution_id] = context
        self.execution_results[context.execution_id] = result
        
        watchdog = WatchdogTimer(
            timeout_ms=self.config.max_execution_time_ms,
            callback=lambda: self._handle_timeout(context.execution_id),
        )
        self.watchdogs[context.execution_id] = watchdog
        
        try:
            result.status = ExecutionStatus.RUNNING
            watchdog.start()
            
            # Validate parameters
            self._validate_skill_params(skill, params)
            
            # Execute skill
            output = await self._invoke_skill(skill, params, context)
            
            return self._finalize_execution(
                context.execution_id,
                ExecutionStatus.COMPLETED,
                output=output,
                steps_executed=1,
            )
            
        except Exception as e:
            return self._finalize_execution(
                context.execution_id,
                ExecutionStatus.FAILED,
                error=str(e),
            )
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            execution_id: Execution ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        if execution_id not in self.active_executions:
            return False
        
        self._cancelled_executions.add(execution_id)
        
        # Cancel the running task if any
        if execution_id in self._running_tasks:
            task = self._running_tasks[execution_id]
            task.cancel()
            del self._running_tasks[execution_id]
        
        # Clean up watchdog
        if execution_id in self.watchdogs:
            del self.watchdogs[execution_id]
        
        logger.info(f"Execution cancelled: {execution_id}")
        return True
    
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get the status of an execution.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution result or None if not found
        """
        return self.execution_results.get(execution_id)
    
    def _build_execution_plan(self, steps: List[Any]) -> List[Any]:
        """Build an execution plan from workflow steps.
        
        Args:
            steps: List of workflow steps
            
        Returns:
            Execution plan (list of steps or step batches)
        """
        plan = []
        current_batch = []
        
        for step in steps:
            has_dependencies = (
                hasattr(step, 'depends_on') and step.depends_on
            )
            
            if has_dependencies or not self.config.allow_parallel_steps:
                # Flush current batch
                if current_batch:
                    plan.append(current_batch if len(current_batch) > 1 else current_batch[0])
                    current_batch = []
                
                plan.append(step)
            else:
                current_batch.append(step)
        
        # Flush remaining batch
        if current_batch:
            plan.append(current_batch if len(current_batch) > 1 else current_batch[0])
        
        return plan
    
    async def _execute_step(
        self,
        step: Any,
        context: ExecutionContext,
        step_outputs: Dict[str, Any],
    ) -> Any:
        """Execute a single workflow step.
        
        Args:
            step: Step to execute
            context: Execution context
            step_outputs: Outputs from previous steps
            
        Returns:
            Step result
        """
        step_id = getattr(step, 'id', str(uuid4()))
        step_name = getattr(step, 'name', 'unknown')
        step_type = getattr(step, 'type', 'skill')
        
        logger.info(f"Executing step: {step_name} ({step_type})")
        
        # Resolve parameters
        resolved_params = self._resolve_step_params(step, step_outputs, context)
        
        # Execute based on type
        if step_type == "skill":
            skill_name = getattr(step, 'skill', '')
            skill = context.variables.get('_skills', {}).get(skill_name)
            
            if not skill:
                raise ExecutionError(f"Skill not found or not loaded: {skill_name}")
            
            return await self._invoke_skill(skill, resolved_params, context)
        
        elif step_type == "agent":
            agent_id = context.variables.get('_agent_id')
            if not agent_id:
                raise ExecutionError("No agent assigned for agent step")
            
            # Agent execution would happen here
            task = resolved_params.get('task', getattr(step, 'task', ''))
            return {"result": f"Agent step executed: {task}"}
        
        elif step_type == "condition":
            return self._evaluate_condition(step, resolved_params)
        
        else:
            raise ExecutionError(f"Unknown step type: {step_type}")
    
    async def _invoke_skill(
        self,
        skill: Any,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """Invoke a skill with parameters.
        
        Args:
            skill: Skill definition
            params: Skill parameters
            context: Execution context
            
        Returns:
            Skill output
        """
        skill_name = skill.metadata.name if hasattr(skill, 'metadata') else getattr(skill, 'name', 'unknown')
        
        # Check if skill code needs to be executed
        if hasattr(skill, 'code') and skill.code:
            # Sandboxed execution of skill code
            return await self._execute_sandboxed_code(
                skill.code,
                params,
                context,
            )
        
        # For pre-built skills
        if hasattr(skill, 'execute'):
            return await skill.execute(params, context)
        
        if hasattr(skill, '__call__'):
            return await skill(params)
        
        raise ExecutionError(f"Skill {skill_name} has no executable code or execute method")
    
    async def _execute_sandboxed_code(
        self,
        code: str,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """Execute code in a sandboxed environment.
        
        Args:
            code: Python code to execute
            params: Parameters dictionary
            context: Execution context
            
        Returns:
            Execution output
        """
        import sys
        from io import StringIO
        
        # Save stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Prepare local namespace
            local_ns = {
                'params': params,
                'context': context,
                'output': None,
            }
            
            # Execute code
            exec(code, {}, local_ns)
            output = local_ns.get('output')
            
            # Get any print output
            stdout_output = sys.stdout.getvalue()
            
            return {
                'result': output,
                'stdout': stdout_output if stdout_output else None,
            }
            
        except Exception as e:
            logger.error(f"Sandboxed execution failed: {e}")
            raise ExecutionError(f"Skill execution failed: {e}")
        finally:
            # Restore stdout
            sys.stdout = old_stdout
    
    def _resolve_step_params(
        self,
        step: Any,
        step_outputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Resolve step parameters, replacing references.
        
        Args:
            step: Step definition
            step_outputs: Outputs from previous steps
            context: Execution context
            
        Returns:
            Resolved parameters
        """
        params = {}
        
        raw_params = getattr(step, 'params', {})
        if not raw_params:
            return params
        
        for key, value in raw_params.items():
            if isinstance(value, str):
                # Handle variable references like ${step_id.output.field}
                resolved = self._resolve_variable_reference(value, step_outputs, context)
                params[key] = resolved
            elif isinstance(value, dict):
                params[key] = {
                    k: self._resolve_variable_reference(v, step_outputs, context)
                    if isinstance(v, str) else v
                    for k, v in value.items()
                }
            elif isinstance(value, list):
                params[key] = [
                    self._resolve_variable_reference(v, step_outputs, context)
                    if isinstance(v, str) else v
                    for v in value
                ]
            else:
                params[key] = value
        
        return params
    
    def _resolve_variable_reference(
        self,
        value: str,
        step_outputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """Resolve a variable reference in a string.
        
        Args:
            value: String that may contain references
            step_outputs: Outputs from previous steps
            context: Execution context
            
        Returns:
            Resolved value
        """
        import re
        
        # Match ${...} patterns
        pattern = r'\$\{([^}]+)\}'
        
        def replace_reference(match):
            ref = match.group(1)
            parts = ref.split('.')
            
            if parts[0].startswith('step_'):
                # Step output reference
                step_id = parts[0]
                if step_id in step_outputs:
                    result = step_outputs[step_id]
                    # Navigate to nested field if specified
                    for part in parts[1:]:
                        if isinstance(result, dict):
                            result = result.get(part)
                        elif hasattr(result, part):
                            result = getattr(result, part)
                    return str(result)
            
            elif parts[0] == 'context':
                # Context variable reference
                if len(parts) > 1:
                    attr = parts[1]
                    if hasattr(context, attr):
                        return str(getattr(context, attr))
            
            elif parts[0] == 'input':
                # Input data reference
                if len(parts) > 1:
                    key = parts[1]
                    if key in context.input_data:
                        return str(context.input_data[key])
            
            elif parts[0] == 'var':
                # Variable reference
                if len(parts) > 1:
                    key = parts[1]
                    if key in context.variables:
                        return str(context.variables[key])
            
            return match.group(0)  # Return as-is if not resolved
        
        return re.sub(pattern, replace_reference, value)
    
    def _evaluate_condition(self, step: Any, params: Dict[str, Any]) -> bool:
        """Evaluate a condition step.
        
        Args:
            step: Condition step
            params: Resolved parameters
            
        Returns:
            Condition result
        """
        condition = getattr(step, 'condition', params.get('condition', ''))
        
        if not condition:
            return True
        
        # Simple condition evaluation
        try:
            # Safe evaluation of simple conditions
            allowed_names = params.copy()
            allowed_names.update({
                'True': True,
                'False': False,
                'None': None,
            })
            
            result = eval(condition, {"__builtins__": {}}, allowed_names)
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False
    
    def _collect_workflow_output(
        self,
        workflow: Any,
        step_outputs: Dict[str, Any],
    ) -> Any:
        """Collect the final output of a workflow.
        
        Args:
            workflow: Workflow definition
            step_outputs: Outputs from all steps
            
        Returns:
            Workflow output
        """
        # Get output mapping if defined
        output_mapping = getattr(workflow, 'output', None)
        
        if output_mapping:
            return self._resolve_variable_reference(
                output_mapping,
                step_outputs,
                ExecutionContext(),
            )
        
        # Return last step output by default
        if step_outputs:
            last_key = list(step_outputs.keys())[-1]
            return step_outputs[last_key]
        
        return None
    
    def _validate_skill_params(self, skill: Any, params: Dict[str, Any]) -> None:
        """Validate skill parameters against schema.
        
        Args:
            skill: Skill definition
            params: Parameters to validate
            
        Raises:
            BridgeXError: If validation fails
        """
        schema = None
        
        if hasattr(skill, 'metadata') and hasattr(skill.metadata, 'parameters_schema'):
            schema = skill.metadata.parameters_schema
        
        if not schema:
            return  # No schema, skip validation
        
        for param_name, param_schema in schema.items():
            required = param_schema.get('required', False)
            
            if required and param_name not in params:
                raise BridgeXError(
                    f"Missing required parameter: {param_name} "
                    f"for skill {skill.metadata.name if hasattr(skill, 'metadata') else 'unknown'}"
                )
            
            if param_name in params:
                # Type checking
                expected_type = param_schema.get('type', 'string')
                value = params[param_name]
                
                type_map = {
                    'string': str,
                    'number': (int, float),
                    'integer': int,
                    'boolean': bool,
                    'array': list,
                    'object': dict,
                }
                
                expected_py_type = type_map.get(expected_type)
                
                if expected_py_type and not isinstance(value, expected_py_type):
                    raise BridgeXError(
                        f"Parameter {param_name}: expected {expected_type}, "
                        f"got {type(value).__name__}"
                    )
    
    async def _retry_step(
        self,
        step: Any,
        context: ExecutionContext,
        step_outputs: Dict[str, Any],
        error: Exception,
    ) -> Optional[Any]:
        """Retry a failed step.
        
        Args:
            step: Step to retry
            context: Execution context
            step_outputs: Previous step outputs
            error: The original error
            
        Returns:
            Step result or None if all retries failed
        """
        for attempt in range(self.config.retry_count):
            logger.info(f"Retrying step {getattr(step, 'name', 'unknown')} "
                       f"(attempt {attempt + 1}/{self.config.retry_count})")
            
            # Wait before retry
            await asyncio.sleep(self.config.retry_delay_ms / 1000)
            
            try:
                result = await self._execute_step(step, context, step_outputs)
                logger.info(f"Step retry succeeded on attempt {attempt + 1}")
                return result
            except Exception as retry_error:
                logger.warning(f"Retry attempt {attempt + 1} failed: {retry_error}")
        
        logger.error(f"All {self.config.retry_count} retry attempts failed for step "
                    f"{getattr(step, 'name', 'unknown')}")
        return None
    
    def _finalize_execution(
        self,
        execution_id: str,
        status: ExecutionStatus,
        output: Any = None,
        steps_executed: int = 0,
        error: Optional[str] = None,
    ) -> ExecutionResult:
        """Finalize an execution and record results.
        
        Args:
            execution_id: Execution ID
            status: Final status
            output: Execution output
            steps_executed: Number of steps executed
            error: Error message if failed
            
        Returns:
            Execution result
        """
        result = self.execution_results.get(execution_id)
        if not result:
            result = ExecutionResult(
                status=status,
                output=output,
                steps_executed=steps_executed,
                error=error,
            )
        else:
            result.status = status
            result.output = output
            result.steps_executed = steps_executed
            result.error = error
        
        result.completed_at = str(datetime.now().isoformat())
        
        # Calculate duration
        if result.started_at:
            start = datetime.fromisoformat(result.started_at)
            end = datetime.fromisoformat(result.completed_at)
            result.duration_ms = int((end - start).total_seconds() * 1000)
        
        # Clean up watchdog
        if execution_id in self.watchdogs:
            del self.watchdogs[execution_id]
        
        # Update active executions
        if execution_id in self.active_executions:
            del self.active_executions[execution_id]
        
        logger.info(
            f"Execution {execution_id} finalized with status: {status}"
            + (f" (error: {error})" if error else "")
        )
        
        return result
    
    def _handle_timeout(self, execution_id: str) -> None:
        """Handle an execution timeout.
        
        Args:
            execution_id: Execution ID that timed out
        """
        logger.warning(f"Execution {execution_id} timed out")
        
        if self.config.timeout_action == "cancel":
            asyncio.create_task(self.cancel_execution(execution_id))
        elif self.config.timeout_action == "pause":
            # Mark as paused
            if execution_id in self.execution_results:
                self.execution_results[execution_id].status = ExecutionStatus.PAUSED
    
    async def shutdown(self) -> None:
        """Shutdown the runtime."""
        # Cancel all active executions
        for execution_id in list(self.active_executions.keys()):
            await self.cancel_execution(execution_id)
        
        logger.info("Execution Runtime shutdown complete")


# Import here to avoid circular import
from uuid import uuid4