#!/usr/bin/env python3
"""
CodeBaseBuddy Example - Demonstrating How to Use It

Shows practical examples of asking questions about your codebase
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool


async def main():
    """Run examples"""

    # Initialize CodeBaseBuddy
    tool = CodeBaseBuddyMCPTool(
        server_url="http://localhost:3004",
        config={"scan_paths": ["./src", "./mcp_servers", "./config"]},
    )

    print("\n")
    print("=" * 80)
    print("CodeBaseBuddy Examples - How to Ask Questions About Your Code")
    print("=" * 80)
    print()

    # Example 1: Semantic Search
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Search for 'What is ConversationManager?'")
    print("=" * 80)

    result = await tool.semantic_search(
        query="What is ConversationManager and what does it do?", top_k=3
    )

    print(f"\nFound {result['results_count']} results:\n")
    for i, res in enumerate(result["results"], 1):
        print(f"{i}. {res['file_path']}")
        print(f"   Line {res['start_line']}: {res['content_preview'][:150]}")
        print()

    # Example 2: Find Usages
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Search for 'Where is MCPToolManager used?'")
    print("=" * 80)

    result = await tool.find_usages(symbol_name="MCPToolManager", top_k=3)

    print(f"\nFound {result['results_count']} usages:\n")
    for i, res in enumerate(result["results"], 1):
        print(f"{i}. {res['file_path']}")
        print(f"   Line {res['line_number']}: {res['line_content'][:100]}")
        print()

    # Example 3: Get Code Context
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Get context around line in base_tool.py")
    print("=" * 80)

    result = await tool.get_code_context(
        file_path="./src/mcp/base_tool.py", line_number=50, context_lines=3
    )

    if result.get("success"):
        print(f"\nRetrieved lines {result['start_line']}-{result['end_line']}:\n")
        print(result["context"][:500])
        print()
    else:
        print(f"Error: {result.get('error')}")

    # Example 4: Find Similar Code
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Find similar async function patterns")
    print("=" * 80)

    result = await tool.find_similar_code(
        code_snippet="async def execute(self, operation: str):", top_k=2
    )

    print(f"\nFound {result['results_count']} similar patterns:\n")
    for i, res in enumerate(result["results"], 1):
        print(f"{i}. {res['file_path']}")
        print(f"   Similarity Score: {res['similarity_score']:.2%}")
        print()

    # Example 5: Get Index Stats
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Check index statistics")
    print("=" * 80)

    result = await tool.get_index_stats()

    if result.get("success"):
        stats = result.get("stats", {})
        print(f"\nIndex Statistics:")
        print(f"   Files: {stats.get('files_indexed', 0)}")
        print(f"   Functions: {stats.get('functions_indexed', 0)}")
        print(f"   Classes: {stats.get('classes_indexed', 0)}")
        print(f"   Mode: {stats.get('mode', 'N/A')}")
        print()

    print("\n" + "=" * 80)
    print("EXAMPLES COMPLETE")
    print("=" * 80)
    print("\nWhat You Can Do With CodeBaseBuddy:\n")
    print("1. Search by natural language:")
    print("   await tool.semantic_search('How does authentication work?')\n")

    print("2. Find where symbols are used:")
    print("   await tool.find_usages('CircuitBreaker')\n")

    print("3. Read code with context:")
    print("   await tool.get_code_context('./src/file.py', 100)\n")

    print("4. Find similar code patterns:")
    print("   await tool.find_similar_code('async def foo():')\n")

    print("5. Check what's indexed:")
    print("   await tool.get_index_stats()\n")

    print("6. Build or rebuild index:")
    print("   await tool.build_index('./src', ['.py'], rebuild=True)\n")

    print("Try the interactive mode:")
    print("   python scripts/codebasebuddy_interactive.py\n")


if __name__ == "__main__":
    asyncio.run(main())
