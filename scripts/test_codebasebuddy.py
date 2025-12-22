"""
CodeBaseBuddy Comprehensive Test Script
Tests all features of the CodeBaseBuddy MCP server

Features tested:
1. Server startup and health check
2. Index building
3. Semantic search
4. Find similar code
5. Get code context
6. Find symbol usages
7. Get index statistics
8. Error handling
"""

import asyncio
import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")  # Set console to UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool


class CodeBaseBuddyTester:
    """Comprehensive tester for CodeBaseBuddy"""

    def __init__(self):
        self.tool = None
        self.test_results = []
        self.passed = 0
        self.failed = 0

    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "[PASS]" if passed else "[FAIL]"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        if passed:
            self.passed += 1
        else:
            self.failed += 1

        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")

    async def test_01_tool_initialization(self):
        """Test 1: CodeBaseBuddy tool initialization"""
        try:
            config = {
                "server_url": "http://localhost:3004",
                "index_path": "./data/codebase_index",
                "scan_paths": ["./src", "./mcp_servers"],
                "timeout": 60,
            }

            self.tool = CodeBaseBuddyMCPTool(server_url=config["server_url"], config=config)

            # Connect to server
            await self.tool.connect()

            self.log_test(
                "Tool Initialization", True, f"Connected to server at {config['server_url']}"
            )

        except Exception as e:
            self.log_test("Tool Initialization", False, f"Failed to initialize: {e}")

    async def test_02_health_check(self):
        """Test 2: Server health check"""
        try:
            result = await self.tool.health_check()

            success = result.get("status") in ["healthy", "fallback"]
            message = f"Status: {result.get('status')}, "
            message += f"Embeddings: {result.get('embeddings_available', False)}, "
            message += f"FAISS: {result.get('faiss_available', False)}, "
            message += f"Index loaded: {result.get('index_loaded', False)}"

            self.log_test("Health Check", success, message)

            # Print full health response
            print("\n    Health Check Details:")
            print(json.dumps(result, indent=4))

        except Exception as e:
            self.log_test("Health Check", False, f"Error: {e}")

    async def test_03_build_index(self):
        """Test 3: Build semantic code index"""
        try:
            print("\n    Building index (this may take 30-60 seconds)...")

            result = await self.tool.build_index(
                root_path="./src",
                file_extensions=[".py"],
                rebuild=True,  # Force rebuild for testing
            )

            success = result.get("success", False)

            if success:
                stats = result.get("stats", {})
                message = f"Indexed {stats.get('files_indexed', 0)} files, "
                message += f"{stats.get('functions_indexed', 0)} functions, "
                message += f"{stats.get('classes_indexed', 0)} classes, "
                message += f"Total vectors: {stats.get('total_vectors', 0)}"

                self.log_test("Build Index", True, message)

                # Print detailed stats
                print("\n    Index Statistics:")
                print(json.dumps(stats, indent=4))
            else:
                error = result.get("error", "Unknown error")
                self.log_test("Build Index", False, error)

        except Exception as e:
            self.log_test("Build Index", False, f"Error: {e}")

    async def test_04_get_index_stats(self):
        """Test 4: Get index statistics"""
        try:
            result = await self.tool.get_index_stats()

            success = result.get("success", False)

            if success:
                stats = result.get("stats", {})
                message = f"Index has {stats.get('total_vectors', 0)} vectors"
                self.log_test("Get Index Stats", True, message)

                print("\n    Current Index Stats:")
                print(json.dumps(stats, indent=4))
            else:
                self.log_test("Get Index Stats", False, result.get("error", "Failed"))

        except Exception as e:
            self.log_test("Get Index Stats", False, f"Error: {e}")

    async def test_05_semantic_search_authentication(self):
        """Test 5: Semantic search - 'How does authentication work?'"""
        try:
            query = "How does authentication work?"
            print(f"\n    Query: '{query}'")

            result = await self.tool.semantic_search(query=query, top_k=5)

            success = result.get("success", False)

            if success:
                results_count = result.get("results_count", 0)
                results = result.get("results", [])

                message = f"Found {results_count} results"
                self.log_test("Semantic Search (Authentication)", True, message)

                # Print top 3 results
                print("\n    Top Results:")
                for i, res in enumerate(results[:3], 1):
                    print(f"\n    {i}. {res.get('name')} in {Path(res.get('file_path', '')).name}")
                    print(f"       Score: {res.get('similarity_score', 0):.4f}")
                    print(f"       Type: {res.get('chunk_type')}")
                    print(f"       Lines: {res.get('start_line')}-{res.get('end_line')}")
                    print(f"       Preview: {res.get('content_preview', '')[:100]}...")
            else:
                self.log_test(
                    "Semantic Search (Authentication)", False, result.get("error", "Failed")
                )

        except Exception as e:
            self.log_test("Semantic Search (Authentication)", False, f"Error: {e}")

    async def test_06_semantic_search_error_handling(self):
        """Test 6: Semantic search - 'error handling and exceptions'"""
        try:
            query = "error handling and exceptions"
            print(f"\n    Query: '{query}'")

            result = await self.tool.semantic_search(
                query=query, top_k=5, file_filter=".*security.*"  # Filter to security files
            )

            success = result.get("success", False)

            if success:
                results_count = result.get("results_count", 0)
                message = f"Found {results_count} results in security files"
                self.log_test("Semantic Search (Error Handling)", True, message)

                # Print results
                results = result.get("results", [])
                print(f"\n    Found {len(results)} results:")
                for i, res in enumerate(results[:3], 1):
                    print(
                        f"    {i}. {res.get('name')} - Score: {res.get('similarity_score', 0):.4f}"
                    )
            else:
                self.log_test(
                    "Semantic Search (Error Handling)", False, result.get("error", "Failed")
                )

        except Exception as e:
            self.log_test("Semantic Search (Error Handling)", False, f"Error: {e}")

    async def test_07_find_similar_code(self):
        """Test 7: Find similar code patterns"""
        try:
            code_snippet = """
async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
    # Validate parameters
    self.validate_params(operation, params)
    return await self._execute_operation(operation, params)
"""
            print(f"\n    Code snippet: {code_snippet[:80]}...")

            result = await self.tool.find_similar_code(
                code_snippet=code_snippet, top_k=5, exclude_self=True
            )

            success = result.get("success", False)

            if success:
                results_count = result.get("results_count", 0)
                message = f"Found {results_count} similar code patterns"
                self.log_test("Find Similar Code", True, message)

                # Print similar patterns
                results = result.get("results", [])
                print(f"\n    Similar patterns found:")
                for i, res in enumerate(results[:3], 1):
                    print(f"\n    {i}. {res.get('name')} in {Path(res.get('file_path', '')).name}")
                    print(f"       Similarity: {res.get('similarity_score', 0):.4f}")
            else:
                self.log_test("Find Similar Code", False, result.get("error", "Failed"))

        except Exception as e:
            self.log_test("Find Similar Code", False, f"Error: {e}")

    async def test_08_get_code_context(self):
        """Test 8: Get code context around a line"""
        try:
            # Test with a known file
            file_path = "./src/mcp/base_tool.py"
            line_number = 50  # Around BaseMCPTool class

            print(f"\n    File: {file_path}, Line: {line_number}")

            result = await self.tool.get_code_context(
                file_path=file_path, line_number=line_number, context_lines=5
            )

            success = result.get("success", False)

            if success:
                start = result.get("start_line")
                end = result.get("end_line")
                total = result.get("total_lines")
                message = f"Retrieved context (lines {start}-{end} of {total})"
                self.log_test("Get Code Context", True, message)

                # Print context
                print(f"\n    Context around line {line_number}:")
                print("    " + "-" * 60)
                for i, line in enumerate(result.get("context", "").split("\n")[:10], start):
                    print(f"    {i:4d} | {line}")
                print("    " + "-" * 60)
            else:
                self.log_test("Get Code Context", False, result.get("error", "Failed"))

        except Exception as e:
            self.log_test("Get Code Context", False, f"Error: {e}")

    async def test_09_find_usages(self):
        """Test 9: Find symbol usages"""
        try:
            symbol = "MCPToolManager"
            print(f"\n    Symbol: '{symbol}'")

            result = await self.tool.find_usages(symbol_name=symbol, top_k=10)

            success = result.get("success", False)

            if success:
                results_count = result.get("results_count", 0)
                message = f"Found {results_count} usages of '{symbol}'"
                self.log_test("Find Usages", True, message)

                # Print usages
                results = result.get("results", [])
                print(f"\n    Usages found:")
                for i, res in enumerate(results[:5], 1):
                    print(f"    {i}. {Path(res.get('file_path', '')).name}:{res.get('start_line')}")
            else:
                self.log_test("Find Usages", False, result.get("error", "Failed"))

        except Exception as e:
            self.log_test("Find Usages", False, f"Error: {e}")

    async def test_10_error_handling_empty_query(self):
        """Test 10: Error handling - empty query"""
        try:
            result = await self.tool.semantic_search(query="", top_k=5)

            # Should fail with validation error
            success = not result.get("success", True)
            message = "Correctly rejected empty query"

            self.log_test("Error Handling (Empty Query)", success, message)

        except Exception as e:
            # Expected to raise validation error
            self.log_test(
                "Error Handling (Empty Query)", True, "Raised validation error as expected"
            )

    async def test_11_caching(self):
        """Test 11: Verify caching works"""
        try:
            query = "test caching query"
            print(f"\n    Query: '{query}'")

            # First call (should hit server)
            result1 = await self.tool.semantic_search(query=query, top_k=3)

            # Second call (should use cache)
            result2 = await self.tool.semantic_search(query=query, top_k=3)

            success = result1 == result2
            message = "Cache returned identical results"

            self.log_test("Caching", success, message)

        except Exception as e:
            self.log_test("Caching", False, f"Error: {e}")

    async def test_12_fallback_mode(self):
        """Test 12: Fallback mode when server unavailable"""
        try:
            # Create a tool with invalid server URL
            fallback_tool = CodeBaseBuddyMCPTool(
                server_url="http://localhost:9999",  # Wrong port
                config={"index_path": "./data/codebase_index", "scan_paths": ["./src"]},
            )

            result = await fallback_tool.semantic_search(query="test fallback", top_k=3)

            # Fallback should still return results
            fallback_used = result.get("fallback_used", False)

            self.log_test(
                "Fallback Mode", fallback_used, "Fallback search activated when server unavailable"
            )

        except Exception as e:
            self.log_test("Fallback Mode", False, f"Error: {e}")

    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print("\n" + "=" * 80)
        print("CODEBASEBUDDY TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests:   {total}")
        print(f"[+] Passed:    {self.passed}")
        print(f"[-] Failed:    {self.failed}")
        print(f"Pass Rate:     {pass_rate:.1f}%")
        print("=" * 80)

        # Save results to file
        report_path = Path("reports/codebasebuddy_test_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": total,
                    "passed": self.passed,
                    "failed": self.failed,
                    "pass_rate": pass_rate,
                    "results": self.test_results,
                },
                f,
                indent=2,
            )

        print(f"\n[*] Detailed report saved to: {report_path}")

        return self.failed == 0

    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 80)
        print("CODEBASEBUDDY COMPREHENSIVE TEST SUITE")
        print("=" * 80 + "\n")

        # Run tests in order
        await self.test_01_tool_initialization()
        await self.test_02_health_check()
        await self.test_03_build_index()
        await self.test_04_get_index_stats()
        await self.test_05_semantic_search_authentication()
        await self.test_06_semantic_search_error_handling()
        await self.test_07_find_similar_code()
        await self.test_08_get_code_context()
        await self.test_09_find_usages()
        await self.test_10_error_handling_empty_query()
        await self.test_11_caching()
        await self.test_12_fallback_mode()

        # Print summary
        all_passed = self.print_summary()

        return 0 if all_passed else 1


async def main():
    """Main entry point"""
    tester = CodeBaseBuddyTester()
    exit_code = await tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
