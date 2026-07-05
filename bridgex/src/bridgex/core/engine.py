"""
BridgeX Core Engine - The heart of the execution bridge.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from bridgex.core.models import WorkflowDefinition, WorkflowStep
from bridgex.core.orchestrator import Orchestrator
from bridgex.agents.manager import AgentManager
from bridgex.skills.marketplace import SkillMarketplace
from bridgex.execution.runtime import ExecutionRuntime
from bridgex.trust.verifier import TrustVerifier
from bridgex.utils.exceptions import BridgeXError

logger = logging.getLogger(__name__)


class ExecutionResult(BaseModel):
    """Result of workflow execution."""
    workflow_id: str
    execution_id: str
    status: str  # pending, running, completed, failed, cancelled
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class BridgeEngine:
    """Main engine that coordinates all BridgeX components."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        enable_trust: bool = True,
        enable_audit: bool = True,
    ):
        """Initialize the BridgeX engine.
        
        Args:
            config: Configuration dictionary
            enable_trust: Enable trust verification layer
            enable_audit: Enable audit logging
        """
        self.config = config or {}
        self.enable_trust = enable_trust
        self.enable_audit = enable_audit
        
        # Initialize core components
        self.orchestrator = Orchestrator()
        self.agent_manager = AgentManager()
        self.skill_marketplace = SkillMarketplace()
        self.execution_runtime = ExecutionRuntime()
        
        if enable_trust:
            self.trust_verifier = TrustVerifier()
        
        # State management
        self.active_workflows: Dict[str, asyncio.Task] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.execution_history: Dict[str, ExecutionResult] = {}
        
        logger.info("BridgeX Engine initialized")
    
    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("Initializing BridgeX components...")
        
        # Initialize components in parallel
        tasks = [
            self.skill_marketplace.initialize(),
            self.agent_manager.initialize(),
            self.execution_runtime.initialize(),
        ]
        
        if self.enable_trust:
            tasks.append(self.trust_verifier.initialize())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("BridgeX initialization complete")
    
    def register_workflow(self, workflow_def: Union[Dict[str, Any], WorkflowDefinition]) -> str:
        """Register a workflow definition.
        
        Args:
            workflow_def: Workflow definition as dict or WorkflowDefinition
            
        Returns:
            Workflow ID
        """
        try:
            if isinstance(workflow_def, dict):
                workflow = WorkflowDefinition(**workflow_def)
            else:
                workflow = workflow_def
            
            # Validate workflow
            self._validate_workflow(workflow)
            
            # Register workflow
            self.workflow_definitions[workflow.id] = workflow
            
            logger.info(f"Workflow registered: {workflow.name} (ID: {workflow.id})")
            return workflow.id
            
        except ValidationError as e:
            raise BridgeXValidationError(f"Invalid workflow definition: {e}")
        except Exception as e:
            raise BridgeXError(f"Failed to register workflow: {e}")
    
    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute a registered workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            input_data: Input data for the workflow
            context: Execution context
            
        Returns:
            Execution result
        """
        if workflow_id not in self.workflow_definitions:
            raise BridgeXError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflow_definitions[workflow_id]
        execution_id = str(uuid4())
        
        # Create execution result
        result = ExecutionResult(
            workflow_id=workflow_id,
            execution_id=execution_id,
            status="running",
            start_time=str(datetime.now().isoformat()),
        )
        
        self.execution_history[execution_id] = result
        
        try:
            # Pre-execution trust verification
            if self.enable_trust:
                trust_result = await self.trust_verifier.verify_workflow(
                    workflow=workflow,
                    input_data=input_data or {},
                    context=context or {},
                )
                
                if not trust_result.approved:
                    result.status = "failed"
                    result.errors.append({
                        "type": "trust_verification_failed",
                        "message": trust_result.reason,
                        "details": trust_result.details,
                    })
                    return result
            
            # Execute workflow through orchestrator
            execution_result = await self.orchestrator.execute(
                workflow=workflow,
                input_data=input_data or {},
                context=context or {},
                engine=self,
            )
            
            # Update result
            result.status = "completed"
            result.end_time = str(datetime.now().isoformat())
            result.results = execution_result.results
            result.metrics = execution_result.metrics
            
            # Post-execution audit
            if self.enable_audit:
                await self._audit_execution(result)
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            
            result.status = "failed"
            result.end_time = str(datetime.now().isoformat())
            result.errors.append({
                "type": "execution_error",
                "message": str(e),
                "details": {"exception_type": type(e).__name__},
            })
        
        return result
    
    async def execute_skill(
        self,
        skill_name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a single skill directly.
        
        Args:
            skill_name: Name of the skill to execute
            params: Skill parameters
            context: Execution context
            
        Returns:
            Skill execution result
        """
        try:
            # Get skill from marketplace
            skill = await self.skill_marketplace.get_skill(skill_name)
            if not skill:
                raise BridgeXError(f"Skill not found: {skill_name}")
            
            # Pre-execution trust verification
            if self.enable_trust:
                trust_result = await self.trust_verifier.verify_skill(
                    skill=skill,
                    params=params,
                    context=context or {},
                )
                
                if not trust_result.approved:
                    raise BridgeXError(f"Skill execution not approved: {trust_result.reason}")
            
            # Execute skill
            result = await self.execution_runtime.execute_skill(
                skill=skill,
                params=params,
                context=context or {},
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Skill execution failed: {e}", exc_info=True)
            raise
    
    def _validate_workflow(self, workflow: WorkflowDefinition) -> None:
        """Validate a workflow definition.
        
        Args:
            workflow: Workflow to validate
            
        Raises:
            BridgeXValidationError: If workflow is invalid
        """
        # Check for circular dependencies
        step_ids = {step.id for step in workflow.steps}
        
        for step in workflow.steps:
            if step.on_success and step.on_success not in step_ids:
                raise BridgeXValidationError(
                    f"Step {step.id} references non-existent success step: {step.on_success}"
                )
            
            if step.on_failure and step.on_failure not in step_ids:
                raise BridgeXValidationError(
                    f"Step {step.id} references non-existent failure step: {step.on_failure}"
                )
        
        # Validate skill references
        for step in workflow.steps:
            if step.type == "skill" and step.skill:
                # Check if skill exists in marketplace
                if not self.skill_marketplace.has_skill(step.skill):
                    logger.warning(f"Skill not found in marketplace: {step.skill}")
    
    async def _audit_execution(self, result: ExecutionResult) -> None:
        """Audit an execution result.
        
        Args:
            result: Execution result to audit
        """
        audit_data = {
            "execution_id": result.execution_id,
            "workflow_id": result.workflow_id,
            "status": result.status,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "duration": (
                datetime.fromisoformat(result.end_time) - 
                datetime.fromisoformat(result.start_time)
            ).total_seconds() if result.start_time and result.end_time else None,
            "errors": len(result.errors),
            "metrics": result.metrics,
        }
        
        logger.info(f"Execution audit: {audit_data}")
        
        # TODO: Implement proper audit logging to persistent storage
    
    async def shutdown(self) -> None:
        """Shutdown the engine and all components."""
        logger.info("Shutting down BridgeX Engine...")
        
        # Cancel all active workflows
        for task in self.active_workflows.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.active_workflows:
            await asyncio.gather(*self.active_workflows.values(), return_exceptions=True)
        
        # Shutdown components
        shutdown_tasks = [
            self.skill_marketplace.shutdown(),
            self.agent_manager.shutdown(),
            self.execution_runtime.shutdown(),
        ]
        
        if self.enable_trust:
            shutdown_tasks.append(self.trust_verifier.shutdown())
        
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        logger.info("BridgeX Engine shutdown complete")


# Import datetime here to avoid circular import
from datetime import datetime