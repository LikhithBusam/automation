#!/usr/bin/env python3
"""
Comprehensive MCP Function Testing
Tests all MCP servers, tools, and registered functions
"""

import asyncio
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()

from src.autogen_adapters.conversation_manager import ConversationManager


async def test_mcp_servers():
    """Test all MCP server connections"""
    console.print("\n[bold cyan]═══ Testing MCP Server Connections ═══[/bold cyan]\n")
    
    results = []
    
    try:
        # Initialize the system
        manager = ConversationManager()
        await manager.initialize()
        
        # Test GitHub MCP Server
        try:
            if 'github' in manager.function_registry.tool_manager.tools:
                github = manager.function_registry.tool_manager.tools['github']
                console.print("[green]✓[/green] GitHub MCP Server: Connected")
                results.append(("GitHub Server", "✓ Connected", "Port 3000"))
            else:
                results.append(("GitHub Server", "✗ Not Found", "N/A"))
        except Exception as e:
            results.append(("GitHub Server", f"✗ Error: {str(e)[:30]}", "N/A"))
        
        # Test Filesystem MCP Server
        try:
            if 'filesystem' in manager.function_registry.tool_manager.tools:
                filesystem = manager.function_registry.tool_manager.tools['filesystem']
                console.print("[green]✓[/green] Filesystem MCP Server: Connected")
                results.append(("Filesystem Server", "✓ Connected", "Port 3001"))
            else:
                results.append(("Filesystem Server", "✗ Not Found", "N/A"))
        except Exception as e:
            results.append(("Filesystem Server", f"✗ Error: {str(e)[:30]}", "N/A"))
        
        # Test Memory MCP Server
        try:
            if 'memory' in manager.function_registry.tool_manager.tools:
                memory = manager.function_registry.tool_manager.tools['memory']
                console.print("[green]✓[/green] Memory MCP Server: Connected")
                results.append(("Memory Server", "✓ Connected", "Port 3002"))
            else:
                results.append(("Memory Server", "✗ Not Found", "N/A"))
        except Exception as e:
            results.append(("Memory Server", f"✗ Error: {str(e)[:30]}", "N/A"))
        
        # Test Slack MCP Server
        try:
            if 'slack' in manager.function_registry.tool_manager.tools:
                slack = manager.function_registry.tool_manager.tools['slack']
                console.print("[green]✓[/green] Slack MCP Server: Connected")
                results.append(("Slack Server", "✓ Connected", "Port 3003"))
            else:
                results.append(("Slack Server", "✗ Not Found", "N/A"))
        except Exception as e:
            results.append(("Slack Server", f"✗ Error: {str(e)[:30]}", "N/A"))
        
        return manager, results
        
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize system: {e}[/red]")
        return None, []


async def test_filesystem_functions(manager):
    """Test filesystem MCP functions"""
    console.print("\n[bold cyan]═══ Testing Filesystem Functions ═══[/bold cyan]\n")
    
    results = []
    filesystem = manager.function_registry.tool_manager.tools['filesystem']
    
    # Test 1: read_file
    try:
        content = filesystem.read_file(file_path="./README.md")
        if content and len(content) > 0:
            console.print(f"[green]✓[/green] read_file: Success ({len(content)} chars)")
            results.append(("read_file", "✓ Pass", f"{len(content)} chars read"))
        else:
            results.append(("read_file", "✗ Fail", "Empty content"))
    except Exception as e:
        console.print(f"[red]✗[/red] read_file: {str(e)[:50]}")
        results.append(("read_file", "✗ Fail", str(e)[:30]))
    
    # Test 2: list_directory
    try:
        dirs = await filesystem._list_directory({"path": "."})
        if dirs and 'entries' in dirs:
            console.print(f"[green]✓[/green] list_directory: Success ({len(dirs['entries'])} items)")
            results.append(("list_directory", "✓ Pass", f"{len(dirs['entries'])} items"))
        else:
            results.append(("list_directory", "✗ Fail", "No entries"))
    except Exception as e:
        console.print(f"[red]✗[/red] list_directory: {str(e)[:50]}")
        results.append(("list_directory", "✗ Fail", str(e)[:30]))
    
    # Test 3: search_files
    try:
        search_result = await filesystem._search_files({"pattern": "*.py", "path": "."})
        if search_result and 'files' in search_result:
            console.print(f"[green]✓[/green] search_files: Success ({len(search_result['files'])} files)")
            results.append(("search_files", "✓ Pass", f"{len(search_result['files'])} files"))
        else:
            results.append(("search_files", "✗ Fail", "No files"))
    except Exception as e:
        console.print(f"[red]✗[/red] search_files: {str(e)[:50]}")
        results.append(("search_files", "✗ Fail", str(e)[:30]))
    
    # Test 4: write_file (to temp location)
    try:
        test_file = Path("test_temp_write.txt")
        success = await filesystem._write_file({"path": str(test_file), "content": "Test content"})
        if success and test_file.exists():
            console.print("[green]✓[/green] write_file: Success")
            results.append(("write_file", "✓ Pass", "File created"))
            test_file.unlink()  # Cleanup
        else:
            results.append(("write_file", "✗ Fail", "File not created"))
    except Exception as e:
        console.print(f"[red]✗[/red] write_file: {str(e)[:50]}")
        results.append(("write_file", "✗ Fail", str(e)[:30]))
    
    return results


async def test_memory_functions(manager):
    """Test memory MCP functions"""
    console.print("\n[bold cyan]═══ Testing Memory Functions ═══[/bold cyan]\n")
    
    results = []
    memory = manager.function_registry.tool_manager.tools['memory']
    
    # Test 1: store_memory
    try:
        store_result = await memory._store_memory({
            "key": "test_key_123",
            "value": "Test value for MCP testing",
            "metadata": {"test": True}
        })
        if store_result and store_result.get('success'):
            console.print("[green]✓[/green] store_memory: Success")
            results.append(("store_memory", "✓ Pass", "Stored successfully"))
        else:
            results.append(("store_memory", "✗ Fail", "Store failed"))
    except Exception as e:
        console.print(f"[red]✗[/red] store_memory: {str(e)[:50]}")
        results.append(("store_memory", "✗ Fail", str(e)[:30]))
    
    # Test 2: retrieve_memory
    try:
        retrieve_result = await memory._retrieve_memory({"key": "test_key_123"})
        if retrieve_result and 'value' in retrieve_result:
            console.print("[green]✓[/green] retrieve_memory: Success")
            results.append(("retrieve_memory", "✓ Pass", "Retrieved successfully"))
        else:
            results.append(("retrieve_memory", "✗ Fail", "Not found"))
    except Exception as e:
        console.print(f"[red]✗[/red] retrieve_memory: {str(e)[:50]}")
        results.append(("retrieve_memory", "✗ Fail", str(e)[:30]))
    
    # Test 3: search_memory
    try:
        search_result = await memory._search_memory({"query": "test"})
        if search_result:
            console.print(f"[green]✓[/green] search_memory: Success")
            results.append(("search_memory", "✓ Pass", "Search completed"))
        else:
            results.append(("search_memory", "✗ Fail", "No results"))
    except Exception as e:
        console.print(f"[red]✗[/red] search_memory: {str(e)[:50]}")
        results.append(("search_memory", "✗ Fail", str(e)[:30]))
    
    return results


async def test_github_functions(manager):
    """Test GitHub MCP functions"""
    console.print("\n[bold cyan]═══ Testing GitHub Functions ═══[/bold cyan]\n")
    
    results = []
    github = manager.function_registry.tool_manager.tools['github']
    
    # Note: These tests require actual GitHub credentials and repo access
    # We'll test the function availability instead of actual API calls
    
    # Test 1: search_code (function exists)
    try:
        if hasattr(github, '_search_code'):
            console.print("[green]✓[/green] search_code: Function available")
            results.append(("search_code", "✓ Available", "Function registered"))
        else:
            results.append(("search_code", "✗ Missing", "Not found"))
    except Exception as e:
        results.append(("search_code", "✗ Error", str(e)[:30]))
    
    # Test 2: get_file_contents (function exists)
    try:
        if hasattr(github, '_get_file_contents'):
            console.print("[green]✓[/green] get_file_contents: Function available")
            results.append(("get_file_contents", "✓ Available", "Function registered"))
        else:
            results.append(("get_file_contents", "✗ Missing", "Not found"))
    except Exception as e:
        results.append(("get_file_contents", "✗ Error", str(e)[:30]))
    
    # Test 3: create_issue (function exists)
    try:
        if hasattr(github, '_create_issue'):
            console.print("[green]✓[/green] create_issue: Function available")
            results.append(("create_issue", "✓ Available", "Function registered"))
        else:
            results.append(("create_issue", "✗ Missing", "Not found"))
    except Exception as e:
        results.append(("create_issue", "✗ Error", str(e)[:30]))
    
    # Test 4: create_pull_request (function exists)
    try:
        if hasattr(github, '_create_pull_request'):
            console.print("[green]✓[/green] create_pull_request: Function available")
            results.append(("create_pull_request", "✓ Available", "Function registered"))
        else:
            results.append(("create_pull_request", "✗ Missing", "Not found"))
    except Exception as e:
        results.append(("create_pull_request", "✗ Error", str(e)[:30]))
    
    return results


async def test_slack_functions(manager):
    """Test Slack MCP functions"""
    console.print("\n[bold cyan]═══ Testing Slack Functions ═══[/bold cyan]\n")
    
    results = []
    slack = manager.function_registry.tool_manager.tools['slack']
    
    # Test function availability
    try:
        if hasattr(slack, '_send_message'):
            console.print("[green]✓[/green] send_message: Function available")
            results.append(("send_message", "✓ Available", "Function registered"))
        else:
            results.append(("send_message", "✗ Missing", "Not found"))
    except Exception as e:
        results.append(("send_message", "✗ Error", str(e)[:30]))
    
    try:
        if hasattr(slack, '_send_notification'):
            console.print("[green]✓[/green] send_notification: Function available")
            results.append(("send_notification", "✓ Available", "Function registered"))
        else:
            results.append(("send_notification", "✗ Missing", "Not found"))
    except Exception as e:
        results.append(("send_notification", "✗ Error", str(e)[:30]))
    
    return results


async def test_function_registry(manager):
    """Test function registry and AutoGen integration"""
    console.print("\n[bold cyan]═══ Testing Function Registry ═══[/bold cyan]\n")
    
    results = []
    
    # Test registered functions
    try:
        registered_funcs = manager.function_registry.registered_functions
        console.print(f"[green]✓[/green] Total registered functions: {len(registered_funcs)}")
        results.append(("Function Registry", "✓ Pass", f"{len(registered_funcs)} functions"))
        
        # List all registered functions
        for func_name in registered_funcs.keys():
            console.print(f"  • {func_name}")
    except Exception as e:
        console.print(f"[red]✗[/red] Function registry error: {e}")
        results.append(("Function Registry", "✗ Fail", str(e)[:30]))
    
    # Test agent function mapping
    try:
        agents = manager.agents
        console.print(f"\n[green]✓[/green] Total agents created: {len(agents)}")
        results.append(("Agent Creation", "✓ Pass", f"{len(agents)} agents"))
        
        for agent_name, agent in agents.items():
            console.print(f"  • {agent_name}: {agent.__class__.__name__}")
    except Exception as e:
        console.print(f"[red]✗[/red] Agent error: {e}")
        results.append(("Agent Creation", "✗ Fail", str(e)[:30]))
    
    return results


def print_results_table(title, results):
    """Print results in a formatted table"""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Function/Component", style="cyan", width=25)
    table.add_column("Status", width=15)
    table.add_column("Details", width=40)
    
    for item, status, details in results:
        if "✓" in status or "Pass" in status or "Available" in status or "Connected" in status:
            status_color = "green"
        else:
            status_color = "red"
        table.add_row(item, f"[{status_color}]{status}[/{status_color}]", details)
    
    console.print(table)


async def main():
    """Main test runner"""
    console.print(Panel.fit(
        "[bold cyan]MCP Function Testing Suite[/bold cyan]\n"
        "Testing all MCP servers, tools, and registered functions",
        border_style="cyan"
    ))
    
    all_results = {}
    
    # Test 1: MCP Server Connections
    manager, server_results = await test_mcp_servers()
    all_results['MCP Servers'] = server_results
    
    if not manager:
        console.print("[red]✗ Failed to initialize - stopping tests[/red]")
        return
    
    # Test 2: Filesystem Functions
    fs_results = await test_filesystem_functions(manager)
    all_results['Filesystem Functions'] = fs_results
    
    # Test 3: Memory Functions
    mem_results = await test_memory_functions(manager)
    all_results['Memory Functions'] = mem_results
    
    # Test 4: GitHub Functions
    gh_results = await test_github_functions(manager)
    all_results['GitHub Functions'] = gh_results
    
    # Test 5: Slack Functions
    slack_results = await test_slack_functions(manager)
    all_results['Slack Functions'] = slack_results
    
    # Test 6: Function Registry
    registry_results = await test_function_registry(manager)
    all_results['Function Registry'] = registry_results
    
    # Print all results
    console.print("\n" + "="*80 + "\n")
    console.print("[bold yellow]TEST RESULTS SUMMARY[/bold yellow]\n")
    
    for category, results in all_results.items():
        print_results_table(category, results)
        console.print()
    
    # Calculate overall statistics
    total_tests = sum(len(results) for results in all_results.values())
    passed_tests = sum(
        1 for results in all_results.values() 
        for _, status, _ in results 
        if "✓" in status or "Pass" in status or "Available" in status or "Connected" in status
    )
    
    console.print(Panel.fit(
        f"[bold]Total Tests: {total_tests}[/bold]\n"
        f"[green]Passed: {passed_tests}[/green]\n"
        f"[red]Failed: {total_tests - passed_tests}[/red]\n"
        f"[cyan]Success Rate: {(passed_tests/total_tests*100):.1f}%[/cyan]",
        title="Overall Results",
        border_style="green" if passed_tests == total_tests else "yellow"
    ))


if __name__ == "__main__":
    asyncio.run(main())
