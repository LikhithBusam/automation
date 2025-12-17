"""
GitHub MCP Server using FastMCP
Provides GitHub API operations with rate limiting
"""

from fastmcp import FastMCP
from typing import List, Optional, Dict, Any
import logging
import os
import asyncio
from datetime import datetime
import httpx


# Initialize FastMCP server
mcp = FastMCP("GitHub Operations")
logger = logging.getLogger("mcp.github")

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"

# Rate limiting using Token Bucket Algorithm
class TokenBucket:
    """Token bucket rate limiter for GitHub API requests"""
    def __init__(self, rate_per_minute: int = 60, rate_per_hour: int = 1000):
        self.rate_per_minute = rate_per_minute
        self.rate_per_hour = rate_per_hour
        self.tokens_minute = rate_per_minute
        self.tokens_hour = rate_per_hour
        self.last_refill_minute = datetime.now()
        self.last_refill_hour = datetime.now()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Acquire a token, waiting if necessary"""
        async with self._lock:
            now = datetime.now()
            
            # Refill minute tokens
            elapsed_minutes = (now - self.last_refill_minute).total_seconds() / 60
            if elapsed_minutes >= 1:
                self.tokens_minute = self.rate_per_minute
                self.last_refill_minute = now
            
            # Refill hour tokens
            elapsed_hours = (now - self.last_refill_hour).total_seconds() / 3600
            if elapsed_hours >= 1:
                self.tokens_hour = self.rate_per_hour
                self.last_refill_hour = now
            
            # Check if we have tokens
            if self.tokens_minute <= 0:
                wait_time = 60 - (now - self.last_refill_minute).total_seconds()
                logger.warning(f"Rate limit (minute): waiting {wait_time:.1f}s")
                await asyncio.sleep(max(0, wait_time))
                self.tokens_minute = self.rate_per_minute
                self.last_refill_minute = datetime.now()
            
            if self.tokens_hour <= 0:
                raise Exception("Hourly rate limit exceeded. Please wait.")
            
            self.tokens_minute -= 1
            self.tokens_hour -= 1
            return True
    
    def get_remaining(self) -> Dict[str, int]:
        """Get remaining tokens"""
        return {
            "minute_remaining": self.tokens_minute,
            "hour_remaining": self.tokens_hour
        }

# Initialize rate limiter
rate_limiter = TokenBucket(rate_per_minute=60, rate_per_hour=1000)

# Request statistics
request_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "last_request_time": None
}


async def github_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make authenticated request to GitHub API with rate limiting"""
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    # Acquire rate limit token
    await rate_limiter.acquire()
    
    request_stats["total_requests"] += 1
    request_stats["last_request_time"] = datetime.now().isoformat()

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    url = f"{GITHUB_API_BASE}{endpoint}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, json=data)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            request_stats["successful_requests"] += 1
            
            # Handle empty responses
            if response.status_code == 204:
                return {"status": "success"}
            return response.json()
    except Exception as e:
        request_stats["failed_requests"] += 1
        logger.error(f"GitHub API error: {str(e)}")
        raise


@mcp.tool()
async def create_pull_request(
    repo: str,
    title: str,
    head: str,
    base: str,
    body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a pull request on GitHub.

    Args:
        repo: Repository in format "owner/repo"
        title: PR title
        head: Source branch name
        base: Target branch name (usually "main" or "master")
        body: Optional PR description

    Returns:
        Created PR details including number and URL

    Example:
        pr = await create_pull_request(
            repo="facebook/react",
            title="Fix memory leak",
            head="fix-memory-leak",
            base="main",
            body="This PR fixes a memory leak in..."
        )
        print(f"Created PR #{pr['number']}: {pr['url']}")
    """
    endpoint = f"/repos/{repo}/pulls"
    data = {
        "title": title,
        "head": head,
        "base": base,
        "body": body or ""
    }

    result = await github_request("POST", endpoint, data=data)

    logger.info(f"Created PR #{result['number']} in {repo}")

    return {
        "number": result["number"],
        "url": result["html_url"],
        "state": result["state"],
        "created_at": result["created_at"],
        "user": result["user"]["login"]
    }


@mcp.tool()
async def get_pull_request(repo: str, pr_number: int) -> Dict[str, Any]:
    """
    Get details of a specific pull request.

    Args:
        repo: Repository in format "owner/repo"
        pr_number: Pull request number

    Returns:
        PR details including status, reviews, and files

    Example:
        pr = await get_pull_request("facebook/react", 12345)
        print(f"PR state: {pr['state']}, Mergeable: {pr['mergeable']}")
    """
    endpoint = f"/repos/{repo}/pulls/{pr_number}"
    result = await github_request("GET", endpoint)

    return {
        "number": result["number"],
        "title": result["title"],
        "state": result["state"],
        "mergeable": result.get("mergeable"),
        "merged": result.get("merged", False),
        "changed_files": result.get("changed_files", 0),
        "additions": result.get("additions", 0),
        "deletions": result.get("deletions", 0),
        "url": result["html_url"],
        "user": result["user"]["login"],
        "created_at": result["created_at"],
        "updated_at": result["updated_at"]
    }


@mcp.tool()
async def create_issue(
    repo: str,
    title: str,
    body: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create an issue on GitHub.

    Args:
        repo: Repository in format "owner/repo"
        title: Issue title
        body: Issue description
        labels: Optional labels to add
        assignees: Optional users to assign

    Returns:
        Created issue details

    Example:
        issue = await create_issue(
            repo="facebook/react",
            title="Button component not rendering",
            body="Steps to reproduce:\\n1. ...",
            labels=["bug", "component"]
        )
    """
    endpoint = f"/repos/{repo}/issues"
    data = {
        "title": title,
        "body": body or "",
    }

    if labels:
        data["labels"] = labels
    if assignees:
        data["assignees"] = assignees

    result = await github_request("POST", endpoint, data=data)

    logger.info(f"Created issue #{result['number']} in {repo}")

    return {
        "number": result["number"],
        "url": result["html_url"],
        "state": result["state"],
        "created_at": result["created_at"]
    }


@mcp.tool()
async def search_code(
    query: str,
    language: Optional[str] = None,
    repo: Optional[str] = None,
    per_page: int = 10
) -> Dict[str, Any]:
    """
    Search for code across GitHub repositories.

    Args:
        query: Search query (supports GitHub search syntax)
        language: Optional programming language filter
        repo: Optional repository filter (owner/repo)
        per_page: Number of results per page (max 100)

    Returns:
        Search results with code snippets and file paths

    Example:
        results = await search_code(
            query="async def",
            language="python",
            per_page=5
        )
        for item in results["items"]:
            print(f"{item['repo']}: {item['path']}")
    """
    # Build search query
    search_query = query
    if language:
        search_query += f" language:{language}"
    if repo:
        search_query += f" repo:{repo}"

    endpoint = "/search/code"
    params = {
        "q": search_query,
        "per_page": min(per_page, 100)
    }

    result = await github_request("GET", endpoint, params=params)

    items = [
        {
            "repo": item["repository"]["full_name"],
            "path": item["path"],
            "url": item["html_url"],
            "score": item.get("score", 0)
        }
        for item in result.get("items", [])
    ]

    logger.info(f"Found {result.get('total_count', 0)} code results for '{query}'")

    return {
        "total_count": result.get("total_count", 0),
        "items": items
    }


@mcp.tool()
async def search_repositories(
    query: str,
    sort: str = "stars",
    per_page: int = 10
) -> Dict[str, Any]:
    """
    Search for GitHub repositories.

    Args:
        query: Search query (e.g., "machine learning language:python")
        sort: Sort by "stars", "forks", "updated", or "best-match"
        per_page: Number of results (max 100)

    Returns:
        List of repositories with metadata

    Example:
        repos = await search_repositories(
            query="fastapi stars:>1000",
            sort="stars"
        )
        for repo in repos["repositories"]:
            print(f"{repo['name']}: {repo['stars']} stars")
    """
    endpoint = "/search/repositories"
    params = {
        "q": query,
        "sort": sort,
        "per_page": min(per_page, 100)
    }

    result = await github_request("GET", endpoint, params=params)

    repositories = [
        {
            "name": repo["full_name"],
            "description": repo.get("description", ""),
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "language": repo.get("language"),
            "url": repo["html_url"],
            "updated_at": repo["updated_at"]
        }
        for repo in result.get("items", [])
    ]

    return {
        "total_count": result.get("total_count", 0),
        "repositories": repositories
    }


@mcp.tool()
async def get_file_content(
    repo: str,
    path: str,
    ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get the content of a file from a GitHub repository.

    Args:
        repo: Repository in format "owner/repo"
        path: File path within the repository
        ref: Optional branch, tag, or commit SHA (default: default branch)

    Returns:
        File content and metadata

    Example:
        file = await get_file_content(
            repo="facebook/react",
            path="README.md"
        )
        print(file["content"])
    """
    endpoint = f"/repos/{repo}/contents/{path}"
    params = {"ref": ref} if ref else {}

    result = await github_request("GET", endpoint, params=params)

    # Decode base64 content
    import base64
    content = base64.b64decode(result["content"]).decode('utf-8')

    return {
        "content": content,
        "path": result["path"],
        "size": result["size"],
        "sha": result["sha"],
        "url": result["html_url"]
    }


@mcp.tool()
async def list_commits(
    repo: str,
    branch: Optional[str] = None,
    since: Optional[str] = None,
    per_page: int = 10
) -> Dict[str, Any]:
    """
    List recent commits in a repository.

    Args:
        repo: Repository in format "owner/repo"
        branch: Branch name to get commits from (default: default branch)
        since: Only commits after this date (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)
        per_page: Number of commits to retrieve (max 100)

    Returns:
        List of recent commits

    Example:
        commits = await list_commits(
            "facebook/react",
            branch="main",
            since="2024-01-01T00:00:00Z",
            per_page=5
        )
        for commit in commits["commits"]:
            print(f"{commit['sha'][:7]}: {commit['message']}")
    """
    endpoint = f"/repos/{repo}/commits"
    params = {"per_page": min(per_page, 100)}
    
    if branch:
        params["sha"] = branch
    if since:
        params["since"] = since

    result = await github_request("GET", endpoint, params=params)

    commits = [
        {
            "sha": commit["sha"],
            "message": commit["commit"]["message"].split('\n')[0],  # First line only
            "full_message": commit["commit"]["message"],
            "author": commit["commit"]["author"]["name"],
            "author_email": commit["commit"]["author"]["email"],
            "date": commit["commit"]["author"]["date"],
            "url": commit["html_url"]
        }
        for commit in result
    ]

    return {
        "commits": commits,
        "count": len(commits),
        "repo": repo,
        "branch": branch
    }


@mcp.tool()
async def list_repositories(
    org: Optional[str] = None,
    user: Optional[str] = None,
    visibility: str = "all",
    sort: str = "updated",
    per_page: int = 30
) -> Dict[str, Any]:
    """
    List repositories for an organization or user.

    Args:
        org: Organization name (mutually exclusive with user)
        user: Username (mutually exclusive with org)
        visibility: Filter by visibility: "all", "public", "private"
        sort: Sort by: "created", "updated", "pushed", "full_name"
        per_page: Number of results (max 100)

    Returns:
        List of repositories with metadata

    Example:
        repos = await list_repositories(org="microsoft", visibility="public")
        for repo in repos["repositories"]:
            print(f"{repo['name']}: {repo['stars']} stars")
    """
    if org:
        endpoint = f"/orgs/{org}/repos"
    elif user:
        endpoint = f"/users/{user}/repos"
    else:
        # List authenticated user's repos
        endpoint = "/user/repos"
    
    params = {
        "type": visibility if visibility != "all" else "all",
        "sort": sort,
        "per_page": min(per_page, 100)
    }

    result = await github_request("GET", endpoint, params=params)

    repositories = [
        {
            "name": repo["full_name"],
            "description": repo.get("description", ""),
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "language": repo.get("language"),
            "visibility": "private" if repo.get("private") else "public",
            "url": repo["html_url"],
            "clone_url": repo["clone_url"],
            "default_branch": repo.get("default_branch", "main"),
            "created_at": repo["created_at"],
            "updated_at": repo["updated_at"],
            "pushed_at": repo.get("pushed_at")
        }
        for repo in result
    ]

    logger.info(f"Listed {len(repositories)} repositories")

    return {
        "repositories": repositories,
        "count": len(repositories),
        "org": org,
        "user": user
    }


@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    Check GitHub MCP server health and API connectivity.

    Returns:
        Health status including API connectivity and rate limits

    Example:
        health = await health_check()
        print(f"Status: {health['status']}")
    """
    health = {
        "server": "github_mcp",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "token_configured": bool(GITHUB_TOKEN),
        "rate_limits": rate_limiter.get_remaining(),
        "stats": request_stats
    }
    
    # Test GitHub API connectivity
    if GITHUB_TOKEN:
        try:
            result = await github_request("GET", "/rate_limit")
            health["github_api"] = {
                "connected": True,
                "rate_limit_remaining": result.get("resources", {}).get("core", {}).get("remaining", 0),
                "rate_limit_reset": result.get("resources", {}).get("core", {}).get("reset", 0)
            }
        except Exception as e:
            health["github_api"] = {
                "connected": False,
                "error": str(e)
            }
            health["status"] = "degraded"
    else:
        health["github_api"] = {"connected": False, "error": "Token not configured"}
        health["status"] = "unconfigured"
    
    return health


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN environment variable not set")
        print("Set it with: export GITHUB_TOKEN=your_token_here")
        print("Server will start but GitHub operations will fail\n")

    print("Starting GitHub MCP Server on http://localhost:3000...")
    if GITHUB_TOKEN:
        print(f"GitHub Token: {'*' * 20}{GITHUB_TOKEN[-4:]}")

    # Run server directly
    mcp.run(transport="sse", port=3000, host="0.0.0.0")
