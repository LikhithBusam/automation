# MCP Server Management Guide

## Overview

This project now includes robust server management tools that prevent interruptions and ensure servers run persistently in the background.

### Problem Solved

Previously, MCP servers would:
- Stop when you closed the terminal
- Get interrupted by Ctrl+C accidentally
- Not automatically restart if they crashed
- Require manual restart every time

### New Solution

The new server management system provides:
- ✅ **Background execution** - Servers run detached from terminal
- ✅ **Persistence** - Servers survive terminal closure
- ✅ **Auto-restart** - Automatic recovery from crashes
- ✅ **Health monitoring** - Continuous health checks
- ✅ **Easy management** - Simple batch files for Windows
- ✅ **Process isolation** - Servers run independently
- ✅ **PID management** - Track and control server processes
- ✅ **Logging** - Comprehensive logs for debugging

---

## Quick Start (Windows)

### Start Servers
```bash
# Double-click or run:
start_servers.bat
```

This starts all 3 MCP servers in the background. You can close the window and servers will keep running.

### Check Status
```bash
# Double-click or run:
check_servers.bat
```

Shows which servers are running, their PIDs, ports, and uptime.

### Stop Servers
```bash
# Double-click or run:
stop_servers.bat
```

Gracefully stops all servers.

### Restart Servers
```bash
# Double-click or run:
restart_servers.bat
```

Stops and restarts all servers.

### Start Watchdog (Auto-Restart)
```bash
# Double-click or run:
start_watchdog.bat
```

Starts a monitoring service that automatically restarts servers if they crash.

---

## Advanced Usage

### Using Python Commands Directly

#### Start servers in background:
```bash
python mcp_server_daemon.py start
```

#### Check server status:
```bash
python mcp_server_daemon.py status
```

#### Stop all servers:
```bash
python mcp_server_daemon.py stop
```

#### Restart all servers:
```bash
python mcp_server_daemon.py restart
```

#### Run watchdog (auto-restart monitor):
```bash
python mcp_server_watchdog.py
```

---

## System Architecture

### Components

1. **`mcp_server_daemon.py`** - Server process manager
   - Starts servers as detached background processes
   - Manages PID files
   - Tracks server state
   - Provides start/stop/restart/status commands

2. **`mcp_server_watchdog.py`** - Auto-restart monitor
   - Monitors server health every 30 seconds
   - Checks both process status and HTTP health
   - Automatically restarts crashed servers
   - Implements exponential backoff to prevent restart loops
   - Limits max restarts per hour to prevent infinite loops

3. **`start_mcp_servers.py`** - Interactive dashboard (original)
   - Real-time status dashboard
   - Manual control
   - Useful for development/debugging

### How It Works

#### Background Server Startup

When you run `start_servers.bat`:

1. **Daemon creates detached processes** using:
   - Windows: `CREATE_NEW_PROCESS_GROUP` + `CREATE_NO_WINDOW` + `DETACHED_PROCESS` flags
   - Unix: `start_new_session=True` for full terminal detachment

2. **PID files created** in `daemon/pids/`
   - `github_server.pid`
   - `filesystem_server.pid`
   - `memory_server.pid`

3. **State tracked** in `daemon/daemon_state.json`
   - Server name, PID, port, status
   - Start time, restart count
   - Last crash timestamp

4. **Logs written** to `logs/mcp_servers/`
   - Separate log file per server
   - Daily rotation (filename includes date)
   - All stdout/stderr captured

#### Process Isolation

Servers run completely independent of the terminal:
- Separate process groups (Windows) or sessions (Unix)
- No stdin attached
- stdout/stderr redirected to log files
- Parent process can exit without affecting servers

#### Auto-Restart Mechanism

The watchdog service:

1. **Checks every 30 seconds**:
   - Is the process running? (via PID check)
   - Is the server responding? (via HTTP health check on `/sse` endpoint)

2. **On failure detection**:
   - Logs the failure
   - Checks restart history (last hour)
   - If under max attempts (5/hour), calculates backoff delay
   - Waits backoff delay (exponential: 2^n seconds, max 5 min)
   - Restarts server
   - Records restart time

3. **Prevents restart loops**:
   - Max 5 restarts per hour per server
   - Exponential backoff between restarts
   - If max exceeded, requires manual intervention

---

## Configuration

### Server Definitions

Edit `mcp_server_daemon.py` to add/modify servers:

```python
SERVERS_CONFIG = [
    {
        "name": "github_server",
        "display_name": "GitHub Server",
        "script": "mcp_servers/github_server.py",
        "port": 3000,
    },
    # Add more servers here...
]
```

### Watchdog Settings

Edit `mcp_server_watchdog.py` to adjust monitoring:

```python
config = WatchdogConfig(
    check_interval=30,        # Seconds between health checks
    health_check_timeout=5,   # HTTP request timeout
    max_restart_attempts=5,   # Max restarts per hour
    restart_backoff_base=2.0, # Exponential backoff multiplier
    max_restart_delay=300,    # Max delay between restarts (5 min)
)
```

---

## File Locations

### Daemon Files

```
daemon/
├── pids/                    # PID files for running servers
│   ├── github_server.pid
│   ├── filesystem_server.pid
│   └── memory_server.pid
└── daemon_state.json        # Server state persistence
```

### Logs

```
logs/mcp_servers/
├── github_server_20251216.log
├── filesystem_server_20251216.log
├── memory_server_20251216.log
├── daemon_20251216.log      # Daemon operations
└── watchdog_20251216.log    # Watchdog monitoring
```

---

## Troubleshooting

### Servers won't start

1. **Check if already running**:
   ```bash
   python mcp_server_daemon.py status
   ```

2. **Check logs**:
   ```bash
   # Look at today's log files in logs/mcp_servers/
   type logs\mcp_servers\github_server_20251216.log
   ```

3. **Manually stop and restart**:
   ```bash
   python mcp_server_daemon.py stop
   python mcp_server_daemon.py start
   ```

### Server keeps crashing

1. **Check server logs** for error messages:
   ```bash
   type logs\mcp_servers\memory_server_20251216.log
   ```

2. **Common issues**:
   - Missing environment variables (e.g., `GITHUB_TOKEN`)
   - Port already in use
   - Python dependencies not installed
   - File permissions

3. **Test server directly**:
   ```bash
   python mcp_servers/github_server.py
   ```

### Watchdog not restarting servers

1. **Check watchdog logs**:
   ```bash
   type logs\mcp_servers\watchdog_20251216.log
   ```

2. **Verify max restart limit not exceeded**:
   - Watchdog limits to 5 restarts per hour per server
   - Check restart history in logs
   - If limit exceeded, fix underlying issue and restart manually

### Ports still in use after stop

1. **Force kill processes**:
   ```bash
   # Windows
   netstat -ano | findstr "300[0-2]"
   taskkill /F /PID <pid>
   ```

2. **Clean up PID files**:
   ```bash
   del daemon\pids\*.pid
   ```

---

## Migration from Old System

### Before (Old Way)
```bash
# Had to keep terminal open
python start_mcp_servers.py

# Ctrl+C would stop everything
# Terminal close would stop everything
```

### After (New Way)
```bash
# Start in background
start_servers.bat

# Can close terminal - servers keep running!

# Optional: Start watchdog for auto-restart
start_watchdog.bat
```

### Compatibility

The old `start_mcp_servers.py` still works if you prefer:
- Real-time dashboard
- Interactive control
- Development/debugging

But for production use, the new daemon + watchdog is recommended.

---

## Best Practices

### Production Deployment

1. **Start servers in background**:
   ```bash
   python mcp_server_daemon.py start
   ```

2. **Start watchdog** (in separate terminal or as service):
   ```bash
   python mcp_server_watchdog.py
   ```

3. **Monitor logs** periodically:
   ```bash
   tail -f logs/mcp_servers/watchdog_*.log
   ```

### Development

1. **Use interactive dashboard** for development:
   ```bash
   python start_mcp_servers.py
   ```

2. **Check status frequently**:
   ```bash
   python mcp_server_daemon.py status
   ```

3. **Read logs** when debugging:
   ```bash
   type logs\mcp_servers\github_server_*.log
   ```

### Maintenance

1. **Regular health checks**:
   ```bash
   python mcp_server_daemon.py status
   ```

2. **Log rotation** happens automatically (daily files)

3. **Clean old logs** periodically:
   ```bash
   # Delete logs older than 7 days
   forfiles /p logs\mcp_servers /s /m *.log /d -7 /c "cmd /c del @path"
   ```

---

## Windows Service Setup (Optional)

To run servers as a Windows service that starts automatically on boot:

### Using NSSM (Non-Sucking Service Manager)

1. **Download NSSM**: https://nssm.cc/download

2. **Install daemon as service**:
   ```bash
   nssm install MCP_Servers "C:\Python\python.exe" "C:\path\to\mcp_server_daemon.py start"
   nssm set MCP_Servers AppDirectory "C:\Users\Likith\OneDrive\Desktop\automaton"
   nssm start MCP_Servers
   ```

3. **Install watchdog as service**:
   ```bash
   nssm install MCP_Watchdog "C:\Python\python.exe" "C:\path\to\mcp_server_watchdog.py"
   nssm set MCP_Watchdog AppDirectory "C:\Users\Likith\OneDrive\Desktop\automaton"
   nssm start MCP_Watchdog
   ```

Now servers will start automatically on system boot!

---

## API Reference

### Daemon Commands

```python
from mcp_server_daemon import ServerDaemon

daemon = ServerDaemon()

# Start all servers
daemon.start_all(detached=True)

# Start specific server
daemon.start_server(config, detached=True)

# Stop all servers
daemon.stop_all()

# Stop specific server
daemon.stop_server(config)

# Restart server
daemon.restart_server(config)

# Check status
daemon.status()
```

### Watchdog Configuration

```python
from mcp_server_watchdog import ServerWatchdog, WatchdogConfig

config = WatchdogConfig(
    check_interval=30,
    max_restart_attempts=5,
)

watchdog = ServerWatchdog(config)
watchdog.run()
```

---

## Summary

### Key Features

1. ✅ **Background Execution** - Servers survive terminal closure
2. ✅ **Auto-Restart** - Automatic recovery from crashes
3. ✅ **Health Monitoring** - Continuous HTTP health checks
4. ✅ **Process Isolation** - Independent server processes
5. ✅ **Easy Management** - Simple batch file commands
6. ✅ **Comprehensive Logging** - Debug-friendly logs
7. ✅ **Exponential Backoff** - Prevents restart loops
8. ✅ **State Persistence** - Survives daemon restarts

### Files Created

- `mcp_server_daemon.py` - Server process manager
- `mcp_server_watchdog.py` - Auto-restart monitor
- `start_servers.bat` - Start servers (Windows)
- `stop_servers.bat` - Stop servers (Windows)
- `check_servers.bat` - Check status (Windows)
- `restart_servers.bat` - Restart servers (Windows)
- `start_watchdog.bat` - Start watchdog (Windows)
- `SERVER_MANAGEMENT.md` - This file

### No Breaking Changes

- Original `start_mcp_servers.py` still works
- All existing functionality preserved
- New daemon system is optional but recommended

---

## Support

For issues or questions:
1. Check logs in `logs/mcp_servers/`
2. Run status check: `python mcp_server_daemon.py status`
3. Review troubleshooting section above
4. Check GitHub issues (if applicable)

---

**Last Updated**: December 16, 2025
**Version**: 2.0.0 (AutoGen Edition with Persistent Server Management)
