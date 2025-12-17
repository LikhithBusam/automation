#!/usr/bin/env python3
"""
Groq Configuration Diagnostic Script
Tests that Groq API is properly configured and working
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def check_env_vars():
    """Check environment variables"""
    print_section("1. Environment Variables")

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print(f"[OK] GROQ_API_KEY: {groq_key[:20]}... (length: {len(groq_key)})")
        if not groq_key.startswith("gsk_"):
            print("  [WARN] Warning: Groq API keys typically start with 'gsk_'")
    else:
        print("[ERROR] GROQ_API_KEY: NOT SET")
        return False

    # Check other keys
    github_token = os.getenv("GITHUB_TOKEN")
    print(f"{'[OK]' if github_token else '[WARN]'} GITHUB_TOKEN: {'SET' if github_token else 'NOT SET'}")

    return True

def check_config_files():
    """Check configuration files"""
    print_section("2. Configuration Files")

    import yaml

    # Check autogen_agents.yaml
    try:
        with open("config/autogen_agents.yaml", 'r') as f:
            config = yaml.safe_load(f)

        llm_configs = config.get("llm_configs", {})
        print(f"[OK] Found {len(llm_configs)} LLM configurations")

        # Check each config
        for name, cfg in llm_configs.items():
            base_url = cfg.get("base_url", "")
            model = cfg.get("model", "")
            api_type = cfg.get("api_type", "")

            if "groq.com" in base_url:
                print(f"  [OK] {name}: {model} (Groq API)")
            else:
                print(f"  [WARN] {name}: {model} (Not using Groq: {base_url})")

        return True
    except Exception as e:
        print(f"[ERROR] Error reading config: {e}")
        return False

def test_groq_api():
    """Test Groq API directly"""
    print_section("3. Groq API Connection Test")

    try:
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("[ERROR] GROQ_API_KEY not set")
            return False

        print("  Testing connection to Groq API...")
        client = Groq(api_key=api_key)

        # Test with a simple completion
        print("  Sending test request...")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Respond with exactly: 'Groq API is working!'"
                }
            ],
            model="llama-3.1-8b-instant",
            max_tokens=50,
        )

        response = chat_completion.choices[0].message.content
        print(f"  [OK] Response: {response}")
        print(f"  [OK] Groq API is working correctly!")

        return True

    except ImportError:
        print("  [WARN] Groq library not installed. Install with: pip install groq")
        print("  Note: This doesn't prevent AutoGen from working")
        return None
    except Exception as e:
        print(f"  [ERROR] Groq API test failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        return False

def test_autogen_config():
    """Test AutoGen configuration"""
    print_section("4. AutoGen Agent Factory Test")

    try:
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory

        print("  Initializing AutoGen Agent Factory...")
        factory = AutoGenAgentFactory()

        print(f"  [OK] Loaded {len(factory.llm_configs)} LLM configs")
        print(f"  [OK] Loaded {len(factory.agent_configs)} agent configs")

        # Check if Groq configs are present
        for name, cfg in factory.llm_configs.items():
            base_url = cfg.get("base_url", "")
            if "groq.com" in base_url:
                print(f"  [OK] {name}: Using Groq API")

        return True

    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_conversation_manager():
    """Test Conversation Manager initialization"""
    print_section("5. Conversation Manager Test")

    try:
        from src.autogen_adapters.conversation_manager import create_conversation_manager

        print("  Initializing Conversation Manager (this may take 30-60 seconds)...")
        manager = await create_conversation_manager()

        print(f"  [OK] Conversation Manager initialized")

        workflows = manager.list_workflows()
        print(f"  [OK] Loaded {len(workflows)} workflows")

        agents = manager.agent_factory.list_agents()
        print(f"  [OK] Created {len(agents)} agents")

        return True

    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_summary(results):
    """Print test summary"""
    print_section("Test Summary")

    total = len(results)
    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False)
    skipped = sum(1 for r in results if r is None)

    print(f"Total Tests: {total}")
    print(f"[OK] Passed: {passed}")
    print(f"[ERROR] Failed: {failed}")
    print(f"[SKIP] Skipped: {skipped}")
    print()

    if failed == 0:
        print("SUCCESS: All tests passed! Your Groq configuration is correct.")
        print()
        print("Next steps:")
        print("  1. Run the application: python main.py")
        print("  2. Try a workflow: run quick_code_review code_path=./main.py")
        return 0
    else:
        print("WARNING: Some tests failed. Check the errors above.")
        print()
        print("Common fixes:")
        print("  1. Verify GROQ_API_KEY is correct")
        print("  2. Check API key at: https://console.groq.com/keys")
        print("  3. Ensure MCP servers are running: python start_mcp_servers.py")
        return 1

async def main():
    """Run all diagnostic tests"""
    print()
    print("=" * 70)
    print("  GROQ API CONFIGURATION DIAGNOSTIC")
    print("  This script verifies your Groq API configuration is correct")
    print("=" * 70)

    results = []

    # Run tests
    results.append(check_env_vars())
    results.append(check_config_files())
    results.append(test_groq_api())
    results.append(test_autogen_config())
    results.append(await test_conversation_manager())

    # Print summary
    exit_code = print_summary(results)

    return exit_code

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
