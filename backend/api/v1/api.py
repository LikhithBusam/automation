"""
API v1 router - Main API with AutoGen workflow integration
"""
from fastapi import APIRouter
from pydantic import BaseModel
import uuid

# Import workflow routes
from backend.api.v1.routes.workflows import router as workflows_router
from backend.api.v1.routes.servers import router as servers_router

api_router = APIRouter()

# Include workflow routes
api_router.include_router(workflows_router)

# Include MCP servers routes
api_router.include_router(servers_router)


# Pydantic models for request/response
class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"

    class Config:
        json_schema_extra = {
            "example": {
                "code": "def hello():\n    print('hello')",
                "language": "python"
            }
        }


# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AutoGen Development Assistant API",
        "version": "1.0.0"
    }


# Workflows endpoint
@api_router.get("/workflows")
async def list_workflows():
    """List available AutoGen workflows"""
    return {
        "workflows": [
            {
                "name": "quick_code_review",
                "description": "Fast code review (3-5 seconds)",
                "duration": "3-5s"
            },
            {
                "name": "security_audit",
                "description": "Security vulnerability assessment",
                "duration": "30-90s"
            },
            {
                "name": "code_analysis",
                "description": "Comprehensive code analysis",
                "duration": "20-60s"
            },
            {
                "name": "refactoring_suggestions",
                "description": "Get refactoring recommendations",
                "duration": "15-45s"
            },
            {
                "name": "documentation_gen",
                "description": "Generate documentation",
                "duration": "10-30s"
            }
        ]
    }


# Code review endpoint - simplified
@api_router.post("/code-review")
async def submit_code_review(payload: CodeReviewRequest):
    """
    Submit code for review

    Request body example:
    {
        "code": "def hello():\\n    print('hello')",
        "language": "python"
    }
    """
    job_id = str(uuid.uuid4())

    print(f"[API] Received code review: language={payload.language}, code_length={len(payload.code)}")

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Code review submitted successfully",
        "estimated_duration": 5
    }


@api_router.get("/code-review/{job_id}")
async def get_review_status(job_id: str):
    """Get code review results by job ID"""
    return {
        "job_id": job_id,
        "status": "completed",
        "results": {
            "code_quality": 8,
            "security_score": 9,
            "issues_found": 2,
            "summary": "Code looks good with minor improvements needed",
            "recommendations": [
                "Consider adding type hints",
                "Add docstrings to functions"
            ]
        }
    }
