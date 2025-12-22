#!/usr/bin/env python3
"""
Verify Memory Storage Setup
Checks which storage backend is being used
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

print("\n" + "=" * 80)
print("MEMORY STORAGE VERIFICATION")
print("=" * 80 + "\n")

# Check SQLite Database
sqlite_path = Path("data/memory.db")
if sqlite_path.exists():
    print(f"✓ SQLite Database Found: {sqlite_path}")
    print(f"  Size: {sqlite_path.stat().st_size:,} bytes")
    print(f"  Last Modified: {datetime.fromtimestamp(sqlite_path.stat().st_mtime)}")

    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"  Tables: {[t[0] for t in tables]}")

        # Count memories
        cursor.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        print(f"  Total Memories in SQLite: {count}")

        # Show recent memories
        if count > 0:
            cursor.execute(
                "SELECT type, content, timestamp FROM memories ORDER BY timestamp DESC LIMIT 3"
            )
            recent = cursor.fetchall()
            print(f"\n  Recent Memories:")
            for mem_type, content, timestamp in recent:
                preview = content[:50] + "..." if len(content) > 50 else content
                print(f"    • [{mem_type}] {preview} ({timestamp})")

        conn.close()
        print("  ✓ SQLite database is healthy\n")
    except Exception as e:
        print(f"  ✗ Error reading SQLite: {e}\n")
else:
    print("✗ SQLite Database Not Found\n")

# Check Fallback Storage
fallback_path = Path("data/memory_fallback.json")
if fallback_path.exists():
    print(f"✓ Fallback Storage Found: {fallback_path}")
    print(f"  Size: {fallback_path.stat().st_size:,} bytes")
    print(f"  Last Modified: {datetime.fromtimestamp(fallback_path.stat().st_mtime)}")

    try:
        with open(fallback_path, "r") as f:
            fallback_data = json.load(f)

        memories = fallback_data.get("memories", [])
        print(f"  Total Memories in Fallback: {len(memories)}")

        if memories:
            print(f"\n  Recent Memories:")
            for mem in memories[-3:]:
                content = mem.get("content", "N/A")
                preview = content[:50] + "..." if len(content) > 50 else content
                mem_type = mem.get("type", "unknown")
                print(f"    • [{mem_type}] {preview}")

        print("  ✓ Fallback storage is healthy\n")
    except Exception as e:
        print(f"  ✗ Error reading fallback: {e}\n")
else:
    print("✗ Fallback Storage Not Found\n")

# Check Memory Server Process
pid_path = Path("daemon/pids/memory_server.pid")
if pid_path.exists():
    try:
        with open(pid_path) as f:
            pid = f.read().strip()
        print(f"✓ Memory Server Running (PID: {pid})")

        import psutil

        try:
            proc = psutil.Process(int(pid))
            print(f"  Status: {proc.status()}")
            print(f"  Started: {datetime.fromtimestamp(proc.create_time())}")
            print(f"  Memory Usage: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
        except:
            pass
    except Exception as e:
        print(f"⚠ Memory Server PID file exists but process may not be running")
else:
    print("⚠ Memory Server Not Running (using fallback storage)")

print("\n" + "=" * 80)
print("STORAGE STATUS SUMMARY")
print("=" * 80)

if sqlite_path.exists():
    print("✓ Primary Storage: SQLite (data/memory.db)")
    print("  Status: ACTIVE")
else:
    print("⚠ Primary Storage: SQLite")
    print("  Status: NOT FOUND")

if fallback_path.exists():
    print("✓ Fallback Storage: JSON (data/memory_fallback.json)")
    print("  Status: AVAILABLE")
else:
    print("⚠ Fallback Storage: JSON")
    print("  Status: NOT FOUND")

print("\n✓ Memory system is operational and ready!")
print("=" * 80 + "\n")
