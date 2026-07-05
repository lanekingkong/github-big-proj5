"""
Basic BridgeX Usage Example
===========================

This example demonstrates how to use BridgeX to execute AI-powered workflows
with built-in trust verification and skill management.
"""

import asyncio
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_workflow_example() -> None:
    """Example: Basic workflow execution with BridgeX."""
    from bridgex import BridgeEngine, WorkflowDefinition, WorkflowStep
    
    print("🚀 BridgeX Basic Workflow Example")
    print("=" * 50)
    
    try:
        # 1. Initialize BridgeX Engine
        print("\n1. Initializing BridgeX Engine...")
        engine = BridgeEngine()
        await engine.initialize()
        print("   ✓ Engine initialized")
        
        # 2. Create a simple workflow
        print("\n2. Creating workflow...")
        
        # Define workflow steps
        steps = [
            WorkflowStep(
                type="skill",
                name="data_analysis",
                skill="data_analyzer",
                params={
                    "dataset": "sales_data.csv",
                    "analysis_type": "trend_analysis",
                    "timeframe": "last_30_days"
                },
                on_success="report_generation",
                on_failure="error_handling"
            ),
            WorkflowStep(
                type="skill",
                name="report_generation",
                skill="report_generator",
                params={
                    "format": "pdf",
                    "template": "executive_summary",
                    "include_charts": True
                },
                on_success="notification",
                on_failure="error_handling"
            ),
            WorkflowStep(
                type="skill",
                name="notification",
                skill="email_sender",
                params={
                    "recipient": "team@example.com",
                    "subject": "Analysis Report Ready",
                    "body_template": "report_notification"
                }
            ),
            WorkflowStep(
                type="skill",
                name="error_handling",
                skill="error_handler",
                params={
                    "notification_level": "critical",
                    "fallback_action": "log_and_notify"
                }
            )
        ]
        
        # Create workflow definition
        workflow = WorkflowDefinition(
            name="sales_analysis_workflow",
            description="Automated sales data analysis and reporting",
            steps=steps,
            variables={
                "company_name": "Acme Corp",
                "report_quarter": "Q1 2026",
                "priority": "high"
            }
        )
        
        print(f"   ✓ Workflow created: {workflow.name}")
        print(f"   ✓ Steps: {len(workflow.steps)}")
        
        # 3. Execute workflow
        print("\n3. Executing workflow...")
        
        input_data = {
            "sales_data_source": "database",
            "analysis_depth": "detailed",
            "report_recipients": ["management@example.com", "sales@example.com"]
        }
        
        context = {
            "user_id": "user_123",
            "session_id": "session_456",
            "environment": "production"
        }
        
        result = await engine.execute_workflow(
            workflow=workflow,
            input_data=input_data,
            context=context
        )
        
        print(f"   ✓ Execution completed")
        print(f"   ✓ Execution ID: {result.execution_id}")
        print(f"   ✓ Status: {result.status}")
        print(f"   ✓ Duration: {result.duration_seconds:.2f} seconds")
        
        if result.errors:
            print(f"   ⚠️  Errors: {len(result.errors)}")
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"     - {error.get('message', 'Unknown error')}")
        else:
            print("   ✓ No errors")
        
        # 4. Display results
        print("\n4. Results:")
        if result.results:
            for key, value in result.results.items():
                if isinstance(value, dict):
                    print(f"   {key}: {len(value)} items")
                elif isinstance(value, list):
                    print(f"   {key}: {len(value)} items")
                else:
                    print(f"   {key}: {value}")
        
        # 5. Cleanup
        print("\n5. Cleaning up...")
        await engine.shutdown()
        print("   ✓ Engine shutdown complete")
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        raise


async def direct_skill_execution() -> None:
    """Example: Direct skill execution without workflow."""
    from bridgex import BridgeEngine
    from bridgex.utils.exceptions import BridgeXError
    
    print("\n\n🔧 Direct Skill Execution Example")
    print("=" * 50)
    
    try:
        # Initialize engine
        engine = BridgeEngine()
        await engine.initialize()
        print("✓ Engine initialized")
        
        # Execute a skill directly
        print("\nExecuting web_search skill...")
        
        result = await engine.execute_skill(
            skill_name="web_search",
            params={
                "query": "latest AI trends 2026",
                "max_results": 5,
                "sources": ["news", "blogs", "academic"]
            },
            context={
                "purpose": "market_research",
                "user": "researcher_001"
            }
        )
        
        print(f"✓ Skill execution completed")
        print(f"  Results found: {len(result.get('results', []))}")
        
        # Show sample results
        if 'results' in result:
            for i, item in enumerate(result['results'][:3], 1):
                print(f"  {i}. {item.get('title', 'No title')}")
                print(f"     {item.get('snippet', 'No snippet')[:100]}...")
        
        await engine.shutdown()
        print("\n✓ Engine shutdown complete")
        
    except BridgeXError as e:
        logger.error(f"BridgeX error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)


async def trust_verification_example() -> None:
    """Example: Trust verification in action."""
    from bridgex import BridgeEngine, TrustVerifier
    from bridgex.trust.verifier import VerificationResult
    
    print("\n\n🛡️ Trust Verification Example")
    print("=" * 50)
    
    try:
        # Initialize trust verifier
        verifier = TrustVerifier()
        await verifier.initialize()
        print("✓ Trust verifier initialized")
        
        # Test verification scenarios
        test_cases = [
            {
                "name": "Low risk - Data query",
                "action_type": "data_query",
                "parameters": {"table": "users", "limit": 10},
                "context": {"user_role": "admin", "environment": "staging"}
            },
            {
                "name": "Medium risk - File deletion",
                "action_type": "file_delete",
                "parameters": {"path": "/tmp/old_logs.log", "recursive": True},
                "context": {"user_role": "developer", "environment": "production"}
            },
            {
                "name": "High risk - System command",
                "action_type": "system_command",
                "parameters": {"command": "rm -rf /", "sudo": True},
                "context": {"user_role": "root", "environment": "production"}
            }
        ]
        
        for test_case in test_cases:
            print(f"\nVerifying: {test_case['name']}")
            
            result = await verifier.verify_action(
                action_type=test_case["action_type"],
                parameters=test_case["parameters"],
                context=test_case["context"]
            )
            
            print(f"  Approved: {result.approved}")
            print(f"  Risk Level: {result.risk_level}")
            print(f"  Reason: {result.reason}")
            
            if result.required_approvals:
                print(f"  Required Approvals: {result.required_approvals}")
        
        await verifier.shutdown()
        print("\n✓ Trust verifier shutdown complete")
        
    except Exception as e:
        logger.error(f"Trust verification example failed: {e}", exc_info=True)


async def skill_marketplace_example() -> None:
    """Example: Skill marketplace operations."""
    from bridgex import SkillMarketplace
    from bridgex.skills.marketplace import SkillMetadata
    
    print("\n\n🛒 Skill Marketplace Example")
    print("=" * 50)
    
    try:
        # Initialize marketplace
        marketplace = SkillMarketplace()
        await marketplace.initialize()
        print("✓ Skill marketplace initialized")
        
        # List available skills
        print("\nAvailable skills:")
        skills = await marketplace.list_skills()
        
        for skill in skills[:5]:  # Show first 5 skills
            print(f"  • {skill.name} v{skill.version}")
            print(f"    {skill.description[:80]}...")
            print(f"    Category: {skill.category}, Risk: {skill.risk_level}")
            print()
        
        # Search for skills
        print("Searching for 'data' skills...")
        search_results = await marketplace.search_skills("data")
        
        print(f"Found {len(search_results)} skills:")
        for skill in search_results[:3]:
            print(f"  - {skill.name}: {skill.description[:60]}...")
        
        # Install a skill
        print("\nInstalling 'web_scraper' skill...")
        try:
            await marketplace.install_skill("web_scraper", "1.0.0")
            print("  ✓ Skill installed successfully")
        except Exception as e:
            print(f"  ⚠️  Skill installation failed: {e}")
        
        await marketplace.shutdown()
        print("\n✓ Skill marketplace shutdown complete")
        
    except Exception as e:
        logger.error(f"Skill marketplace example failed: {e}", exc_info=True)


async def agent_management_example() -> None:
    """Example: Multi-agent management."""
    from bridgex import AgentManager
    from bridgex.agents.manager import AgentDefinition
    
    print("\n\n🤖 Agent Management Example")
    print("=" * 50)
    
    try:
        # Initialize agent manager
        manager = AgentManager()
        await manager.initialize()
        print("✓ Agent manager initialized")
        
        # Create agent definitions
        agents = [
            AgentDefinition(
                name="research_assistant",
                type="assistant",
                description="AI research assistant for gathering and analyzing information",
                capabilities=["web_search", "document_analysis", "summary_generation"],
                llm_model="gpt-4",
                system_prompt="You are a helpful research assistant. Provide accurate, well-researched information."
            ),
            AgentDefinition(
                name="code_reviewer",
                type="reviewer", 
                description="AI code reviewer for quality assurance and best practices",
                capabilities=["code_analysis", "security_check", "performance_review"],
                llm_model="claude-3-opus",
                system_prompt="You are a meticulous code reviewer. Focus on security, performance, and maintainability."
            ),
            AgentDefinition(
                name="workflow_orchestrator",
                type="coordinator",
                description="Orchestrates complex multi-agent workflows",
                capabilities=["task_decomposition", "agent_coordination", "progress_tracking"],
                llm_model="gpt-4-turbo",
                system_prompt="You are a workflow orchestrator. Break down tasks and coordinate agents effectively."
            )
        ]
        
        # Register agents
        print("\nRegistering agents...")
        for agent_def in agents:
            agent_id = await manager.register_agent(agent_def)
            print(f"  ✓ Registered: {agent_def.name} (ID: {agent_id})")
        
        # List active agents
        print("\nActive agents:")
        active_agents = await manager.list_agents()
        for agent in active_agents:
            print(f"  • {agent.name} - {agent.type} - Status: {agent.status}")
        
        # Execute agent task
        print("\nExecuting research task...")
        try:
            result = await manager.execute_agent_task(
                agent_name="research_assistant",
                task="Research the latest developments in quantum computing for 2026",
                context={"depth": "comprehensive", "sources": "recent_papers"}
            )
            
            print(f"  ✓ Task completed")
            print(f"  Response length: {len(result.get('response', ''))} characters")
            
        except Exception as e:
            print(f"  ⚠️  Task execution failed: {e}")
        
        await manager.shutdown()
        print("\n✓ Agent manager shutdown complete")
        
    except Exception as e:
        logger.error(f"Agent management example failed: {e}", exc_info=True)


async def main() -> None:
    """Run all examples."""
    print("BridgeX Examples Suite")
    print("=" * 50)
    
    try:
        # Run examples in sequence
        await basic_workflow_example()
        await direct_skill_execution()
        await trust_verification_example()
        await skill_marketplace_example()
        await agent_management_example()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Examples interrupted by user")
    except Exception as e:
        logger.error(f"Examples suite failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())