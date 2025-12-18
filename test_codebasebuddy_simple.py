"""
Simple test for CodeBaseBuddy server
Tests basic connectivity and SSE endpoint
"""
import sys
import io
import urllib.request
import urllib.error

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_simple():
    """Simple synchronous test"""
    print("=" * 60)
    print("Simple CodeBaseBuddy Server Test")
    print("=" * 60)

    url = "http://localhost:3004/sse"

    print(f"\n[Test 1] Connecting to: {url}")
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            status = response.status
            print(f"✅ Server is responding!")
            print(f"   Status code: {status}")
            print(f"   Headers: {dict(response.headers)}")

            # Read first 200 bytes
            data = response.read(200)
            print(f"   Response preview: {data[:200]}")

    except urllib.error.URLError as e:
        print(f"❌ Connection failed: {e}")
        print(f"\nTroubleshooting:")
        print(f"1. Check if server is running: python scripts/mcp_server_daemon.py status")
        print(f"2. Check if port 3004 is listening: netstat -ano | findstr :3004")
        print(f"3. Check server logs: logs\\mcp_servers\\codebasebuddy_server_20251218.log")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ Test passed! Server is accessible.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_simple()
