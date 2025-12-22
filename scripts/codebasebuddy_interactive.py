#!/usr/bin/env python3
"""
CodeBaseBuddy Interactive Chat
Ask natural language questions about your codebase

Usage:
    python scripts/codebasebuddy_interactive.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool


class CodeBaseBuddyChat:
    """Interactive chat with CodeBaseBuddy"""

    def __init__(self):
        self.tool = CodeBaseBuddyMCPTool(
            server_url="http://localhost:3004",
            config={
                "index_path": "./data/codebase_index",
                "scan_paths": ["./src", "./mcp_servers", "./config"],
            },
        )
        self.search_history = []

    async def semantic_search(self, query: str, top_k: int = 5):
        """Search for code by natural language"""
        print(f"\n🔍 Searching for: '{query}'")
        print("─" * 80)

        result = await self.tool.semantic_search(query=query, top_k=top_k)

        if result["results_count"] == 0:
            print("❌ No results found")
            return

        print(f"✅ Found {result['results_count']} results:\n")

        for i, res in enumerate(result["results"], 1):
            print(f"{i}. 📄 {res['file_path']}")
            print(f"   Line {res['start_line']}: {res['content_preview']}")
            print()

    async def find_usages(self, symbol: str, top_k: int = 5):
        """Find where a symbol is used"""
        print(f"\n🔎 Finding usages of: '{symbol}'")
        print("─" * 80)

        result = await self.tool.find_usages(symbol_name=symbol, top_k=top_k)

        if result["results_count"] == 0:
            print(f"❌ No usages found for '{symbol}'")
            return

        print(f"✅ Found {result['results_count']} usages:\n")

        for i, res in enumerate(result["results"], 1):
            print(f"{i}. 📄 {res['file_path']}")
            print(f"   Line {res['line_number']}: {res['line_content'][:100]}")
            print()

    async def get_context(self, file_path: str, line_number: int, context: int = 5):
        """Get code context around a specific line"""
        print(f"\n📖 Reading context from: {file_path} (line {line_number})")
        print("─" * 80)

        result = await self.tool.get_code_context(
            file_path=file_path, line_number=line_number, context_lines=context
        )

        if not result.get("success"):
            print(f"❌ Error: {result.get('error')}")
            return

        print(
            f"✅ Retrieved lines {result['start_line']}-{result['end_line']} of {result['total_lines']}:\n"
        )
        print(result["context"])
        print()

    async def find_similar(self, code_snippet: str, top_k: int = 3):
        """Find similar code patterns"""
        print(f"\n🔄 Finding similar code patterns")
        print("─" * 80)

        result = await self.tool.find_similar_code(code_snippet=code_snippet, top_k=top_k)

        if result["results_count"] == 0:
            print("❌ No similar code found")
            return

        print(f"✅ Found {result['results_count']} similar patterns:\n")

        for i, res in enumerate(result["results"], 1):
            print(f"{i}. 📄 {res['file_path']}")
            print(f"   Similarity: {res['similarity_score']:.2%}")
            print()

    async def show_help(self):
        """Show available commands"""
        help_text = """
╔════════════════════════════════════════════════════════════════════╗
║          CodeBaseBuddy Interactive - Available Commands            ║
╚════════════════════════════════════════════════════════════════════╝

SEARCH COMMANDS:
  search <query>              - Search for code by natural language
                               Example: search "how does authentication work"
  
  usages <symbol>             - Find where a symbol is used
                               Example: usages MCPToolManager
  
  similar <snippet>           - Find similar code patterns
                               Example: similar "async def execute"
  
  context <file> <line>       - Get code context around a line
                               Example: context ./src/mcp/base_tool.py 50

UTILITY COMMANDS:
  help                        - Show this message
  history                     - Show recent searches
  stats                       - Show index statistics
  exit / quit / q             - Exit the chat

EXAMPLES:
  
  1. Search for a concept:
     > search "how are workflows executed"
     
  2. Find where something is used:
     > usages ConversationManager
     
  3. Get code context:
     > context ./src/autogen_adapters/agent_factory.py 100
     
  4. Find similar patterns:
     > similar "async def __init__(self):"

────────────────────────────────────────────────────────────────────
Tips:
  • Use natural language for searches
  • Be specific with file paths for context
  • Use symbol names for finding usages
  • Type 'exit' to quit
────────────────────────────────────────────────────────────────────
        """
        print(help_text)

    async def show_stats(self):
        """Show index statistics"""
        print("\n📊 Index Statistics")
        print("─" * 80)

        result = await self.tool.get_index_stats()

        if result.get("success"):
            stats = result.get("stats", {})
            print(f"✅ Index Statistics:\n")
            print(f"  Files indexed: {stats.get('files_indexed', 0)}")
            print(f"  Functions: {stats.get('functions_indexed', 0)}")
            print(f"  Classes: {stats.get('classes_indexed', 0)}")
            print(f"  Vectors: {stats.get('total_vectors', 0)}")
            print(f"  Mode: {stats.get('mode', 'N/A')}")
        else:
            print(f"❌ Error: {result.get('error')}")
        print()

    async def show_history(self):
        """Show search history"""
        if not self.search_history:
            print("\n📋 No search history yet\n")
            return

        print("\n📋 Recent Searches:")
        print("─" * 80)
        for i, query in enumerate(self.search_history[-10:], 1):
            print(f"{i}. {query}")
        print()

    async def process_command(self, user_input: str):
        """Process user command"""
        user_input = user_input.strip()

        if not user_input:
            return True

        # Parse command
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Check if this looks like a search query (natural language)
        # If user types something that's not a known command, treat as search
        is_search_query = command not in [
            "exit",
            "quit",
            "q",
            "help",
            "history",
            "stats",
            "search",
            "usages",
            "similar",
            "context",
        ]

        # Handle commands
        if command in ["exit", "quit", "q"]:
            print("\n👋 Goodbye!")
            return False

        elif command == "help":
            await self.show_help()

        elif command == "history":
            await self.show_history()

        elif command == "stats":
            await self.show_stats()

        elif command == "search":
            if not args:
                print("❌ Please provide a search query")
                print("   Usage: search <query>")
            else:
                self.search_history.append(f"search: {args}")
                await self.semantic_search(args)

        elif command == "usages":
            if not args:
                print("❌ Please provide a symbol name")
                print("   Usage: usages <symbol>")
            else:
                self.search_history.append(f"usages: {args}")
                await self.find_usages(args)

        elif command == "similar":
            if not args:
                print("❌ Please provide code snippet")
                print("   Usage: similar <code>")
            else:
                self.search_history.append(f"similar: {args}")
                await self.find_similar(args)

        elif command == "context":
            parts = args.split()
            if len(parts) < 2:
                print("❌ Invalid syntax")
                print("   Usage: context <file_path> <line_number>")
            else:
                file_path = parts[0]
                try:
                    line_number = int(parts[1])
                    self.search_history.append(f"context: {file_path}:{line_number}")
                    await self.get_context(file_path, line_number)
                except ValueError:
                    print("❌ Line number must be an integer")

        elif is_search_query:
            # Treat entire input as search query
            self.search_history.append(f"search: {user_input}")
            await self.semantic_search(user_input)

        return True

    async def run(self):
        """Run interactive chat loop"""
        print("\n")
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║          🤖 CodeBaseBuddy - Codebase Q&A Chat                     ║")
        print("║                                                                    ║")
        print("║  Ask natural language questions about your codebase!              ║")
        print("║  Type 'help' for available commands                              ║")
        print("║  Type 'exit' to quit                                              ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()

        while True:
            try:
                user_input = input("💬 You: ").strip()

                if not user_input:
                    continue

                continue_chat = await self.process_command(user_input)

                if not continue_chat:
                    break

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


async def main():
    """Main entry point"""
    chat = CodeBaseBuddyChat()
    await chat.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(1)
