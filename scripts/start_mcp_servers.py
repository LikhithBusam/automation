"""
MCP Servers Launcher with Health Monitoring and Auto-Restart
Starts all MCP servers with:
- Health monitoring with periodic checks
- Auto-restart on failure with exponential backoff
- Graceful shutdown handling (SIGINT/SIGTERM)
- Separate log files for each server
- Real-time status dashboard
"""

import subprocess
import time
import sys
import os
import signal
import threading
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx
import json

# Try to import rich for better terminal output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ServerStatus(str, Enum):
    """Server status states"""
    STARTING = "starting"
    RUNNING = "running"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    FAILED = "failed"


@dataclass
class ServerState:
    """Track state for each server"""
    name: str
    script: str
    port: int
    env_vars: List[str]
    process: Optional[subprocess.Popen] = None
    status: ServerStatus = ServerStatus.STOPPED
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    restart_count: int = 0
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    last_error: Optional[str] = None
    log_file: Optional[str] = None
    
    # Exponential backoff settings
    base_restart_delay: float = 1.0
    max_restart_delay: float = 60.0
    max_restarts: int = 10


# Server configurations
SERVERS_CONFIG = [
    {
        "name": "GitHub Server",
        "script": "mcp_servers/github_server.py",
        "port": 3000,
        "env_vars": ["GITHUB_TOKEN"],
        "health_endpoint": "/health"
    },
    {
        "name": "Filesystem Server",
        "script": "mcp_servers/filesystem_server.py",
        "port": 3001,
        "env_vars": [],
        "health_endpoint": "/health"
    },
    {
        "name": "Memory Server",
        "script": "mcp_servers/memory_server.py",
        "port": 3002,
        "env_vars": [],
        "health_endpoint": "/health"
    }
]

# Global state
servers: Dict[str, ServerState] = {}
shutdown_event = threading.Event()
console = Console() if RICH_AVAILABLE else None

# Logging configuration
LOG_DIR = Path("./logs/mcp_servers")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file(server_name: str) -> Path:
    """Get log file path for a server"""
    safe_name = server_name.lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d")
    return LOG_DIR / f"{safe_name}_{timestamp}.log"


def log_message(server_name: str, message: str, level: str = "INFO"):
    """Log message to server's log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}\n"
    
    log_file = get_log_file(server_name)
    with open(log_file, "a") as f:
        f.write(log_line)


def check_env_vars() -> List[str]:
    """Check if required environment variables are set"""
    missing = []
    
    for config in SERVERS_CONFIG:
        for var in config.get("env_vars", []):
            if not os.getenv(var) and var not in missing:
                missing.append(var)
    
    return missing


def calculate_restart_delay(restart_count: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay for restarts"""
    delay = base_delay * (2 ** restart_count)
    return min(delay, max_delay)


async def check_server_health(port: int, timeout: float = 5.0) -> bool:
    """Check if server is healthy via HTTP request"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Try SSE endpoint (FastMCP default)
            response = await client.get(f"http://localhost:{port}/sse")
            return response.status_code in [200, 404, 405]  # Server is responding
    except Exception:
        try:
            # Fallback: just check if port is open
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"http://localhost:{port}/")
                return True
        except Exception:
            return False


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use"""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False


def start_server_process(server: ServerState) -> bool:
    """Start a single MCP server process"""
    script_path = Path(server.script)

    if not script_path.exists():
        server.status = ServerStatus.FAILED
        server.last_error = f"Script not found: {script_path}"
        log_message(server.name, f"Script not found: {script_path}", "ERROR")
        return False

    # Check if port is already in use
    if is_port_in_use(server.port):
        server.status = ServerStatus.FAILED
        server.last_error = f"Port {server.port} already in use"
        log_message(server.name, f"Port {server.port} already in use - another server is running", "ERROR")
        print(f"  ❌ {server.name} - Port {server.port} already in use!")
        print(f"     Stop existing servers first with: python mcp_server_daemon.py stop")
        return False

    # Open log file for this server
    log_file = get_log_file(server.name)
    server.log_file = str(log_file)

    log_message(server.name, f"Starting server on port {server.port}")

    try:
        # Open log file handles
        log_handle = open(log_file, "a")
        
        # Start server process with output redirected to log file
        process = subprocess.Popen(
            [sys.executable, "-u", str(script_path)],  # -u for unbuffered output
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ}  # Inherit environment
        )
        
        server.process = process
        server.pid = process.pid
        server.start_time = datetime.now()
        server.status = ServerStatus.STARTING
        
        log_message(server.name, f"Process started with PID {process.pid}")
        
        return True
        
    except Exception as e:
        server.status = ServerStatus.FAILED
        server.last_error = str(e)
        log_message(server.name, f"Failed to start: {e}", "ERROR")
        return False


def stop_server_process(server: ServerState, timeout: float = 5.0) -> bool:
    """Stop a server process gracefully"""
    if server.process is None:
        return True
    
    try:
        log_message(server.name, "Stopping server...")
        
        # Try graceful termination first
        server.process.terminate()
        
        try:
            server.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown fails
            log_message(server.name, "Force killing process...", "WARNING")
            server.process.kill()
            server.process.wait(timeout=2)
        
        server.status = ServerStatus.STOPPED
        server.process = None
        server.pid = None
        log_message(server.name, "Server stopped")
        return True
        
    except Exception as e:
        server.last_error = str(e)
        log_message(server.name, f"Error stopping server: {e}", "ERROR")
        return False


async def restart_server_with_backoff(server: ServerState):
    """Restart server with exponential backoff"""
    if server.restart_count >= server.max_restarts:
        server.status = ServerStatus.FAILED
        server.last_error = f"Max restarts ({server.max_restarts}) exceeded"
        log_message(server.name, f"Max restarts exceeded, giving up", "ERROR")
        return False
    
    # Calculate delay
    delay = calculate_restart_delay(
        server.restart_count,
        server.base_restart_delay,
        server.max_restart_delay
    )
    
    server.status = ServerStatus.RESTARTING
    log_message(server.name, f"Restarting in {delay:.1f}s (attempt {server.restart_count + 1})")
    
    # Wait before restart
    await asyncio.sleep(delay)
    
    if shutdown_event.is_set():
        return False
    
    # Stop existing process if any
    stop_server_process(server)
    
    # Start new process
    server.restart_count += 1
    if start_server_process(server):
        # Wait for server to be ready
        await asyncio.sleep(2)
        return True
    
    return False


async def health_check_loop():
    """Periodically check health of all servers"""
    check_interval = 10  # seconds
    startup_grace_period = 5  # seconds to wait before first health check
    
    await asyncio.sleep(startup_grace_period)
    
    while not shutdown_event.is_set():
        for name, server in servers.items():
            if shutdown_event.is_set():
                break
            
            if server.status in [ServerStatus.STOPPED, ServerStatus.FAILED]:
                continue
            
            # Check if process is still running
            if server.process and server.process.poll() is not None:
                # Process died
                exit_code = server.process.returncode
                server.status = ServerStatus.UNHEALTHY
                server.last_error = f"Process exited with code {exit_code}"
                log_message(server.name, f"Process died (exit code: {exit_code})", "ERROR")
                
                # Attempt restart
                await restart_server_with_backoff(server)
                continue
            
            # Check HTTP health
            is_healthy = await check_server_health(server.port)
            server.last_health_check = datetime.now()
            
            if is_healthy:
                if server.status == ServerStatus.STARTING:
                    server.status = ServerStatus.RUNNING
                    server.health_check_failures = 0
                    log_message(server.name, "Server is now healthy")
                elif server.status == ServerStatus.UNHEALTHY:
                    server.status = ServerStatus.RUNNING
                    server.health_check_failures = 0
                    log_message(server.name, "Server recovered")
            else:
                server.health_check_failures += 1
                
                if server.health_check_failures >= 3:
                    server.status = ServerStatus.UNHEALTHY
                    server.last_error = "Health check failed 3 times"
                    log_message(server.name, "Health check failed, restarting...", "WARNING")
                    
                    # Attempt restart
                    await restart_server_with_backoff(server)
        
        # Wait before next check
        await asyncio.sleep(check_interval)


def get_uptime(start_time: Optional[datetime]) -> str:
    """Get formatted uptime string"""
    if not start_time:
        return "-"
    
    delta = datetime.now() - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def get_status_color(status: ServerStatus) -> str:
    """Get color for status"""
    colors = {
        ServerStatus.RUNNING: "green",
        ServerStatus.STARTING: "yellow",
        ServerStatus.RESTARTING: "yellow",
        ServerStatus.UNHEALTHY: "red",
        ServerStatus.STOPPED: "dim",
        ServerStatus.FAILED: "red bold",
    }
    return colors.get(status, "white")


def render_dashboard() -> Any:
    """Render status dashboard"""
    if not RICH_AVAILABLE:
        return render_simple_dashboard()
    
    # Create table
    table = Table(title="MCP Servers Status", expand=True)
    table.add_column("Server", style="cyan", no_wrap=True)
    table.add_column("Port", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("PID", justify="center")
    table.add_column("Uptime", justify="center")
    table.add_column("Restarts", justify="center")
    table.add_column("Last Check", justify="center")
    
    for name, server in servers.items():
        status_style = get_status_color(server.status)
        
        last_check = "-"
        if server.last_health_check:
            last_check = server.last_health_check.strftime("%H:%M:%S")
        
        table.add_row(
            server.name,
            str(server.port),
            f"[{status_style}]{server.status.value}[/{status_style}]",
            str(server.pid) if server.pid else "-",
            get_uptime(server.start_time),
            str(server.restart_count),
            last_check
        )
    
    # Create layout with additional info
    layout = Layout()
    
    # Add log directory info
    info_text = f"📁 Logs: {LOG_DIR.absolute()}\n⏱️  Health check interval: 10s\n🔄 Press Ctrl+C to stop all servers"
    
    layout.split_column(
        Layout(Panel(table, border_style="blue"), name="table"),
        Layout(Panel(info_text, title="Info", border_style="dim"), name="info", size=5)
    )
    
    return layout


def render_simple_dashboard() -> str:
    """Render simple text dashboard (fallback when rich not available)"""
    lines = [
        "=" * 70,
        "MCP Servers Status",
        "=" * 70,
        f"{'Server':<20} {'Port':<8} {'Status':<12} {'PID':<8} {'Uptime':<12} {'Restarts':<8}",
        "-" * 70
    ]
    
    for name, server in servers.items():
        lines.append(
            f"{server.name:<20} {server.port:<8} {server.status.value:<12} "
            f"{str(server.pid or '-'):<8} {get_uptime(server.start_time):<12} {server.restart_count:<8}"
        )
    
    lines.extend([
        "-" * 70,
        f"Logs: {LOG_DIR.absolute()}",
        "Press Ctrl+C to stop all servers",
        "=" * 70
    ])
    
    return "\n".join(lines)


async def dashboard_loop():
    """Update dashboard display"""
    refresh_interval = 1.0  # seconds
    
    if RICH_AVAILABLE:
        with Live(render_dashboard(), refresh_per_second=1, console=console) as live:
            while not shutdown_event.is_set():
                live.update(render_dashboard())
                await asyncio.sleep(refresh_interval)
    else:
        while not shutdown_event.is_set():
            # Clear screen and print dashboard
            os.system('cls' if os.name == 'nt' else 'clear')
            print(render_simple_dashboard())
            await asyncio.sleep(refresh_interval)


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n\nReceived shutdown signal...")
    shutdown_event.set()


async def main_async():
    """Main async entry point"""
    global servers

    print("=" * 60)
    print("MCP Servers Launcher - Interactive Dashboard")
    print("=" * 60)
    print()
    print("NOTE: For background servers that survive terminal closure, use:")
    print("  Windows: start_servers.bat")
    print("  Command: python mcp_server_daemon.py start")
    print()
    print("This launcher keeps servers attached to the terminal.")
    print("Press Ctrl+C to stop all servers and exit.")
    print("=" * 60)
    print()
    
    # Check environment variables
    missing_vars = check_env_vars()
    if missing_vars:
        print("⚠️  Warning: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nSome servers may not work correctly without these.")
        print("Set them in your .env file or environment.\n")
    
    # Initialize server states
    for config in SERVERS_CONFIG:
        state = ServerState(
            name=config["name"],
            script=config["script"],
            port=config["port"],
            env_vars=config.get("env_vars", [])
        )
        servers[config["name"]] = state
    
    print(f"📁 Log directory: {LOG_DIR.absolute()}\n")
    
    # Start all servers
    print("Starting servers...")
    started_count = 0
    
    for name, server in servers.items():
        if start_server_process(server):
            started_count += 1
            print(f"  ✅ {server.name} starting on port {server.port}")
        else:
            print(f"  ❌ {server.name} failed to start")
    
    if started_count == 0:
        print("\n❌ No servers started successfully")
        return
    
    print(f"\n✅ Started {started_count}/{len(SERVERS_CONFIG)} servers")
    print("\nWaiting for servers to be ready...")
    await asyncio.sleep(3)
    
    # Start background tasks
    health_task = asyncio.create_task(health_check_loop())
    dashboard_task = asyncio.create_task(dashboard_loop())
    
    try:
        # Wait for shutdown signal
        while not shutdown_event.is_set():
            await asyncio.sleep(0.5)
    
    except asyncio.CancelledError:
        pass
    
    finally:
        # Cancel background tasks
        health_task.cancel()
        dashboard_task.cancel()
        
        try:
            await health_task
        except asyncio.CancelledError:
            pass
        
        try:
            await dashboard_task
        except asyncio.CancelledError:
            pass
        
        # Stop all servers
        print("\nStopping all servers...")
        for name, server in servers.items():
            if stop_server_process(server):
                print(f"  ✅ Stopped {server.name}")
            else:
                print(f"  ⚠️  Error stopping {server.name}")
        
        print("\n✅ All servers stopped.")
        print(f"📁 Logs available at: {LOG_DIR.absolute()}")


def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows-specific: handle Ctrl+C properly
    if sys.platform == 'win32':
        signal.signal(signal.SIGBREAK, signal_handler)
    
    # Run async main
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
