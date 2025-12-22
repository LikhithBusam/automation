"""
Diagnostic script to check AutoGen installation
"""

import sys
import os

print("=" * 70)
print("AUTOGEN INSTALLATION DIAGNOSTIC")
print("=" * 70)
print()

# Check Python version
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print()

# Check if in virtual environment
in_venv = hasattr(sys, "real_prefix") or (
    hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
)
print(f"In Virtual Environment: {in_venv}")
if in_venv:
    print(f"Virtual Environment: {sys.prefix}")
print()

# Try importing autogen
print("Testing AutoGen Import...")
print("-" * 70)
try:
    import autogen

    print(f"✓ autogen module found")
    print(f"  Location: {autogen.__file__}")
    print(f"  Version: {getattr(autogen, '__version__', 'unknown')}")
    print()

    # Try importing specific classes
    try:
        from autogen import AssistantAgent

        print(f"✓ AssistantAgent imported successfully")
    except ImportError as e:
        print(f"✗ AssistantAgent import failed: {e}")

    try:
        from autogen import UserProxyAgent

        print(f"✓ UserProxyAgent imported successfully")
    except ImportError as e:
        print(f"✗ UserProxyAgent import failed: {e}")

    try:
        from autogen import GroupChatManager

        print(f"✓ GroupChatManager imported successfully")
    except ImportError as e:
        print(f"✗ GroupChatManager import failed: {e}")

    try:
        from autogen.agentchat.contrib.teachable_agent import TeachableAgent

        print(f"✓ TeachableAgent imported successfully")
    except ImportError as e:
        print(f"✗ TeachableAgent import failed: {e}")

    print()
    print("=" * 70)
    print("RESULT: AutoGen is properly installed!")
    print("=" * 70)

except ImportError as e:
    print(f"✗ autogen module NOT found")
    print(f"  Error: {e}")
    print()
    print("=" * 70)
    print("SOLUTION:")
    print("=" * 70)
    print()
    if in_venv:
        print("Run in PowerShell:")
        print("  .\\venv\\Scripts\\Activate.ps1")
        print("  pip install 'pyautogen<0.3.0'")
        print()
        print("Or run the install script:")
        print("  .\\install_autogen.ps1")
    else:
        print("You are not in a virtual environment!")
        print("Run in PowerShell:")
        print("  .\\venv\\Scripts\\Activate.ps1")
        print("  pip install 'pyautogen<0.3.0'")
    print()
    print("=" * 70)

print()
input("Press Enter to exit...")
