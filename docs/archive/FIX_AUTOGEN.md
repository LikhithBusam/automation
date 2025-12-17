# Fix AutoGen Installation Issue

## Problem
You're seeing: `Warning: pyautogen not installed. Run: pip install pyautogen`

Even though AutoGen might be installed on your system, it's **not installed in your virtual environment**.

## Quick Fix (Recommended)

### Option 1: Use the install script (Easiest)

**In PowerShell:**
```powershell
.\install_autogen.ps1
```

**In Command Prompt:**
```cmd
install_autogen.bat
```

### Option 2: Manual installation

**Step 1: Activate your virtual environment**

In PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```

In Command Prompt:
```cmd
venv\Scripts\activate.bat
```

You should see `(venv)` at the start of your prompt.

**Step 2: Install pyautogen**
```bash
pip install "pyautogen<0.3.0"
```

**Step 3: Verify installation**
```bash
python diagnose.py
```

You should see:
```
✓ autogen module found
✓ AssistantAgent imported successfully
✓ UserProxyAgent imported successfully
✓ GroupChatManager imported successfully
✓ TeachableAgent imported successfully

RESULT: AutoGen is properly installed!
```

**Step 4: Run your application**
```bash
python main.py
```

## Diagnostic Tool

Run this to check your installation status:
```bash
python diagnose.py
```

This will tell you:
- If you're in a virtual environment
- If AutoGen is installed
- What's missing
- Exactly how to fix it

## Why This Happens

Your system has **TWO Python environments**:

1. **Global Python** (C:\Users\Likith\AppData\Local\Programs\Python\Python313)
   - AutoGen IS installed here ✓

2. **Virtual Environment** (.\venv)
   - AutoGen is NOT installed here ✗
   - Your `main.py` runs here

When you run `pip install pyautogen` **without activating venv**, it installs to global Python.

When you run `python main.py` **with venv activated**, it uses the venv Python, which doesn't have AutoGen.

## Solution Summary

**Always activate venv before installing packages:**

```powershell
# Activate venv first
.\venv\Scripts\Activate.ps1

# Then install
pip install "pyautogen<0.3.0"

# Then run
python main.py
```

## Verify It Works

After installation, you should see:

```
Initializing AutoGen System...
AgentFactory initialized with 7 agent configs
✓ Successfully imported autogen version 0.2.x
✓ Created agent: code_analyzer (AssistantAgent)
✓ Created agent: security_auditor (AssistantAgent)
✓ Created agent: documentation_agent (AssistantAgent)
✓ Created agent: deployment_agent (AssistantAgent)
✓ Created agent: research_agent (AssistantAgent)
✓ Created agent: project_manager (GroupChatManager)
✓ Created agent: user_proxy_executor (UserProxyAgent)
Created 7 agents  ← Should say 7, NOT 0!
```

## Still Not Working?

Run the diagnostic:
```bash
python diagnose.py
```

Check the output and follow the instructions provided.
