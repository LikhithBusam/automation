"""
MCP Integration Test Suite
Tests all MCP tool wrappers and integrations
"""

import asyncio
import logging
from rich.console import Console
from rich.table import Table
from src.mcp.tool_manager import MCPToolManager
import yaml


console = Console()
logging.basicConfig(level=logging.INFO)


async def test_github_mcp(tool_manager: MCPToolManager):
    """Test GitHub MCP integration"""
    console.print("\n[bold cyan]Testing GitHub MCP...[/bold cyan]")
    
    if not tool_manager.is_tool_available("github"):
        console.print("[yellow]GitHub MCP not configured[/yellow]")
        return False
    
    try:
        # Test search_code operation
        result = await tool_manager.execute(
            "github",
            "search_code",
            {"query": "language:python async def", "per_page": 3}
        )
        console.print(f"[green]✓ GitHub search successful ({result.get('total_count', 0)} results)[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ GitHub test failed: {str(e)}[/red]")
        return False


async def test_filesystem_mcp(tool_manager: MCPToolManager):
    """Test Filesystem MCP integration"""
    console.print("\n[bold cyan]Testing Filesystem MCP...[/bold cyan]")
    
    if not tool_manager.is_tool_available("filesystem"):
        console.print("[yellow]Filesystem MCP not configured[/yellow]")
        return False
    
    try:
        # Test read_file operation
        result = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "./README.md"}
        )
        console.print(f"[green]✓ File read successful ({len(result.get('content', ''))} chars)[/green]")
        
        # Test list_directory operation
        result = await tool_manager.execute(
            "filesystem",
            "list_directory",
            {"path": "./src"}
        )
        console.print(f"[green]✓ Directory listing successful ({len(result.get('files', []))} items)[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Filesystem test failed: {str(e)}[/red]")
        return False


async def test_memory_mcp(tool_manager: MCPToolManager):
    """Test Memory MCP integration"""
    console.print("\n[bold cyan]Testing Memory MCP...[/bold cyan]")
    
    if not tool_manager.is_tool_available("memory"):
        console.print("[yellow]Memory MCP not configured[/yellow]")
        return False
    
    try:
        # Test store operation
        store_result = await tool_manager.execute(
            "memory",
            "store",
            {
                "content": "Test memory: FastAPI is great for building APIs",
                "type": "pattern",
                "tags": ["test", "api", "best-practice"],
                "agent": "test_suite"
            }
        )
        console.print(f"[green]✓ Memory store successful (ID: {store_result.get('id', 'N/A')})[/green]")
        
        # Test search operation
        search_result = await tool_manager.execute(
            "memory",
            "search",
            {
                "query": "API best practices",
                "limit": 3
            }
        )
        console.print(f"[green]✓ Memory search successful ({len(search_result.get('results', []))} results)[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Memory test failed: {str(e)}[/red]")
        return False


async def test_slack_mcp(tool_manager: MCPToolManager):
    """Test Slack MCP integration"""
    console.print("\n[bold cyan]Testing Slack MCP...[/bold cyan]")
    
    if not tool_manager.is_tool_available("slack"):
        console.print("[yellow]Slack MCP not configured[/yellow]")
        return False
    
    try:
        # Test send_notification operation
        result = await tool_manager.execute(
            "slack",
            "send_notification",
            {
                "type": "info",
                "title": "Test Notification",
                "message": "Testing Slack integration",
                "details": {
                    "test": "integration_test",
                    "status": "running"
                }
            }
        )
        console.print(f"[green]✓ Slack notification sent (ts: {result.get('ts', 'N/A')})[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Slack test failed: {str(e)}[/red]")
        return False


async def test_health_checks(tool_manager: MCPToolManager):
    """Test health checks for all tools"""
    console.print("\n[bold cyan]Running Health Checks...[/bold cyan]")
    
    health = await tool_manager.health_check()
    
    table = Table(title="MCP Server Health Status")
    table.add_column("Server", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")
    
    for tool_name, status in health.items():
        status_str = status.get("status", "unknown")
        status_color = "green" if status_str == "healthy" else "red"
        details = status.get("error", "OK")
        
        table.add_row(
            tool_name,
            f"[{status_color}]{status_str}[/{status_color}]",
            details
        )
    
    console.print(table)


async def test_statistics(tool_manager: MCPToolManager):
    """Display tool usage statistics"""
    console.print("\n[bold cyan]Tool Usage Statistics[/bold cyan]")
    
    stats = tool_manager.get_stats()
    
    table = Table(title="MCP Tool Statistics")
    table.add_column("Tool", style="cyan")
    table.add_column("Total Requests", justify="right")
    table.add_column("Successful", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Success Rate")
    table.add_column("Cache Hit Rate")
    
    for tool_name, tool_stats in stats.items():
        table.add_row(
            tool_name,
            str(tool_stats.get("total_requests", 0)),
            str(tool_stats.get("successful_requests", 0)),
            str(tool_stats.get("failed_requests", 0)),
            tool_stats.get("success_rate", "0%"),
            tool_stats.get("cache_hit_rate", "0%")
        )
    
    console.print(table)


async def test_cache_functionality(tool_manager: MCPToolManager):
    """Test caching functionality"""
    console.print("\n[bold cyan]Testing Cache Functionality...[/bold cyan]")
    
    if not tool_manager.is_tool_available("filesystem"):
        console.print("[yellow]Filesystem MCP not available for cache test[/yellow]")
        return
    
    try:
        # First call (cache miss)
        import time
        start = time.time()
        result1 = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "./README.md"},
            use_cache=True
        )
        time1 = time.time() - start
        
        # Second call (cache hit)
        start = time.time()
        result2 = await tool_manager.execute(
            "filesystem",
            "read_file",
            {"path": "./README.md"},
            use_cache=True
        )
        time2 = time.time() - start
        
        console.print(f"[green]✓ First call (cache miss): {time1:.4f}s[/green]")
        console.print(f"[green]✓ Second call (cache hit): {time2:.4f}s[/green]")
        console.print(f"[cyan]Speedup: {time1/time2:.2f}x[/cyan]")
        
    except Exception as e:
        console.print(f"[red]✗ Cache test failed: {str(e)}[/red]")


async def main():
    """Run all integration tests"""
    console.print("[bold green]MCP Integration Test Suite[/bold green]")
    console.print("=" * 60)
    
    # Load configuration
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Initialize tool manager
    console.print("\n[bold]Initializing MCPToolManager...[/bold]")
    tool_manager = MCPToolManager(config)
    console.print(f"[green]✓ Initialized {len(tool_manager.get_available_tools())} tools[/green]")
    
    # Run tests
    results = {}
    
    # Health checks first
    await test_health_checks(tool_manager)
    
    # Individual tool tests
    results["github"] = await test_github_mcp(tool_manager)
    results["filesystem"] = await test_filesystem_mcp(tool_manager)
    results["memory"] = await test_memory_mcp(tool_manager)
    results["slack"] = await test_slack_mcp(tool_manager)
    
    # Cache test
    await test_cache_functionality(tool_manager)
    
    # Statistics
    await test_statistics(tool_manager)
    
    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold]Test Summary[/bold]")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    console.print(f"Tests Passed: [green]{passed}/{total}[/green]")
    console.print(f"Tests Failed: [red]{total - passed}/{total}[/red]")
    
    if passed == total:
        console.print("\n[bold green]✓ All tests passed![/bold green]")
    else:
        console.print("\n[bold yellow]⚠ Some tests failed. Check configuration.[/bold yellow]")


if __name__ == "__main__":
    asyncio.run(main())
