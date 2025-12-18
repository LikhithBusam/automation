"""
Test script for CodeBaseBuddy MCP Server
Tests semantic code search functionality
"""
import sys
import io
import asyncio
import httpx
import json

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_codebasebuddy():
    """Test CodeBaseBuddy server functionality"""
    base_url = "http://localhost:3004"
    
    print("=" * 60)
    print("Testing CodeBaseBuddy MCP Server")
    print("=" * 60)
    
    # Test 1: Check server health
    print("\n[Test 1] Checking server health...")
    try:
        async with httpx.AsyncClient() as client:
            # Use a very short timeout since SSE keeps connection open
            response = await client.get(f"{base_url}/sse", timeout=httpx.Timeout(1.0, read=1.0))
            print(f"✅ Server is responding: {response.status_code}")
    except httpx.ReadTimeout:
        # This is expected for SSE - connection opened successfully
        print(f"✅ Server is responding (SSE stream active)")
    except httpx.ConnectTimeout:
        print(f"❌ Server connection timeout - server may not be running")
        return
    except Exception as e:
        print(f"⚠️  Server health check: {type(e).__name__}: {e}")
        # Continue anyway - server might be working
    
    # Test 2: Test semantic search via MCP call
    print("\n[Test 2] Testing semantic code search...")
    try:
        async with httpx.AsyncClient() as client:
            # MCP call format for semantic search
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "semantic_code_search",
                    "arguments": {
                        "query": "FastMCP server implementation",
                        "top_k": 3
                    }
                }
            }
            
            response = await client.post(
                f"{base_url}/rpc",
                json=mcp_request,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Semantic search successful!")
                print(f"   Found results: {json.dumps(result, indent=2)}")
            else:
                print(f"⚠️  Response code: {response.status_code}")
                print(f"   Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Semantic search test failed: {e}")
    
    # Test 3: List available tools
    print("\n[Test 3] Listing available tools...")
    try:
        async with httpx.AsyncClient() as client:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            response = await client.post(
                f"{base_url}/rpc",
                json=mcp_request,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Available tools:")
                if "result" in result and "tools" in result["result"]:
                    for tool in result["result"]["tools"]:
                        print(f"   - {tool.get('name', 'unknown')}: {tool.get('description', 'N/A')}")
                else:
                    print(f"   {json.dumps(result, indent=2)}")
            else:
                print(f"⚠️  Response code: {response.status_code}")
                
    except Exception as e:
        print(f"❌ List tools test failed: {e}")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_codebasebuddy())