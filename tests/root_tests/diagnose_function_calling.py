"""
Diagnostic Script - Check Function Calling Setup
Verifies that agents have proper access to MCP tools
"""

import asyncio
import io
import logging
import sys
from pathlib import Path

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    print("=" * 70)
    print("Function Calling Diagnostic")
    print("=" * 70)

    # Import the conversation manager
    print("\n[1] Importing conversation manager...")
    try:
        from src.autogen_adapters.conversation_manager import create_conversation_manager

        print("✅ Import successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return

    # Create conversation manager
    print("\n[2] Creating conversation manager (initializing agents)...")
    try:
        manager = await create_conversation_manager()
        print("✅ Manager created")
    except Exception as e:
        print(f"❌ Manager creation failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # Check agent factory
    print("\n[3] Checking agents...")
    agent_factory = manager.agent_factory
    agents = agent_factory.list_agents()
    print(f"✅ Found {len(agents)} agents: {', '.join(agents)}")

    # Check code_analyzer
    print("\n[4] Checking code_analyzer agent...")
    code_analyzer = agent_factory.get_agent("code_analyzer")
    if code_analyzer:
        print(f"✅ Agent type: {type(code_analyzer).__name__}")
        print(f"   Name: {code_analyzer.name}")

        # Check if agent has llm_config with tools
        if hasattr(code_analyzer, "llm_config") and code_analyzer.llm_config:
            tools = code_analyzer.llm_config.get("tools", [])
            print(f"   Tools in llm_config: {len(tools)}")
            if tools:
                print(f"   Available tools:")
                for tool in tools[:5]:  # Show first 5
                    if "function" in tool:
                        func_name = tool["function"].get("name", "unknown")
                        print(f"     - {func_name}")
        else:
            print("   ⚠️  No llm_config found!")
    else:
        print("❌ code_analyzer not found")

    # Check user_proxy_executor
    print("\n[5] Checking user_proxy_executor agent...")
    executor = agent_factory.get_agent("user_proxy_executor")
    if executor:
        print(f"✅ Agent type: {type(executor).__name__}")
        print(f"   Name: {executor.name}")

        # Check function_map
        if hasattr(executor, "_function_map"):
            func_map = executor._function_map
            print(f"   Functions registered: {len(func_map) if func_map else 0}")
            if func_map:
                print(f"   Registered functions:")
                for func_name in list(func_map.keys())[:10]:  # Show first 10
                    print(f"     - {func_name}")
        else:
            print("   ⚠️  No _function_map attribute!")
    else:
        print("❌ user_proxy_executor not found")

    # Check function registry
    print("\n[6] Checking function registry...")
    func_registry = manager.function_registry
    print(f"   Total functions in registry: {len(func_registry.functions)}")
    if func_registry.functions:
        print(f"   Sample functions:")
        for func_name in list(func_registry.functions.keys())[:10]:
            print(f"     - {func_name}")

    # Test a simple read_file call
    print("\n[7] Testing read_file function directly...")
    if "read_file" in func_registry.functions:
        read_file_func = func_registry.functions["read_file"]
        print(f"✅ read_file function exists: {read_file_func}")

        try:
            # Try calling it
            test_path = "./README.md"
            print(f"   Attempting to call: read_file(file_path='{test_path}')")
            result = await read_file_func(file_path=test_path)
            if result:
                content = result.get("content", "") if isinstance(result, dict) else str(result)
                preview = content[:200] if content else "No content"
                print(f"✅ Function executed successfully!")
                print(f"   Result preview: {preview}...")
            else:
                print(f"⚠️  Function returned: {result}")
        except Exception as e:
            print(f"❌ Function call failed: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("❌ read_file function not found in registry")

    # Check MCP tool manager
    print("\n[8] Checking MCP Tool Manager...")
    tool_manager = func_registry.tool_manager
    print(f"   Tool manager type: {type(tool_manager).__name__}")

    # Check available tools
    if hasattr(tool_manager, "tools"):
        print(f"   Available MCP tools:")
        for tool_name, tool in tool_manager.tools.items():
            print(f"     - {tool_name}: {type(tool).__name__}")

    print("\n" + "=" * 70)
    print("Diagnostic Complete!")
    print("=" * 70)

    print("\n📊 Summary:")
    print(f"   ✅ Agents created: {len(agents)}")
    print(f"   ✅ Functions registered: {len(func_registry.functions)}")
    print(
        f"   {'✅' if 'read_file' in func_registry.functions else '❌'} read_file function available"
    )

    if executor and hasattr(executor, "_function_map") and executor._function_map:
        print(f"   ✅ Executor has function_map with {len(executor._function_map)} functions")
    else:
        print(f"   ⚠️  Executor function_map issue detected!")

    print("\nIf all checks pass, the issue is likely with:")
    print("1. How the agent formats the function call")
    print("2. The conversation flow/termination")
    print("3. The model's ability to generate correct function calls")


if __name__ == "__main__":
    asyncio.run(main())
