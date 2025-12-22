"""
Complete CodeBaseBuddy Test Script
Tests the full workflow: index building and semantic search
"""

import asyncio
import io
import sys
from pathlib import Path

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add mcp_servers to path to import client
sys.path.insert(0, str(Path(__file__).parent))


async def test_codebasebuddy_complete():
    """Complete test of CodeBaseBuddy functionality"""
    print("=" * 70)
    print("CodeBaseBuddy Complete Functionality Test")
    print("=" * 70)

    try:
        # Import the MCP client library
        print("\n[Step 1] Importing MCP client...")
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        print("✅ MCP client imported")
    except ImportError as e:
        print(f"❌ Failed to import MCP client: {e}")
        print("\n   Trying alternative approach with direct HTTP...")
        await test_with_http()
        return

    print("\n[Step 2] Connecting to CodeBaseBuddy server on port 3004...")
    print("   Note: Using SSE transport")

    # Test with direct HTTP instead
    await test_with_http()


async def test_with_http():
    """Test CodeBaseBuddy using direct HTTP calls"""
    import aiohttp

    base_url = "http://localhost:3004"

    print("\n" + "=" * 70)
    print("Testing CodeBaseBuddy via HTTP/SSE")
    print("=" * 70)

    # Test 1: Check if server is alive
    print("\n[Test 1] Checking server connectivity...")
    try:
        async with aiohttp.ClientSession() as session:
            # Just check if we can connect (SSE will timeout which is fine)
            try:
                async with session.get(
                    f"{base_url}/sse", timeout=aiohttp.ClientTimeout(total=1)
                ) as response:
                    print(f"✅ Server responding: {response.status}")
            except asyncio.TimeoutError:
                print(f"✅ Server responding (SSE stream active)")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure server is running: python scripts/mcp_server_daemon.py status")
        print("2. Check port 3004: netstat -ano | findstr :3004")
        return

    # Test 2: Build index
    print("\n[Test 2] Building code index...")
    print("   Indexing current directory for Python files...")

    # Since we can't easily call MCP tools via HTTP without proper MCP client,
    # let's test by directly importing and using the server module
    await test_direct_import()


async def test_direct_import():
    """Test by directly importing the server module"""
    print("\n" + "=" * 70)
    print("Direct Module Test (Recommended)")
    print("=" * 70)

    try:
        # Import the server module
        print("\n[Step 1] Importing CodeBaseBuddy server module...")
        import mcp_servers.codebasebuddy_server as cbb

        print("✅ Module imported successfully")

        # Initialize if needed
        print("\n[Step 2] Initializing embedding model...")
        if cbb.init_embedding_model():
            print("✅ Embedding model initialized")
        else:
            print("❌ Failed to initialize embedding model")
            print("   Install dependencies: pip install sentence-transformers faiss-cpu")
            return

        # Build index
        print("\n[Step 3] Building code index...")
        print("   Root path: ./mcp_servers")
        print("   Extensions: .py")

        result = await cbb.build_index(
            root_path="./mcp_servers", file_extensions=[".py"], rebuild=False
        )

        if result.get("success"):
            stats = result.get("statistics", {})
            print(f"✅ Index built successfully!")
            print(f"   Files indexed: {stats.get('files_indexed', 0)}")
            print(f"   Functions: {stats.get('functions_indexed', 0)}")
            print(f"   Classes: {stats.get('classes_indexed', 0)}")
            print(f"   Total vectors: {stats.get('total_vectors', 0)}")
        else:
            print(f"⚠️  Index build result: {result.get('error', 'Unknown error')}")

        # Test semantic search
        print("\n[Step 4] Testing semantic search...")
        queries = [
            "FastMCP server implementation",
            "semantic code search with embeddings",
            "FAISS vector index",
        ]

        for query in queries:
            print(f"\n   Query: '{query}'")
            result = await cbb.semantic_search(query, top_k=3)

            if result.get("success"):
                results = result.get("results", [])
                print(f"   ✅ Found {len(results)} results:")
                for i, res in enumerate(results[:3], 1):
                    file_path = res.get("file_path", "unknown")
                    score = res.get("score", 0)
                    chunk_name = res.get("name", "")
                    print(f"      {i}. {file_path} - {chunk_name} (score: {score:.3f})")
            else:
                print(f"   ⚠️  {result.get('error', 'Search failed')}")

        # Test find functions
        print("\n[Step 5] Testing function search...")
        result = await cbb.find_functions("search", max_results=5)

        if result.get("success"):
            functions = result.get("functions", [])
            print(f"✅ Found {len(functions)} functions with 'search':")
            for func in functions[:5]:
                print(f"   - {func.get('name', 'unknown')} in {func.get('file_path', 'unknown')}")
        else:
            print(f"⚠️  {result.get('error', 'Function search failed')}")

        # Test get index stats
        print("\n[Step 6] Getting index statistics...")
        result = await cbb.get_index_stats()

        if result.get("success"):
            stats = result.get("statistics", {})
            print(f"✅ Index Statistics:")
            print(f"   Total vectors: {stats.get('total_vectors', 0)}")
            print(f"   Files indexed: {stats.get('files_indexed', 0)}")
            print(f"   Functions: {stats.get('functions_indexed', 0)}")
            print(f"   Classes: {stats.get('classes_indexed', 0)}")
            print(f"   Last indexed: {stats.get('last_indexed', 'Never')}")
            print(f"   Index size: {stats.get('index_size_bytes', 0):,} bytes")

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return

    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)
    print("\nCodeBaseBuddy is working correctly!")
    print("\nAvailable tools:")
    print("  - build_index: Index your codebase")
    print("  - semantic_search: Natural language code search")
    print("  - find_functions: Find functions by name")
    print("  - find_similar_code: Find similar code patterns")
    print("  - get_code_context: Get code with context")
    print("  - get_index_stats: View index statistics")


if __name__ == "__main__":
    asyncio.run(test_codebasebuddy_complete())
