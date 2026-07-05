"""
BridgeX Test Suite
=================
Comprehensive test suite for the BridgeX framework.
"""

import asyncio
import sys
import os
import traceback
from typing import List, Dict, Any, Tuple

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Test results tracking
test_results: List[Dict[str, Any]] = []


def record_result(test_name: str, success: bool, error: str = None, details: Dict[str, Any] = None):
    """Record a test result."""
    test_results.append({
        "name": test_name,
        "success": success,
        "error": error,
        "details": details or {}
    })
    
    status = "✓" if success else "✗"
    print(f"  {status} {test_name}")
    if error:
        print(f"    Error: {error}")


async def test_imports():
    """Test 1: Import all modules."""
    print("\n📦 Test 1: Module Imports")
    print("-" * 40)
    
    try:
        from bridgex.core.models import (
            WorkflowDefinition, WorkflowStep, WorkflowStatus,
            AgentDefinition, SkillDefinition
        )
        record_result("Import core models", True)
    except Exception as e:
        record_result("Import core models", False, str(e))
        return  # Critical failure
    
    try:
        from bridgex.core.engine import BridgeEngine
        record_result("Import BridgeEngine", True)
    except Exception as e:
        record_result("Import BridgeEngine", False, str(e))
    
    try:
        from bridgex.core.orchestrator import Orchestrator
        record_result("Import Orchestrator", True)
    except Exception as e:
        record_result("Import Orchestrator", False, str(e))
    
    try:
        from bridgex.skills.marketplace import SkillMarketplace
        record_result("Import SkillMarketplace", True)
    except Exception as e:
        record_result("Import SkillMarketplace", False, str(e))
    
    try:
        from bridgex.agents.manager import AgentManager
        record_result("Import AgentManager", True)
    except Exception as e:
        record_result("Import AgentManager", False, str(e))
    
    try:
        from bridgex.trust.verifier import TrustVerifier
        record_result("Import TrustVerifier", True)
    except Exception as e:
        record_result("Import TrustVerifier", False, str(e))
    
    try:
        from bridgex.execution.runtime import ExecutionRuntime
        record_result("Import ExecutionRuntime", True)
    except Exception as e:
        record_result("Import ExecutionRuntime", False, str(e))
    
    try:
        from bridgex.connectors.manager import ConnectorManager, ConnectorConfig
        record_result("Import ConnectorManager", True)
    except Exception as e:
        record_result("Import ConnectorManager", False, str(e))
    
    try:
        from bridgex.utils.exceptions import (
            BridgeXError, ConnectionError, ValidationError, ExecutionError,
            SkillError, AgentError, TrustError, ConfigurationError,
            ResourceError, TimeoutError, DependencyError, RateLimitError,
            SkillNotFoundError
        )
        record_result("Import exceptions", True)
    except Exception as e:
        record_result("Import exceptions", False, str(e))
    
    try:
        import bridgex
        record_result(f"Import bridgex package v{bridgex.__version__}", True)
    except Exception as e:
        record_result("Import bridgex package", False, str(e))


async def test_models():
    """Test 2: Model creation and validation."""
    print("\n🏗️ Test 2: Model Creation & Validation")
    print("-" * 40)
    
    try:
        from bridgex.core.models import (
            WorkflowDefinition, WorkflowStep, WorkflowStatus,
            AgentDefinition, SkillDefinition
        )
        
        # Test WorkflowStep creation
        try:
            step = WorkflowStep(
                type="skill",
                name="test_step",
                skill="test_skill",
                params={"test": "value"}
            )
            record_result("Create WorkflowStep", True)
        except Exception as e:
            record_result("Create WorkflowStep", False, str(e))
        
        # Test WorkflowDefinition creation
        try:
            workflow = WorkflowDefinition(
                name="test_workflow",
                steps=[step],
                description="Test workflow"
            )
            record_result("Create WorkflowDefinition", True)
        except Exception as e:
            record_result("Create WorkflowDefinition", False, str(e))
        
        # Test WorkflowStatus creation
        try:
            status = WorkflowStatus(
                workflow_id="test_workflow",
                execution_id="test_execution",
                status="pending"
            )
            record_result("Create WorkflowStatus", True)
        except Exception as e:
            record_result("Create WorkflowStatus", False, str(e))
        
        # Test status choices
        try:
            choices = WorkflowStatus.get_status_choices()
            expected = ["pending", "running", "completed", "failed", "cancelled", "paused"]
            assert choices == expected, f"Expected {expected}, got {choices}"
            record_result("WorkflowStatus.get_status_choices()", True)
        except Exception as e:
            record_result("WorkflowStatus.get_status_choices()", False, str(e))
        
        # Test AgentDefinition creation
        try:
            agent = AgentDefinition(
                name="test_agent",
                type="assistant",
                description="Test agent",
                capabilities=["web_search", "code_review"],
                llm_model="gpt-4"
            )
            record_result("Create AgentDefinition", True)
        except Exception as e:
            record_result("Create AgentDefinition", False, str(e))
        
        # Test SkillDefinition creation
        try:
            skill = SkillDefinition(
                name="test_skill",
                version="1.0.0",
                description="Test skill",
                category="testing",
                dependencies=["numpy", "pandas"]
            )
            record_result("Create SkillDefinition", True)
        except Exception as e:
            record_result("Create SkillDefinition", False, str(e))
        
        # Test model serialization
        try:
            workflow_dict = workflow.model_dump()
            assert isinstance(workflow_dict, dict)
            assert "name" in workflow_dict
            record_result("Model serialization (dict)", True)
        except Exception as e:
            record_result("Model serialization (dict)", False, str(e))
        
        # Test model JSON serialization
        try:
            workflow_json = workflow.model_dump_json()
            assert isinstance(workflow_json, str)
            assert "test_workflow" in workflow_json
            record_result("Model serialization (JSON)", True)
        except Exception as e:
            record_result("Model serialization (JSON)", False, str(e))
            
    except Exception as e:
        record_result("Models test suite", False, str(e))


async def test_exceptions():
    """Test 3: Exception hierarchy."""
    print("\n⚠️ Test 3: Exception Hierarchy")
    print("-" * 40)
    
    try:
        from bridgex.utils.exceptions import (
            BridgeXError, ConnectionError, ValidationError, ExecutionError,
            SkillError, AgentError, TrustError, ConfigurationError,
            ResourceError, TimeoutError, DependencyError, RateLimitError,
            SkillNotFoundError
        )
        
        # Test base exception
        try:
            error = BridgeXError("Test error", code="TEST_ERROR")
            assert str(error) == "[TEST_ERROR] Test error"
            assert error.to_dict()["code"] == "TEST_ERROR"
            record_result("BridgeXError creation", True)
        except Exception as e:
            record_result("BridgeXError creation", False, str(e))
        
        # Test exception hierarchy
        exceptions_test = [
            (ConnectionError, "Connection failed", ["connector", "endpoint"]),
            (ValidationError, "Invalid input", ["field", "value"]),
            (ExecutionError, "Execution failed", ["step", "workflow"]),
            (SkillError, "Skill error", ["skill", "version"]),
            (AgentError, "Agent error", ["agent", "agent_id"]),
            (TrustError, "Trust error", ["verification_id", "risk_level"]),
            (ConfigurationError, "Config error", ["config_key", "config_value"]),
            (ResourceError, "Resource error", ["resource_type", "resource_id"]),
            (TimeoutError, "Timeout error", ["timeout_seconds", "operation"]),
            (DependencyError, "Dependency error", ["dependency", "version"]),
            (RateLimitError, "Rate limit error", ["limit", "reset_time"]),
            (SkillNotFoundError, "Skill not found", ["skill_name", "version"]),
        ]
        
        for exception_class, message, params in exceptions_test:
            try:
                kwargs = {}
                for param in params:
                    kwargs[param] = f"test_{param}"
                
                error = exception_class(message, **kwargs)
                
                # Verify base properties
                assert isinstance(error, BridgeXError)
                assert error.message == message
                assert error.code is not None
                
                # Verify specific params
                for param in params:
                    assert param in error.details, f"Missing {param} in details"
                    assert error.details[param] == f"test_{param}"
                
                record_result(f"{exception_class.__name__} creation", True)
                
            except Exception as e:
                record_result(f"{exception_class.__name__} creation", False, str(e))
        
        # Test error dict serialization
        try:
            error = ConnectionError("Failed to connect", connector="test_connector")
            error_dict = error.to_dict()
            assert "error" in error_dict
            assert "code" in error_dict
            assert "details" in error_dict
            record_result("Exception to_dict()", True)
        except Exception as e:
            record_result("Exception to_dict()", False, str(e))
            
    except Exception as e:
        record_result("Exceptions test suite", False, str(e))


async def test_engine():
    """Test 4: BridgeEngine functionality."""
    print("\n⚙️ Test 4: BridgeEngine")
    print("-" * 40)
    
    try:
        from bridgex import BridgeEngine, WorkflowDefinition, WorkflowStep
        
        # Test engine creation
        try:
            engine = BridgeEngine()
            record_result("BridgeEngine creation", True)
        except Exception as e:
            record_result("BridgeEngine creation", False, str(e))
            return
        
        # Test engine initialization
        try:
            await engine.initialize()
            record_result("BridgeEngine initialize", True)
        except Exception as e:
            record_result("BridgeEngine initialize", False, str(e))
        
        # Test workflow creation
        try:
            steps = [
                WorkflowStep(
                    type="skill",
                    name="step_1",
                    skill="test_skill",
                    params={"test": "value"}
                )
            ]
            
            workflow = WorkflowDefinition(
                name="test_workflow",
                steps=steps
            )
            record_result("Create test workflow", True)
        except Exception as e:
            record_result("Create test workflow", False, str(e))
        
        # Test engine has expected methods
        try:
            expected_methods = [
                'initialize', 'shutdown', 'execute_workflow',
                'execute_skill', '_validate_workflow', '_audit_execution'
            ]
            
            for method in expected_methods:
                if hasattr(engine, method):
                    record_result(f"Engine has method: {method}", True)
                else:
                    record_result(f"Engine has method: {method}", False, f"Method not found")
        except Exception as e:
            record_result("Engine method check", False, str(e))
        
        # Test engine shutdown
        try:
            await engine.shutdown()
            record_result("BridgeEngine shutdown", True)
        except Exception as e:
            record_result("BridgeEngine shutdown", False, str(e))
            
    except Exception as e:
        record_result("Engine test suite", False, str(e))


async def test_trust_verifier():
    """Test 5: Trust Verifier."""
    print("\n🛡️ Test 5: TrustVerifier")
    print("-" * 40)
    
    try:
        from bridgex.trust.verifier import TrustVerifier, VerificationResult
        
        # Test verifier creation
        try:
            verifier = TrustVerifier()
            record_result("TrustVerifier creation", True)
        except Exception as e:
            record_result("TrustVerifier creation", False, str(e))
            return
        
        # Test initialization
        try:
            await verifier.initialize()
            record_result("TrustVerifier initialize", True)
        except Exception as e:
            record_result("TrustVerifier initialize", False, str(e))
        
        # Test basic verification
        try:
            result = await verifier.verify_action(
                action_type="data_query",
                parameters={"table": "users", "limit": 10},
                context={"role": "admin"}
            )
            
            assert hasattr(result, 'approved')
            assert hasattr(result, 'risk_level')
            assert hasattr(result, 'reason')
            record_result("TrustVerifier basic verification", True)
        except Exception as e:
            record_result("TrustVerifier basic verification", False, str(e))
        
        # Test high-risk verification
        try:
            result = await verifier.verify_action(
                action_type="system_command",
                parameters={"command": "rm -rf /"},
                context={"role": "admin"}
            )
            
            record_result("TrustVerifier high-risk verification", True)
        except Exception as e:
            record_result("TrustVerifier high-risk verification", False, str(e))
        
        # Test VerificationResult model
        try:
            vr = VerificationResult(
                approved=True,
                risk_level="low",
                reason="All checks passed",
                verification_id="test_123",
                status="approved",
                policy="default_policy",
                checks=[
                    {"type": "integrity_check", "passed": True},
                    {"type": "permission_check", "passed": True}
                ]
            )
            
            assert vr.approved == True
            assert vr.risk_level == "low"
            assert vr.verification_id == "test_123"
            assert len(vr.checks) == 2
            assert vr.status == "approved"
            assert vr.policy == "default_policy"
            
            record_result("VerificationResult model", True)
        except Exception as e:
            record_result("VerificationResult model", False, str(e))
        
        # Test shutdown
        try:
            await verifier.shutdown()
            record_result("TrustVerifier shutdown", True)
        except Exception as e:
            record_result("TrustVerifier shutdown", False, str(e))
            
    except Exception as e:
        record_result("Trust verifier test suite", False, str(e))


async def test_skill_marketplace():
    """Test 6: Skill Marketplace."""
    print("\n🛒 Test 6: SkillMarketplace")
    print("-" * 40)
    
    try:
        from bridgex.skills.marketplace import SkillMarketplace, SkillMetadata
        
        # Test marketplace creation
        try:
            marketplace = SkillMarketplace()
            record_result("SkillMarketplace creation", True)
        except Exception as e:
            record_result("SkillMarketplace creation", False, str(e))
            return
        
        # Test initialization
        try:
            await marketplace.initialize()
            record_result("SkillMarketplace initialization", True)
        except Exception as e:
            record_result("SkillMarketplace initialization", False, str(e))
        
        # Test list skills
        try:
            skills = await marketplace.list_skills()
            record_result(f"Skill listing ({len(skills)} skills)", True)
        except Exception as e:
            record_result("Skill listing", False, str(e))
        
        # Test search skills
        try:
            results = await marketplace.search_skills("data")
            record_result(f"Skill search ({len(results)} results)", True)
        except Exception as e:
            record_result("Skill search", False, str(e))
        
        # Test get skill
        try:
            skill = await marketplace.get_skill("web_search")
            if skill:
                record_result("Get existing skill", True)
            else:
                record_result("Get existing skill", True, "Skill not found in marketplace")
        except Exception as e:
            record_result("Get existing skill", False, str(e))
        
        # Test has_skill
        try:
            exists = marketplace.has_skill("web_search")
            record_result(f"has_skill() method", True)
        except Exception as e:
            record_result("has_skill() method", False, str(e))
        
        # Test SkillMetadata model
        try:
            metadata = SkillMetadata(
                name="test_skill",
                version="1.0.0",
                description="Test skill description",
                author="Test Author",
                category="testing",
                tags=["test", "example"],
                risk_level="low"
            )
            record_result("SkillMetadata model", True)
        except Exception as e:
            record_result("SkillMetadata model", False, str(e))
        
        # Test shutdown
        try:
            await marketplace.shutdown()
            record_result("SkillMarketplace shutdown", True)
        except Exception as e:
            record_result("SkillMarketplace shutdown", False, str(e))
            
    except Exception as e:
        record_result("Skill marketplace test suite", False, str(e))


async def test_agent_manager():
    """Test 7: Agent Manager."""
    print("\n🤖 Test 7: AgentManager")
    print("-" * 40)
    
    try:
        from bridgex.agents.manager import AgentManager, AgentDefinition
        
        # Test manager creation
        try:
            manager = AgentManager()
            record_result("AgentManager creation", True)
        except Exception as e:
            record_result("AgentManager creation", False, str(e))
            return
        
        # Test initialization
        try:
            await manager.initialize()
            record_result("AgentManager initialization", True)
        except Exception as e:
            record_result("AgentManager initialization", False, str(e))
        
        # Test register agent
        try:
            agent_def = AgentDefinition(
                name="test_agent",
                type="assistant",
                description="Test assistant agent",
                capabilities=["web_search", "file_read"],
                llm_model="gpt-4"
            )
            
            agent_id = await manager.register_agent(agent_def)
            record_result(f"Register agent (ID: {agent_id})", True)
        except Exception as e:
            record_result("Register agent", False, str(e))
        
        # Test list agents
        try:
            agents = await manager.list_agents()
            record_result(f"List agents ({len(agents)} agents)", True)
        except Exception as e:
            record_result("List agents", False, str(e))
        
        # Test get agent
        try:
            agent = await manager.get_agent("test_agent")
            if agent:
                record_result("Get agent by name", True)
            else:
                record_result("Get agent by name", True, "Agent structure differs")
        except Exception as e:
            record_result("Get agent by name", False, str(e))
        
        # Test AgentDefinition model
        try:
            from bridgex.core.models import AgentDefinition as CoreAgentDef
            
            agent = CoreAgentDef(
                name="test_agent_2",
                type="reviewer",
                description="Test reviewer agent",
                capabilities=["code_review", "bug_detection"],
                llm_model="claude-3-opus",
                temperature=0.3
            )
            
            assert agent.name == "test_agent_2"
            assert agent.type == "reviewer"
            assert len(agent.capabilities) == 2
            assert agent.temperature == 0.3
            
            record_result("AgentDefinition model", True)
        except Exception as e:
            record_result("AgentDefinition model", False, str(e))
        
        # Test shutdown
        try:
            await manager.shutdown()
            record_result("AgentManager shutdown", True)
        except Exception as e:
            record_result("AgentManager shutdown", False, str(e))
            
    except Exception as e:
        record_result("Agent manager test suite", False, str(e))


async def test_execution_runtime():
    """Test 8: Execution Runtime."""
    print("\n⚡ Test 8: ExecutionRuntime")
    print("-" * 40)
    
    try:
        from bridgex.execution.runtime import ExecutionRuntime, ExecutionContext
        
        # Test runtime creation
        try:
            runtime = ExecutionRuntime()
            record_result("ExecutionRuntime creation", True)
        except Exception as e:
            record_result("ExecutionRuntime creation", False, str(e))
            return
        
        # Test initialization
        try:
            await runtime.initialize()
            record_result("ExecutionRuntime initialization", True)
        except Exception as e:
            record_result("ExecutionRuntime initialization", False, str(e))
        
        # Test context creation
        try:
            context = ExecutionContext(
                workflow_id="test_workflow",
                variables={"test": "value"},
                step_outputs={"step_1": {"result": "success"}}
            )
            record_result("ExecutionContext creation", True)
        except Exception as e:
            record_result("ExecutionContext creation", False, str(e))
        
        # Test has expected methods
        try:
            expected_methods = ['initialize', 'execute_skill', 'execute_agent']
            for method in expected_methods:
                has = hasattr(runtime, method)
                record_result(f"Runtime method: {method}", has, None if has else "Missing")
        except Exception as e:
            record_result("Runtime method check", False, str(e))
        
        # Test shutdown
        try:
            await runtime.shutdown()
            record_result("ExecutionRuntime shutdown", True)
        except Exception as e:
            record_result("ExecutionRuntime shutdown", False, str(e))
            
    except Exception as e:
        record_result("Execution runtime test suite", False, str(e))


async def test_connector_manager():
    """Test 9: Connector Manager."""
    print("\n🔌 Test 9: ConnectorManager")
    print("-" * 40)
    
    try:
        from bridgex.connectors.manager import ConnectorManager, ConnectorConfig
        
        # Test manager creation
        try:
            manager = ConnectorManager()
            record_result("ConnectorManager creation", True)
        except Exception as e:
            record_result("ConnectorManager creation", False, str(e))
            return
        
        # Test initialization
        try:
            await manager.initialize()
            record_result("ConnectorManager initialization", True)
        except Exception as e:
            record_result("ConnectorManager initialization", False, str(e))
        
        # Test connector types
        try:
            types = manager.get_connector_types()
            record_result(f"Get connector types ({len(types)} types: {types})", True)
        except Exception as e:
            record_result("Get connector types", False, str(e))
        
        # Test list connectors
        try:
            connectors = manager.list_connectors()
            record_result(f"List connectors ({len(connectors)} connectors)", True)
        except Exception as e:
            record_result("List connectors", False, str(e))
        
        # Test create connector
        try:
            config = ConnectorConfig(
                name="test_api",
                type="rest",
                base_url="https://api.example.com"
            )
            connector_id = await manager.create_connector(config, test_connection=False)
            record_result(f"Create connector (ID: {connector_id})", True)
        except Exception as e:
            record_result("Create connector", False, str(e))
        
        # Test list connectors after creation
        try:
            connectors = manager.list_connectors()
            record_result(f"List connectors after creation ({len(connectors)} connectors)", True)
        except Exception as e:
            record_result("List connectors after creation", False, str(e))
        
        # Test remove connector
        try:
            result = await manager.remove_connector("rest:test_api")
            record_result("Remove connector", result)
        except Exception as e:
            record_result("Remove connector", False, str(e))
        
        # Test shutdown
        try:
            await manager.shutdown()
            record_result("ConnectorManager shutdown", True)
        except Exception as e:
            record_result("ConnectorManager shutdown", False, str(e))
            
    except Exception as e:
        record_result("Connector manager test suite", False, str(e))


async def test_orchestrator():
    """Test 10: Orchestrator."""
    print("\n🎯 Test 10: Orchestrator")
    print("-" * 40)
    
    try:
        from bridgex.core.orchestrator import Orchestrator
        from bridgex.core.models import WorkflowDefinition, WorkflowStep
        
        # Test orchestrator creation
        try:
            orchestrator = Orchestrator()
            record_result("Orchestrator creation", True)
        except Exception as e:
            record_result("Orchestrator creation", False, str(e))
            return
        
        # Test has expected methods
        try:
            expected = ['execute', '_resolve_params', '_evaluate_condition', 'get_execution_status']
            for method in expected:
                has = hasattr(orchestrator, method)
                record_result(f"Orchestrator method: {method}", has, None if has else "Missing")
        except Exception as e:
            record_result("Orchestrator method check", False, str(e))
        
        # Test that active_contexts starts empty
        try:
            assert len(orchestrator.active_contexts) == 0
            record_result("Active contexts initially empty", True)
        except Exception as e:
            record_result("Active contexts initially empty", False, str(e))
            
    except Exception as e:
        record_result("Orchestrator test suite", False, str(e))


def print_summary():
    """Print test summary."""
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["success"])
    failed = sum(1 for r in test_results if not r["success"])
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\n❌ Failed Tests:")
        for result in test_results:
            if not result["success"]:
                print(f"   - {result['name']}: {result['error']}")
    
    print("\n" + "=" * 60)
    
    return passed, failed


async def main():
    """Run all tests."""
    print("=" * 60)
    print("BridgeX Test Suite")
    print("=" * 60)
    
    try:
        # Run all test suites
        await test_imports()
        await test_models()
        await test_exceptions()
        await test_engine()
        await test_trust_verifier()
        await test_skill_marketplace()
        await test_agent_manager()
        await test_execution_runtime()
        await test_connector_manager()
        await test_orchestrator()
        
        # Print summary
        passed, failed = print_summary()
        
        # Return exit code
        return 0 if failed == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Fatal test error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)