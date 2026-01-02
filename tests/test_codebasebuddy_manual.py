#!/usr/bin/env python3
"""
Manual CodeBaseBuddy Testing Script
Run this to test CodeBaseBuddy features manually

Usage:
    python test_codebasebuddy_manual.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool


async def test_semantic_search():
    """Test semantic search"""
    print("\n" + "="*80)
    print("TEST 1: Semantic Search")
    print("="*80)
    
    tool = CodeBaseBuddyMCPTool(
        config={
            "scan_paths": ["./src", "./mcp_servers", "./config"],
        }
    )
    
    # Test 1: Search for authentication
    print("\n1. Searching for 'authentication'...")
    result = await tool.semantic_search("authentication user login", top_k=5)
    print(f"   Results: {result.get('results_count', 0)}")
    if result.get('results'):
        for i, res in enumerate(result['results'][:3], 1):
            print(f"   {i}. {res.get('file_path', 'N/A')} (line {res.get('start_line', 'N/A')})")
            print(f"      Preview: {res.get('content_preview', '')[:100]}...")
    else:
        print("   No results found")
    
    # Test 2: Search for error handling
    print("\n2. Searching for 'error handling'...")
    result = await tool.semantic_search("error handling exception", top_k=5)
    print(f"   Results: {result.get('results_count', 0)}")
    if result.get('results'):
        for i, res in enumerate(result['results'][:3], 1):
            print(f"   {i}. {res.get('file_path', 'N/A')} (line {res.get('start_line', 'N/A')})")
    else:
        print("   No results found")
    
    # Test 3: Search for workflow
    print("\n3. Searching for 'workflow execution'...")
    result = await tool.semantic_search("workflow execution", top_k=5)
    print(f"   Results: {result.get('results_count', 0)}")
    if result.get('results'):
        for i, res in enumerate(result['results'][:3], 1):
            print(f"   {i}. {res.get('file_path', 'N/A')} (line {res.get('start_line', 'N/A')})")
    else:
        print("   No results found")
    
    print("\n[OK] Semantic search test completed!")


async def test_find_usages():
    """Test find usages"""
    print("\n" + "="*80)
    print("TEST 2: Find Usages")
    print("="*80)
    
    tool = CodeBaseBuddyMCPTool(
        config={
            "scan_paths": ["./src", "./mcp_servers"],
        }
    )
    
    # Test finding usages of a class
    print("\n1. Finding usages of 'ConversationManager'...")
    result = await tool.find_usages("ConversationManager", top_k=5)
    print(f"   Results: {result.get('results_count', 0)}")
    if result.get('results'):
        for i, res in enumerate(result['results'][:3], 1):
            print(f"   {i}. {res.get('file_path', 'N/A')}:{res.get('line_number', 'N/A')} - {res.get('usage_type', 'N/A')}")
            print(f"      Content: {res.get('line_content', '')[:80]}...")
    else:
        print("   No usages found")
    
    # Test finding usages of a function
    print("\n2. Finding usages of 'semantic_search'...")
    result = await tool.find_usages("semantic_search", top_k=5)
    print(f"   Results: {result.get('results_count', 0)}")
    if result.get('results'):
        for i, res in enumerate(result['results'][:3], 1):
            print(f"   {i}. {res.get('file_path', 'N/A')}:{res.get('line_number', 'N/A')} - {res.get('usage_type', 'N/A')}")
    else:
        print("   No usages found")
    
    print("\n[OK] Find usages test completed!")


async def test_get_context():
    """Test get code context"""
    print("\n" + "="*80)
    print("TEST 3: Get Code Context")
    print("="*80)
    
    tool = CodeBaseBuddyMCPTool()
    
    # Test getting context from a file
    print("\n1. Getting context from codebasebuddy_tool.py line 50...")
    result = await tool.get_code_context(
        "./src/mcp/codebasebuddy_tool.py",
        line_number=50,
        context_lines=5
    )
    
    if result.get('success'):
        print(f"   [OK] Success!")
        print(f"   File: {result.get('file_path', 'N/A')}")
        print(f"   Lines: {result.get('start_line', 'N/A')}-{result.get('end_line', 'N/A')} of {result.get('total_lines', 'N/A')}")
        print(f"   Context preview (first 300 chars):")
        context = result.get('context', '')
        print(f"   {context[:300]}...")
    else:
        print(f"   [ERROR] Error: {result.get('error', 'Unknown error')}")
    
    print("\n[OK] Get context test completed!")


async def test_find_similar():
    """Test find similar code"""
    print("\n" + "="*80)
    print("TEST 4: Find Similar Code")
    print("="*80)
    
    tool = CodeBaseBuddyMCPTool(
        config={
            "scan_paths": ["./src"],
        }
    )
    
    # Test finding similar code patterns
    print("\n1. Finding similar code to 'async def execute'...")
    result = await tool.find_similar_code(
        "async def execute",
        top_k=5
    )
    print(f"   Results: {result.get('results_count', 0)}")
    if result.get('results'):
        for i, res in enumerate(result['results'][:3], 1):
            score = res.get('similarity_score', 0)
            if isinstance(score, float):
                print(f"   {i}. {res.get('file_path', 'N/A')} (similarity: {score:.2%})")
            else:
                print(f"   {i}. {res.get('file_path', 'N/A')} (similarity: {score})")
    else:
        print("   No similar code found")
    
    print("\n[OK] Find similar code test completed!")


async def test_index_stats():
    """Test index statistics"""
    print("\n" + "="*80)
    print("TEST 5: Index Statistics")
    print("="*80)
    
    tool = CodeBaseBuddyMCPTool()
    
    print("\nGetting index statistics...")
    result = await tool.get_index_stats()
    
    if result.get('success'):
        stats = result.get('stats', {})
        print(f"   [OK] Success!")
        print(f"   Files indexed: {stats.get('files_indexed', 0)}")
        print(f"   Functions indexed: {stats.get('functions_indexed', 0)}")
        print(f"   Classes indexed: {stats.get('classes_indexed', 0)}")
        print(f"   Total vectors: {stats.get('total_vectors', 0)}")
        print(f"   Index ready: {stats.get('index_ready', False)}")
        print(f"   Mode: {stats.get('mode', 'N/A')}")
    else:
        print(f"   [ERROR] Error: {result.get('error', 'Unknown error')}")
    
    print("\n[OK] Index statistics test completed!")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("CodeBaseBuddy Manual Testing Suite")
    print("="*80)
    print("\nRunning all tests...\n")
    
    try:
        await test_semantic_search()
        await test_find_usages()
        await test_get_context()
        await test_find_similar()
        await test_index_stats()
        
        print("\n" + "="*80)
        print("[OK] ALL TESTS COMPLETED!")
        print("="*80)
        print("\nNext steps:")
        print("1. Try the interactive chat: python scripts/codebasebuddy_interactive.py")
        print("2. Test with your own queries")
        print("3. Check the guide: CODEBASEBUDDY_MANUAL_TESTING_GUIDE.md")
        
    except Exception as e:
        print(f"\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CodeBaseBuddy Manual Testing")
    print("="*80)
    print("\nThis script will test all CodeBaseBuddy features.")
    print("Press Ctrl+C to cancel.\n")
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n[WARNING] Testing cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        sys.exit(1)

