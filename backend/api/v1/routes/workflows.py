"""
Workflow API Routes - Real AutoGen Integration
Connects the frontend to actual AutoGen agent workflows
"""
import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.autogen_adapters.conversation_manager import ConversationManager
from src.autogen_adapters.agent_factory import AutoGenAgentFactory

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger(__name__)

# In-memory job storage (use Redis/DB in production)
jobs: Dict[str, Dict[str, Any]] = {}

# Lazy-loaded managers
_conversation_manager: Optional[ConversationManager] = None


async def get_conversation_manager() -> ConversationManager:
    """Get or create conversation manager singleton"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
        await _conversation_manager.initialize()
    return _conversation_manager


# Request/Response Models
class WorkflowInfo(BaseModel):
    id: str
    name: str
    description: str
    type: str
    agentCount: int
    estimatedTime: str
    category: str


class AnalysisRequest(BaseModel):
    workflowId: str = Field(..., description="ID of the workflow to run")
    files: List[str] = Field(default=[], description="Files or paths to analyze")
    focusAreas: List[str] = Field(default=[], description="Areas to focus on")
    options: Dict[str, Any] = Field(default={}, description="Additional options")

    class Config:
        json_schema_extra = {
            "example": {
                "workflowId": "quick_code_review",
                "files": ["src/api/routes.py"],
                "focusAreas": ["security", "error handling"],
                "options": {}
            }
        }


class AnalysisResponse(BaseModel):
    id: str
    workflowId: str
    status: str
    createdAt: str
    estimatedDuration: float


class AnalysisResult(BaseModel):
    id: str
    workflowId: str
    workflowName: str
    status: str
    createdAt: str
    completedAt: Optional[str]
    duration: Optional[float]
    results: Optional[Dict[str, Any]]


# Available workflows (maps to autogen_workflows.yaml)
WORKFLOWS = {
    "quick_code_review": {
        "id": "quick_code_review",
        "name": "Quick Code Review",
        "description": "Fast code review using 2 agents (3-5 seconds)",
        "type": "two_agent",
        "agentCount": 2,
        "estimatedTime": "3-5s",
        "category": "quick"
    },
    "security_audit": {
        "id": "security_audit",
        "name": "Security Audit",
        "description": "Comprehensive security vulnerability assessment",
        "type": "groupchat",
        "agentCount": 3,
        "estimatedTime": "30-90s",
        "category": "comprehensive"
    },
    "code_analysis": {
        "id": "code_analysis",
        "name": "Code Analysis",
        "description": "In-depth code quality analysis with multiple agents",
        "type": "groupchat",
        "agentCount": 4,
        "estimatedTime": "20-60s",
        "category": "comprehensive"
    },
    "documentation_generation": {
        "id": "documentation_generation",
        "name": "Generate Documentation",
        "description": "Generate or update project documentation",
        "type": "groupchat",
        "agentCount": 2,
        "estimatedTime": "10-30s",
        "category": "quick"
    },
    "deployment": {
        "id": "deployment",
        "name": "Deployment Planning",
        "description": "Plan deployment strategy with CI/CD recommendations",
        "type": "groupchat",
        "agentCount": 2,
        "estimatedTime": "15-45s",
        "category": "comprehensive"
    }
}


@router.get("/", response_model=List[WorkflowInfo])
async def list_workflows():
    """List all available workflows"""
    return list(WORKFLOWS.values())


@router.get("/{workflow_id}", response_model=WorkflowInfo)
async def get_workflow(workflow_id: str):
    """Get workflow details by ID"""
    if workflow_id not in WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return WORKFLOWS[workflow_id]


async def read_file_contents(file_path: str) -> str:
    """Read file contents safely"""
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            return path.read_text(encoding='utf-8')
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {e}"


async def run_analysis_task(job_id: str, workflow_id: str, variables: Dict[str, Any]):
    """Background task to run the actual AutoGen workflow"""
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["startedAt"] = datetime.utcnow().isoformat()
        
        logger.info(f"Starting workflow '{workflow_id}' for job {job_id}")
        
        # Pre-read file contents since free models don't support function calling
        code_path = variables.get("CODE_PATH") or variables.get("code_path", "")
        logger.info(f"DEBUG: code_path = {code_path}")

        # Try to find the file if it doesn't exist at the given path
        file_path = Path(code_path) if code_path else None
        if file_path and not file_path.exists():
            # Frontend might send just filename, search for it
            workspace_root = Path(__file__).parent.parent.parent.parent.parent
            logger.info(f"DEBUG: File not found at {file_path}, searching in workspace...")
            filename = file_path.name
            # Search common directories
            search_dirs = [
                workspace_root / "src",
                workspace_root / "backend",
                workspace_root / "tests",
                workspace_root,
            ]
            for search_dir in search_dirs:
                if search_dir.exists():
                    # Use glob to find the file recursively
                    matches = list(search_dir.rglob(filename))
                    if matches:
                        file_path = matches[0]
                        logger.info(f"DEBUG: Found file at {file_path}")
                        break

        if file_path and file_path.exists():
            file_content = await read_file_contents(str(file_path))
            logger.info(f"DEBUG: Read file, size = {len(file_content)} bytes")
            # Add file content to variables for the workflow (UPPERCASE for template matching)
            variables["FILE_CONTENT"] = file_content  # Uppercase to match template
            variables["file_content"] = file_content  # Keep lowercase for backward compatibility
            variables["FILE_NAME"] = file_path.name
            variables["file_name"] = file_path.name
            variables["CODE_PATH"] = str(file_path)  # Update with actual path
            variables["code_path"] = str(file_path)

            # Count lines for metrics
            lines = file_content.count('\n') + 1 if file_content else 0
            variables["LINES_COUNT"] = lines
            variables["lines_count"] = lines
            logger.info(f"DEBUG: Variables keys = {list(variables.keys())}")
        else:
            logger.warning(f"DEBUG: File not found: {code_path}")
        
        # Get conversation manager and execute workflow
        manager = await get_conversation_manager()
        result = await manager.execute_workflow(workflow_id, variables)
        
        # Process result
        jobs[job_id]["status"] = "completed" if result.status == "success" else "failed"
        jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        jobs[job_id]["duration"] = result.duration_seconds
        
        # Extract analysis results
        issues = []
        agent_contributions = []
        
        # Parse messages for issues and contributions
        for i, msg in enumerate(result.messages):
            content = msg.get("content", "")
            sender = msg.get("name", msg.get("role", "unknown"))
            
            # Track agent contributions - send full message for documentation
            agent_contributions.append({
                "agentId": sender,
                "agentName": sender.replace("_", " ").title(),
                "timestamp": datetime.utcnow().isoformat(),
                "duration": result.duration_seconds / max(len(result.messages), 1),
                "findings": 1,
                "message": content  # Full content, frontend will handle display
            })
            
            # Look for security/code issues in messages
            if "critical" in content.lower() or "vulnerability" in content.lower():
                issues.append({
                    "id": str(uuid.uuid4()),
                    "severity": "critical",
                    "category": "security",
                    "title": "Security Issue Found",
                    "description": content[:500],
                    "file": variables.get("code_path", "unknown"),
                    "line": 0,
                    "resolved": False
                })
            elif "high" in content.lower() or "warning" in content.lower():
                issues.append({
                    "id": str(uuid.uuid4()),
                    "severity": "high",
                    "category": "code_quality",
                    "title": "Code Quality Issue",
                    "description": content[:500],
                    "file": variables.get("code_path", "unknown"),
                    "line": 0,
                    "resolved": False
                })
        
        # Calculate scores based on issues
        critical_count = len([i for i in issues if i["severity"] == "critical"])
        high_count = len([i for i in issues if i["severity"] == "high"])
        
        quality_score = max(1, 10 - (critical_count * 2) - high_count)
        security_score = max(1, 10 - (critical_count * 3) - (high_count * 1.5))
        
        jobs[job_id]["results"] = {
            "qualityScore": round(quality_score, 1),
            "securityScore": round(security_score, 1),
            "summary": result.summary,
            "recommendations": [
                "Review the identified issues",
                "Consider the agent recommendations",
                "Run additional security scans if needed"
            ],
            "issues": issues,
            "agentContributions": agent_contributions,
            "metrics": {
                "linesAnalyzed": variables.get("lines_count", 0),
                "filesReviewed": max(1, len(variables.get("files", []))),
                "issuesFound": len(issues),
                "criticalIssues": critical_count,
                "highIssues": high_count,
                "mediumIssues": 0,
                "lowIssues": 0,
                "timeSaved": f"~{max(1, int(result.duration_seconds * 10))} minutes"
            },
            "rawMessages": result.messages  # Include raw messages for debugging
        }
        
        logger.info(f"Workflow '{workflow_id}' completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Workflow execution failed for job {job_id}: {e}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()


@router.post("/analyze", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Start a new analysis workflow"""
    workflow_id = request.workflowId
    
    if workflow_id not in WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    
    # Create job
    job_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    # Get workspace root (project root directory)
    workspace_root = Path(__file__).parent.parent.parent.parent.parent
    
    # Convert relative paths to absolute paths
    absolute_files = []
    for file_path in request.files:
        if file_path:
            # Check if path is already absolute
            if Path(file_path).is_absolute():
                absolute_files.append(file_path)
            else:
                # Make path absolute relative to workspace root
                abs_path = workspace_root / file_path
                absolute_files.append(str(abs_path))
    
    # Use the first file as the main code path
    code_path = absolute_files[0] if absolute_files else str(workspace_root)
    
    # Prepare variables for the workflow
    # NOTE: Variable names must match template placeholders (case-sensitive)
    # Templates use UPPERCASE placeholders like {CODE_PATH}, {FILE_CONTENT}
    variables = {
        "CODE_PATH": code_path,  # Uppercase to match template
        "code_path": code_path,  # Keep lowercase for backward compatibility
        "FOCUS_AREAS": ", ".join(request.focusAreas) if request.focusAreas else "general review",
        "focus_areas": ", ".join(request.focusAreas) if request.focusAreas else "general review",
        "files": absolute_files,
        "workspace_root": str(workspace_root),
        **request.options
    }
    
    # Store job info
    jobs[job_id] = {
        "id": job_id,
        "workflowId": workflow_id,
        "workflowName": WORKFLOWS[workflow_id]["name"],
        "status": "pending",
        "createdAt": created_at,
        "completedAt": None,
        "duration": None,
        "variables": variables,
        "results": None,
        "error": None
    }
    
    # Add background task to run the workflow
    background_tasks.add_task(run_analysis_task, job_id, workflow_id, variables)
    
    return AnalysisResponse(
        id=job_id,
        workflowId=workflow_id,
        status="pending",
        createdAt=created_at,
        estimatedDuration=30.0  # Estimate
    )


@router.get("/analysis/{job_id}", response_model=AnalysisResult)
async def get_analysis(job_id: str):
    """Get analysis status and results"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Analysis job '{job_id}' not found")
    
    job = jobs[job_id]
    
    return AnalysisResult(
        id=job["id"],
        workflowId=job["workflowId"],
        workflowName=job["workflowName"],
        status=job["status"],
        createdAt=job["createdAt"],
        completedAt=job.get("completedAt"),
        duration=job.get("duration"),
        results=job.get("results")
    )


@router.get("/analysis", response_model=List[AnalysisResult])
async def list_analyses(limit: int = 20, status: Optional[str] = None):
    """List recent analyses"""
    results = list(jobs.values())
    
    # Filter by status if provided
    if status:
        results = [j for j in results if j["status"] == status]
    
    # Sort by creation time (newest first)
    results.sort(key=lambda x: x["createdAt"], reverse=True)
    
    # Limit results
    results = results[:limit]
    
    return [
        AnalysisResult(
            id=j["id"],
            workflowId=j["workflowId"],
            workflowName=j["workflowName"],
            status=j["status"],
            createdAt=j["createdAt"],
            completedAt=j.get("completedAt"),
            duration=j.get("duration"),
            results=j.get("results")
        )
        for j in results
    ]
