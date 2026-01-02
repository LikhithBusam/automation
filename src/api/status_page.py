"""
Status Page API
System health visibility for users
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["status"])


class ComponentStatus(str, Enum):
    """Component status"""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"


class Component(BaseModel):
    """System component"""
    name: str
    status: ComponentStatus
    description: str
    last_updated: datetime


class Incident(BaseModel):
    """Incident information"""
    id: str
    title: str
    status: str  # "investigating", "identified", "monitoring", "resolved"
    impact: str  # "minor", "major", "critical"
    started_at: datetime
    resolved_at: Optional[datetime]
    updates: List[Dict[str, Any]]


class StatusPageResponse(BaseModel):
    """Status page response"""
    status: ComponentStatus
    components: List[Component]
    incidents: List[Incident]
    last_updated: datetime


@router.get("/", response_model=StatusPageResponse)
async def get_status():
    """Get overall system status"""
    # Check component health
    components = await _check_components()
    
    # Get active incidents
    incidents = await _get_active_incidents()
    
    # Determine overall status
    overall_status = _determine_overall_status(components)
    
    return StatusPageResponse(
        status=overall_status,
        components=components,
        incidents=incidents,
        last_updated=datetime.utcnow(),
    )


@router.get("/components")
async def get_components():
    """Get component status"""
    return await _check_components()


@router.get("/incidents")
async def get_incidents():
    """Get incidents"""
    return await _get_active_incidents()


@router.get("/history")
async def get_status_history(days: int = 30):
    """Get status history"""
    # Implementation would query historical data
    return {
        "period": f"Last {days} days",
        "uptime_percentage": 99.9,
        "incidents": [],
    }


async def _check_components() -> List[Component]:
    """Check status of all components"""
    from src.api.health import HealthChecker
    
    health_checker = HealthChecker()
    components = []
    
    # Check API
    api_status = ComponentStatus.OPERATIONAL
    try:
        # API is operational if we can respond
        pass
    except Exception:
        api_status = ComponentStatus.DOWN
    
    components.append(Component(
        name="API",
        status=api_status,
        description="Main API service",
        last_updated=datetime.utcnow(),
    ))
    
    # Check Database
    db_health = await health_checker.check_database()
    db_status = ComponentStatus.OPERATIONAL
    if db_health.status.value == "unhealthy":
        db_status = ComponentStatus.DOWN
    elif db_health.status.value == "degraded":
        db_status = ComponentStatus.DEGRADED
    
    components.append(Component(
        name="Database",
        status=db_status,
        description=f"PostgreSQL database - {db_health.message}",
        last_updated=datetime.utcnow(),
    ))
    
    # Check Redis
    redis_health = await health_checker.check_redis()
    redis_status = ComponentStatus.OPERATIONAL
    if redis_health.status.value == "unhealthy":
        redis_status = ComponentStatus.DOWN
    elif redis_health.status.value == "degraded":
        redis_status = ComponentStatus.DEGRADED
    
    components.append(Component(
        name="Redis",
        status=redis_status,
        description=f"Redis cache - {redis_health.message}",
        last_updated=datetime.utcnow(),
    ))
    
    # Check MCP Servers
    mcp_health_list = await health_checker.check_mcp_servers()
    mcp_status = ComponentStatus.OPERATIONAL
    if any(h.status.value == "unhealthy" for h in mcp_health_list):
        mcp_status = ComponentStatus.DOWN
    elif any(h.status.value == "degraded" for h in mcp_health_list):
        mcp_status = ComponentStatus.DEGRADED
    
    components.append(Component(
        name="MCP Servers",
        status=mcp_status,
        description=f"MCP tool servers - {len([h for h in mcp_health_list if h.status.value == 'healthy'])}/{len(mcp_health_list)} healthy",
        last_updated=datetime.utcnow(),
    ))
    
    return components


async def _get_active_incidents() -> List[Incident]:
    """Get active incidents"""
    # In production, query from incident management system
    return []


def _determine_overall_status(components: List[Component]) -> ComponentStatus:
    """Determine overall system status"""
    if any(c.status == ComponentStatus.DOWN for c in components):
        return ComponentStatus.DOWN
    elif any(c.status == ComponentStatus.DEGRADED for c in components):
        return ComponentStatus.DEGRADED
    elif any(c.status == ComponentStatus.MAINTENANCE for c in components):
        return ComponentStatus.MAINTENANCE
    else:
        return ComponentStatus.OPERATIONAL

