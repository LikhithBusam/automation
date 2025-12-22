"""
Test script to verify GroupChat backward compatibility fix
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def test_groupchat_compatibility():
    """Test that GroupChat creation works with feature detection"""
    print("=" * 70)
    print("Testing GroupChat Backward Compatibility Fix")
    print("=" * 70)
    print()

    # Test 1: Check AutoGen import
    print("Test 1: Checking AutoGen availability...")
    try:
        from autogen import AssistantAgent, GroupChat

        print("  [OK] AutoGen imported successfully")
    except ImportError as e:
        print(f"  [FAIL] AutoGen not available: {e}")
        return False

    # Test 2: Check parameter detection
    print("\nTest 2: Checking parameter detection...")
    import inspect

    params = inspect.signature(GroupChat.__init__).parameters

    print(f"  GroupChat parameters: {list(params.keys())}")
    print(
        f"  - allow_repeat_speaker: {'SUPPORTED' if 'allow_repeat_speaker' in params else 'NOT SUPPORTED'}"
    )
    print(
        f"  - speaker_selection_method: {'SUPPORTED' if 'speaker_selection_method' in params else 'NOT SUPPORTED'}"
    )

    # Test 3: Create simple agents
    print("\nTest 3: Creating test agents...")
    try:
        agent1 = AssistantAgent(
            name="agent1",
            system_message="Test agent 1",
            llm_config=False,  # Disable LLM for testing
        )
        agent2 = AssistantAgent(name="agent2", system_message="Test agent 2", llm_config=False)
        print("  [OK] Test agents created")
    except Exception as e:
        print(f"  [FAIL] Could not create agents: {e}")
        return False

    # Test 4: Try creating GroupChat with our compatibility approach
    print("\nTest 4: Creating GroupChat with feature detection...")
    try:
        # Build kwargs dynamically (same as our fix)
        groupchat_kwargs = {
            "agents": [agent1, agent2],
            "messages": [],
            "max_round": 10,
        }

        # Add optional parameters only if supported
        if "allow_repeat_speaker" in params:
            groupchat_kwargs["allow_repeat_speaker"] = False
            print("  - Using allow_repeat_speaker=False")
        else:
            print("  - Skipping allow_repeat_speaker (not supported)")

        if "speaker_selection_method" in params:
            groupchat_kwargs["speaker_selection_method"] = "auto"
            print("  - Using speaker_selection_method=auto")
        else:
            print("  - Skipping speaker_selection_method (not supported)")

        # Create GroupChat
        groupchat = GroupChat(**groupchat_kwargs)
        print("  [OK] GroupChat created successfully!")

    except TypeError as e:
        print(f"  [FAIL] GroupChat creation failed: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False

    # Test 5: Test GroupChatFactory integration
    print("\nTest 5: Testing GroupChatFactory...")
    try:
        from src.autogen_adapters.groupchat_factory import GroupChatFactory

        factory = GroupChatFactory("config/autogen_workflows.yaml")
        print(
            f"  [OK] GroupChatFactory initialized with {len(factory.groupchat_configs)} chat configs"
        )

    except Exception as e:
        print(f"  [FAIL] GroupChatFactory error: {e}")
        return False

    # All tests passed
    print("\n" + "=" * 70)
    print("[SUCCESS] All compatibility tests passed!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Run 'python main.py' to start the application")
    print("2. Try a multi-agent workflow:")
    print("   >>> run code_analysis code_path=./src")
    print()

    return True


if __name__ == "__main__":
    success = test_groupchat_compatibility()
    sys.exit(0 if success else 1)
