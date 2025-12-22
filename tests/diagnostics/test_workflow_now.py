"""
Test workflow execution RIGHT NOW to confirm everything works
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from src.autogen_adapters.conversation_manager import create_conversation_manager


async def test_workflow():
    """Test the workflow"""
    print("\n" + "=" * 80)
    print("  TESTING WORKFLOW EXECUTION")
    print("=" * 80 + "\n")

    # Create manager
    print("[1/3] Creating conversation manager...")
    try:
        manager = await create_conversation_manager()
        print("[OK] Manager created\n")
    except Exception as e:
        print(f"[ERROR] Failed to create manager: {e}")
        return False

    # Check agents
    print("[2/3] Checking agent registry...")
    agents = manager.agent_factory.list_agents()
    print(f"[OK] {len(agents)} agents registered: {agents}\n")

    # Try to execute workflow
    print("[3/3] Executing quick_code_review workflow...")
    try:
        result = await manager.execute_workflow(
            "quick_code_review",
            variables={"code_path": "./main.py", "focus_areas": "error handling"},
        )

        print(f"\n[RESULT] Status: {result.status}")
        print(f"         Summary: {result.summary}")
        print(f"         Duration: {result.duration_seconds:.2f}s")
        print(f"         Tasks completed: {result.tasks_completed}")
        print(f"         Tasks failed: {result.tasks_failed}")

        if result.error:
            print(f"         Error: {result.error}")

        return result.status == "success"

    except Exception as e:
        print(f"\n[ERROR] Workflow execution failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_workflow())

    print("\n" + "=" * 80)
    if success:
        print("  [SUCCESS] Workflow executed successfully!")
    else:
        print("  [FAILED] Workflow execution failed")
    print("=" * 80 + "\n")
