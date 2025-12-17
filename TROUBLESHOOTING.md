# Troubleshooting Guide - MCP Servers

## Common Issues and Solutions

### Issue: Servers stuck in "starting" status with high restart count

**Symptoms:**
- Status shows "starting" but never becomes "running"
- Restart count is 3 or higher
- New PIDs keep appearing

**Cause:**
Port conflict - multiple processes trying to use the same ports (3000, 3001, 3002)

**Solution:**

1. **Stop ALL servers:**
   ```bash
   # Method 1: Using daemon
   python mcp_server_daemon.py stop

   # Method 2: Force kill by port
   # Find PIDs
   netstat -ano | findstr "300[0-2]"

   # Kill each process
   taskkill /F /PID <pid>
   ```

2. **Clean up PID files:**
   ```bash
   # Delete stale PID files
   del daemon\pids\*.pid
   ```

3. **Verify ports are free:**
   ```bash
   netstat -ano | findstr "LISTENING" | findstr "300[0-2]"
   # Should return nothing
   ```

4. **Start fresh:**
   ```bash
   # Using background daemon (recommended)
   python mcp_server_daemon.py start

   # OR using interactive dashboard
   python start_mcp_servers.py
   ```

---

### Issue: "Port already in use" error

**Symptoms:**
```
❌ GitHub Server - Port 3000 already in use!
Stop existing servers first with: python mcp_server_daemon.py stop
```

**Cause:**
Another server process is already using the port

**Solution:**

**Option 1: Stop existing servers**
```bash
python mcp_server_daemon.py stop
```

**Option 2: Find and kill the process**
```bash
# Find what's using the port
netstat -ano | findstr ":3000"
# Example output: TCP  0.0.0.0:3000  0.0.0.0:0  LISTENING  12345

# Kill it
taskkill /F /PID 12345
```

**Option 3: Use the daemon to adopt existing servers**
```bash
# The daemon will detect and manage already-running servers
python mcp_server_daemon.py start
```

---

### Issue: Can't start servers - they immediately crash

**Symptoms:**
- Servers start but immediately stop
- Status shows "crashed" or "failed"
- Logs show errors

**Common Causes & Solutions:**

#### 1. Missing Python dependencies
```bash
# Reinstall requirements
pip install -r requirements.txt
```

#### 2. Missing environment variables
```bash
# Check .env file exists
type .env

# Required variables (example):
# GITHUB_TOKEN=your_token_here
# Add missing variables to .env
```

#### 3. Check server logs
```bash
# Look at today's log files
type logs\mcp_servers\github_server_20251216.log
type logs\mcp_servers\filesystem_server_20251216.log
type logs\mcp_servers\memory_server_20251216.log

# Look for ERROR or exception messages
```

#### 4. Test server directly
```bash
# Try running a server directly to see errors
python mcp_servers/github_server.py

# If it fails, you'll see the error message
```

---

### Issue: Watchdog keeps restarting servers

**Symptoms:**
- Watchdog logs show frequent restarts
- "Max restart attempts exceeded" errors
- Servers keep crashing

**Cause:**
Underlying issue causing servers to crash repeatedly

**Solution:**

1. **Stop the watchdog:**
   ```
   Press Ctrl+C in watchdog terminal
   ```

2. **Check watchdog logs:**
   ```bash
   type logs\mcp_servers\watchdog_20251216.log
   # Look for patterns in crashes
   ```

3. **Fix the root cause:**
   - Check server logs for errors
   - Verify dependencies installed
   - Check environment variables
   - Ensure ports not blocked by firewall

4. **Test manually:**
   ```bash
   # Stop all servers
   python mcp_server_daemon.py stop

   # Start one server at a time
   python mcp_servers/github_server.py
   # Does it run? Check for errors

   # If successful, try daemon
   python mcp_server_daemon.py start
   ```

5. **Restart watchdog:**
   ```bash
   python mcp_server_watchdog.py
   ```

---

### Issue: Servers not responding / Health check failed

**Symptoms:**
- Watchdog shows "not responding on port"
- Process running but HTTP requests fail
- Status shows "unhealthy"

**Solution:**

1. **Check if server is actually running:**
   ```bash
   python mcp_server_daemon.py status
   ```

2. **Test HTTP endpoint manually:**
   ```bash
   # Using curl or browser
   curl http://localhost:3000/sse
   curl http://localhost:3001/sse
   curl http://localhost:3002/sse

   # Should return 200 or 404, not connection error
   ```

3. **Check firewall:**
   - Windows Firewall may be blocking local connections
   - Add Python to firewall exceptions
   - Or temporarily disable firewall to test

4. **Restart the problematic server:**
   ```bash
   python mcp_server_daemon.py restart
   ```

---

### Issue: Unicode/Encoding errors on Windows

**Symptoms:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'
```

**Cause:**
Windows console encoding issues (FIXED in latest version)

**Solution:**
Already fixed! The code now uses `[OK]` instead of checkmarks.

If you still see this:
1. Update to latest code
2. Or set console encoding:
   ```bash
   chcp 65001  # UTF-8
   ```

---

### Issue: Daemon shows wrong status

**Symptoms:**
- `python mcp_server_daemon.py status` shows servers running but they're not
- Or shows stopped but they are running

**Cause:**
Stale PID files or state file

**Solution:**

1. **Clean up:**
   ```bash
   # Delete PID files
   del daemon\pids\*.pid

   # Delete state file
   del daemon\daemon_state.json
   ```

2. **Check actual processes:**
   ```bash
   netstat -ano | findstr "300[0-2]"
   ```

3. **Restart daemon:**
   ```bash
   # Stop any running servers
   python mcp_server_daemon.py stop

   # Clean start
   python mcp_server_daemon.py start
   ```

---

### Issue: Can't stop servers

**Symptoms:**
- `stop_servers.bat` doesn't work
- Servers keep running
- `taskkill` fails

**Solution:**

1. **Force kill:**
   ```bash
   # Find PIDs
   netstat -ano | findstr "300[0-2]"

   # Force kill with /F flag
   taskkill /F /PID <pid>
   taskkill /F /PID <pid2>
   taskkill /F /PID <pid3>
   ```

2. **Kill all Python processes (nuclear option):**
   ```bash
   # WARNING: Kills ALL Python processes!
   taskkill /F /IM python.exe
   ```

3. **Restart computer** (last resort)

---

### Issue: Logs filling up disk space

**Symptoms:**
- `logs/mcp_servers/` directory very large
- Old log files accumulating

**Solution:**

1. **Manual cleanup:**
   ```bash
   # Delete logs older than 7 days
   forfiles /p logs\mcp_servers /s /m *.log /d -7 /c "cmd /c del @path"
   ```

2. **Keep only recent logs:**
   ```bash
   # Keep only today's logs
   cd logs\mcp_servers
   del *_202512*.log
   # (adjust date pattern)
   ```

3. **Automated cleanup script** (create `cleanup_logs.bat`):
   ```batch
   @echo off
   echo Cleaning up old log files...
   forfiles /p logs\mcp_servers /s /m *.log /d -7 /c "cmd /c del @path"
   echo Done!
   pause
   ```

---

## Diagnostic Commands

### Check server status
```bash
python mcp_server_daemon.py status
```

### Check what's using ports
```bash
netstat -ano | findstr "300[0-2]"
```

### View recent logs
```bash
# Last 20 lines of each server
Get-Content logs\mcp_servers\github_server_*.log -Tail 20
Get-Content logs\mcp_servers\filesystem_server_*.log -Tail 20
Get-Content logs\mcp_servers\memory_server_*.log -Tail 20
```

### Test HTTP endpoints
```bash
# PowerShell
Invoke-WebRequest http://localhost:3000/sse
Invoke-WebRequest http://localhost:3001/sse
Invoke-WebRequest http://localhost:3002/sse
```

### Check daemon health
```bash
# List PID files
dir daemon\pids

# View state
type daemon\daemon_state.json
```

---

## Prevention Tips

### 1. Always use one method consistently

**Don't mix:**
- ❌ Start with `start_mcp_servers.py` then use `mcp_server_daemon.py`
- ❌ Run both simultaneously

**Instead:**
- ✅ Use daemon for background: `start_servers.bat`
- ✅ OR use interactive: `python start_mcp_servers.py`
- ✅ Pick one and stick with it

### 2. Stop properly before starting

```bash
# Always stop first
python mcp_server_daemon.py stop

# Then start
python mcp_server_daemon.py start
```

### 3. Check status regularly

```bash
# Quick health check
python mcp_server_daemon.py status
```

### 4. Monitor logs

```bash
# Watch for errors
type logs\mcp_servers\*_20251216.log | findstr ERROR
```

### 5. Use watchdog for production

```bash
# Start watchdog after starting servers
start_watchdog.bat
# Keep it running for auto-recovery
```

---

## Getting Help

### Before asking for help, collect:

1. **Output of status command:**
   ```bash
   python mcp_server_daemon.py status
   ```

2. **Port check:**
   ```bash
   netstat -ano | findstr "300[0-2]"
   ```

3. **Recent log files:**
   ```bash
   type logs\mcp_servers\github_server_*.log
   type logs\mcp_servers\daemon_*.log
   type logs\mcp_servers\watchdog_*.log
   ```

4. **Error messages:**
   - Copy exact error text
   - Include full stack trace if available

5. **What you tried:**
   - List commands you ran
   - What happened vs what you expected

---

## Quick Reset (Nuclear Option)

If everything is broken and you want a fresh start:

```bash
# 1. Stop everything
python mcp_server_daemon.py stop

# 2. Force kill any remaining
taskkill /F /IM python.exe

# 3. Clean up
del daemon\pids\*.pid
del daemon\daemon_state.json

# 4. Verify ports free
netstat -ano | findstr "300[0-2]"
# (should be empty)

# 5. Fresh start
python mcp_server_daemon.py start

# 6. Verify
python mcp_server_daemon.py status
```

---

**Last Updated**: December 16, 2025
