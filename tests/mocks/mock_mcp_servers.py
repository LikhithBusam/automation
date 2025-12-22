"""
Mock MCP Servers for Testing
Provides mock implementations of MCP servers for testing without requiring real servers
"""

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock


class MockMCPServer:
    """Base class for mock MCP servers"""

    def __init__(self, server_name: str, port: int):
        self.server_name = server_name
        self.port = port
        self.is_running = False
        self.call_history = []

    async def start(self):
        """Start the mock server"""
        self.is_running = True
        return {"status": "started", "port": self.port}

    async def stop(self):
        """Stop the mock server"""
        self.is_running = False
        return {"status": "stopped"}

    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint"""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "server": self.server_name,
            "port": self.port,
        }

    def record_call(self, method: str, params: Dict[str, Any]):
        """Record a call for testing verification"""
        self.call_history.append({"method": method, "params": params})


class MockGitHubServer(MockMCPServer):
    """Mock GitHub MCP Server"""

    def __init__(self):
        super().__init__("GitHub", 3000)
        self.repositories = {}
        self.pull_requests = {}
        self.issues = {}

    async def create_pull_request(
        self, repo: str, title: str, body: str, head: str, base: str = "main"
    ) -> Dict[str, Any]:
        """Mock create pull request"""
        self.record_call("create_pull_request", locals())

        pr_id = len(self.pull_requests) + 1
        pr = {
            "id": pr_id,
            "number": pr_id,
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "state": "open",
            "url": f"https://github.com/{repo}/pull/{pr_id}",
        }
        self.pull_requests[pr_id] = pr
        return pr

    async def get_repository(self, repo: str) -> Dict[str, Any]:
        """Mock get repository"""
        self.record_call("get_repository", {"repo": repo})

        if repo in self.repositories:
            return self.repositories[repo]

        # Return mock repo data
        repo_data = {
            "name": repo.split("/")[-1],
            "full_name": repo,
            "description": f"Mock repository {repo}",
            "url": f"https://github.com/{repo}",
            "stars": 100,
            "forks": 50,
        }
        self.repositories[repo] = repo_data
        return repo_data

    async def search_code(self, query: str, repo: Optional[str] = None) -> Dict[str, Any]:
        """Mock search code"""
        self.record_call("search_code", {"query": query, "repo": repo})

        return {
            "total_count": 2,
            "items": [
                {"path": "src/main.py", "repository": repo or "test/repo", "score": 1.0},
                {"path": "tests/test_main.py", "repository": repo or "test/repo", "score": 0.8},
            ],
        }

    async def create_issue(
        self, repo: str, title: str, body: str, labels: Optional[list] = None
    ) -> Dict[str, Any]:
        """Mock create issue"""
        self.record_call("create_issue", locals())

        issue_id = len(self.issues) + 1
        issue = {
            "id": issue_id,
            "number": issue_id,
            "title": title,
            "body": body,
            "labels": labels or [],
            "state": "open",
            "url": f"https://github.com/{repo}/issues/{issue_id}",
        }
        self.issues[issue_id] = issue
        return issue


class MockFilesystemServer(MockMCPServer):
    """Mock Filesystem MCP Server"""

    def __init__(self):
        super().__init__("Filesystem", 3001)
        self.files = {
            "/test/file.txt": "Test file content",
            "/test/code.py": "def hello():\n    return 'world'",
            "/test/data.json": '{"key": "value"}',
        }

    async def read_file(self, path: str) -> Dict[str, Any]:
        """Mock read file"""
        self.record_call("read_file", {"path": path})

        if path in self.files:
            return {
                "path": path,
                "content": self.files[path],
                "size": len(self.files[path]),
                "exists": True,
            }

        return {
            "path": path,
            "content": None,
            "size": 0,
            "exists": False,
            "error": "File not found",
        }

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Mock write file"""
        self.record_call("write_file", {"path": path, "content": content})

        self.files[path] = content
        return {"path": path, "size": len(content), "success": True}

    async def list_directory(self, path: str) -> Dict[str, Any]:
        """Mock list directory"""
        self.record_call("list_directory", {"path": path})

        # Filter files that start with path
        files = [f for f in self.files.keys() if f.startswith(path)]

        return {
            "path": path,
            "files": [{"name": f.split("/")[-1], "path": f, "type": "file"} for f in files],
            "count": len(files),
        }

    async def delete_file(self, path: str) -> Dict[str, Any]:
        """Mock delete file"""
        self.record_call("delete_file", {"path": path})

        if path in self.files:
            del self.files[path]
            return {"path": path, "deleted": True}

        return {"path": path, "deleted": False, "error": "File not found"}


class MockMemoryServer(MockMCPServer):
    """Mock Memory MCP Server"""

    def __init__(self):
        super().__init__("Memory", 3002)
        self.memories = []
        self.memory_index = {}

    async def store_memory(
        self, content: str, category: str = "general", metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Mock store memory"""
        self.record_call("store_memory", locals())

        memory_id = len(self.memories) + 1
        memory = {
            "id": memory_id,
            "content": content,
            "category": category,
            "metadata": metadata or {},
            "timestamp": "2024-12-18T00:00:00Z",
        }
        self.memories.append(memory)
        self.memory_index[memory_id] = memory

        return {"id": memory_id, "stored": True}

    async def search_memory(
        self, query: str, category: Optional[str] = None, top_k: int = 5
    ) -> Dict[str, Any]:
        """Mock search memory"""
        self.record_call("search_memory", locals())

        # Simple filtering
        results = self.memories
        if category:
            results = [m for m in results if m["category"] == category]

        # Return top_k results
        results = results[:top_k]

        return {"query": query, "results": results, "count": len(results)}

    async def get_memory(self, memory_id: int) -> Dict[str, Any]:
        """Mock get memory by ID"""
        self.record_call("get_memory", {"memory_id": memory_id})

        if memory_id in self.memory_index:
            return self.memory_index[memory_id]

        return {"error": "Memory not found", "id": memory_id}

    async def delete_memory(self, memory_id: int) -> Dict[str, Any]:
        """Mock delete memory"""
        self.record_call("delete_memory", {"memory_id": memory_id})

        if memory_id in self.memory_index:
            memory = self.memory_index[memory_id]
            self.memories.remove(memory)
            del self.memory_index[memory_id]
            return {"id": memory_id, "deleted": True}

        return {"id": memory_id, "deleted": False, "error": "Memory not found"}


class MockCodeBaseBuddyServer(MockMCPServer):
    """Mock CodeBaseBuddy MCP Server"""

    def __init__(self):
        super().__init__("CodeBaseBuddy", 3004)
        self.codebase = {
            "functions": [
                {
                    "name": "calculate_total",
                    "file": "src/utils.py",
                    "line": 10,
                    "signature": "def calculate_total(items: list) -> float",
                },
                {
                    "name": "validate_input",
                    "file": "src/validators.py",
                    "line": 5,
                    "signature": "def validate_input(data: dict) -> bool",
                },
            ],
            "classes": [
                {
                    "name": "UserManager",
                    "file": "src/models.py",
                    "line": 20,
                    "methods": ["create", "update", "delete"],
                }
            ],
        }

    async def semantic_search(
        self, query: str, file_pattern: Optional[str] = None, top_k: int = 5
    ) -> Dict[str, Any]:
        """Mock semantic search"""
        self.record_call("semantic_search", locals())

        # Return mock search results
        results = [
            {"file": "src/main.py", "line": 15, "content": "def main():", "score": 0.95},
            {
                "file": "src/utils.py",
                "line": 10,
                "content": "def calculate_total():",
                "score": 0.85,
            },
        ]

        return {"query": query, "results": results[:top_k], "count": len(results)}

    async def find_definition(self, symbol: str, symbol_type: str = "function") -> Dict[str, Any]:
        """Mock find definition"""
        self.record_call("find_definition", {"symbol": symbol, "type": symbol_type})

        if symbol_type == "function":
            for func in self.codebase["functions"]:
                if func["name"] == symbol:
                    return func

        if symbol_type == "class":
            for cls in self.codebase["classes"]:
                if cls["name"] == symbol:
                    return cls

        return {"error": "Definition not found", "symbol": symbol}

    async def analyze_dependencies(self, file_path: str) -> Dict[str, Any]:
        """Mock analyze dependencies"""
        self.record_call("analyze_dependencies", {"file_path": file_path})

        return {
            "file": file_path,
            "imports": ["os", "sys", "typing"],
            "dependencies": ["utils", "models"],
            "external_packages": ["requests", "pytest"],
        }


class MockMCPServerManager:
    """Manager for all mock MCP servers"""

    def __init__(self):
        self.github = MockGitHubServer()
        self.filesystem = MockFilesystemServer()
        self.memory = MockMemoryServer()
        self.codebasebuddy = MockCodeBaseBuddyServer()

        self.servers = {
            "github": self.github,
            "filesystem": self.filesystem,
            "memory": self.memory,
            "codebasebuddy": self.codebasebuddy,
        }

    async def start_all(self):
        """Start all mock servers"""
        for server in self.servers.values():
            await server.start()

    async def stop_all(self):
        """Stop all mock servers"""
        for server in self.servers.values():
            await server.stop()

    async def health_check_all(self) -> Dict[str, Any]:
        """Health check all servers"""
        results = {}
        for name, server in self.servers.items():
            results[name] = await server.health_check()
        return results

    def get_server(self, name: str) -> Optional[MockMCPServer]:
        """Get a specific mock server"""
        return self.servers.get(name)

    def reset_all(self):
        """Reset all servers to initial state"""
        self.__init__()


# Pytest fixtures for easy use in tests
import pytest


@pytest.fixture
def mock_mcp_manager():
    """Pytest fixture for mock MCP server manager"""
    return MockMCPServerManager()


@pytest.fixture
async def mock_github_server():
    """Pytest fixture for mock GitHub server"""
    server = MockGitHubServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def mock_filesystem_server():
    """Pytest fixture for mock Filesystem server"""
    server = MockFilesystemServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def mock_memory_server():
    """Pytest fixture for mock Memory server"""
    server = MockMemoryServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def mock_codebasebuddy_server():
    """Pytest fixture for mock CodeBaseBuddy server"""
    server = MockCodeBaseBuddyServer()
    await server.start()
    yield server
    await server.stop()
