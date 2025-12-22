#!/usr/bin/env python3
"""Debug scan paths"""
import asyncio
import sys

sys.path.insert(0, ".")
from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool
from pathlib import Path


async def test():
    tool = CodeBaseBuddyMCPTool(
        server_url="http://localhost:3004",
        config={"scan_paths": ["./src", "./mcp_servers", "./config"]},
    )
    print("Scan paths:", tool.scan_paths)

    # Check what files are found
    for sp in tool.scan_paths:
        p = Path(sp)
        print(f"\n{sp}:")
        for pattern in ["*.py", "*.yaml", "*.yml"]:
            files = list(p.rglob(pattern))[:3]
            print(
                f"  {pattern}: {len(list(p.rglob(pattern)))} files, first 3: {[str(f) for f in files]}"
            )

    # Now test actual search
    print('\n--- Testing search for "agents" ---')
    result = await tool.semantic_search("agents")
    print(f'Keywords: {result.get("keywords_used", [])}')
    print(f'Found: {result["results_count"]} results')
    for r in result["results"]:
        print(f'  - {r["file_path"]} (line {r["start_line"]}, score={r["similarity_score"]:.2f})')


asyncio.run(test())
