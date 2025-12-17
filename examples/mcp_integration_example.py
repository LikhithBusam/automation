"""
MCP Integration Examples
Demonstrates how to use MCP servers with CrewAI agents
"""

import asyncio
import yaml
from pathlib import Path
from src.mcp.tool_manager_enhanced import MCPToolManager as EnhancedMCPToolManager
from src.mcp.crewai_tools import get_tools_for_agent, get_all_crewai_tools
from src.mcp.mcp_setup import MCPServerSetup


async def example_1_basic_mcp_operations():
    """Example 1: Basic MCP operations without CrewAI"""
    print("=" * 80)
    print("Example 1: Basic MCP Operations")
    print("=" * 80)

    # Load config
    with open("./config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialize tool manager
    tool_manager = EnhancedMCPToolManager(config)

    print("\n1. Filesystem Operations")
    print("-" * 80)

    # Read a file
    try:
        result = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "./README.md"}
        )
        print(f"✓ Read README.md ({len(result.get('content', ''))} characters)")
    except Exception as e:
        print(f"✗ Error reading file: {e}")

    # List directory
    try:
        result = await tool_manager.execute(
            "filesystem",
            "list_directory",
            {"path": "./src"}
        )
        print(f"✓ Listed ./src ({len(result.get('files', []))} files)")
    except Exception as e:
        print(f"✗ Error listing directory: {e}")

    print("\n2. GitHub Operations")
    print("-" * 80)

    # Search code (example - may require API access)
    try:
        result = await tool_manager.execute(
            "github",
            "search_code",
            {"query": "language:python async def", "per_page": 3}
        )
        print(f"✓ Found {result.get('total_count', 0)} code results")
    except Exception as e:
        print(f"✗ GitHub search failed: {e}")

    print("\n3. Memory Operations")
    print("-" * 80)

    # Store in memory
    try:
        result = await tool_manager.execute(
            "memory",
            "store_context",
            {
                "content": "FastAPI is recommended for building high-performance REST APIs",
                "type": "pattern",
                "metadata": {"tags": ["python", "api", "best-practice"]}
            }
        )
        print(f"✓ Stored pattern in memory (ID: {result.get('id')})")
    except Exception as e:
        print(f"✗ Memory store failed: {e}")

    # Retrieve from memory
    try:
        result = await tool_manager.execute(
            "memory",
            "retrieve_context",
            {"query": "API best practices"}
        )
        print(f"✓ Retrieved {len(result.get('results', []))} memories")
    except Exception as e:
        print(f"✗ Memory retrieve failed: {e}")

    print("\n4. Cache Statistics")
    print("-" * 80)
    stats = await tool_manager.get_cache_stats()
    for tool_name, tool_stats in stats.items():
        print(f"{tool_name}: {tool_stats}")


async def example_2_crewai_tool_integration():
    """Example 2: Using MCP tools with CrewAI agents"""
    print("\n" + "=" * 80)
    print("Example 2: CrewAI Tool Integration")
    print("=" * 80)

    # Load config
    with open("./config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialize tool manager
    tool_manager = EnhancedMCPToolManager(config)

    # Get all available CrewAI tools
    all_tools = get_all_crewai_tools(tool_manager)

    print("\nAvailable Tool Categories:")
    for category, tools in all_tools.items():
        print(f"\n{category.upper()} ({len(tools)} tools):")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description[:60]}...")

    # Get tools for specific agent
    print("\n" + "-" * 80)
    print("Code Analyzer Agent Tools")
    print("-" * 80)

    analyzer_tools = get_tools_for_agent(tool_manager, ["github", "filesystem"])

    print(f"\nCode Analyzer has {len(analyzer_tools)} tools:")
    for tool in analyzer_tools:
        print(f"  • {tool.name}")
        for param_name, param_desc in tool.parameters.items():
            print(f"      - {param_name}: {param_desc}")


async def example_3_agent_with_mcp_tools():
    """Example 3: Creating an agent with MCP tools"""
    print("\n" + "=" * 80)
    print("Example 3: Agent with MCP Tools")
    print("=" * 80)

    from src.models.model_factory import ModelFactory
    from src.memory.memory_manager import MemoryManager
    from src.agents import create_code_analyzer_agent

    # Load config
    with open("./config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialize infrastructure
    model_factory = ModelFactory(config)
    tool_manager = EnhancedMCPToolManager(config)
    memory_manager = MemoryManager(config.get("memory", {}))

    # Create agent with MCP tools
    agent = create_code_analyzer_agent(
        llm=model_factory.get_model("code_analyzer"),
        tool_manager=tool_manager,
        memory_manager=memory_manager
    )

    print("\nCode Analyzer Agent Created")
    print(f"Agent: {agent.config.name}")
    print(f"Role: {agent.config.role}")
    print(f"Tools: {agent.config.tools}")

    # Example task using MCP tools
    print("\n" + "-" * 80)
    print("Executing Task: Analyze a file")
    print("-" * 80)

    try:
        result = await agent.execute_task({
            "type": "analyze_code",
            "file_path": "./src/agents/base_agent.py"
        })
        print(f"\nAnalysis Result:")
        print(f"Status: {result.get('status')}")
        print(f"Issues Found: {result.get('output', {}).get('issues_found', 'N/A')}")
    except Exception as e:
        print(f"Error executing task: {e}")


async def example_4_rate_limiting_and_caching():
    """Example 4: Demonstrating rate limiting and caching"""
    print("\n" + "=" * 80)
    print("Example 4: Rate Limiting and Caching")
    print("=" * 80)

    # Load config
    with open("./config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Modify config for demonstration
    config["mcp_servers"]["filesystem"]["rate_limit_minute"] = 5
    config["mcp_servers"]["filesystem"]["cache_ttl"] = 60

    tool_manager = EnhancedMCPToolManager(config)

    print("\n1. Testing Cache (reading same file multiple times)")
    print("-" * 80)

    import time

    # First read (cache miss)
    start = time.time()
    try:
        result1 = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "./README.md"}
        )
        elapsed1 = time.time() - start
        print(f"✓ First read: {elapsed1:.3f}s (cache miss)")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Second read (cache hit)
    start = time.time()
    try:
        result2 = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "./README.md"}
        )
        elapsed2 = time.time() - start
        print(f"✓ Second read: {elapsed2:.3f}s (cache hit - {(elapsed1/elapsed2):.1f}x faster)")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n2. Testing Rate Limiting (making 6 rapid requests with limit of 5/min)")
    print("-" * 80)

    for i in range(6):
        try:
            result = await tool_manager.execute(
                "filesystem",
                "list_directory",
                {"path": f"./src"}
            )
            print(f"✓ Request {i+1}: Success")
        except Exception as e:
            print(f"✗ Request {i+1}: Rate limited - {e}")

    # Show cache stats
    print("\n3. Cache Statistics")
    print("-" * 80)
    stats = await tool_manager.get_cache_stats()
    for tool_name, tool_stats in stats.items():
        print(f"{tool_name}: {tool_stats}")


async def example_5_security_validation():
    """Example 5: Security validation"""
    print("\n" + "=" * 80)
    print("Example 5: Security Validation")
    print("=" * 80)

    # Load config
    with open("./config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Add security constraints
    config["mcp_servers"]["filesystem"]["allowed_paths"] = [
        "./workspace",
        "./projects",
        "./src"
    ]

    tool_manager = EnhancedMCPToolManager(config)

    print("\n1. Testing Path Security")
    print("-" * 80)

    # Valid path (should succeed)
    try:
        result = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "./src/agents/base_agent.py"}
        )
        print("✓ Allowed path: ./src/agents/base_agent.py")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Invalid path (should fail)
    try:
        result = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "/etc/passwd"}  # Blocked
        )
        print("✗ SECURITY ISSUE: /etc/passwd was accessible!")
    except Exception as e:
        print(f"✓ Blocked unsafe path: /etc/passwd - {e}")

    # Directory traversal attempt (should fail)
    try:
        result = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "../../../etc/passwd"}
        )
        print("✗ SECURITY ISSUE: Directory traversal succeeded!")
    except Exception as e:
        print(f"✓ Blocked directory traversal - {e}")


async def example_6_mcp_setup_validation():
    """Example 6: MCP server setup validation"""
    print("\n" + "=" * 80)
    print("Example 6: MCP Server Setup Validation")
    print("=" * 80)

    # Load config
    with open("./config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Run setup validation
    setup = MCPServerSetup(config)

    print("\nValidating MCP Server Configuration...")
    results = await setup.validate_all_servers()

    # Display results
    for server_name, result in results.items():
        print(f"\n{server_name.upper()}")
        print("-" * 80)
        print(f"Configured: {'✓' if result['configured'] else '✗'}")
        print(f"Reachable: {'✓' if result['reachable'] else '✗'}")
        print(f"Authenticated: {'✓' if result['authenticated'] else '✗'}")

        if result['issues']:
            print("\nIssues:")
            for issue in result['issues']:
                print(f"  • {issue}")

    # Generate setup instructions
    print("\n" + "=" * 80)
    print("Generating Setup Instructions...")
    print("=" * 80)

    instructions = setup.generate_setup_instructions(results)
    print(instructions)


async def main():
    """Run all examples"""
    print("MCP INTEGRATION EXAMPLES")
    print("=" * 80)
    print()

    # Run examples
    try:
        await example_1_basic_mcp_operations()
    except Exception as e:
        print(f"Example 1 error: {e}")

    try:
        await example_2_crewai_tool_integration()
    except Exception as e:
        print(f"Example 2 error: {e}")

    try:
        await example_3_agent_with_mcp_tools()
    except Exception as e:
        print(f"Example 3 error: {e}")

    try:
        await example_4_rate_limiting_and_caching()
    except Exception as e:
        print(f"Example 4 error: {e}")

    try:
        await example_5_security_validation()
    except Exception as e:
        print(f"Example 5 error: {e}")

    try:
        await example_6_mcp_setup_validation()
    except Exception as e:
        print(f"Example 6 error: {e}")

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
