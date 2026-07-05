"""
Trust Verifier - Pre/post execution trust verification and governance.
Ensures the 96% developer trust gap is closed by providing deterministic
verification for every AI-originated action.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from bridgex.utils.exceptions import BridgeXError

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationStatus(str, Enum):
    """Status of a verification."""
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"
    AUTO_APPROVED = "auto_approved"


class TrustPolicy(BaseModel):
    """Trust policy defining what actions are allowed."""
    name: str
    description: str
    max_risk_level: RiskLevel = RiskLevel.MEDIUM
    require_human_approval_for: List[str] = Field(default_factory=list)
    auto_approve_patterns: List[str] = Field(default_factory=list)
    max_executions_per_minute: int = Field(default=100)
    max_data_size_bytes: int = Field(default=10 * 1024 * 1024)  # 10MB
    blocked_skills: List[str] = Field(default_factory=list)
    allowed_connectors: List[str] = Field(default_factory=list)
    enabled: bool = Field(default=True)


class VerificationResult(BaseModel):
    """Result of a trust verification."""
    approved: bool
    reason: str
    status: VerificationStatus
    risk_level: RiskLevel
    policy: str
    checks: List[Dict[str, Any]] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    verification_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: str(datetime.now().isoformat()))


class AuditRecord(BaseModel):
    """Audit record for an action."""
    action_id: str
    action_type: str
    actor: str  # AI agent or user
    skill_name: Optional[str] = None
    workflow_id: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = Field(default=None)
    status: str
    verification: Optional[VerificationResult] = None
    timestamp: str = Field(default_factory=lambda: str(datetime.now().isoformat()))
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class TrustVerifier:
    """Comprehensive trust verification system.
    
    Features:
    - Pre-execution risk assessment
    - Policy-based approval
    - Human-in-the-loop for critical actions
    - Audit trail generation
    - Compliance enforcement
    - Rate limiting
    """
    
    def __init__(self, policies_path: Optional[str] = None):
        """Initialize the trust verifier.
        
        Args:
            policies_path: Path to policy configuration
        """
        self.policies: Dict[str, TrustPolicy] = {}
        self.audit_records: List[AuditRecord] = []
        self.execution_history: Dict[str, List[datetime]] = {}
        
        # Default policies
        self._load_default_policies()
        
        # Risk assessment rules
        self.risk_patterns = {
            RiskLevel.CRITICAL: [
                "delete", "destroy", "format", "reset", "purge",
                "remove_all", "clear_all", "truncate",
            ],
            RiskLevel.HIGH: [
                "modify", "update", "change", "edit", "write",
                "approve", "authorize", "grant",
            ],
            RiskLevel.MEDIUM: [
                "create", "add", "insert", "upload", "send",
                "publish", "deploy", "execute",
            ],
            RiskLevel.LOW: [
                "read", "get", "list", "search", "query",
                "view", "fetch", "download",
            ],
        }
        
        logger.info("Trust Verifier initialized")
    
    async def initialize(self) -> None:
        """Initialize the verifier."""
        # Load custom policies if any
        # TODO: Load policies from file
        
        logger.info("Trust Verifier initialization complete")
    
    async def verify_action(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
    ) -> VerificationResult:
        """Verify a generic action before execution.
        
        Args:
            action_type: Type of action
            parameters: Action parameters
            context: Execution context
            
        Returns:
            Verification result
        """
        # Assess risk based on action type
        risk_level = self._assess_action_risk(action_type)
        
        # Check parameters safety
        param_check = await self._check_parameters_safety(parameters)
        
        # Check policy
        policy_result = await self._check_against_policies(
            skill_name=action_type,
            risk_level=risk_level,
            context=context,
        )
        
        approved = param_check["safe"] and policy_result["approved"]
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            status = VerificationStatus.PENDING_REVIEW
            approved = False
        elif approved:
            status = VerificationStatus.APPROVED
        else:
            status = VerificationStatus.REJECTED
        
        return VerificationResult(
            approved=approved,
            reason=f"Action '{action_type}' assessed as {risk_level}",
            status=status,
            risk_level=risk_level,
            policy=policy_result.get("policy_name", "default"),
            checks=[
                {"type": "parameter_safety", "passed": param_check["safe"], "message": param_check.get("issues", [])},
                {"type": "policy_check", "passed": policy_result["approved"], "message": policy_result.get("reason", "")},
            ],
            details={
                "action_type": action_type,
                "context": {k: str(v) for k, v in context.items()},
            },
        )
    
    async def verify_workflow(
        self,
        workflow: Any,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> VerificationResult:
        """Verify a workflow before execution.
        
        Args:
            workflow: Workflow definition
            input_data: Input data
            context: Execution context
            
        Returns:
            Verification result
        """
        checks = []
        overall_risk = RiskLevel.LOW
        reasons = []
        all_approved = True
        
        # Check each step in the workflow
        for step in workflow.steps:
            step_result = await self._verify_step(step, context)
            checks.append({
                "step_id": step.id,
                "step_name": step.name,
                "result": step_result.dict(),
            })
            
            if not step_result.approved:
                all_approved = False
                reasons.append(f"Step '{step.name}': {step_result.reason}")
            
            # Track highest risk level
            risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
            if risk_order.index(step_result.risk_level) > risk_order.index(overall_risk):
                overall_risk = step_result.risk_level
        
        # Check rate limits
        rate_check = await self._check_rate_limit(context.get("user_id", "default"))
        checks.append({
            "type": "rate_limit",
            "passed": rate_check,
            "message": "Rate limit exceeded" if not rate_check else "Rate limit OK",
        })
        
        if not rate_check:
            all_approved = False
            reasons.append("Rate limit exceeded")
        
        # Check if any step requires human approval
        requires_approval = any(
            step.requires_approval if hasattr(step, 'requires_approval') else False
            for step in workflow.steps
        )
        
        # Build result
        if requires_approval and overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            status = VerificationStatus.PENDING_REVIEW
            reason = "Workflow requires human approval due to high risk"
        elif all_approved:
            status = VerificationStatus.APPROVED
            reason = "All verifications passed"
        else:
            status = VerificationStatus.REJECTED
            reason = "; ".join(reasons)
        
        return VerificationResult(
            approved=all_approved and not requires_approval,
            reason=reason,
            status=status,
            risk_level=overall_risk,
            policy="default_workflow_policy",
            checks=checks,
            details={
                "total_steps": len(workflow.steps),
                "risk_distribution": {
                    "low": sum(1 for c in checks if c.get("result", {}).get("risk_level") == "low"),
                    "medium": sum(1 for c in checks if c.get("result", {}).get("risk_level") == "medium"),
                    "high": sum(1 for c in checks if c.get("result", {}).get("risk_level") == "high"),
                    "critical": sum(1 for c in checks if c.get("result", {}).get("risk_level") == "critical"),
                },
            },
        )
    
    async def verify_agent(
        self,
        agent: Any,
        task: str,
        context: Dict[str, Any],
    ) -> VerificationResult:
        """Verify an agent task execution.
        
        Args:
            agent: Agent definition
            task: Task description
            context: Execution context
            
        Returns:
            Verification result
        """
        checks = []
        
        # Check agent type and capabilities
        agent_name = getattr(agent, 'name', 'unknown')
        agent_type = getattr(agent, 'type', 'generalist')
        
        # Assess risk based on task content
        risk_level = self._assess_action_risk(task.lower())
        
        # Check for sensitive keywords in task
        sensitive_keywords = [
            "delete", "remove", "format", "reset", "password", "key", "token",
            "secret", "private", "confidential", "admin", "root", "system"
        ]
        
        task_risk = RiskLevel.LOW
        for keyword in sensitive_keywords:
            if keyword in task.lower():
                if keyword in ["delete", "remove", "format", "reset", "admin", "root", "system"]:
                    task_risk = max(task_risk, RiskLevel.HIGH)
                else:
                    task_risk = max(task_risk, RiskLevel.MEDIUM)
        
        risk_level = max(risk_level, task_risk, key=lambda r: 
            [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL].index(r))
        
        # Check agent capabilities
        capabilities = getattr(agent, 'capabilities', [])
        if isinstance(capabilities, list):
            for cap in capabilities:
                if isinstance(cap, str) and "system" in cap.lower():
                    risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # Check policy
        policy_result = await self._check_against_policies(
            skill_name=f"agent_{agent_name}",
            risk_level=risk_level,
            context=context,
        )
        
        # Determine if human approval is needed
        needs_approval = risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        if hasattr(agent, 'requires_approval'):
            needs_approval = needs_approval or agent.requires_approval
        
        if needs_approval:
            status = VerificationStatus.PENDING_REVIEW
            approved = False
        elif policy_result["approved"]:
            status = VerificationStatus.APPROVED
            approved = True
        else:
            status = VerificationStatus.REJECTED
            approved = False
        
        return VerificationResult(
            approved=approved and not needs_approval,
            reason=(
                "Approved based on policy"
                if approved
                else f"Risk level {risk_level} requires review"
            ),
            status=status,
            risk_level=risk_level,
            policy=policy_result.get("policy_name", "default"),
            checks=checks,
            details={
                "agent_name": agent_name,
                "agent_type": agent_type,
                "task": task,
                "risk_assessment": risk_level.value,
                "requires_approval": needs_approval,
            },
        )
    
    async def verify_skill(
        self,
        skill: Any,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> VerificationResult:
        """Verify a skill execution.
        
        Args:
            skill: Skill definition
            params: Execution parameters
            context: Execution context
            
        Returns:
            Verification result
        """
        checks = []
        
        # Check if skill is blocked
        block_check = await self._check_blocked_skill(
            skill.metadata.name if hasattr(skill, 'metadata') else getattr(skill, 'name', 'unknown')
        )
        checks.append({
            "type": "blocked_skill",
            "passed": not block_check,
            "message": "Skill is blocked" if block_check else "Skill not blocked",
        })
        
        if block_check:
            return VerificationResult(
                approved=False,
                reason=f"Skill is blocked: {skill.metadata.name if hasattr(skill, 'metadata') else 'unknown'}",
                status=VerificationStatus.REJECTED,
                risk_level=RiskLevel.CRITICAL,
                policy="skill_block_policy",
                checks=checks,
            )
        
        # Assess risk based on skill metadata
        risk_level = RiskLevel.LOW
        if hasattr(skill, 'metadata'):
            if hasattr(skill.metadata, 'risk_level'):
                risk_level = RiskLevel(skill.metadata.risk_level)
            elif hasattr(skill.metadata, 'name'):
                name = skill.metadata.name.lower()
                risk_level = self._assess_action_risk(name)
        else:
            skill_name = getattr(skill, 'name', '')
            risk_level = self._assess_action_risk(skill_name.lower())
        
        # Check parameters for sensitive data
        param_check = await self._check_parameters_safety(params)
        checks.append({
            "type": "parameter_safety",
            "passed": param_check["safe"],
            "message": param_check.get("issues", []),
        })
        
        if not param_check["safe"]:
            risk_level = max(risk_level, RiskLevel.HIGH, key=lambda r: 
                [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL].index(r))
        
        # Check policy
        policy_result = await self._check_against_policies(
            skill_name=skill.metadata.name if hasattr(skill, 'metadata') else getattr(skill, 'name', ''),
            risk_level=risk_level,
            context=context,
        )
        
        approved = param_check["safe"] and policy_result["approved"]
        
        # Determine if human approval is needed
        needs_approval = risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        if hasattr(skill, 'metadata') and hasattr(skill.metadata, 'requires_approval'):
            needs_approval = needs_approval or skill.metadata.requires_approval
        
        if needs_approval:
            status = VerificationStatus.PENDING_REVIEW
            approved = False
        elif approved:
            status = VerificationStatus.APPROVED
        else:
            status = VerificationStatus.REJECTED
        
        return VerificationResult(
            approved=approved and not needs_approval,
            reason=(
                "Approved based on policy"
                if approved
                else f"Risk level {risk_level} requires review"
            ),
            status=status,
            risk_level=risk_level,
            policy=policy_result.get("policy_name", "default"),
            checks=checks,
            details={
                "skill_name": skill.metadata.name if hasattr(skill, 'metadata') else getattr(skill, 'name', ''),
                "version": skill.metadata.version if hasattr(skill, 'metadata') else "unknown",
                "risk_assessment": risk_level.value,
                "requires_approval": needs_approval,
            },
        )
    
    async def audit_execution(
        self,
        action_type: str,
        actor: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> AuditRecord:
        """Create an audit record for an execution.
        
        Args:
            action_type: Type of action
            actor: Who performed the action
            params: Action parameters
            result: Action result
            duration_ms: Execution duration
            error: Error message if failed
            
        Returns:
            Audit record
        """
        record = AuditRecord(
            action_id=str(uuid4()),
            action_type=action_type,
            actor=actor,
            params=params,
            result=result,
            status="failed" if error else "completed",
            duration_ms=duration_ms,
            error=error,
        )
        
        self.audit_records.append(record)
        
        # Log audit record
        logger.info(
            f"Audit [{record.status}]: {action_type} by {actor} "
            f"(duration: {duration_ms}ms)"
        )
        
        return record
    
    async def _verify_step(
        self,
        step: Any,
        context: Dict[str, Any],
    ) -> VerificationResult:
        """Verify a single workflow step.
        
        Args:
            step: Step definition
            context: Execution context
            
        Returns:
            Verification result
        """
        step_name = getattr(step, 'name', str(step))
        step_type = getattr(step, 'type', 'unknown')
        
        # Assess risk based on step type and skill name
        risk_level = RiskLevel.LOW
        
        if step_type == "skill":
            skill_name = getattr(step, 'skill', '')
            if skill_name:
                risk_level = self._assess_action_risk(skill_name)
        elif step_type == "agent":
            risk_level = RiskLevel.MEDIUM
        
        # Check if step is blocked
        skill_name = getattr(step, 'skill', '')
        if skill_name and skill_name in self._get_blocked_skills():
            return VerificationResult(
                approved=False,
                reason=f"Skill is blocked: {skill_name}",
                status=VerificationStatus.REJECTED,
                risk_level=RiskLevel.CRITICAL,
                policy="skill_block_policy",
            )
        
        return VerificationResult(
            approved=risk_level != RiskLevel.CRITICAL,
            reason=f"Step '{step_name}' assessed as {risk_level}",
            status=VerificationStatus.APPROVED if risk_level != RiskLevel.CRITICAL else VerificationStatus.REJECTED,
            risk_level=risk_level,
            policy="default_step_policy",
        )
    
    def _assess_action_risk(self, action_name: str) -> RiskLevel:
        """Assess risk level based on action name.
        
        Args:
            action_name: Name of the action
            
        Returns:
            Risk level
        """
        action_lower = action_name.lower()
        
        # Check critical patterns
        for pattern in self.risk_patterns[RiskLevel.CRITICAL]:
            if pattern in action_lower:
                return RiskLevel.CRITICAL
        
        # Check high risk patterns
        for pattern in self.risk_patterns[RiskLevel.HIGH]:
            if pattern in action_lower:
                return RiskLevel.HIGH
        
        # Check medium risk patterns
        for pattern in self.risk_patterns[RiskLevel.MEDIUM]:
            if pattern in action_lower:
                return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    async def _check_blocked_skill(self, skill_name: str) -> bool:
        """Check if a skill is blocked.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            True if blocked
        """
        blocked = self._get_blocked_skills()
        return skill_name in blocked
    
    async def _check_rate_limit(self, user_id: str) -> bool:
        """Check rate limit for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if within limits
        """
        now = datetime.now()
        
        if user_id not in self.execution_history:
            self.execution_history[user_id] = []
        
        # Clean old entries
        cutoff = now - timedelta(minutes=1)
        self.execution_history[user_id] = [
            t for t in self.execution_history[user_id] if t > cutoff
        ]
        
        # Check limit
        if len(self.execution_history[user_id]) >= 100:  # Default limit
            return False
        
        # Record execution
        self.execution_history[user_id].append(now)
        
        return True
    
    async def _check_parameters_safety(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check parameters for safety issues.
        
        Args:
            params: Parameters to check
            
        Returns:
            Safety check results
        """
        issues = []
        safe = True
        
        # Check for sensitive data patterns
        sensitive_patterns = [
            r'\b\d{16}\b',  # Credit card numbers
            r'\b[A-Z]{2}\d{6}\b',  # Passport numbers
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        ]
        
        import re
        
        # Recursively check parameters
        def check_value(value: Any, path: str):
            nonlocal safe
            if isinstance(value, str):
                for pattern in sensitive_patterns:
                    if re.search(pattern, value):
                        issues.append(f"Sensitive data found at {path}")
                        safe = False
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(v, f"{path}.{k}")
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    check_value(v, f"{path}[{i}]")
        
        check_value(params, "params")
        
        return {"safe": safe, "issues": issues}
    
    async def _check_against_policies(
        self,
        skill_name: str,
        risk_level: RiskLevel,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check skill against applicable policies.
        
        Args:
            skill_name: Name of the skill
            risk_level: Risk level
            context: Execution context
            
        Returns:
            Policy check result
        """
        for policy_name, policy in self.policies.items():
            if not policy.enabled:
                continue
            
            # Check if skill is explicitly blocked
            if skill_name in policy.blocked_skills:
                return {
                    "approved": False,
                    "reason": f"Skill blocked by policy: {policy_name}",
                    "policy_name": policy_name,
                }
            
            # Check risk level against policy
            risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
            if risk_order.index(risk_level) > risk_order.index(policy.max_risk_level):
                return {
                    "approved": False,
                    "reason": f"Risk level {risk_level} exceeds policy maximum {policy.max_risk_level}",
                    "policy_name": policy_name,
                }
        
        return {
            "approved": True,
            "reason": "Policy check passed",
            "policy_name": "default",
        }
    
    def _load_default_policies(self) -> None:
        """Load default trust policies."""
        self.policies["default"] = TrustPolicy(
            name="default",
            description="Default policy for all actions",
            max_risk_level=RiskLevel.HIGH,
            require_human_approval_for=[
                "destroy", "purge", "format", "reset",
            ],
            auto_approve_patterns=[
                "read_*", "get_*", "list_*", "search_*",
            ],
        )
        
        self.policies["strict"] = TrustPolicy(
            name="strict",
            description="Strict policy requiring approval for most actions",
            max_risk_level=RiskLevel.LOW,
            require_human_approval_for=[
                "create_*", "update_*", "delete_*",
            ],
        )
        
        self.policies["enterprise"] = TrustPolicy(
            name="enterprise",
            description="Enterprise policy with compliance requirements",
            max_risk_level=RiskLevel.MEDIUM,
            require_human_approval_for=[
                "delete_*", "deploy_*", "publish_*", "approve_*",
            ],
            blocked_skills=[
                "system.execute_root",
                "system.execute_unrestricted",
            ],
        )
    
    def _get_blocked_skills(self) -> Set[str]:
        """Get all blocked skills from active policies.
        
        Returns:
            Set of blocked skill names
        """
        blocked: Set[str] = set()
        for policy in self.policies.values():
            if policy.enabled:
                blocked.update(policy.blocked_skills)
        return blocked
    
    async def shutdown(self) -> None:
        """Shutdown the verifier."""
        logger.info("Trust Verifier shutdown complete")


# Import here to avoid circular import
from uuid import uuid4