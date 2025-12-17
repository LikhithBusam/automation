# Quick Start - MCP Server Management

## ✅ Problem Fixed!

Your MCP servers will no longer be interrupted. They now run persistently in the background!

---

## 🚀 How to Use (Windows)

### Option 1: Use Batch Files (Easiest)

#### Start Servers
```bash
Double-click: start_servers.bat
```
- Starts all 3 MCP servers in background
- You can close the window - servers keep running!
- Servers survive terminal closure

#### Check Status
```bash
Double-click: check_servers.bat
```
- Shows which servers are running
- Displays PID, port, uptime

#### Stop Servers
```bash
Double-click: stop_servers.bat
```
- Gracefully stops all servers

#### Start Auto-Restart Monitor (Optional)
```bash
Double-click: start_watchdog.bat
```
- Monitors servers every 30 seconds
- Auto-restarts if they crash
- Keep this window open or minimize it

---

### Option 2: Use Python Commands

```bash
# Start servers in background
python mcp_server_daemon.py start

# Check status
python mcp_server_daemon.py status

# Stop servers
python mcp_server_daemon.py stop

# Restart servers
python mcp_server_daemon.py restart

# Run watchdog (optional)
python mcp_server_watchdog.py
```

---

## 📊 What's Different?

### Before
- ❌ Servers stopped when you closed terminal
- ❌ Ctrl+C accidentally killed everything
- ❌ Manual restart every time
- ❌ No crash recovery

### After
- ✅ Servers run in background
- ✅ Survive terminal closure
- ✅ Auto-restart on crash (with watchdog)
- ✅ Easy start/stop/status management
- ✅ Process isolation and PID tracking
- ✅ Comprehensive logging

---

## 📁 Important Files

### New Server Management
- `mcp_server_daemon.py` - Server manager
- `mcp_server_watchdog.py` - Auto-restart monitor
- `start_servers.bat` - Start servers (Windows)
- `stop_servers.bat` - Stop servers (Windows)
- `check_servers.bat` - Check status (Windows)
- `start_watchdog.bat` - Start auto-restart monitor (Windows)
- `SERVER_MANAGEMENT.md` - Comprehensive documentation

### Logs & State
- `logs/mcp_servers/` - All server logs
- `daemon/pids/` - Process ID files
- `daemon/daemon_state.json` - Server state

### Old Files (Still Work)
- `start_mcp_servers.py` - Interactive dashboard (for dev/debugging)

---

## 🔧 Typical Workflow

### Daily Use

1. **Start servers** (once):
   ```bash
   start_servers.bat
   ```

2. **Work normally**
   - Servers run in background
   - Close terminals freely
   - No interruptions

3. **Stop when done** (optional):
   ```bash
   stop_servers.bat
   ```

### With Auto-Restart Protection

1. **Start servers**:
   ```bash
   start_servers.bat
   ```

2. **Start watchdog** (keep window open or minimize):
   ```bash
   start_watchdog.bat
   ```

3. **Work safely**
   - Servers auto-restart if they crash
   - Monitored every 30 seconds
   - Max 5 restarts per hour per server

---

## 🆘 Troubleshooting

### Servers won't start
```bash
# Check status
check_servers.bat

# Check logs
type logs\mcp_servers\github_server_20251216.log

# Force restart
stop_servers.bat
start_servers.bat
```

### Port already in use
```bash
# Find what's using the port
netstat -ano | findstr "3000"

# Kill the process
taskkill /F /PID <pid>

# Or just restart
restart_servers.bat
```

### Watchdog not restarting
- Check `logs\mcp_servers\watchdog_*.log`
- May have hit max restart limit (5/hour)
- Fix the underlying issue and restart manually

---

## 📚 More Information

- **Full Documentation**: [SERVER_MANAGEMENT.md](SERVER_MANAGEMENT.md)
- **Project Guide**: [PROJECT_EXPLANATION.md](PROJECT_EXPLANATION.md)
- **Main README**: [README.md](README.md)

---

## ✨ Key Benefits

1. **No More Interruptions**
   - Servers survive terminal closure
   - Immune to accidental Ctrl+C
   - Process isolation

2. **Automatic Recovery**
   - Watchdog monitors health
   - Auto-restart on crash
   - Exponential backoff prevents loops

3. **Easy Management**
   - Simple batch files
   - Clear status reporting
   - Comprehensive logging

4. **Production Ready**
   - Background execution
   - PID management
   - State persistence

---

**You're all set! Your servers will now run reliably without interruptions.**
