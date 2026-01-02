#!/usr/bin/env python3
"""
Test script to verify the api_base fix
"""
import asyncio
import sys

from src.autogen_adapters.conversation_manager import create_conversation_manager


async def test_workflow():
    """Test the quick_code_review workflow"""
    print("Testing AutoGen api_base fix...")
    print("-" * 50)

    try:
        # Initialize conversation manager
        print("1. Initializing conversation manager...")
        manager = await create_conversation_manager()
        print("   [OK] Manager initialized successfully")

        # List workflows
        print("\n2. Listing available workflows...")
        workflows = manager.list_workflows()
        print(f"   [OK] Found {len(workflows)} workflows")

        # Execute quick_code_review
        print("\n3. Testing quick_code_review workflow...")
        result = await manager.execute_workflow(
            "quick_code_review", {"code_path": "./main.py", "focus_areas": "structure, imports"}
        )

        print(f"\n4. Workflow execution result:")
        print(f"   Status: {result.status}")
        print(f"   Duration: {result.duration_seconds:.2f}s")
        print(f"   Tasks completed: {result.tasks_completed}")
        print(f"   Tasks failed: {result.tasks_failed}")

        if result.error:
            print(f"   Error: {result.error}")
            return 1

        print("\n" + "=" * 50)
        print("SUCCESS! The api_base fix is working correctly.")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_workflow())
    sys.exit(exit_code)
