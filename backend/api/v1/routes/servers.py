"""
MCP Servers API Routes
Provides endpoints to check MCP server status and manage them
"""
import asyncio
import logging
import socket
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/servers", tags=["servers"])
logger = logging.getLogger(__name__)

# MCP Server configurations
MCP_SERVERS = [
    {
        "id": "github",
        "name": "GitHub Server",
        "port": 3000,
        "icon": "github",
    },
    {
        "id": "filesystem",
        "name": "Filesystem Server",
        "port": 3001,
        "icon": "folder",
    },
    {
        "id": "memory",
        "name": "Memory Server",
        "port": 3002,
        "icon": "brain",
    },
    {
        "id": "codebasebuddy",
        "name": "CodeBaseBuddy",
        "port": 3004,
        "icon": "code",
    },
]


class ServerStatus(BaseModel):
    id: str
    name: str
    port: int
    status: str  # running, stopped, error
    icon: str
    message: Optional[str] = None


class ServersStatusResponse(BaseModel):
    servers: List[ServerStatus]


async def check_server_health(server: Dict[str, Any], timeout: float = 2.0) -> ServerStatus:
    """Check if a single MCP server is running by trying to connect to its port"""
    port = server['port']
    
    def check_port():
        """Try to connect to the port"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex(('localhost', port))
            return result == 0  # 0 means connection successful
        finally:
            sock.close()
    
    try:
        # Run socket check in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        is_running = await loop.run_in_executor(None, check_port)
        
        if is_running:
            return ServerStatus(
                id=server["id"],
                name=server["name"],
                port=server["port"],
                status="running",
                icon=server["icon"],
                message="Server is listening"
            )
        else:
            return ServerStatus(
                id=server["id"],
                name=server["name"],
                port=server["port"],
                status="stopped",
                icon=server["icon"],
                message="Port not listening"
            )
    except Exception as e:
        return ServerStatus(
            id=server["id"],
            name=server["name"],
            port=server["port"],
            status="error",
            icon=server["icon"],
            message=str(e)
        )


@router.get("/status", response_model=ServersStatusResponse)
async def get_servers_status():
    """Get status of all MCP servers"""
    # Check all servers concurrently
    tasks = [check_server_health(server) for server in MCP_SERVERS]
    statuses = await asyncio.gather(*tasks)
    
    return ServersStatusResponse(servers=list(statuses))


@router.get("/{server_id}/status", response_model=ServerStatus)
async def get_server_status(server_id: str):
    """Get status of a specific MCP server"""
    server = next((s for s in MCP_SERVERS if s["id"] == server_id), None)
    
    if not server:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' not found")
    
    return await check_server_health(server)


@router.post("/{server_id}/restart")
async def restart_server(server_id: str):
    """Restart a specific MCP server (placeholder - needs actual implementation)"""
    server = next((s for s in MCP_SERVERS if s["id"] == server_id), None)
    
    if not server:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' not found")
    
    # TODO: Implement actual restart logic
    # This would need to call the MCP server manager script
    
    return {
        "success": True,
        "message": f"Restart signal sent to {server['name']}",
        "server_id": server_id
    }


@router.get("/{server_id}/logs")
async def get_server_logs(server_id: str, lines: int = 100):
    """Get logs for a specific MCP server"""
    from pathlib import Path
    from datetime import datetime
    
    server = next((s for s in MCP_SERVERS if s["id"] == server_id), None)
    
    if not server:
        raise HTTPException(status_code=404, detail=f"Server '{server_id}' not found")
    
    # Look for log file
    log_dir = Path("./logs/mcp_servers")
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"{server_id}_server_{today}.log"
    
    if not log_file.exists():
        # Try alternative naming
        log_file = log_dir / f"{server['name'].lower().replace(' ', '_')}_{today}.log"
    
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                return {
                    "server_id": server_id,
                    "log_file": str(log_file),
                    "lines": all_lines[-lines:]
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading logs: {e}")
    
    return {
        "server_id": server_id,
        "log_file": None,
        "lines": [],
        "message": "No log file found for today"
    }
