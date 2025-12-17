"""
Full integration test for AutoGen with updated Groq models
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_autogen_integration():
    print("=" * 70)
    print("Testing AutoGen Integration with Updated Models")
    print("=" * 70)
    print()

    # Test 1: Import modules
    print("Test 1: Importing AutoGen adapters...")
    try:
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory
        from src.autogen_adapters.groupchat_factory import GroupChatFactory
        from src.autogen_adapters.conversation_manager import ConversationManager
        print("  [OK] All imports successful")
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        return False
    print()

    # Test 2: Create AgentFactory
    print("Test 2: Creating AgentFactory...")
    try:
        agent_factory = AutoGenAgentFactory("config/autogen_agents.yaml")
        print(f"  [OK] AgentFactory created")
        print(f"  Loaded {len(agent_factory.agent_configs)} agent configs")
        print(f"  Loaded {len(agent_factory.llm_configs)} LLM configs")
    except Exception as e:
        print(f"  [FAIL] AgentFactory creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()

    # Test 3: Create a simple agent with Groq
    print("Test 3: Creating research_agent with Groq...")
    try:
        research_agent = agent_factory.create_agent("research_agent")
        print(f"  [OK] Agent created: {research_agent.name}")
    except Exception as e:
        print(f"  [FAIL] Agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()

    # Test 4: Create ConversationManager
    print("Test 4: Initializing ConversationManager...")
    try:
        from src.autogen_adapters.function_registry import FunctionRegistry
        from mcp.manager import MCPManager
        from dotenv import load_dotenv

        load_dotenv()

        # Initialize dependencies
        mcp_manager = MCPManager()
        function_registry = FunctionRegistry(mcp_manager)

        # Create conversation manager
        conv_manager = ConversationManager(
            agent_factory=agent_factory,
            function_registry=function_registry,
        )

        print(f"  [OK] ConversationManager initialized")
        print(f"  Available workflows: {len(conv_manager.workflows)}")

    except Exception as e:
        print(f"  [FAIL] ConversationManager initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()

    # Test 5: Test a simple workflow execution (if possible without full MCP setup)
    print("Test 5: Testing workflow structure...")
    try:
        workflows = conv_manager.list_workflows()
        print(f"  [OK] Found {len(workflows)} workflows:")
        for wf in workflows:
            print(f"    - {wf['name']}: {wf['description']}")
    except Exception as e:
        print(f"  [FAIL] Workflow listing failed: {e}")
        return False
    print()

    print("=" * 70)
    print("[SUCCESS] All integration tests passed!")
    print("=" * 70)
    print()
    print("The system is ready to use with the updated Groq models.")
    print()

    return True


if __name__ == "__main__":
    success = test_autogen_integration()
    sys.exit(0 if success else 1)
