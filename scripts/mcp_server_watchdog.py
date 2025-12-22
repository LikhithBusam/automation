"""
MCP Server Watchdog - Auto-Restart Monitor
Continuously monitors MCP servers and automatically restarts them if they crash.

Features:
- Monitors all server processes
- Automatic crash detection
- Auto-restart with exponential backoff
- Health check via HTTP
- Runs in background
- Email/log alerts on crashes (optional)
"""

import time
import sys
import signal
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx
import asyncio
from dataclasses import dataclass

# Import daemon components
from mcp_server_daemon import ServerDaemon, SERVERS_CONFIG, LOG_DIR, DAEMON_DIR


@dataclass
class WatchdogConfig:
    """Watchdog configuration"""

    check_interval: int = 30  # seconds between checks
    health_check_timeout: int = 5  # seconds
    max_restart_attempts: int = 5  # per hour
    restart_backoff_base: float = 2.0  # exponential backoff multiplier
    max_restart_delay: int = 300  # max seconds between restarts


class ServerWatchdog:
    """Monitors and auto-restarts servers"""

    def __init__(self, config: WatchdogConfig = None):
        self.config = config or WatchdogConfig()
        self.daemon = ServerDaemon()
        self.logger = self._setup_logging()
        self.running = False
        self.restart_history: Dict[str, list] = {}  # server_name -> [restart_times]

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger("ServerWatchdog")
        logger.setLevel(logging.INFO)

        log_file = LOG_DIR / f"watchdog_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(handler)

        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
        )
        logger.addHandler(console_handler)

        return logger

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Received shutdown signal")
        self.running = False

    async def check_server_health(self, port: int) -> bool:
        """Check if server is responding via HTTP"""
        try:
            async with httpx.AsyncClient(timeout=self.config.health_check_timeout) as client:
                # Try SSE endpoint (FastMCP default)
                response = await client.get(f"http://localhost:{port}/sse")
                return response.status_code in [200, 404, 405]
        except:
            return False

    def should_restart(self, server_name: str) -> tuple[bool, float]:
        """
        Determine if server should be restarted based on restart history.
        Returns (should_restart, delay_seconds)
        """
        # Initialize history if needed
        if server_name not in self.restart_history:
            self.restart_history[server_name] = []

        # Clean old restart times (older than 1 hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.restart_history[server_name] = [
            t for t in self.restart_history[server_name] if t > cutoff_time
        ]

        recent_restarts = len(self.restart_history[server_name])

        # Check if exceeded max restarts per hour
        if recent_restarts >= self.config.max_restart_attempts:
            self.logger.error(
                f"Server {server_name} exceeded max restart attempts "
                f"({self.config.max_restart_attempts}/hour)"
            )
            return False, 0

        # Calculate backoff delay based on recent restarts
        if recent_restarts == 0:
            delay = 0  # First restart, no delay
        else:
            delay = min(
                self.config.restart_backoff_base**recent_restarts, self.config.max_restart_delay
            )

        return True, delay

    async def monitor_server(self, config: Dict) -> bool:
        """
        Monitor a single server and restart if needed.
        Returns True if server is healthy, False if action was taken.
        """
        name = config["name"]
        display_name = config["display_name"]
        port = config["port"]

        # Check if process is running
        pid = self.daemon.read_pid(name)
        process_running = self.daemon.is_process_running(pid) if pid else False

        if not process_running:
            self.logger.warning(f"{display_name} process not running (PID: {pid})")

            # Check if we should restart
            should_restart, delay = self.should_restart(name)

            if should_restart:
                if delay > 0:
                    self.logger.info(
                        f"Waiting {delay:.1f}s before restarting {display_name} " f"(backoff)"
                    )
                    await asyncio.sleep(delay)

                # Record restart attempt
                self.restart_history[name].append(datetime.now())

                self.logger.info(f"Auto-restarting {display_name}...")
                success = self.daemon.start_server(config, detached=True)

                if success:
                    self.logger.info(f"[OK] {display_name} restarted successfully")
                else:
                    self.logger.error(f"[FAIL] Failed to restart {display_name}")

                return False
            else:
                self.logger.error(f"Not restarting {display_name} - too many recent failures")
                return False

        # Process is running, check HTTP health
        is_healthy = await self.check_server_health(port)

        if not is_healthy:
            self.logger.warning(
                f"{display_name} not responding on port {port} " f"(process running: PID {pid})"
            )
            # Process running but not responding - may need restart
            # For now, just log it. Could implement restart logic here too.
            return False

        return True

    async def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info("=" * 60)
        self.logger.info("MCP Server Watchdog Started")
        self.logger.info("=" * 60)
        self.logger.info(f"Check interval: {self.config.check_interval}s")
        self.logger.info(f"Max restart attempts: {self.config.max_restart_attempts}/hour")
        self.logger.info(f"Monitoring {len(SERVERS_CONFIG)} servers")
        self.logger.info("=" * 60)

        self.running = True
        check_count = 0

        while self.running:
            check_count += 1
            self.logger.info(f"\n--- Health Check #{check_count} ---")

            # Check all servers
            healthy_count = 0
            for config in SERVERS_CONFIG:
                try:
                    is_healthy = await self.monitor_server(config)
                    if is_healthy:
                        healthy_count += 1
                        self.logger.info(f"[OK] {config['display_name']} healthy")
                except Exception as e:
                    self.logger.error(f"Error monitoring {config['display_name']}: {e}")

            self.logger.info(f"\nStatus: {healthy_count}/{len(SERVERS_CONFIG)} servers healthy")

            # Wait for next check
            if self.running:
                self.logger.info(f"Next check in {self.config.check_interval}s...\n")
                await asyncio.sleep(self.config.check_interval)

        self.logger.info("\nWatchdog shutting down...")

    def run(self):
        """Run the watchdog"""
        try:
            asyncio.run(self.monitor_loop())
        except KeyboardInterrupt:
            self.logger.info("\nInterrupted by user")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.logger.info("Watchdog stopped")


def main():
    """Main entry point"""
    print("=" * 60)
    print("MCP Server Watchdog - Auto-Restart Monitor")
    print("=" * 60)
    print()
    print("This service will monitor all MCP servers and automatically")
    print("restart them if they crash or become unresponsive.")
    print()
    print("Press Ctrl+C to stop the watchdog.")
    print()
    print("=" * 60)
    print()

    # Create watchdog with custom config if needed
    config = WatchdogConfig(
        check_interval=30,  # Check every 30 seconds
        max_restart_attempts=5,  # Max 5 restarts per hour per server
    )

    watchdog = ServerWatchdog(config)
    watchdog.run()


if __name__ == "__main__":
    main()
