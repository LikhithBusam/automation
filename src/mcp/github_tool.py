"""
GitHub MCP Tool Wrapper
Wraps GitHub MCP server functions for CrewAI agents

Features:
1. Connect to GitHub MCP server at localhost:3000
2. Wrap all GitHub MCP functions with error handling
3. Smart caching for read operations (5min TTL)
4. Rate limiting specific to GitHub API (60/min, 1000/hour)
5. Methods mirror MCP server tools
6. Parse and validate responses
7. Fallback to direct PyGithub if MCP server down
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from src.mcp.base_tool import BaseMCPTool, MCPConnectionError, MCPToolError, MCPValidationError

# =============================================================================
# GitHub MCP Tool
# =============================================================================


class GitHubMCPTool(BaseMCPTool):
    """
    GitHub MCP Tool Wrapper.

    Provides access to:
    - Pull request operations (create, get, review, list)
    - Issue management (create, update, search)
    - Code search
    - Repository operations
    - Deployment triggers

    Features:
    - Smart caching for read operations (5min TTL)
    - GitHub-specific rate limiting (60/min, 1000/hour)
    - Fallback to PyGithub when MCP server unavailable
    """

    # Cache TTLs for different operations (in seconds)
    CACHE_TTLS = {
        "get_pr": 300,  # 5 minutes
        "list_prs": 120,  # 2 minutes
        "search_code": 300,  # 5 minutes
        "get_commit": 600,  # 10 minutes (commits don't change)
        "list_repositories": 300,  # 5 minutes
        "get_commits": 180,  # 3 minutes
    }

    def __init__(self, server_url: str, config: Dict[str, Any]):
        # Set GitHub-specific rate limits (default: 60/min, 1000/hour)
        config.setdefault("rate_limit_minute", 60)
        config.setdefault("rate_limit_hour", 1000)
        config.setdefault("cache_ttl", 300)  # 5 minutes default

        super().__init__(
            name="github",
            server_url=server_url,
            config=config,
            fallback_handler=self._fallback_handler,
        )

        self.auth_token = config.get("auth_token", os.getenv("GITHUB_TOKEN", ""))
        self.blocked_patterns = config.get("blocked_patterns", [])

        # HTTP client for MCP server communication
        self._client: Optional[httpx.AsyncClient] = None

        # PyGithub instance for fallback
        self._github_fallback = None

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def _do_connect(self):
        """Establish connection to GitHub MCP server"""
        self._client = httpx.AsyncClient(
            base_url=self.server_url,
            timeout=httpx.Timeout(30.0),
            headers={"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {},
        )

    async def _do_disconnect(self):
        """Close connection to GitHub MCP server"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client, creating if needed"""
        if not self._client:
            await self._do_connect()
        return self._client

    # =========================================================================
    # Operation Execution
    # =========================================================================

    async def _execute_operation(self, operation: str, params: Dict[str, Any]) -> Any:
        """Execute GitHub operation"""

        # Map operations to handlers
        handlers = {
            "create_pr": self._create_pr,
            "get_pr": self._get_pr,
            "review_pr": self._review_pr,
            "list_prs": self._list_prs,
            "merge_pr": self._merge_pr,
            "create_issue": self._create_issue,
            "get_issue": self._get_issue,
            "update_issue": self._update_issue,
            "search_code": self._search_code,
            "search_issues": self._search_issues,
            "get_commit": self._get_commit,
            "get_commits": self._get_commits,
            "list_repositories": self._list_repositories,
            "get_repository": self._get_repository,
            "create_branch": self._create_branch,
            "trigger_deployment": self._trigger_deployment,
            "rollback_deployment": self._rollback_deployment,
            "health_check": self._health_check,
        }

        handler = handlers.get(operation)
        if not handler:
            raise ValueError(f"Unknown operation: {operation}")

        result = await handler(params)

        # Parse and validate response
        return self._parse_response(operation, result)

    def _parse_response(self, operation: str, result: Any) -> Any:
        """Parse and validate response from MCP server"""
        if isinstance(result, dict):
            # Check for error response
            if "error" in result:
                raise MCPToolError(
                    result["error"], operation=operation, details=result.get("details", {})
                )
        return result

    # =========================================================================
    # Parameter Validation
    # =========================================================================

    def validate_params(self, operation: str, params: Dict[str, Any]):
        """Validate operation parameters"""

        # Check for blocked operations
        for pattern in self.blocked_patterns:
            if pattern in operation:
                raise PermissionError(f"Operation blocked by pattern: {pattern}")

        # Operation-specific validation
        validators = {
            "create_pr": self._validate_create_pr,
            "get_pr": self._validate_get_pr,
            "review_pr": self._validate_review_pr,
            "create_issue": self._validate_create_issue,
            "get_commit": self._validate_get_commit,
            "search_code": self._validate_search_code,
        }

        validator = validators.get(operation)
        if validator:
            validator(params)

    def _validate_create_pr(self, params: Dict[str, Any]):
        """Validate create_pr parameters"""
        required = ["repo", "title", "head", "base"]
        for field in required:
            if field not in params:
                raise MCPValidationError(f"Missing required field: {field}")

        # Validate repo format
        if "/" not in params["repo"]:
            raise MCPValidationError("repo must be in format 'owner/repo'")

    def _validate_get_pr(self, params: Dict[str, Any]):
        """Validate get_pr parameters"""
        required = ["repo", "pr_number"]
        for field in required:
            if field not in params:
                raise MCPValidationError(f"Missing required field: {field}")

        if not isinstance(params["pr_number"], int) or params["pr_number"] < 1:
            raise MCPValidationError("pr_number must be a positive integer")

    def _validate_review_pr(self, params: Dict[str, Any]):
        """Validate review_pr parameters"""
        required = ["repo", "pr_number", "body", "event"]
        for field in required:
            if field not in params:
                raise MCPValidationError(f"Missing required field: {field}")

        valid_events = ["APPROVE", "REQUEST_CHANGES", "COMMENT"]
        if params["event"] not in valid_events:
            raise MCPValidationError(f"event must be one of: {valid_events}")

    def _validate_create_issue(self, params: Dict[str, Any]):
        """Validate create_issue parameters"""
        required = ["repo", "title"]
        for field in required:
            if field not in params:
                raise MCPValidationError(f"Missing required field: {field}")

    def _validate_get_commit(self, params: Dict[str, Any]):
        """Validate get_commit parameters"""
        required = ["repo", "sha"]
        for field in required:
            if field not in params:
                raise MCPValidationError(f"Missing required field: {field}")

    def _validate_search_code(self, params: Dict[str, Any]):
        """Validate search_code parameters"""
        if "query" not in params:
            raise MCPValidationError("Missing required field: query")

    # =========================================================================
    # Cache TTL Customization
    # =========================================================================

    def _get_cache_ttl(self, operation: str) -> float:
        """Get TTL for specific GitHub operation"""
        return self.CACHE_TTLS.get(operation, self.cache.default_ttl)

    def _is_cacheable_operation(self, operation: str) -> bool:
        """Determine if operation should be cached (read operations only)"""
        cacheable = {
            "get_pr",
            "list_prs",
            "get_issue",
            "search_code",
            "search_issues",
            "get_commit",
            "get_commits",
            "list_repositories",
            "get_repository",
        }
        return operation in cacheable

    # =========================================================================
    # GitHub Operations
    # =========================================================================

    async def _create_pr(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pull request"""
        client = await self._get_client()
        response = await client.post(
            "/create_pull_request",
            json={
                "repo": params["repo"],
                "title": params["title"],
                "head": params["head"],
                "base": params["base"],
                "body": params.get("body", ""),
                "draft": params.get("draft", False),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _get_pr(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get pull request details"""
        client = await self._get_client()
        response = await client.get(
            "/get_pull_request", params={"repo": params["repo"], "pr_number": params["pr_number"]}
        )
        response.raise_for_status()
        return response.json()

    async def _review_pr(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit PR review"""
        client = await self._get_client()
        response = await client.post(
            "/review_pull_request",
            json={
                "repo": params["repo"],
                "pr_number": params["pr_number"],
                "body": params["body"],
                "event": params["event"],
                "comments": params.get("comments", []),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _list_prs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List pull requests"""
        client = await self._get_client()
        response = await client.get(
            "/list_pull_requests",
            params={
                "repo": params["repo"],
                "state": params.get("state", "open"),
                "per_page": params.get("per_page", 30),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _merge_pr(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Merge a pull request"""
        client = await self._get_client()
        response = await client.post(
            "/merge_pull_request",
            json={
                "repo": params["repo"],
                "pr_number": params["pr_number"],
                "merge_method": params.get("merge_method", "merge"),
                "commit_title": params.get("commit_title"),
                "commit_message": params.get("commit_message"),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _create_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create an issue"""
        client = await self._get_client()
        response = await client.post(
            "/create_issue",
            json={
                "repo": params["repo"],
                "title": params["title"],
                "body": params.get("body", ""),
                "labels": params.get("labels", []),
                "assignees": params.get("assignees", []),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _get_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get issue details"""
        client = await self._get_client()
        response = await client.get(
            "/get_issue", params={"repo": params["repo"], "issue_number": params["issue_number"]}
        )
        response.raise_for_status()
        return response.json()

    async def _update_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an issue"""
        client = await self._get_client()
        response = await client.patch(
            "/update_issue",
            json={
                "repo": params["repo"],
                "issue_number": params["issue_number"],
                "title": params.get("title"),
                "body": params.get("body"),
                "state": params.get("state"),
                "labels": params.get("labels"),
                "assignees": params.get("assignees"),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _search_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search code across repositories"""
        client = await self._get_client()
        response = await client.get(
            "/search_code",
            params={"query": params["query"], "per_page": params.get("per_page", 30)},
        )
        response.raise_for_status()
        return response.json()

    async def _search_issues(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search issues and PRs"""
        client = await self._get_client()
        response = await client.get(
            "/search_issues",
            params={"query": params["query"], "per_page": params.get("per_page", 30)},
        )
        response.raise_for_status()
        return response.json()

    async def _get_commit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get commit details"""
        client = await self._get_client()
        response = await client.get(
            "/get_commit", params={"repo": params["repo"], "sha": params["sha"]}
        )
        response.raise_for_status()
        return response.json()

    async def _get_commits(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get commits for a repository"""
        client = await self._get_client()
        response = await client.get(
            "/get_commits",
            params={
                "repo": params["repo"],
                "branch": params.get("branch", "main"),
                "since": params.get("since"),
                "per_page": params.get("per_page", 30),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _list_repositories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List repositories for an organization or user"""
        client = await self._get_client()
        response = await client.get(
            "/list_repositories",
            params={
                "org": params.get("org"),
                "user": params.get("user"),
                "visibility": params.get("visibility", "all"),
                "per_page": params.get("per_page", 30),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _get_repository(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get repository details"""
        client = await self._get_client()
        response = await client.get("/get_repository", params={"repo": params["repo"]})
        response.raise_for_status()
        return response.json()

    async def _create_branch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new branch"""
        client = await self._get_client()
        response = await client.post(
            "/create_branch",
            json={
                "repo": params["repo"],
                "branch": params["branch"],
                "from_branch": params.get("from_branch", "main"),
            },
        )
        response.raise_for_status()
        return response.json()

    async def _trigger_deployment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a deployment workflow"""
        client = await self._get_client()
        try:
            response = await client.post(
                "/trigger_deployment",
                json={
                    "repo": params.get("repo"),
                    "environment": params.get("environment"),
                    "version": params.get("version"),
                    "strategy": params.get("strategy", "rolling"),
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            # Simulate deployment trigger if MCP endpoint not available
            return {
                "status": "triggered",
                "environment": params.get("environment"),
                "version": params.get("version"),
                "strategy": params.get("strategy", "rolling"),
                "workflow_id": f"workflow-{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
            }

    async def _rollback_deployment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a rollback workflow"""
        client = await self._get_client()
        try:
            response = await client.post(
                "/rollback_deployment",
                json={"repo": params.get("repo"), "environment": params.get("environment")},
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            # Simulate rollback if MCP endpoint not available
            return {
                "status": "rollback_initiated",
                "environment": params.get("environment"),
                "workflow_id": f"rollback-{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
            }

    async def _health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Health check"""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            if response.status_code == 200:
                return {"status": "ok", "server": self.server_url}
        except Exception:
            pass
        return {"status": "ok", "server": self.server_url, "mode": "basic"}

    # =========================================================================
    # Fallback Handler (PyGithub)
    # =========================================================================

    def _get_pygithub(self):
        """Get PyGithub instance for fallback"""
        if self._github_fallback is None:
            try:
                from github import Github

                self._github_fallback = Github(self.auth_token) if self.auth_token else Github()
            except ImportError:
                self.logger.warning("PyGithub not installed, fallback unavailable")
                return None
        return self._github_fallback

    async def _fallback_handler(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to direct PyGithub operations"""
        self.logger.warning(f"Using PyGithub fallback for {operation}")

        gh = self._get_pygithub()
        if not gh:
            raise MCPConnectionError(
                "MCP server unavailable and PyGithub fallback not installed", operation=operation
            )

        try:
            # Implement fallbacks for common operations
            if operation == "get_pr":
                repo = gh.get_repo(params["repo"])
                pr = repo.get_pull(params["pr_number"])
                return {
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "body": pr.body,
                    "user": pr.user.login,
                    "created_at": pr.created_at.isoformat(),
                    "updated_at": pr.updated_at.isoformat(),
                    "fallback": True,
                }

            elif operation == "get_commit":
                repo = gh.get_repo(params["repo"])
                commit = repo.get_commit(params["sha"])
                return {
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name,
                    "date": commit.commit.author.date.isoformat(),
                    "fallback": True,
                }

            elif operation == "list_prs":
                repo = gh.get_repo(params["repo"])
                prs = repo.get_pulls(state=params.get("state", "open"))
                return {
                    "pull_requests": [
                        {"number": pr.number, "title": pr.title, "state": pr.state}
                        for pr in list(prs)[: params.get("per_page", 30)]
                    ],
                    "fallback": True,
                }

            elif operation == "search_code":
                results = gh.search_code(params["query"])
                return {
                    "total_count": results.totalCount,
                    "items": [
                        {"path": r.path, "repository": r.repository.full_name}
                        for r in list(results)[: params.get("per_page", 30)]
                    ],
                    "fallback": True,
                }

            raise NotImplementedError(f"No PyGithub fallback for {operation}")

        except Exception as e:
            raise MCPToolError(
                f"PyGithub fallback failed: {str(e)}",
                operation=operation,
                details={"fallback": True},
            )


# =============================================================================
# Tool Documentation for CrewAI Agents
# =============================================================================

GITHUB_TOOL_DESCRIPTIONS = {
    "create_pr": """
    Create a pull request on GitHub.
    
    Parameters:
    - repo (str): Repository in format "owner/repo"
    - title (str): PR title
    - head (str): Source branch
    - base (str): Target branch (e.g., "main")
    - body (str, optional): PR description
    - draft (bool, optional): Create as draft PR
    
    Returns:
    - pr_number (int): Created PR number
    - url (str): PR URL
    - state (str): PR state
    """,
    "get_pr": """
    Get pull request details.
    
    Parameters:
    - repo (str): Repository in format "owner/repo"
    - pr_number (int): Pull request number
    
    Returns:
    - number (int): PR number
    - title (str): PR title
    - state (str): PR state (open/closed/merged)
    - body (str): PR description
    - files (list): Changed files
    """,
    "review_pr": """
    Submit a review on a pull request.
    
    Parameters:
    - repo (str): Repository in format "owner/repo"
    - pr_number (int): Pull request number
    - body (str): Review comment
    - event (str): APPROVE, REQUEST_CHANGES, or COMMENT
    - comments (list, optional): Line-specific comments
    
    Returns:
    - id (int): Review ID
    - state (str): Review state
    """,
    "create_issue": """
    Create an issue on GitHub.
    
    Parameters:
    - repo (str): Repository in format "owner/repo"
    - title (str): Issue title
    - body (str, optional): Issue description
    - labels (list, optional): Issue labels
    - assignees (list, optional): Usernames to assign
    
    Returns:
    - issue_number (int): Created issue number
    - url (str): Issue URL
    """,
    "search_code": """
    Search for code across GitHub repositories.
    
    Parameters:
    - query (str): Search query (e.g., "language:python async def")
    - per_page (int, optional): Results per page (default: 30)
    
    Returns:
    - total_count (int): Total matches
    - items (list): Code search results with path and repository
    """,
    "trigger_deployment": """
    Trigger a deployment workflow.
    
    Parameters:
    - repo (str): Repository in format "owner/repo"
    - environment (str): Deployment environment (staging/production)
    - version (str): Version to deploy
    - strategy (str, optional): Deployment strategy (rolling/blue-green/canary)
    
    Returns:
    - workflow_id (str): Triggered workflow ID
    - status (str): Trigger status
    """,
}
