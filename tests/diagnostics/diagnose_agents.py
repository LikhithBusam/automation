"""
Comprehensive Agent Diagnostic Script
Identifies exactly why agents are not being created or retrieved
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from src.autogen_adapters.agent_factory import AutoGenAgentFactory
from src.autogen_adapters.conversation_manager import create_conversation_manager


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


async def main():
    """Main diagnostic"""
    print_section("AGENT SYSTEM DIAGNOSTIC")

    # Phase 1: Check configuration files
    print_section("Phase 1: Configuration Files")

    import yaml

    # Load agent config
    with open("config/autogen_agents.yaml", "r") as f:
        agent_config = yaml.safe_load(f)

    agents_defined = list(agent_config.get("agents", {}).keys())
    print(f"[1] Agents defined in autogen_agents.yaml:")
    for agent_name in agents_defined:
        agent_cfg = agent_config["agents"][agent_name]
        display_name = agent_cfg.get("name", "N/A")
        agent_type = agent_cfg.get("agent_type", "N/A")
        print(f"    - YAML key: '{agent_name}'")
        print(f"      Display name: '{display_name}'")
        print(f"      Type: {agent_type}")

    # Load workflow config
    with open("config/autogen_workflows.yaml", "r") as f:
        workflow_config = yaml.safe_load(f)

    print(f"\n[2] Agents required by workflows:")
    for workflow_name, workflow_cfg in workflow_config.get("workflows", {}).items():
        agent_names = workflow_cfg.get("agents", [])
        if agent_names:
            print(f"    - {workflow_name}: {agent_names}")

    # Phase 2: Try to create agent factory
    print_section("Phase 2: Agent Factory Creation")

    try:
        print("[1] Creating AutoGenAgentFactory...")
        factory = AutoGenAgentFactory()
        print("[OK] Factory created successfully")

        print(f"\n[2] Agent configurations loaded: {len(factory.agent_configs)}")
        print(f"    Available configs: {list(factory.agent_configs.keys())}")

    except Exception as e:
        print(f"[ERROR] Failed to create factory: {e}")
        import traceback

        traceback.print_exc()
        return

    # Phase 3: Try to create each agent individually
    print_section("Phase 3: Individual Agent Creation")

    created_agents = []
    failed_agents = []

    for agent_name in agents_defined:
        print(f"\n[{len(created_agents) + len(failed_agents) + 1}] Creating agent: '{agent_name}'")

        try:
            agent = factory.create_agent(agent_name)

            if agent:
                print(f"    [OK] Agent created successfully")
                print(f"         Agent object: {type(agent).__name__}")
                print(f"         Agent.name: {getattr(agent, 'name', 'N/A')}")
                created_agents.append(agent_name)
            else:
                print(f"    [ERROR] Agent is None")
                failed_agents.append(agent_name)

        except Exception as e:
            print(f"    [ERROR] Exception: {e}")
            import traceback

            traceback.print_exc()
            failed_agents.append(agent_name)

    # Phase 4: Check agent registry
    print_section("Phase 4: Agent Registry Status")

    print(f"[1] Agents successfully created: {len(created_agents)}/{len(agents_defined)}")
    print(f"    Created: {created_agents}")
    print(f"    Failed: {failed_agents}")

    print(f"\n[2] Agent registry contents:")
    print(f"    Registry keys: {factory.list_agents()}")
    print(f"    Registry size: {len(factory.agents)}")

    # Phase 5: Test agent retrieval
    print_section("Phase 5: Agent Retrieval Test")

    test_names = ["code_analyzer", "user_proxy_executor", "CodeAnalyzer", "Executor"]

    for test_name in test_names:
        agent = factory.get_agent(test_name)
        status = "[OK] Found" if agent else "[FAIL] Not found"
        print(f"    get_agent('{test_name}'): {status}")

    # Phase 6: Test conversation manager
    print_section("Phase 6: Conversation Manager Test")

    try:
        print("[1] Creating conversation manager...")
        manager = await create_conversation_manager()
        print("[OK] Manager created")

        print(f"\n[2] Manager's agent factory:")
        print(f"    Registered agents: {manager.agent_factory.list_agents()}")

        print(f"\n[3] Testing workflow agent retrieval:")
        workflow_cfg = workflow_config["workflows"]["quick_code_review"]
        required_agents = workflow_cfg.get("agents", [])

        print(f"    Workflow requires: {required_agents}")

        for agent_name in required_agents:
            agent = manager.agent_factory.get_agent(agent_name)
            if agent:
                print(f"    - '{agent_name}': [OK] Found")
            else:
                print(f"    - '{agent_name}': [FAIL] NOT FOUND")
                print(f"      Available in registry: {manager.agent_factory.list_agents()}")

    except Exception as e:
        print(f"[ERROR] Failed to create manager: {e}")
        import traceback

        traceback.print_exc()

    # Phase 7: Summary and Recommendations
    print_section("Phase 7: Diagnostic Summary")

    if failed_agents:
        print("[CRITICAL] Some agents failed to create:")
        for agent_name in failed_agents:
            print(f"  - {agent_name}")
        print("\nRecommendations:")
        print("  1. Check logs above for specific error messages")
        print("  2. Verify Groq API key is valid")
        print("  3. Check model names in config/autogen_agents.yaml")
        print("  4. Ensure all required dependencies are installed")

    else:
        print("[OK] All agents created successfully!")

        registry_keys = set(factory.list_agents())
        workflow_needs = set()
        for wf_cfg in workflow_config.get("workflows", {}).values():
            workflow_needs.update(wf_cfg.get("agents", []))

        missing = workflow_needs - registry_keys

        if missing:
            print(f"\n[WARNING] Name mismatch detected:")
            print(f"  Workflows need: {sorted(workflow_needs)}")
            print(f"  Registry has: {sorted(registry_keys)}")
            print(f"  Missing: {sorted(missing)}")
            print("\nRecommendation:")
            print("  Update workflow configs to use these agent names:")
            for agent_name in sorted(registry_keys):
                print(f"    - '{agent_name}'")
        else:
            print("\n[OK] All workflow agent names match registry!")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
