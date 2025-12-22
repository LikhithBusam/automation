#!/usr/bin/env python3
"""Quick test of improved fallback search"""
import asyncio
import sys

sys.path.insert(0, ".")
from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool


async def test():
    tool = CodeBaseBuddyMCPTool(
        server_url="http://localhost:3004",
        config={"scan_paths": ["./src", "./mcp_servers", "./config"]},
    )

    print("=== Test 1: Search for authentication ===")
    result = await tool.semantic_search("how does authentication work")
    print(f"Keywords used: {result.get('keywords_used', [])}")
    print(f"Found {result['results_count']} results:")
    for r in result["results"][:3]:
        preview = r["content_preview"].replace("\n", " ")[:80]
        print(f"  - {r['file_path']} (line {r['start_line']}): {preview}...")

    print()
    print("=== Test 2: Find usages of CircuitBreaker ===")
    result = await tool.find_usages(symbol_name="CircuitBreaker")
    print(f"Found {result['results_count']} usages:")
    for r in result["results"][:5]:
        usage_type = r.get("usage_type", "ref")
        content = r["line_content"][:60]
        print(f"  - [{usage_type}] {r['file_path']} (line {r['line_number']}): {content}...")

    print()
    print("=== Test 3: Search for MCPToolManager ===")
    result = await tool.semantic_search("what is MCPToolManager")
    print(f"Keywords used: {result.get('keywords_used', [])}")
    print(f"Found {result['results_count']} results:")
    for r in result["results"][:3]:
        preview = r["content_preview"].replace("\n", " ")[:80]
        print(f"  - {r['file_path']} (line {r['start_line']}): {preview}...")

    print()
    print("=== Test 4: Search for agents (should find YAML config) ===")
    result = await tool.semantic_search("what agents are available")
    print(f"Keywords used: {result.get('keywords_used', [])}")
    print(f"Found {result['results_count']} results:")
    for r in result["results"][:5]:
        preview = r["content_preview"].replace("\n", " ")[:80]
        print(f"  - {r['file_path']} (line {r['start_line']}): {preview}...")

    print()
    print("=== Test 5: Search for code_analyzer (specific agent) ===")
    result = await tool.semantic_search("code_analyzer")
    print(f"Keywords used: {result.get('keywords_used', [])}")
    print(f"Found {result['results_count']} results:")
    for r in result["results"][:5]:
        preview = r["content_preview"].replace("\n", " ")[:80]
        print(f"  - {r['file_path']} (line {r['start_line']}): {preview}...")


if __name__ == "__main__":
    asyncio.run(test())
