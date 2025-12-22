"""
Test script to verify Groq API configuration fix
This tests that base_url is properly included in the AutoGen config
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.autogen_adapters.agent_factory import AutoGenAgentFactory


def test_llm_config_has_base_url():
    """Test that LLM config includes base_url for Groq"""
    print("=" * 80)
    print("Testing Groq API Configuration Fix")
    print("=" * 80)

    # Create agent factory
    print("\n1. Creating AutoGenAgentFactory...")
    factory = AutoGenAgentFactory()

    # Check environment
    groq_key = os.getenv("GROQ_API_KEY")
    print(f"\n2. Environment Check:")
    print(f"   GROQ_API_KEY: {'[OK] Set' if groq_key else '[FAIL] NOT SET'}")
    if groq_key:
        print(f"   Key prefix: {groq_key[:10]}...")

    # Test LLM config creation
    print(f"\n3. Testing LLM Config Creation:")
    llm_config = factory._create_llm_config("code_analysis_config")

    print(f"\n4. Generated LLM Config:")
    print(f"   Config structure: {llm_config.keys()}")

    if "config_list" in llm_config:
        config_list = llm_config["config_list"]
        print(f"   config_list length: {len(config_list)}")

        if len(config_list) > 0:
            config_entry = config_list[0]
            print(f"\n5. Config Entry Details:")
            print(f"   model: {config_entry.get('model')}")
            print(
                f"   api_key: {'***' + config_entry.get('api_key', '')[-8:] if config_entry.get('api_key') else 'NOT SET'}"
            )

            # THE CRITICAL CHECK
            base_url = config_entry.get("base_url")
            has_base_url = "base_url" in config_entry

            print(f"   base_url present: {has_base_url}")
            if has_base_url:
                print(f"   base_url value: {base_url}")

            print(f"\n6. Validation Results:")
            all_passed = True

            # Check 1: base_url must be present
            if has_base_url:
                print(f"   [PASS] base_url is included in config")
            else:
                print(f"   [FAIL] base_url is MISSING from config")
                all_passed = False

            # Check 2: base_url must be Groq's endpoint
            if base_url == "https://api.groq.com/openai/v1":
                print(f"   [PASS] base_url points to Groq")
            else:
                print(f"   [FAIL] base_url is incorrect (expected Groq endpoint)")
                all_passed = False

            # Check 3: model should use LiteLLM format
            if config_entry.get("model", "").startswith("groq/"):
                print(f"   [PASS] Model uses LiteLLM format (groq/...)")
            else:
                print(f"   [WARNING] Model doesn't use LiteLLM format")

            # Check 4: API key is set
            if config_entry.get("api_key"):
                print(f"   [PASS] API key is set")
            else:
                print(f"   [FAIL] API key is missing")
                all_passed = False

            print(f"\n{'='*80}")
            if all_passed:
                print("[PASS] ALL TESTS PASSED - Groq API configuration is correct!")
                print("  The fix successfully includes base_url in the AutoGen config.")
                print("  Agents will now use Groq's endpoint instead of OpenAI's.")
            else:
                print("[FAIL] TESTS FAILED - Configuration issues detected")
                print("  Please review the errors above.")
            print(f"{'='*80}\n")

            return all_passed
        else:
            print("   [FAIL] config_list is empty")
            return False
    else:
        print("   [FAIL] config_list not in llm_config")
        return False


if __name__ == "__main__":
    try:
        success = test_llm_config_has_base_url()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
