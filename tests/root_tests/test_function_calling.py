#!/usr/bin/env python3
"""
Test script to verify function calling fix
"""
import asyncio
import logging
from src.autogen_adapters.conversation_manager import create_conversation_manager

logging.basicConfig(level=logging.INFO)


async def main():
    print("=== Testing Function Calling Fix ===\n")

    # Initialize system
    print("Initializing AutoGen system...")
    manager = await create_conversation_manager()
    print("[OK] System initialized\n")

    # Check function registration
    print("Checking function registration...")
    user_proxy = manager.agent_factory.get_agent("user_proxy_executor")
    code_analyzer = manager.agent_factory.get_agent("code_analyzer")

    print(f"[OK] UserProxyAgent: {user_proxy.name}")
    print(f"[OK] CodeAnalyzer: {code_analyzer.name}\n")

    # Check if functions are registered
    if hasattr(user_proxy, "_function_map"):
        print(
            f"[OK] UserProxyAgent has {len(user_proxy._function_map)} functions registered for execution"
        )
        print(f"  Functions: {list(user_proxy._function_map.keys())[:5]}...\n")
    else:
        print("[ERROR] UserProxyAgent has NO functions registered\n")

    # Run quick code review
    print("Running quick_code_review workflow...")
    result = await manager.execute_workflow(
        "quick_code_review",
        variables={"code_path": "./main.py", "focus_areas": "error handling, security"},
    )

    print(f"\n=== Results ===")
    print(f"Status: {result.status}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Messages: {len(result.messages)}")
    print(f"\nSummary:\n{result.summary}")


if __name__ == "__main__":
    asyncio.run(main())
