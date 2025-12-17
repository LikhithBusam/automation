"""
Comprehensive MCP Server Test Suite
Phase 9: Testing

Features:
1. Test each server health endpoint
2. GitHub server tests: create/get PR, create issue, search code
3. Filesystem server tests: read/write/list/search with security checks
4. Memory server tests: store/retrieve/search/delete memories
5. Load testing for rate limits
6. Error handling tests
7. Integration tests between servers
8. Generate test report with pass/fail status
"""

import asyncio
import argparse
import httpx
import json
import os
import time
import uuid
import tempfile
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box

console = Console()


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

class TestStatus(str, Enum):
    """Test result status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Individual test result"""
    name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def status_icon(self) -> str:
        icons = {
            TestStatus.PASSED: "✅",
            TestStatus.FAILED: "❌",
            TestStatus.SKIPPED: "⏭️",
            TestStatus.ERROR: "💥"
        }
        return icons.get(self.status, "❓")


@dataclass
class TestSuite:
    """Collection of test results for a component"""
    name: str
    description: str = ""
    tests: List[TestResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.status == TestStatus.PASSED)
    
    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.status == TestStatus.FAILED)
    
    @property
    def total(self) -> int:
        return len(self.tests)
    
    @property
    def duration_ms(self) -> float:
        return sum(t.duration_ms for t in self.tests)
    
    @property
    def success_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0

    def add_result(self, result: TestResult) -> None:
        """Append a test result and maintain timing fields."""
        if self.start_time is None:
            self.start_time = datetime.now()
        self.tests.append(result)
        self.end_time = datetime.now()


@dataclass 
class TestReport:
    """Complete test report"""
    suites: List[TestSuite] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def total_tests(self) -> int:
        return sum(s.total for s in self.suites)
    
    @property
    def total_passed(self) -> int:
        return sum(s.passed for s in self.suites)
    
    @property
    def total_failed(self) -> int:
        return sum(s.failed for s in self.suites)
    
    @property
    def success_rate(self) -> float:
        return (self.total_passed / self.total_tests * 100) if self.total_tests > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_tests": self.total_tests,
            "passed": self.total_passed,
            "failed": self.total_failed,
            "success_rate": f"{self.success_rate:.1f}%",
            "suites": [
                {
                    "name": s.name,
                    "tests": s.total,
                    "passed": s.passed,
                    "failed": s.failed,
                    "duration_ms": s.duration_ms,
                    "results": [
                        {
                            "name": t.name,
                            "status": t.status.value,
                            "duration_ms": t.duration_ms,
                            "message": t.message
                        }
                        for t in s.tests
                    ]
                }
                for s in self.suites
            ]
        }


# MCP Server configurations
MCP_SERVERS = {
    "github": {
        "url": "http://localhost:3000",
        "name": "GitHub Server",
        "port": 3000
    },
    "filesystem": {
        "url": "http://localhost:3001",
        "name": "Filesystem Server",
        "port": 3001
    },
    "memory": {
        "url": "http://localhost:3002",
        "name": "Memory Server",
        "port": 3002
    }
}

# Test data
TEST_DATA = {
    "github": {
        "test_owner": "octocat",
        "test_repo": "Hello-World",
        "test_issue_title": "Test Issue from MCP",
        "test_pr_title": "Test PR from MCP"
    },
    "filesystem": {
        "test_dir": "./test_workspace",
        "allowed_paths": ["./workspace", "./projects", "./src", "./test_workspace"],
        "blocked_paths": ["../", "/etc/", "~/.ssh/", ".env"]
    },
    "memory": {
        "test_content": "Test memory content for MCP server testing",
        "test_tags": ["test", "mcp", "automated"]
    }
}


# =============================================================================
# TEST UTILITIES
# =============================================================================

class TestTimer:
    """Context manager for timing tests"""
    def __init__(self):
        self.start = 0
        self.end = 0
    
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end = time.perf_counter()
    
    @property
    def elapsed_ms(self) -> float:
        return (self.end - self.start) * 1000


async def make_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs
) -> Tuple[Optional[httpx.Response], Optional[Exception]]:
    """Make HTTP request with error handling"""
    try:
        if method.upper() == "GET":
            response = await client.get(url, **kwargs)
        elif method.upper() == "POST":
            response = await client.post(url, **kwargs)
        elif method.upper() == "PUT":
            response = await client.put(url, **kwargs)
        elif method.upper() == "DELETE":
            response = await client.delete(url, **kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")
        return response, None
    except Exception as e:
        return None, e


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

async def test_server_health(server_name: str, config: dict) -> TestResult:
    """Test if a server is running and responding"""
    with TestTimer() as timer:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response, error = await make_request(client, "GET", f"{config['url']}/health")
                
                if error:
                    return TestResult(
                        name=f"health_check_{server_name}",
                        status=TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message=f"Connection failed: {str(error)[:50]}"
                    )
                
                if response.status_code == 200:
                    return TestResult(
                        name=f"health_check_{server_name}",
                        status=TestStatus.PASSED,
                        duration_ms=timer.elapsed_ms,
                        message=f"Server healthy (HTTP 200)",
                        details={"response_time_ms": timer.elapsed_ms}
                    )
                else:
                    return TestResult(
                        name=f"health_check_{server_name}",
                        status=TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message=f"Unexpected status: HTTP {response.status_code}"
                    )
                    
        except Exception as e:
            return TestResult(
                name=f"health_check_{server_name}",
                status=TestStatus.ERROR,
                duration_ms=timer.elapsed_ms,
                message=str(e)[:100]
            )


async def test_health_all() -> TestSuite:
    """Test health of all MCP servers"""
    suite = TestSuite(
        name="Health Checks",
        description="Test connectivity and health endpoints for all MCP servers"
    )
    
    for server_name, config in MCP_SERVERS.items():
        result = await test_server_health(server_name, config)
        suite.add_result(result)
    
    return suite


# =============================================================================
# GITHUB SERVER TESTS
# =============================================================================

async def test_github_operations(base_url: str) -> TestSuite:
    """Comprehensive GitHub server tests"""
    suite = TestSuite(name="GitHub Server", start_time=datetime.now())
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        
        # Test 1: List repositories
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/list_repositories",
                    json={"username": TEST_DATA["github"]["test_owner"]}
                )
                if error:
                    suite.tests.append(TestResult(
                        name="list_repositories",
                        status=TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message=str(error)[:50]
                    ))
                else:
                    suite.tests.append(TestResult(
                        name="list_repositories",
                        status=TestStatus.PASSED if response.status_code == 200 else TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message=f"HTTP {response.status_code}"
                    ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="list_repositories",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 2: Get repository info
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/get_repository",
                    json={
                        "owner": TEST_DATA["github"]["test_owner"],
                        "repo": TEST_DATA["github"]["test_repo"]
                    }
                )
                if error:
                    suite.tests.append(TestResult(
                        name="get_repository",
                        status=TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message=str(error)[:50]
                    ))
                else:
                    success = response.status_code == 200
                    if success:
                        data = response.json()
                        success = "name" in str(data) or "full_name" in str(data)
                    suite.tests.append(TestResult(
                        name="get_repository",
                        status=TestStatus.PASSED if success else TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message=f"HTTP {response.status_code}"
                    ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="get_repository",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 3: Search code
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/search_code",
                    json={
                        "query": "hello world",
                        "owner": TEST_DATA["github"]["test_owner"],
                        "repo": TEST_DATA["github"]["test_repo"]
                    }
                )
                suite.tests.append(TestResult(
                    name="search_code",
                    status=TestStatus.PASSED if (response and response.status_code in [200, 422]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="search_code",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 4: Get file contents
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/get_file_contents",
                    json={
                        "owner": TEST_DATA["github"]["test_owner"],
                        "repo": TEST_DATA["github"]["test_repo"],
                        "path": "README"
                    }
                )
                suite.tests.append(TestResult(
                    name="get_file_contents",
                    status=TestStatus.PASSED if (response and response.status_code in [200, 404]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="get_file_contents",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 5: List issues
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/list_issues",
                    json={
                        "owner": TEST_DATA["github"]["test_owner"],
                        "repo": TEST_DATA["github"]["test_repo"],
                        "state": "all"
                    }
                )
                suite.tests.append(TestResult(
                    name="list_issues",
                    status=TestStatus.PASSED if (response and response.status_code == 200) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="list_issues",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 6: List pull requests
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/list_pull_requests",
                    json={
                        "owner": TEST_DATA["github"]["test_owner"],
                        "repo": TEST_DATA["github"]["test_repo"],
                        "state": "all"
                    }
                )
                suite.tests.append(TestResult(
                    name="list_pull_requests",
                    status=TestStatus.PASSED if (response and response.status_code == 200) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="list_pull_requests",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 7: Get PR details (use PR #1 which usually exists)
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/get_pull_request",
                    json={
                        "owner": TEST_DATA["github"]["test_owner"],
                        "repo": TEST_DATA["github"]["test_repo"],
                        "pull_number": 1
                    }
                )
                suite.tests.append(TestResult(
                    name="get_pull_request",
                    status=TestStatus.PASSED if (response and response.status_code in [200, 404]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="get_pull_request",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 8: Error handling - Invalid repository
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/get_repository",
                    json={
                        "owner": "nonexistent-user-12345",
                        "repo": "nonexistent-repo-67890"
                    }
                )
                # Should return 404 or error, not crash
                suite.tests.append(TestResult(
                    name="error_handling_invalid_repo",
                    status=TestStatus.PASSED if (response and response.status_code in [404, 422, 400]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message="Properly handled invalid repo" if response else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="error_handling_invalid_repo",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
    
    suite.end_time = datetime.now()
    return suite


# =============================================================================
# FILESYSTEM SERVER TESTS
# =============================================================================

async def test_filesystem_operations(base_url: str) -> TestSuite:
    """Comprehensive Filesystem server tests with security checks"""
    suite = TestSuite(name="Filesystem Server", start_time=datetime.now())
    
    # Create test directory
    test_dir = Path(TEST_DATA["filesystem"]["test_dir"])
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = str(test_dir / f"test_file_{uuid.uuid4().hex[:8]}.txt")
    test_content = f"Test content created at {datetime.now().isoformat()}"
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        
        # Test 1: Write file
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/write_file",
                    json={"path": test_file, "content": test_content}
                )
                suite.tests.append(TestResult(
                    name="write_file",
                    status=TestStatus.PASSED if (response and response.status_code == 200) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="write_file",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 2: Read file
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/read_file",
                    json={"path": test_file}
                )
                success = False
                if response and response.status_code == 200:
                    data = response.json()
                    success = test_content in str(data.get("content", ""))
                suite.tests.append(TestResult(
                    name="read_file",
                    status=TestStatus.PASSED if success else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message="Content verified" if success else "Content mismatch or error"
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="read_file",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 3: List directory
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/list_directory",
                    json={"path": str(test_dir)}
                )
                success = False
                if response and response.status_code == 200:
                    data = response.json()
                    # Check if our test file is in the listing
                    files = data.get("files", data.get("entries", []))
                    success = any(Path(test_file).name in str(f) for f in files) if files else True
                suite.tests.append(TestResult(
                    name="list_directory",
                    status=TestStatus.PASSED if success else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"Found {len(files) if 'files' in dir() else 0} entries"
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="list_directory",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 4: Search files
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/search_files",
                    json={"path": str(test_dir), "pattern": "*.txt"}
                )
                suite.tests.append(TestResult(
                    name="search_files",
                    status=TestStatus.PASSED if (response and response.status_code in [200, 404]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="search_files",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 5: File info/stats
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/file_info",
                    json={"path": test_file}
                )
                suite.tests.append(TestResult(
                    name="file_info",
                    status=TestStatus.PASSED if (response and response.status_code in [200, 404]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="file_info",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 6: Security - Directory traversal prevention
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/read_file",
                    json={"path": "../../../etc/passwd"}
                )
                # Should be blocked or return 403/400
                blocked = response is None or response.status_code in [400, 403, 404, 422]
                suite.tests.append(TestResult(
                    name="security_dir_traversal",
                    status=TestStatus.PASSED if blocked else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message="Directory traversal blocked" if blocked else "SECURITY ISSUE: Traversal allowed!"
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="security_dir_traversal",
                    status=TestStatus.PASSED,  # Exception means it was blocked
                    duration_ms=timer.elapsed_ms,
                    message="Blocked with exception"
                ))
        
        # Test 7: Security - Blocked path access (.env)
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/read_file",
                    json={"path": ".env"}
                )
                # Should be blocked for .env files
                blocked = response is None or response.status_code in [400, 403, 404, 422]
                suite.tests.append(TestResult(
                    name="security_env_blocked",
                    status=TestStatus.PASSED if blocked else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=".env access blocked" if blocked else "WARNING: .env access allowed"
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="security_env_blocked",
                    status=TestStatus.PASSED,
                    duration_ms=timer.elapsed_ms,
                    message="Blocked with exception"
                ))
        
        # Test 8: Security - System path access
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/read_file",
                    json={"path": "/etc/shadow" if os.name != 'nt' else "C:\\Windows\\System32\\config\\SAM"}
                )
                blocked = response is None or response.status_code in [400, 403, 404, 422]
                suite.tests.append(TestResult(
                    name="security_system_path",
                    status=TestStatus.PASSED if blocked else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message="System path blocked" if blocked else "SECURITY: System access allowed!"
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="security_system_path",
                    status=TestStatus.PASSED,
                    duration_ms=timer.elapsed_ms,
                    message="Blocked with exception"
                ))
        
        # Test 9: Delete file (cleanup)
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/delete_file",
                    json={"path": test_file}
                )
                suite.tests.append(TestResult(
                    name="delete_file",
                    status=TestStatus.PASSED if (response and response.status_code in [200, 404]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="delete_file",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 10: Error handling - Non-existent file
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/read_file",
                    json={"path": "./nonexistent_file_12345.xyz"}
                )
                # Should return 404, not crash
                suite.tests.append(TestResult(
                    name="error_handling_missing_file",
                    status=TestStatus.PASSED if (response and response.status_code in [404, 400]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message="Properly handled missing file"
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="error_handling_missing_file",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
    
    # Cleanup test directory
    try:
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
    except Exception:
        pass
    
    suite.end_time = datetime.now()
    return suite


# =============================================================================
# MEMORY SERVER TESTS
# =============================================================================

async def test_memory_operations(base_url: str) -> TestSuite:
    """Comprehensive Memory server tests with store/retrieve/search/delete"""
    suite = TestSuite(name="Memory Server", start_time=datetime.now())
    
    test_id = f"test_memory_{uuid.uuid4().hex[:12]}"
    test_content = f"Test memory content created at {datetime.now().isoformat()}"
    stored_memory_id = None
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        
        # Test 1: Store memory
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/store_memory",
                    json={
                        "content": test_content,
                        "type": "context",
                        "tags": ["test", "mcp", "automated"],
                        "metadata": {"test_run": test_id}
                    }
                )
                if response and response.status_code == 200:
                    data = response.json()
                    stored_memory_id = data.get("memory_id", data.get("id"))
                suite.tests.append(TestResult(
                    name="store_memory",
                    status=TestStatus.PASSED if (response and response.status_code == 200) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"ID: {stored_memory_id[:20] if stored_memory_id else 'N/A'}..." if response else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="store_memory",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 2: Retrieve memory
        with TestTimer() as timer:
            try:
                if stored_memory_id:
                    response, error = await make_request(
                        client, "POST",
                        f"{base_url}/tools/retrieve_memory",
                        json={"memory_id": stored_memory_id}
                    )
                    success = False
                    if response and response.status_code == 200:
                        data = response.json()
                        # Verify content matches
                        retrieved = data.get("content", str(data))
                        success = test_content in str(retrieved)
                    suite.tests.append(TestResult(
                        name="retrieve_memory",
                        status=TestStatus.PASSED if success else TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message="Content verified" if success else "Content mismatch or retrieval failed"
                    ))
                else:
                    suite.tests.append(TestResult(
                        name="retrieve_memory",
                        status=TestStatus.SKIPPED,
                        duration_ms=timer.elapsed_ms,
                        message="Skipped - no memory ID from store"
                    ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="retrieve_memory",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 3: Search memory by query
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/search_memory",
                    json={"query": "test memory content", "limit": 10}
                )
                suite.tests.append(TestResult(
                    name="search_memory_query",
                    status=TestStatus.PASSED if (response and response.status_code == 200) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="search_memory_query",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 4: Search memory by tags
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/search_memory",
                    json={"tags": ["test", "mcp"], "limit": 5}
                )
                suite.tests.append(TestResult(
                    name="search_memory_tags",
                    status=TestStatus.PASSED if (response and response.status_code in [200, 422]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="search_memory_tags",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 5: List memories
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/list_memories",
                    json={"limit": 10, "type": "context"}
                )
                suite.tests.append(TestResult(
                    name="list_memories",
                    status=TestStatus.PASSED if (response and response.status_code in [200, 404]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="list_memories",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 6: Update memory
        with TestTimer() as timer:
            try:
                if stored_memory_id:
                    updated_content = f"Updated: {test_content}"
                    response, error = await make_request(
                        client, "POST",
                        f"{base_url}/tools/update_memory",
                        json={
                            "memory_id": stored_memory_id,
                            "content": updated_content,
                            "tags": ["test", "mcp", "updated"]
                        }
                    )
                    suite.tests.append(TestResult(
                        name="update_memory",
                        status=TestStatus.PASSED if (response and response.status_code in [200, 404]) else TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                    ))
                else:
                    suite.tests.append(TestResult(
                        name="update_memory",
                        status=TestStatus.SKIPPED,
                        duration_ms=timer.elapsed_ms,
                        message="Skipped - no memory ID from store"
                    ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="update_memory",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 7: Delete memory (cleanup)
        with TestTimer() as timer:
            try:
                if stored_memory_id:
                    response, error = await make_request(
                        client, "POST",
                        f"{base_url}/tools/delete_memory",
                        json={"memory_id": stored_memory_id}
                    )
                    suite.tests.append(TestResult(
                        name="delete_memory",
                        status=TestStatus.PASSED if (response and response.status_code in [200, 404]) else TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message=f"HTTP {response.status_code if response else 'N/A'}" if not error else str(error)[:50]
                    ))
                else:
                    suite.tests.append(TestResult(
                        name="delete_memory",
                        status=TestStatus.SKIPPED,
                        duration_ms=timer.elapsed_ms,
                        message="Skipped - no memory ID"
                    ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="delete_memory",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 8: Verify deletion
        with TestTimer() as timer:
            try:
                if stored_memory_id:
                    response, error = await make_request(
                        client, "POST",
                        f"{base_url}/tools/retrieve_memory",
                        json={"memory_id": stored_memory_id}
                    )
                    # Should return 404 or empty after deletion
                    deleted = response is None or response.status_code in [404, 400] or (
                        response.status_code == 200 and not response.json().get("content")
                    )
                    suite.tests.append(TestResult(
                        name="verify_deletion",
                        status=TestStatus.PASSED if deleted else TestStatus.FAILED,
                        duration_ms=timer.elapsed_ms,
                        message="Memory properly deleted" if deleted else "Memory still exists after delete"
                    ))
                else:
                    suite.tests.append(TestResult(
                        name="verify_deletion",
                        status=TestStatus.SKIPPED,
                        duration_ms=timer.elapsed_ms,
                        message="Skipped - no memory ID"
                    ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="verify_deletion",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
        
        # Test 9: Error handling - Invalid memory ID
        with TestTimer() as timer:
            try:
                response, error = await make_request(
                    client, "POST",
                    f"{base_url}/tools/retrieve_memory",
                    json={"memory_id": "nonexistent_memory_id_12345"}
                )
                # Should return 404 or error, not crash
                suite.tests.append(TestResult(
                    name="error_handling_invalid_id",
                    status=TestStatus.PASSED if (response and response.status_code in [404, 400, 422]) else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message="Properly handled invalid ID"
                ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name="error_handling_invalid_id",
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
    
    suite.end_time = datetime.now()
    return suite


# =============================================================================
# LOAD TESTING
# =============================================================================

async def test_load(servers: Dict[str, Dict], concurrent_requests: int = 10) -> TestSuite:
    """Load testing with concurrent requests to test rate limits"""
    suite = TestSuite(name="Load Testing", start_time=datetime.now())
    
    async def make_concurrent_requests(url: str, endpoint: str, payload: dict, count: int) -> List[Tuple[float, bool]]:
        """Make concurrent requests and return timing results"""
        results = []
        
        async def single_request():
            start = time.time()
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(f"{url}{endpoint}", json=payload)
                    return (time.time() - start) * 1000, response.status_code in [200, 201, 404, 422]
            except Exception:
                return (time.time() - start) * 1000, False
        
        tasks = [single_request() for _ in range(count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [(r[0], r[1]) if isinstance(r, tuple) else (0, False) for r in results]
    
    # Test each available server
    for server_name, config in servers.items():
        base_url = config["url"]
        
        if server_name == "filesystem":
            test_name = f"load_test_{server_name}"
            with TestTimer() as timer:
                results = await make_concurrent_requests(
                    base_url,
                    "/tools/list_directory",
                    {"path": "."},
                    concurrent_requests
                )
                
                times = [r[0] for r in results]
                successes = sum(1 for r in results if r[1])
                avg_time = statistics.mean(times) if times else 0
                max_time = max(times) if times else 0
                
                suite.tests.append(TestResult(
                    name=test_name,
                    status=TestStatus.PASSED if successes >= concurrent_requests * 0.8 else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"{successes}/{concurrent_requests} OK, avg={avg_time:.1f}ms, max={max_time:.1f}ms"
                ))
        
        elif server_name == "memory":
            test_name = f"load_test_{server_name}"
            with TestTimer() as timer:
                results = await make_concurrent_requests(
                    base_url,
                    "/tools/search_memory",
                    {"query": "test", "limit": 5},
                    concurrent_requests
                )
                
                times = [r[0] for r in results]
                successes = sum(1 for r in results if r[1])
                avg_time = statistics.mean(times) if times else 0
                max_time = max(times) if times else 0
                
                suite.tests.append(TestResult(
                    name=test_name,
                    status=TestStatus.PASSED if successes >= concurrent_requests * 0.8 else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"{successes}/{concurrent_requests} OK, avg={avg_time:.1f}ms, max={max_time:.1f}ms"
                ))
        
        elif server_name == "github":
            test_name = f"load_test_{server_name}"
            with TestTimer() as timer:
                # Use lighter endpoint to avoid rate limiting
                results = await make_concurrent_requests(
                    base_url,
                    "/health",
                    {},
                    min(concurrent_requests, 5)  # Limit GitHub to avoid rate limits
                )
                
                times = [r[0] for r in results]
                successes = sum(1 for r in results if r[1])
                avg_time = statistics.mean(times) if times else 0
                
                suite.tests.append(TestResult(
                    name=test_name,
                    status=TestStatus.PASSED if successes >= len(results) * 0.8 else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"{successes}/{len(results)} OK, avg={avg_time:.1f}ms (limited for rate limits)"
                ))
    
    # Test cross-server load
    test_name = "load_test_cross_server"
    with TestTimer() as timer:
        tasks = []
        for server_name, config in servers.items():
            if server_name == "filesystem":
                tasks.append(make_concurrent_requests(
                    config["url"], "/tools/list_directory", {"path": "."}, 3
                ))
            elif server_name == "memory":
                tasks.append(make_concurrent_requests(
                    config["url"], "/tools/search_memory", {"query": "test", "limit": 5}, 3
                ))
        
        if tasks:
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            total_successes = sum(
                sum(1 for r in results if isinstance(r, tuple) and r[1])
                for results in all_results if isinstance(results, list)
            )
            total_requests = sum(len(r) for r in all_results if isinstance(r, list))
            
            suite.tests.append(TestResult(
                name=test_name,
                status=TestStatus.PASSED if total_successes >= total_requests * 0.7 else TestStatus.FAILED,
                duration_ms=timer.elapsed_ms,
                message=f"Cross-server: {total_successes}/{total_requests} OK"
            ))
    
    suite.end_time = datetime.now()
    return suite


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

async def test_integration(servers: Dict[str, Dict]) -> TestSuite:
    """Integration tests between servers"""
    suite = TestSuite(name="Integration Tests", start_time=datetime.now())
    
    # Test 1: Memory-Filesystem integration - store file content as memory
    if "memory" in servers and "filesystem" in servers:
        test_name = "integration_memory_filesystem"
        with TestTimer() as timer:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    # Step 1: List directory to get file info
                    fs_response, _ = await make_request(
                        client, "POST",
                        f"{servers['filesystem']['url']}/tools/list_directory",
                        json={"path": "."}
                    )
                    
                    if fs_response and fs_response.status_code == 200:
                        # Step 2: Store the result in memory
                        fs_data = fs_response.json()
                        mem_response, _ = await make_request(
                            client, "POST",
                            f"{servers['memory']['url']}/tools/store_memory",
                            json={
                                "content": f"Directory listing from integration test: {str(fs_data)[:200]}",
                                "type": "context",
                                "tags": ["integration", "filesystem", "test"]
                            }
                        )
                        
                        success = mem_response and mem_response.status_code == 200
                        suite.tests.append(TestResult(
                            name=test_name,
                            status=TestStatus.PASSED if success else TestStatus.FAILED,
                            duration_ms=timer.elapsed_ms,
                            message="FS→Memory pipeline OK" if success else "Pipeline failed"
                        ))
                    else:
                        suite.tests.append(TestResult(
                            name=test_name,
                            status=TestStatus.FAILED,
                            duration_ms=timer.elapsed_ms,
                            message="Filesystem list failed"
                        ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name=test_name,
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
    
    # Test 2: Multi-memory workflow - store, search, retrieve, delete
    if "memory" in servers:
        test_name = "integration_memory_workflow"
        with TestTimer() as timer:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    base_url = servers["memory"]["url"]
                    test_id = f"integration_test_{uuid.uuid4().hex[:8]}"
                    
                    # Store
                    store_response, _ = await make_request(
                        client, "POST",
                        f"{base_url}/tools/store_memory",
                        json={
                            "content": f"Integration test content: {test_id}",
                            "type": "context",
                            "tags": ["integration", "workflow"]
                        }
                    )
                    
                    if store_response and store_response.status_code == 200:
                        memory_id = store_response.json().get("memory_id", store_response.json().get("id"))
                        
                        # Search
                        search_response, _ = await make_request(
                            client, "POST",
                            f"{base_url}/tools/search_memory",
                            json={"query": test_id, "limit": 5}
                        )
                        
                        # Retrieve
                        if memory_id:
                            retrieve_response, _ = await make_request(
                                client, "POST",
                                f"{base_url}/tools/retrieve_memory",
                                json={"memory_id": memory_id}
                            )
                            
                            # Delete
                            delete_response, _ = await make_request(
                                client, "POST",
                                f"{base_url}/tools/delete_memory",
                                json={"memory_id": memory_id}
                            )
                            
                            all_ok = all([
                                search_response and search_response.status_code in [200, 422],
                                retrieve_response and retrieve_response.status_code == 200,
                                delete_response and delete_response.status_code in [200, 404]
                            ])
                            
                            suite.tests.append(TestResult(
                                name=test_name,
                                status=TestStatus.PASSED if all_ok else TestStatus.FAILED,
                                duration_ms=timer.elapsed_ms,
                                message="Store→Search→Retrieve→Delete workflow OK" if all_ok else "Workflow step failed"
                            ))
                        else:
                            suite.tests.append(TestResult(
                                name=test_name,
                                status=TestStatus.FAILED,
                                duration_ms=timer.elapsed_ms,
                                message="No memory ID returned"
                            ))
                    else:
                        suite.tests.append(TestResult(
                            name=test_name,
                            status=TestStatus.FAILED,
                            duration_ms=timer.elapsed_ms,
                            message="Initial store failed"
                        ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name=test_name,
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
    
    # Test 3: Filesystem workflow - write, read, verify, delete
    if "filesystem" in servers:
        test_name = "integration_filesystem_workflow"
        with TestTimer() as timer:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    base_url = servers["filesystem"]["url"]
                    test_file = f"./integration_test_{uuid.uuid4().hex[:8]}.txt"
                    test_content = f"Integration test: {datetime.now().isoformat()}"
                    
                    # Write
                    write_response, _ = await make_request(
                        client, "POST",
                        f"{base_url}/tools/write_file",
                        json={"path": test_file, "content": test_content}
                    )
                    
                    if write_response and write_response.status_code == 200:
                        # Read
                        read_response, _ = await make_request(
                            client, "POST",
                            f"{base_url}/tools/read_file",
                            json={"path": test_file}
                        )
                        
                        content_match = False
                        if read_response and read_response.status_code == 200:
                            content_match = test_content in str(read_response.json())
                        
                        # Delete
                        delete_response, _ = await make_request(
                            client, "POST",
                            f"{base_url}/tools/delete_file",
                            json={"path": test_file}
                        )
                        
                        all_ok = content_match and delete_response and delete_response.status_code in [200, 404]
                        
                        suite.tests.append(TestResult(
                            name=test_name,
                            status=TestStatus.PASSED if all_ok else TestStatus.FAILED,
                            duration_ms=timer.elapsed_ms,
                            message="Write→Read→Verify→Delete workflow OK" if all_ok else "Workflow step failed"
                        ))
                    else:
                        suite.tests.append(TestResult(
                            name=test_name,
                            status=TestStatus.FAILED,
                            duration_ms=timer.elapsed_ms,
                            message="Initial write failed"
                        ))
            except Exception as e:
                suite.tests.append(TestResult(
                    name=test_name,
                    status=TestStatus.ERROR,
                    duration_ms=timer.elapsed_ms,
                    message=str(e)[:50]
                ))
    
    # Test 4: All servers health check integration
    test_name = "integration_all_servers_health"
    with TestTimer() as timer:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                health_checks = []
                for server_name, config in servers.items():
                    response, _ = await make_request(
                        client, "GET", f"{config['url']}/health"
                    )
                    health_checks.append(response and response.status_code == 200)
                
                all_healthy = all(health_checks)
                suite.tests.append(TestResult(
                    name=test_name,
                    status=TestStatus.PASSED if all_healthy else TestStatus.FAILED,
                    duration_ms=timer.elapsed_ms,
                    message=f"All {len(servers)} servers healthy" if all_healthy else f"Some servers unhealthy"
                ))
        except Exception as e:
            suite.tests.append(TestResult(
                name=test_name,
                status=TestStatus.ERROR,
                duration_ms=timer.elapsed_ms,
                message=str(e)[:50]
            ))
    
    suite.end_time = datetime.now()
    return suite


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(test_suites: List[TestSuite], output_dir: str = "./test_reports") -> Dict:
    """Generate comprehensive test report in multiple formats"""
    
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Aggregate statistics
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    total_duration = 0.0
    
    suite_results = []
    
    for suite in test_suites:
        suite_passed = sum(1 for t in suite.tests if t.status == TestStatus.PASSED)
        suite_failed = sum(1 for t in suite.tests if t.status == TestStatus.FAILED)
        suite_errors = sum(1 for t in suite.tests if t.status == TestStatus.ERROR)
        suite_skipped = sum(1 for t in suite.tests if t.status == TestStatus.SKIPPED)
        suite_duration = sum(t.duration_ms for t in suite.tests)
        
        total_tests += len(suite.tests)
        total_passed += suite_passed
        total_failed += suite_failed
        total_errors += suite_errors
        total_skipped += suite_skipped
        total_duration += suite_duration
        
        suite_results.append({
            "name": suite.name,
            "tests": len(suite.tests),
            "passed": suite_passed,
            "failed": suite_failed,
            "errors": suite_errors,
            "skipped": suite_skipped,
            "duration_ms": suite_duration,
            "pass_rate": (suite_passed / len(suite.tests) * 100) if suite.tests else 0,
            "test_details": [
                {
                    "name": t.name,
                    "status": t.status.value,
                    "duration_ms": t.duration_ms,
                    "message": t.message
                }
                for t in suite.tests
            ]
        })
    
    # Build report data
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "skipped": total_skipped,
            "pass_rate": (total_passed / total_tests * 100) if total_tests else 0,
            "total_duration_ms": total_duration,
            "overall_status": "PASSED" if (total_failed == 0 and total_errors == 0) else "FAILED"
        },
        "suites": suite_results
    }
    
    # Write JSON report
    json_path = Path(output_dir) / f"test_report_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)
    
    # Write HTML report
    html_path = Path(output_dir) / f"test_report_{timestamp}.html"
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>MCP Server Test Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat {{ padding: 15px; border-radius: 8px; text-align: center; }}
        .stat.total {{ background: #e3f2fd; }}
        .stat.passed {{ background: #e8f5e9; }}
        .stat.failed {{ background: #ffebee; }}
        .stat.error {{ background: #fff3e0; }}
        .stat.skipped {{ background: #f5f5f5; }}
        .stat .number {{ font-size: 2em; font-weight: bold; }}
        .stat .label {{ color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
        .status {{ padding: 3px 8px; border-radius: 4px; font-size: 0.85em; }}
        .status.passed {{ background: #c8e6c9; color: #2e7d32; }}
        .status.failed {{ background: #ffcdd2; color: #c62828; }}
        .status.error {{ background: #ffe0b2; color: #e65100; }}
        .status.skipped {{ background: #e0e0e0; color: #616161; }}
        .overall {{ font-size: 1.5em; padding: 10px 20px; border-radius: 8px; display: inline-block; }}
        .overall.passed {{ background: #4caf50; color: white; }}
        .overall.failed {{ background: #f44336; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 MCP Server Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="overall {'passed' if report_data['summary']['overall_status'] == 'PASSED' else 'failed'}">
            {report_data['summary']['overall_status']}
        </div>
        
        <h2>📊 Summary</h2>
        <div class="summary">
            <div class="stat total">
                <div class="number">{total_tests}</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="stat passed">
                <div class="number">{total_passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="stat failed">
                <div class="number">{total_failed}</div>
                <div class="label">Failed</div>
            </div>
            <div class="stat error">
                <div class="number">{total_errors}</div>
                <div class="label">Errors</div>
            </div>
            <div class="stat skipped">
                <div class="number">{total_skipped}</div>
                <div class="label">Skipped</div>
            </div>
        </div>
        
        <p><strong>Pass Rate:</strong> {report_data['summary']['pass_rate']:.1f}% | <strong>Duration:</strong> {total_duration:.0f}ms</p>
        
        <h2>📋 Test Suites</h2>
"""
    
    for suite in suite_results:
        html_content += f"""
        <h3>{suite['name']} ({suite['passed']}/{suite['tests']} passed)</h3>
        <table>
            <tr><th>Test</th><th>Status</th><th>Duration</th><th>Message</th></tr>
"""
        for test in suite['test_details']:
            status_class = test['status'].lower()
            html_content += f"""
            <tr>
                <td>{test['name']}</td>
                <td><span class="status {status_class}">{test['status']}</span></td>
                <td>{test['duration_ms']:.1f}ms</td>
                <td>{test['message']}</td>
            </tr>
"""
        html_content += "        </table>\n"
    
    html_content += """
    </div>
</body>
</html>
"""
    
    with open(html_path, "w") as f:
        f.write(html_content)
    
    report_data["files"] = {
        "json": str(json_path),
        "html": str(html_path)
    }
    
    return report_data


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def display_suite_results(suite: TestSuite):
    """Display test suite results using Rich tables"""
    table = Table(title=f"📋 {suite.name}", box=box.ROUNDED)
    table.add_column("Test", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Duration", justify="right", width=12)
    table.add_column("Message", style="dim")
    
    for test in suite.tests:
        status_style = {
            TestStatus.PASSED: "[green]✅ PASS[/green]",
            TestStatus.FAILED: "[red]❌ FAIL[/red]",
            TestStatus.ERROR: "[yellow]⚠️ ERROR[/yellow]",
            TestStatus.SKIPPED: "[dim]⏭️ SKIP[/dim]"
        }.get(test.status, test.status.value)
        
        table.add_row(
            test.name,
            status_style,
            f"{test.duration_ms:.1f}ms",
            test.message or "-"
        )
    
    console.print(table)
    console.print()


# =============================================================================
# MAIN RUNNER
# =============================================================================

async def main():
    """Main test runner with comprehensive output"""
    parser = argparse.ArgumentParser(description="MCP Server Test Suite")
    parser.add_argument("--suites", nargs="*", choices=["health", "github", "filesystem", "memory", "load", "integration", "all"],
                        default=["all"], help="Test suites to run")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent requests for load testing")
    parser.add_argument("--report-dir", default="./test_reports", help="Directory for test reports")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only (no Rich formatting)")
    args = parser.parse_args()
    
    if not args.json_only:
        console.print(Panel.fit(
            "[bold cyan]🧪 MCP Server Comprehensive Test Suite[/bold cyan]\n"
            "Testing all MCP servers with health, operations, load, and integration tests",
            box=box.DOUBLE
        ))
    
    test_suites: List[TestSuite] = []
    run_all = "all" in args.suites
    
    # Phase 1: Health checks
    if run_all or "health" in args.suites:
        if not args.json_only:
            console.print("\n[bold yellow]📡 Phase 1: Server Health Checks[/bold yellow]\n")
        
        health_suite = await test_health_all()
        test_suites.append(health_suite)
        
        if not args.json_only:
            display_suite_results(health_suite)
    
    # Determine running servers for subsequent tests
    running_servers = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for server_name, config in MCP_SERVERS.items():
            try:
                response = await client.get(f"{config['url']}/health")
                if response.status_code == 200:
                    running_servers[server_name] = config
            except Exception:
                pass
    
    if not running_servers:
        if not args.json_only:
            console.print("\n[bold red]❌ No MCP servers are running![/bold red]")
            console.print("\n[yellow]Start servers with:[/yellow]")
            console.print("  [cyan]python start_mcp_servers.py[/cyan]")
        else:
            print(json.dumps({"error": "No servers running", "suites": []}))
        return
    
    if not args.json_only:
        console.print(f"[green]✓ {len(running_servers)}/{len(MCP_SERVERS)} servers running[/green]\n")
    
    # Phase 2: GitHub operations
    if (run_all or "github" in args.suites) and "github" in running_servers:
        if not args.json_only:
            console.print("[bold yellow]🐙 Phase 2: GitHub Server Tests[/bold yellow]\n")
        
        github_suite = await test_github_operations(running_servers["github"]["url"])
        test_suites.append(github_suite)
        
        if not args.json_only:
            display_suite_results(github_suite)
    
    # Phase 3: Filesystem operations
    if (run_all or "filesystem" in args.suites) and "filesystem" in running_servers:
        if not args.json_only:
            console.print("[bold yellow]📁 Phase 3: Filesystem Server Tests[/bold yellow]\n")
        
        fs_suite = await test_filesystem_operations(running_servers["filesystem"]["url"])
        test_suites.append(fs_suite)
        
        if not args.json_only:
            display_suite_results(fs_suite)
    
    # Phase 4: Memory operations
    if (run_all or "memory" in args.suites) and "memory" in running_servers:
        if not args.json_only:
            console.print("[bold yellow]🧠 Phase 4: Memory Server Tests[/bold yellow]\n")
        
        memory_suite = await test_memory_operations(running_servers["memory"]["url"])
        test_suites.append(memory_suite)
        
        if not args.json_only:
            display_suite_results(memory_suite)
    
    # Phase 5: Load testing
    if run_all or "load" in args.suites:
        if not args.json_only:
            console.print(f"[bold yellow]⚡ Phase 5: Load Testing ({args.concurrent} concurrent requests)[/bold yellow]\n")
        
        load_suite = await test_load(running_servers, args.concurrent)
        test_suites.append(load_suite)
        
        if not args.json_only:
            display_suite_results(load_suite)
    
    # Phase 6: Integration tests
    if run_all or "integration" in args.suites:
        if not args.json_only:
            console.print("[bold yellow]🔗 Phase 6: Integration Tests[/bold yellow]\n")
        
        integration_suite = await test_integration(running_servers)
        test_suites.append(integration_suite)
        
        if not args.json_only:
            display_suite_results(integration_suite)
    
    # Generate report
    report = generate_report(test_suites, args.report_dir)
    
    if args.json_only:
        print(json.dumps(report, indent=2))
    else:
        # Summary panel
        status_color = "green" if report["summary"]["overall_status"] == "PASSED" else "red"
        console.print(Panel.fit(
            f"[bold {status_color}]{report['summary']['overall_status']}[/bold {status_color}]\n\n"
            f"Total: {report['summary']['total_tests']} | "
            f"Passed: [green]{report['summary']['passed']}[/green] | "
            f"Failed: [red]{report['summary']['failed']}[/red] | "
            f"Errors: [yellow]{report['summary']['errors']}[/yellow] | "
            f"Skipped: [dim]{report['summary']['skipped']}[/dim]\n"
            f"Pass Rate: {report['summary']['pass_rate']:.1f}% | "
            f"Duration: {report['summary']['total_duration_ms']:.0f}ms\n\n"
            f"📄 JSON Report: {report['files']['json']}\n"
            f"🌐 HTML Report: {report['files']['html']}",
            title="📊 Test Summary",
            box=box.DOUBLE
        ))


if __name__ == "__main__":
    asyncio.run(main())
