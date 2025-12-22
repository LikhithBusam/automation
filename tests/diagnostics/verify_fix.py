"""
Verification script to confirm all bugs are fixed
Run this to verify the system is working correctly
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_test(name, passed):
    status = "[OK]  " if passed else "[FAIL]"
    symbol = "+" if passed else "X"
    print(f"  {symbol} {status} {name}")
    return passed


all_passed = True

print_header("VERIFICATION: Bug Fixes Applied")

# Test 1: Environment variables
print("\n1. Environment Variables")
groq_key = os.getenv("GROQ_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")
all_passed &= print_test("GROQ_API_KEY loaded", bool(groq_key))
all_passed &= print_test("GEMINI_API_KEY loaded", bool(gemini_key))

# Test 2: Groq models work
print("\n2. Groq Model Availability")
try:
    from openai import OpenAI

    client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")

    # Test routing model
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant", messages=[{"role": "user", "content": "Hi"}], max_tokens=5
        )
        all_passed &= print_test("llama-3.1-8b-instant (routing model)", True)
    except Exception as e:
        all_passed &= print_test(f"llama-3.1-8b-instant (routing model): {e}", False)

    # Test research model
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        all_passed &= print_test("llama-3.3-70b-versatile (research model)", True)
    except Exception as e:
        all_passed &= print_test(f"llama-3.3-70b-versatile (research model): {e}", False)

except Exception as e:
    all_passed &= print_test(f"Groq API connection: {e}", False)

# Test 3: AutoGen imports
print("\n3. AutoGen Imports")
try:
    from autogen import AssistantAgent, GroupChatManager, UserProxyAgent

    all_passed &= print_test("Core AutoGen classes", True)
except Exception as e:
    all_passed &= print_test(f"Core AutoGen classes: {e}", False)

# Test 4: Agent Factory
print("\n4. Agent Factory")
try:
    from src.autogen_adapters.agent_factory import AutoGenAgentFactory

    factory = AutoGenAgentFactory("config/autogen_agents.yaml")
    all_passed &= print_test("AgentFactory initialization", True)
    all_passed &= print_test(
        f"Loaded {len(factory.agent_configs)} agent configs", len(factory.agent_configs) == 8
    )
    all_passed &= print_test(
        f"Loaded {len(factory.llm_configs)} LLM configs", len(factory.llm_configs) == 6
    )

    # Try creating an agent with Groq
    try:
        research_agent = factory.create_agent("research_agent")
        all_passed &= print_test("Created research_agent (Groq)", True)
    except Exception as e:
        all_passed &= print_test(f"Created research_agent (Groq): {e}", False)

    # Try creating an agent with Gemini
    try:
        code_analyzer = factory.create_agent("code_analyzer")
        all_passed &= print_test("Created code_analyzer (Gemini)", True)
    except Exception as e:
        all_passed &= print_test(f"Created code_analyzer (Gemini): {e}", False)

except Exception as e:
    all_passed &= print_test(f"AgentFactory: {e}", False)
    import traceback

    traceback.print_exc()

# Test 5: GroupChat Factory
print("\n5. GroupChat Factory")
try:
    from src.autogen_adapters.groupchat_factory import GroupChatFactory

    gcf = GroupChatFactory("config/autogen_groupchats.yaml")
    all_passed &= print_test("GroupChatFactory initialization", True)
    all_passed &= print_test(
        f"Loaded {len(gcf.groupchat_configs)} chat configs", len(gcf.groupchat_configs) > 0
    )

except Exception as e:
    all_passed &= print_test(f"GroupChatFactory: {e}", False)

# Test 6: Configuration files
print("\n6. Configuration Files")
configs = [
    "config/autogen_agents.yaml",
    "config/autogen_workflows.yaml",
    "config/autogen_groupchats.yaml",
    ".env",
]
for config in configs:
    exists = Path(config).exists()
    all_passed &= print_test(f"{config} exists", exists)

# Final summary
print_header("VERIFICATION SUMMARY")
if all_passed:
    print("\n  [SUCCESS] ALL TESTS PASSED!")
    print("\n  The system is ready to use. You can now run:")
    print("     python main.py")
    print()
    sys.exit(0)
else:
    print("\n  [ERROR] SOME TESTS FAILED")
    print("\n  Please review the failures above and ensure:")
    print("  1. All dependencies are installed (pip install -r requirements.txt)")
    print("  2. Environment variables are set in .env file")
    print("  3. Configuration files are present in config/ directory")
    print()
    sys.exit(1)
