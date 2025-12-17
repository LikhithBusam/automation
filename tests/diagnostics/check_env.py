"""
Check environment and imports
"""
import sys
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")
print(f"Path: {sys.path[:3]}")

print("\n[1] Testing autogen import...")
try:
    from autogen import AssistantAgent, UserProxyAgent
    print("[OK] AutoGen imports work!")
    print(f"    AssistantAgent: {AssistantAgent}")
    print(f"    UserProxyAgent: {UserProxyAgent}")
except ImportError as e:
    print(f"[FAIL] AutoGen import failed: {e}")

print("\n[2] Testing agent_factory import...")
try:
    sys.path.insert(0, '.')
    from src.autogen_adapters.agent_factory import HAS_AUTOGEN, AutoGenAgentFactory
    print(f"[OK] Agent factory imports!")
    print(f"    HAS_AUTOGEN: {HAS_AUTOGEN}")

    print("\n[3] Creating agent factory...")
    factory = AutoGenAgentFactory()
    print(f"[OK] Factory created with {len(factory.agent_configs)} agent configs")

    print("\n[4] Trying to create an agent...")
    agent = factory.create_agent('user_proxy_executor')
    if agent:
        print(f"[OK] Agent created: {type(agent).__name__}")
    else:
        print("[FAIL] Agent is None")

except Exception as e:
    print(f"[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
