#!/usr/bin/env python3
"""
Diagnose Groq API Issue with AutoGen
Tests the actual API call to identify where the validation error occurs
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("  GROQ API DIAGNOSTIC - Finding the 'Incorrect API key' error")
print("=" * 70)

# Step 1: Verify API key is loaded
print("\n[Step 1] Checking environment variables...")
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    print(f"  [OK] GROQ_API_KEY loaded: {groq_key[:20]}...")
    print(
        f"  [OK] Key format: {'Correct (gsk_*)' if groq_key.startswith('gsk_') else 'INCORRECT - should start with gsk_'}"
    )
else:
    print("  [ERROR] GROQ_API_KEY not found in environment")
    sys.exit(1)

# Step 2: Test direct Groq API call
print("\n[Step 2] Testing direct Groq API call...")
try:
    from groq import Groq

    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Say 'hello' in one word"}],
        model="llama-3.1-8b-instant",
        max_tokens=10,
    )
    print(f"  [OK] Direct Groq API works!")
    print(f"  Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"  [ERROR] Direct Groq API failed: {e}")
    print("  This means your GROQ_API_KEY is invalid or expired")
    print("  Get a new key at: https://console.groq.com/keys")
    sys.exit(1)

# Step 3: Test AutoGen agent creation
print("\n[Step 3] Testing AutoGen agent creation...")
try:
    from autogen import AssistantAgent

    llm_config = {
        "config_list": [
            {
                "model": "llama-3.1-8b-instant",
                "api_key": groq_key,
                "base_url": "https://api.groq.com/openai/v1",
            }
        ],
        "temperature": 0.3,
        "max_tokens": 100,
    }

    agent = AssistantAgent(
        name="TestAgent", llm_config=llm_config, system_message="You are a test agent."
    )
    print(f"  [OK] AutoGen agent created successfully")

except Exception as e:
    print(f"  [ERROR] AutoGen agent creation failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Step 4: Test agent conversation (this is where the error likely occurs)
print("\n[Step 4] Testing agent conversation (actual API call)...")
try:
    from autogen import UserProxyAgent

    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
        code_execution_config=False,
    )

    print("  Sending test message to agent...")
    user_proxy.initiate_chat(agent, message="Say 'hello' in one word and then TERMINATE")

    print(f"  [OK] Conversation successful!")

except Exception as e:
    print(f"  [ERROR] Conversation failed: {type(e).__name__}: {e}")
    print("\n  This is where your 'Incorrect API key' error occurs!")
    print("\n  Error Analysis:")
    error_str = str(e)

    if "Incorrect API key" in error_str:
        print("  - AutoGen is validating the API key format")
        print("  - It expects OpenAI format (sk-*) but got Groq format (gsk-*)")
        print("\n  SOLUTION:")
        print("  The issue is that AutoGen's OpenAI client is validating the key")
        print("  before sending the request. We need to bypass this validation.")

    if "platform.openai.com" in error_str:
        print("  - AutoGen is using OpenAI client instead of generic OpenAI-compatible client")
        print("\n  SOLUTION:")
        print("  Need to configure AutoGen to use the correct client for custom base_url")

    import traceback

    print("\n  Full traceback:")
    traceback.print_exc()
    sys.exit(1)

# Step 5: Test with AutoGen's config from YAML
print("\n[Step 5] Testing with actual AutoGen configuration...")
try:
    from src.autogen_adapters.agent_factory import AutoGenAgentFactory

    factory = AutoGenAgentFactory()

    print(f"  [OK] Factory loaded {len(factory.llm_configs)} LLM configs")

    # Check code_analysis_config
    code_cfg = factory.llm_configs.get("code_analysis_config")
    if code_cfg:
        print(f"  [OK] code_analysis_config found:")
        print(f"      model: {code_cfg.get('model')}")
        print(f"      base_url: {code_cfg.get('base_url')}")
        print(
            f"      api_key: {code_cfg.get('api_key')[:20] if code_cfg.get('api_key') else 'NOT SET'}..."
        )

        # Create agent using factory
        print("\n  Creating code_analyzer agent...")
        code_analyzer = factory.create_agent("code_analyzer")
        print(f"  [OK] Agent created: {code_analyzer.name}")

        # Test conversation
        print("\n  Testing conversation with code_analyzer...")
        user = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config=False,
        )

        user.initiate_chat(code_analyzer, message="Say 'hello' in one word and then TERMINATE")

        print(f"  [OK] Conversation with factory-created agent successful!")

except Exception as e:
    print(f"  [ERROR] Factory test failed: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("  ALL TESTS PASSED!")
print("  Your Groq API configuration is working correctly.")
print("=" * 70)
print("\nIf you still experience 'Incorrect API key' errors in the main")
print("application, the issue is likely in:")
print("  1. How the conversation manager initializes agents")
print("  2. Environment variable loading timing")
print("  3. Different code path being used")
print("\nRun the main application with DEBUG logging to see the actual error.")
