"""
BridgeX - Universal AI Execution Bridge
========================================
Connect AI reasoning to real-world actions with built-in trust, verification, and governance.

The #1 bottleneck in AI adoption today: 95% of AI pilots never reach production
because AI can think but cannot act. BridgeX solves this by providing a universal
execution layer that bridges the gap between AI reasoning and real-world systems.
"""

__version__ = "0.1.0"
__author__ = "lanekingkong"
__license__ = "Apache-2.0"

from bridgex.core.engine import BridgeEngine
from bridgex.core.orchestrator import Orchestrator
from bridgex.core.models import WorkflowDefinition, WorkflowStep, WorkflowStatus, AgentDefinition, SkillDefinition
from bridgex.agents.manager import AgentManager
from bridgex.skills.marketplace import SkillMarketplace
from bridgex.execution.runtime import ExecutionRuntime
from bridgex.trust.verifier import TrustVerifier
from bridgex.utils.exceptions import BridgeXError

__all__ = [
    "BridgeEngine",
    "Orchestrator",
    "WorkflowDefinition",
    "WorkflowStep", 
    "WorkflowStatus",
    "AgentDefinition",
    "SkillDefinition",
    "AgentManager",
    "SkillMarketplace",
    "ExecutionRuntime",
    "TrustVerifier",
    "BridgeXError",
]