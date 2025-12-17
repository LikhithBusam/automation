"""Test script to verify agent initialization"""
import asyncio
import sys
import yaml
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

async def test_agents():
    """Test agent initialization"""

    print("=" * 70)
    print("AGENT INITIALIZATION TEST")
    print("=" * 70)

    try:
        # Load config
        print("\n[1/5] Loading configuration...")
        with open("config/config.yaml") as f:
            config = yaml.safe_load(f)
        print("SUCCESS: Configuration loaded")

        # Import components
        print("\n[2/5] Importing components...")
        from src.mcp.tool_manager import MCPToolManager
        from src.memory.memory_manager import MemoryManager
        from src.models.model_factory import ModelFactory
        from src.agents import (
            create_code_analyzer_agent,
            create_documentation_agent,
            create_deployment_agent,
            create_research_agent,
            create_project_manager_agent
        )
        print("SUCCESS: All imports successful")

        # Initialize managers
        print("\n[3/5] Initializing managers...")
        tool_manager = MCPToolManager(config)
        print("  - Tool Manager initialized")

        memory_manager = MemoryManager(config.get("memory", {}))
        print("  - Memory Manager initialized")

        model_factory = ModelFactory(config)
        print("  - Model Factory initialized")

        # Initialize agents
        print("\n[4/5] Initializing agents...")
        agents = {}

        agent_factories = {
            "code_analyzer": create_code_analyzer_agent,
            "documentation": create_documentation_agent,
            "deployment": create_deployment_agent,
            "research": create_research_agent,
        }

        agent_configs = config.get("agents", {})

        for agent_name, factory_func in agent_factories.items():
            agent_config = agent_configs.get(agent_name, {})

            if not agent_config.get("enabled", False):
                print(f"  - {agent_name}: SKIPPED (disabled in config)")
                continue

            try:
                # Create agent with llm=None for fast initialization
                agent = factory_func(
                    llm=None,
                    tool_manager=tool_manager,
                    memory_manager=memory_manager
                )
                agents[agent_name] = agent
                print(f"  - {agent_name}: SUCCESS")

            except Exception as e:
                print(f"  - {agent_name}: FAILED - {str(e)}")
                import traceback
                traceback.print_exc()

        # Initialize project manager last
        if agent_configs.get("project_manager", {}).get("enabled", False):
            try:
                agent = create_project_manager_agent(
                    llm=None,
                    tool_manager=tool_manager,
                    memory_manager=memory_manager,
                    all_agents=agents
                )
                agents["project_manager"] = agent
                print(f"  - project_manager: SUCCESS")
            except Exception as e:
                print(f"  - project_manager: FAILED - {str(e)}")
                import traceback
                traceback.print_exc()

        # Summary
        print("\n[5/5] Initialization Summary")
        print(f"  Total agents initialized: {len(agents)}")
        print(f"  Agent names: {', '.join(agents.keys())}")

        # Cleanup
        print("\n[CLEANUP] Shutting down managers...")
        await memory_manager.close()
        print("SUCCESS: Memory manager closed")

        print("\n" + "=" * 70)
        print(f"TEST RESULT: {'PASSED' if len(agents) > 0 else 'FAILED'}")
        print("=" * 70)

        return len(agents) > 0

    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agents())
    sys.exit(0 if success else 1)
