"""
BridgeX Exceptions - Custom exceptions for the BridgeX framework.
"""

from typing import Any, Dict, Optional


class BridgeXError(Exception):
    """Base exception for all BridgeX errors."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the error.
        
        Args:
            message: Error message
            code: Error code for programmatic handling
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error": self.message,
            "code": self.code,
            "details": self.details,
        }


class ConnectionError(BridgeXError):
    """Error related to connections."""
    
    def __init__(
        self,
        message: str,
        connector: Optional[str] = None,
        endpoint: Optional[str] = None,
        **kwargs,
    ):
        """Initialize connection error.
        
        Args:
            message: Error message
            connector: Connector name
            endpoint: Endpoint URL
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if connector:
            details["connector"] = connector
        if endpoint:
            details["endpoint"] = endpoint
        
        super().__init__(
            message=message,
            code="CONNECTION_ERROR",
            details=details,
        )


class ValidationError(BridgeXError):
    """Error related to validation."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected: Optional[Any] = None,
        **kwargs,
    ):
        """Initialize validation error.
        
        Args:
            message: Error message
            field: Field name that failed validation
            value: Invalid value
            expected: Expected value or type
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        if expected is not None:
            details["expected"] = expected
        
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details,
        )


class ExecutionError(BridgeXError):
    """Error related to execution."""
    
    def __init__(
        self,
        message: str,
        step: Optional[str] = None,
        workflow: Optional[str] = None,
        retry_count: Optional[int] = None,
        **kwargs,
    ):
        """Initialize execution error.
        
        Args:
            message: Error message
            step: Step name that failed
            workflow: Workflow name
            retry_count: Number of retry attempts made
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if step:
            details["step"] = step
        if workflow:
            details["workflow"] = workflow
        if retry_count is not None:
            details["retry_count"] = retry_count
        
        super().__init__(
            message=message,
            code="EXECUTION_ERROR",
            details=details,
        )


class SkillError(BridgeXError):
    """Error related to skills."""
    
    def __init__(
        self,
        message: str,
        skill: Optional[str] = None,
        version: Optional[str] = None,
        **kwargs,
    ):
        """Initialize skill error.
        
        Args:
            message: Error message
            skill: Skill name
            version: Skill version
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if skill:
            details["skill"] = skill
        if version:
            details["version"] = version
        
        super().__init__(
            message=message,
            code="SKILL_ERROR",
            details=details,
        )


class AgentError(BridgeXError):
    """Error related to agents."""
    
    def __init__(
        self,
        message: str,
        agent: Optional[str] = None,
        agent_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize agent error.
        
        Args:
            message: Error message
            agent: Agent name
            agent_id: Agent instance ID
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if agent:
            details["agent"] = agent
        if agent_id:
            details["agent_id"] = agent_id
        
        super().__init__(
            message=message,
            code="AGENT_ERROR",
            details=details,
        )


class TrustError(BridgeXError):
    """Error related to trust verification."""
    
    def __init__(
        self,
        message: str,
        verification_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        **kwargs,
    ):
        """Initialize trust error.
        
        Args:
            message: Error message
            verification_id: Verification session ID
            risk_level: Risk level (low/medium/high)
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if verification_id:
            details["verification_id"] = verification_id
        if risk_level:
            details["risk_level"] = risk_level
        
        super().__init__(
            message=message,
            code="TRUST_ERROR",
            details=details,
        )


class ConfigurationError(BridgeXError):
    """Error related to configuration."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs,
    ):
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key
            config_value: Configuration value
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if config_key:
            details["config_key"] = config_key
        if config_value is not None:
            details["config_value"] = config_value
        
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details=details,
        )


class ResourceError(BridgeXError):
    """Error related to resources."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize resource error.
        
        Args:
            message: Error message
            resource_type: Type of resource (skill, agent, connector, etc.)
            resource_id: Resource identifier
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            code="RESOURCE_ERROR",
            details=details,
        )


class TimeoutError(BridgeXError):
    """Error related to timeouts."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[int] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        """Initialize timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            operation: Operation that timed out
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            code="TIMEOUT_ERROR",
            details=details,
        )


class DependencyError(BridgeXError):
    """Error related to dependencies."""
    
    def __init__(
        self,
        message: str,
        dependency: Optional[str] = None,
        version: Optional[str] = None,
        **kwargs,
    ):
        """Initialize dependency error.
        
        Args:
            message: Error message
            dependency: Dependency name
            version: Required version
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if dependency:
            details["dependency"] = dependency
        if version:
            details["version"] = version
        
        super().__init__(
            message=message,
            code="DEPENDENCY_ERROR",
            details=details,
        )


class RateLimitError(BridgeXError):
    """Error related to rate limiting."""
    
    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        reset_time: Optional[str] = None,
        **kwargs,
    ):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            limit: Rate limit value
            reset_time: When the limit resets
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if limit is not None:
            details["limit"] = limit
        if reset_time:
            details["reset_time"] = reset_time
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            details=details,
        )


class SkillNotFoundError(BridgeXError):
    """Error when a skill is not found."""
    
    def __init__(
        self,
        message: str,
        skill_name: Optional[str] = None,
        version: Optional[str] = None,
        **kwargs,
    ):
        """Initialize skill not found error.
        
        Args:
            message: Error message
            skill_name: Skill name
            version: Skill version
            **kwargs: Additional details
        """
        details = kwargs.copy()
        if skill_name:
            details["skill_name"] = skill_name
        if version:
            details["version"] = version
        
        super().__init__(
            message=message,
            code="SKILL_NOT_FOUND",
            details=details,
        )