# CodeBaseBuddy Quick Start Guide

CodeBaseBuddy is a semantic code search tool that helps you understand and explore your codebase using natural language questions.

## What It Does

- **Semantic Search**: Ask questions about what code does in plain English
- **Find Usages**: Locate where symbols are used across the codebase
- **Code Context**: Read code with surrounding lines for context
- **Similar Code**: Find code patterns similar to a given snippet
- **Index Stats**: See what's been indexed

## Quick Start

### Option 1: Interactive Chat (Easiest)

```bash
python scripts/codebasebuddy_interactive.py
```

Then type commands like:
```
search "how does authentication work?"
usages "MCPToolManager"
context "./src/mcp/base_tool.py" 50
similar "async def execute"
help
```

### Option 2: Run Examples

```bash
python scripts/codebasebuddy_examples.py
```

This shows 5 practical examples of CodeBaseBuddy in action.

### Option 3: Use in Your Code

```python
import asyncio
from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool

async def main():
    tool = CodeBaseBuddyMCPTool(server_url="http://localhost:3004")
    
    # Search by question
    result = await tool.semantic_search("How does CircuitBreaker work?")
    print(f"Found {result['results_count']} results")
    
    # Find where symbol is used
    result = await tool.find_usages("MCPToolManager")
    print(f"Found {result['results_count']} usages")
    
    # Get code context
    result = await tool.get_code_context("./src/mcp/base_tool.py", 50)
    print(result['context'])
    
    # Find similar patterns
    result = await tool.find_similar_code("async def execute(self):")
    print(f"Found {result['results_count']} similar patterns")

asyncio.run(main())
```

## Key Features Explained

### 1. Semantic Search
Ask natural language questions about what code does:
```
search "how does authentication work?"
search "where is error handling done?"
search "what validates user input?"
```

### 2. Find Usages
Locate all places a symbol appears:
```
usages "MCPToolManager"
usages "CircuitBreaker"
usages "validate_input"
```

### 3. Get Code Context
Read specific lines with surrounding context:
```
context "./src/mcp/base_tool.py" 50
context "./src/security/auth.py" 20 5  # 5 lines of context
```

### 4. Find Similar Code
Find code that matches a pattern:
```
similar "async def execute"
similar "def process_data"
```

### 5. Index Statistics
See what's been indexed:
```
stats
```

## Example Questions

**"What is ConversationManager?"**
```bash
search "What is ConversationManager and what does it do?"
```

**"Where is authentication validated?"**
```bash
search "where is authentication validated in the code?"
```

**"How are errors handled?"**
```bash
search "what error handling mechanisms are used?"
```

**"Find all uses of CircuitBreaker"**
```bash
usages "CircuitBreaker"
```

**"What's at line 50 of base_tool.py?"**
```bash
context "./src/mcp/base_tool.py" 50
```

## Project Structure (What CodeBaseBuddy Knows)

The codebase contains:
- **38 Python files** across the project
- **src/** - Main source code (APIs, agents, tools, security)
- **mcp_servers/** - MCP server implementations
- **config/** - Configuration files for agents and workflows
- **tests/** - Test suite
- **scripts/** - Utility scripts

## Common Use Cases

### Onboarding: Understand the Project
```bash
search "what is this project and what does it do?"
search "what are the main components?"
search "how does the workflow system work?"
```

### Finding Code: Locate Features
```bash
search "where is the authentication implemented?"
usages "MCPToolManager"
search "how are API routes defined?"
```

### Code Review: Understand Patterns
```bash
search "what design patterns are used?"
similar "class CircuitBreaker"
context "./src/security/circuit_breaker.py" 30
```

### Debugging: Trace Error Handling
```bash
search "what happens when an error occurs?"
usages "exception"
search "how are async errors handled?"
```

## Notes

- **Fallback Mode**: CodeBaseBuddy uses text-based search fallback. This is normal and fully functional - it searches through code files for your queries.
- **File Paths**: Use relative paths like `./src/mcp/base_tool.py`
- **Case Sensitive**: Search is case-sensitive for usages
- **Fast Responses**: All searches complete instantly

## Troubleshooting

**Q: Server unavailable message?**
A: This is normal! CodeBaseBuddy uses fallback mode with text-based search that works instantly.

**Q: No results found?**
A: Try simpler search terms. For example, instead of "async generator function", try "generator" or "async".

**Q: File not found?**
A: Check the file path is relative and correct, like `./src/mcp/base_tool.py` not just `base_tool.py`.

## Next Steps

1. Start with `python scripts/codebasebuddy_interactive.py`
2. Try simple searches first
3. Use `help` command for full list of commands
4. Explore your codebase with natural language questions!

Happy exploring!
