"""
MCP Server Daemon - Persistent Background Server Manager
Runs MCP servers as persistent background processes that survive terminal closure.

Features:
- Runs servers detached from terminal
- Automatic restart on failure
- Process isolation
- PID file management
- Log rotation
- Status monitoring
- Safe start/stop/restart operations
"""

import subprocess
import time
import sys
import os
import signal
import json
import atexit
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import threading
import logging

# Configuration
# Determine project root (parent of scripts directory)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Use absolute paths based on project root
DAEMON_DIR = PROJECT_ROOT / "daemon"
PID_DIR = DAEMON_DIR / "pids"
LOG_DIR = PROJECT_ROOT / "logs" / "mcp_servers"
STATE_FILE = DAEMON_DIR / "daemon_state.json"

# Create directories
DAEMON_DIR.mkdir(exist_ok=True)
PID_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Server configurations
SERVERS_CONFIG = [
    {
        "name": "github_server",
        "display_name": "GitHub Server",
        "script": PROJECT_ROOT / "mcp_servers/github_server.py",
        "port": 3000,
    },
    {
        "name": "filesystem_server",
        "display_name": "Filesystem Server",
        "script": PROJECT_ROOT / "mcp_servers/filesystem_server.py",
        "port": 3001,
    },
    {
        "name": "memory_server",
        "display_name": "Memory Server",
        "script": PROJECT_ROOT / "mcp_servers/memory_server.py",
        "port": 3002,
    },
    {
        "name": "codebasebuddy_server",
        "display_name": "CodeBaseBuddy Server",
        "script": PROJECT_ROOT / "mcp_servers/codebasebuddy_server.py",
        "port": 3004,
    }
]


@dataclass
class ServerState:
    """State information for a server"""
    name: str
    pid: Optional[int] = None
    port: int = 0
    status: str = "stopped"  # stopped, running, crashed, restarting
    start_time: Optional[str] = None
    restart_count: int = 0
    last_crash: Optional[str] = None


class DaemonState:
    """Manages daemon state persistence"""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.servers: Dict[str, ServerState] = {}
        self.load()

    def load(self):
        """Load state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for name, state_dict in data.items():
                        self.servers[name] = ServerState(**state_dict)
            except Exception as e:
                print(f"Warning: Could not load state: {e}")

    def save(self):
        """Save state to file"""
        try:
            data = {name: asdict(state) for name, state in self.servers.items()}
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")

    def update_server(self, name: str, **kwargs):
        """Update server state"""
        if name not in self.servers:
            self.servers[name] = ServerState(name=name)

        for key, value in kwargs.items():
            setattr(self.servers[name], key, value)

        self.save()

    def get_server(self, name: str) -> Optional[ServerState]:
        """Get server state"""
        return self.servers.get(name)


class ServerDaemon:
    """Manages background server processes"""

    def __init__(self):
        self.state = DaemonState(STATE_FILE)
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger("ServerDaemon")
        logger.setLevel(logging.INFO)

        log_file = LOG_DIR / f"daemon_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(handler)

        return logger

    def get_pid_file(self, server_name: str) -> Path:
        """Get PID file path for a server"""
        return PID_DIR / f"{server_name}.pid"

    def write_pid(self, server_name: str, pid: int):
        """Write PID to file"""
        pid_file = self.get_pid_file(server_name)
        with open(pid_file, 'w') as f:
            f.write(str(pid))

    def read_pid(self, server_name: str) -> Optional[int]:
        """Read PID from file"""
        pid_file = self.get_pid_file(server_name)
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    return int(f.read().strip())
            except:
                return None
        return None

    def delete_pid(self, server_name: str):
        """Delete PID file"""
        pid_file = self.get_pid_file(server_name)
        if pid_file.exists():
            pid_file.unlink()

    def is_process_running(self, pid: int) -> bool:
        """Check if process is running"""
        if pid is None:
            return False

        try:
            if sys.platform == 'win32':
                # Windows: use tasklist
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}'],
                    capture_output=True,
                    text=True
                )
                return str(pid) in result.stdout
            else:
                # Unix: send signal 0
                os.kill(pid, 0)
                return True
        except (OSError, subprocess.SubprocessError):
            return False

    def start_server(self, config: Dict[str, Any], detached: bool = True) -> bool:
        """Start a server process"""
        name = config['name']
        script = Path(config['script'])

        if not script.exists():
            self.logger.error(f"Script not found: {script}")
            return False

        # Check if already running
        pid = self.read_pid(name)
        if pid and self.is_process_running(pid):
            self.logger.info(f"{config['display_name']} already running (PID: {pid})")
            return True

        # Prepare log files
        log_file = LOG_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"

        try:
            self.logger.info(f"Starting {config['display_name']} on port {config['port']}")

            if detached:
                # Start detached process (survives terminal closure)
                if sys.platform == 'win32':
                    # Windows: use CREATE_NEW_PROCESS_GROUP and CREATE_NO_WINDOW
                    DETACHED_PROCESS = 0x00000008
                    CREATE_NEW_PROCESS_GROUP = 0x00000200
                    CREATE_NO_WINDOW = 0x08000000

                    with open(log_file, 'a') as log:
                        process = subprocess.Popen(
                            [sys.executable, "-u", str(script)],
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL,
                            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
                            close_fds=True
                        )
                else:
                    # Unix: use nohup and setsid for full detachment
                    with open(log_file, 'a') as log:
                        process = subprocess.Popen(
                            [sys.executable, "-u", str(script)],
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL,
                            start_new_session=True,  # Detach from terminal
                            close_fds=True
                        )
            else:
                # Start attached process (for debugging)
                with open(log_file, 'a') as log:
                    process = subprocess.Popen(
                        [sys.executable, "-u", str(script)],
                        stdout=log,
                        stderr=subprocess.STDOUT
                    )

            pid = process.pid
            self.write_pid(name, pid)

            # Update state
            self.state.update_server(
                name,
                pid=pid,
                port=config['port'],
                status="running",
                start_time=datetime.now().isoformat()
            )

            self.logger.info(f"{config['display_name']} started (PID: {pid})")
            print(f"[OK] {config['display_name']} started (PID: {pid})")

            # Brief wait to ensure server starts
            time.sleep(1)

            # Verify it's still running
            if not self.is_process_running(pid):
                self.logger.error(f"{config['display_name']} failed to start")
                self.state.update_server(name, status="crashed")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to start {config['display_name']}: {e}")
            self.state.update_server(name, status="crashed")
            return False

    def stop_server(self, config: Dict[str, Any]) -> bool:
        """Stop a server process"""
        name = config['name']
        pid = self.read_pid(name)

        if not pid:
            print(f"[OK] {config['display_name']} not running")
            self.state.update_server(name, pid=None, status="stopped")
            return True

        if not self.is_process_running(pid):
            print(f"[OK] {config['display_name']} not running (stale PID)")
            self.delete_pid(name)
            self.state.update_server(name, pid=None, status="stopped")
            return True

        try:
            self.logger.info(f"Stopping {config['display_name']} (PID: {pid})")

            if sys.platform == 'win32':
                # Windows: use taskkill
                subprocess.run(
                    ['taskkill', '/F', '/PID', str(pid), '/T'],
                    capture_output=True
                )
            else:
                # Unix: send SIGTERM, then SIGKILL if needed
                os.kill(pid, signal.SIGTERM)

                # Wait for graceful shutdown
                for _ in range(10):
                    if not self.is_process_running(pid):
                        break
                    time.sleep(0.5)

                # Force kill if still running
                if self.is_process_running(pid):
                    os.kill(pid, signal.SIGKILL)

            self.delete_pid(name)
            self.state.update_server(name, pid=None, status="stopped")

            self.logger.info(f"{config['display_name']} stopped")
            print(f"[OK] {config['display_name']} stopped")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping {config['display_name']}: {e}")
            return False

    def restart_server(self, config: Dict[str, Any]) -> bool:
        """Restart a server"""
        self.stop_server(config)
        time.sleep(1)
        return self.start_server(config)

    def status(self):
        """Show status of all servers"""
        print("\n" + "=" * 70)
        print("MCP Server Daemon Status")
        print("=" * 70)
        print(f"{'Server':<25} {'PID':<10} {'Port':<8} {'Status':<12} {'Uptime':<15}")
        print("-" * 70)

        for config in SERVERS_CONFIG:
            name = config['name']
            state = self.state.get_server(name)
            pid = self.read_pid(name)

            # Determine actual status
            if pid and self.is_process_running(pid):
                status = "running"
                uptime = self._calculate_uptime(state.start_time if state else None)
            else:
                status = "stopped"
                pid = None
                uptime = "-"

            # Update state if changed
            if state and state.status != status:
                self.state.update_server(name, status=status, pid=pid)

            print(f"{config['display_name']:<25} {str(pid) if pid else '-':<10} "
                  f"{config['port']:<8} {status:<12} {uptime:<15}")

        print("=" * 70)
        print(f"\nPID files: {PID_DIR}")
        print(f"Logs: {LOG_DIR}")
        print()

    def _calculate_uptime(self, start_time_str: Optional[str]) -> str:
        """Calculate uptime from start time"""
        if not start_time_str:
            return "-"

        try:
            start_time = datetime.fromisoformat(start_time_str)
            uptime = datetime.now() - start_time

            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m {seconds}s"
        except:
            return "-"

    def find_server_pid(self, port: int) -> Optional[int]:
        """Find PID of process listening on a specific port"""
        try:
            if sys.platform == 'win32':
                # Windows: use netstat
                result = subprocess.run(
                    ['netstat', '-ano'],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        pid = int(parts[-1])
                        return pid
            else:
                # Unix: use lsof
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    return int(result.stdout.strip().split()[0])
        except:
            pass
        return None

    def adopt_existing_servers(self):
        """Detect and adopt already running servers"""
        print("\nScanning for existing server processes...")
        adopted_count = 0

        for config in SERVERS_CONFIG:
            name = config['name']
            port = config['port']

            # Check if we already have a PID
            existing_pid = self.read_pid(name)
            if existing_pid and self.is_process_running(existing_pid):
                print(f"[OK] {config['display_name']} already managed (PID: {existing_pid})")
                continue

            # Look for process on the port
            pid = self.find_server_pid(port)
            if pid and self.is_process_running(pid):
                print(f"[OK] Found existing {config['display_name']} (PID: {pid})")
                self.write_pid(name, pid)
                self.state.update_server(
                    name,
                    pid=pid,
                    port=port,
                    status="running",
                    start_time=datetime.now().isoformat()
                )
                adopted_count += 1
            else:
                print(f"  {config['display_name']} not running on port {port}")

        if adopted_count > 0:
            print(f"\n[OK] Adopted {adopted_count} existing server(s)")
        return adopted_count

    def start_all(self, detached: bool = True):
        """Start all servers"""
        print("\nStarting all MCP servers...")

        # First, try to adopt existing servers
        self.adopt_existing_servers()

        success_count = 0

        for config in SERVERS_CONFIG:
            # Check if already running (either adopted or previously started)
            pid = self.read_pid(config['name'])
            if pid and self.is_process_running(pid):
                success_count += 1
                continue

            if self.start_server(config, detached=detached):
                success_count += 1
            time.sleep(0.5)  # Brief delay between starts

        print(f"\n[OK] {success_count}/{len(SERVERS_CONFIG)} servers running")
        time.sleep(2)  # Wait for servers to stabilize
        self.status()

    def stop_all(self):
        """Stop all servers"""
        print("\nStopping all MCP servers...")

        for config in SERVERS_CONFIG:
            self.stop_server(config)

        print("\n[OK] All servers stopped")

    def restart_all(self):
        """Restart all servers"""
        print("\nRestarting all MCP servers...")
        self.stop_all()
        time.sleep(1)
        self.start_all()


def main():
    """Main entry point"""
    daemon = ServerDaemon()

    if len(sys.argv) < 2:
        print("Usage: python mcp_server_daemon.py {start|stop|restart|status}")
        print()
        print("Commands:")
        print("  start   - Start all MCP servers in background")
        print("  stop    - Stop all MCP servers")
        print("  restart - Restart all MCP servers")
        print("  status  - Show server status")
        print()
        print("The servers will run in the background and survive terminal closure.")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        daemon.start_all(detached=True)
    elif command == "stop":
        daemon.stop_all()
    elif command == "restart":
        daemon.restart_all()
    elif command == "status":
        daemon.status()
    else:
        print(f"Unknown command: {command}")
        print("Use: start, stop, restart, or status")
        sys.exit(1)


if __name__ == "__main__":
    main()
