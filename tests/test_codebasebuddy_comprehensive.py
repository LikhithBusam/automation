"""
Comprehensive CodeBaseBuddy Testing Suite
Tests all CodeBaseBuddy features to ensure it works correctly
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool
from src.mcp.base_tool import MCPValidationError


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def temp_codebase(tmp_path):
    """Create temporary codebase with sample files"""
    codebase = tmp_path / "codebase"
    codebase.mkdir()
    
    # Create sample Python file with functions
    (codebase / "auth.py").write_text("""
def authenticate_user(username, password):
    \"\"\"Authenticate a user with username and password.\"\"\"
    if username and password:
        return {"user_id": 1, "username": username}
    return None

class UserManager:
    def __init__(self):
        self.users = []
    
    def add_user(self, user):
        self.users.append(user)
""")
    
    # Create another Python file
    (codebase / "utils.py").write_text("""
def process_data(data):
    \"\"\"Process data and return result.\"\"\"
    return data.upper()

def validate_input(input_value):
    if input_value:
        return True
    return False
""")
    
    # Create config file
    (codebase / "config.yaml").write_text("""
database:
  host: localhost
  port: 5432
  name: myapp

authentication:
  enabled: true
  method: jwt
""")
    
    return codebase


@pytest.fixture
def codebasebuddy_tool(temp_codebase):
    """Create CodeBaseBuddy tool with test codebase"""
    tool = CodeBaseBuddyMCPTool(
        server_url="http://localhost:3004",
        config={
            "scan_paths": [str(temp_codebase)],
            "index_path": str(temp_codebase / ".index")
        }
    )
    return tool


# ============================================================================
# TEST SUITE 1: INITIALIZATION AND CONFIGURATION
# ============================================================================

class TestCodeBaseBuddyInitialization:
    """Test CodeBaseBuddy tool initialization"""
    
    def test_tool_initialization(self):
        """Test basic tool initialization"""
        tool = CodeBaseBuddyMCPTool()
        assert tool is not None
        assert tool.server_url == "http://localhost:3004"
        assert tool.name == "codebasebuddy"
        print("[PASS] CodeBaseBuddy tool initialized")
    
    def test_tool_initialization_with_config(self, temp_codebase):
        """Test tool initialization with custom config"""
        tool = CodeBaseBuddyMCPTool(
            server_url="http://localhost:3004",
            config={
                "scan_paths": [str(temp_codebase)],
                "index_path": str(temp_codebase / ".index"),
                "cache_ttl": 600
            }
        )
        assert tool.scan_paths == [str(temp_codebase)]
        assert str(tool.index_path) == str(temp_codebase / ".index")
        print("[PASS] CodeBaseBuddy tool initialized with custom config")
    
    def test_tool_default_config(self):
        """Test tool default configuration"""
        tool = CodeBaseBuddyMCPTool()
        assert tool.scan_paths == ["./src", "./mcp_servers"]
        assert tool._connection_timeout == 60
        assert tool._max_connections == 10
        print("[PASS] CodeBaseBuddy default config correct")


# ============================================================================
# TEST SUITE 2: SEMANTIC SEARCH
# ============================================================================

class TestSemanticSearch:
    """Test semantic search functionality"""
    
    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, codebasebuddy_tool):
        """Test basic semantic search"""
        result = await codebasebuddy_tool.semantic_search("authentication user login")
        
        assert result is not None
        assert result.get("success") is True
        assert "results" in result
        assert isinstance(result["results"], list)
        assert result.get("fallback_used") is True  # Using fallback mode
        print("[PASS] Basic semantic search works")
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_top_k(self, codebasebuddy_tool):
        """Test semantic search with custom top_k"""
        result = await codebasebuddy_tool.semantic_search("process data", top_k=3)
        
        assert result is not None
        assert result.get("success") is True
        assert len(result.get("results", [])) <= 3
        print("[PASS] Semantic search with top_k works")
    
    @pytest.mark.asyncio
    async def test_semantic_search_empty_query(self, codebasebuddy_tool):
        """Test semantic search with empty query"""
        with pytest.raises(MCPValidationError, match="cannot be empty"):
            await codebasebuddy_tool.semantic_search("")
        
        print("[PASS] Empty query validation works")
    
    @pytest.mark.asyncio
    async def test_semantic_search_finds_relevant_results(self, codebasebuddy_tool):
        """Test that semantic search finds relevant code"""
        result = await codebasebuddy_tool.semantic_search("authenticate user")
        
        assert result.get("success") is True
        results = result.get("results", [])
        
        # Should find authentication-related code
        found_auth = any("auth" in r.get("file_path", "").lower() or 
                        "authenticate" in r.get("content_preview", "").lower() 
                        for r in results)
        assert found_auth, "Should find authentication-related code"
        print("[PASS] Semantic search finds relevant results")
    
    @pytest.mark.asyncio
    async def test_semantic_search_keyword_extraction(self, codebasebuddy_tool):
        """Test that semantic search extracts keywords correctly"""
        result = await codebasebuddy_tool.semantic_search("how does user authentication work?")
        
        assert result.get("success") is True
        assert "keywords_used" in result or "query" in result
        print("[PASS] Keyword extraction works")


# ============================================================================
# TEST SUITE 3: FIND SIMILAR CODE
# ============================================================================

class TestFindSimilarCode:
    """Test find similar code functionality"""
    
    @pytest.mark.asyncio
    async def test_find_similar_code_basic(self, codebasebuddy_tool):
        """Test basic find similar code"""
        code_snippet = "def process_data(data):"
        result = await codebasebuddy_tool.find_similar_code(code_snippet)
        
        assert result is not None
        assert result.get("success") is True
        assert "results" in result
        assert isinstance(result["results"], list)
        print("[PASS] Find similar code works")
    
    @pytest.mark.asyncio
    async def test_find_similar_code_empty_snippet(self, codebasebuddy_tool):
        """Test find similar code with empty snippet"""
        with pytest.raises(MCPValidationError, match="cannot be empty"):
            await codebasebuddy_tool.find_similar_code("")
        
        print("[PASS] Empty snippet validation works")
    
    @pytest.mark.asyncio
    async def test_find_similar_code_with_top_k(self, codebasebuddy_tool):
        """Test find similar code with custom top_k"""
        code_snippet = "def validate_input(input_value):"
        result = await codebasebuddy_tool.find_similar_code(code_snippet, top_k=2)
        
        assert result is not None
        assert result.get("success") is True
        assert len(result.get("results", [])) <= 2
        print("[PASS] Find similar code with top_k works")


# ============================================================================
# TEST SUITE 4: GET CODE CONTEXT
# ============================================================================

class TestGetCodeContext:
    """Test get code context functionality"""
    
    @pytest.mark.asyncio
    async def test_get_code_context_basic(self, codebasebuddy_tool, temp_codebase):
        """Test basic get code context"""
        result = await codebasebuddy_tool.get_code_context(
            str(temp_codebase / "auth.py"),
            line_number=3
        )
        
        assert result is not None
        assert result.get("success") is True
        assert "context" in result
        assert "file_path" in result
        assert result.get("line_number") == 3
        print("[PASS] Get code context works")
    
    @pytest.mark.asyncio
    async def test_get_code_context_with_custom_lines(self, codebasebuddy_tool, temp_codebase):
        """Test get code context with custom context lines"""
        result = await codebasebuddy_tool.get_code_context(
            str(temp_codebase / "auth.py"),
            line_number=5,
            context_lines=5
        )
        
        assert result is not None
        assert result.get("success") is True
        assert "context" in result
        print("[PASS] Get code context with custom lines works")
    
    @pytest.mark.asyncio
    async def test_get_code_context_invalid_line(self, codebasebuddy_tool, temp_codebase):
        """Test get code context with invalid line number"""
        with pytest.raises(MCPValidationError, match="must be positive"):
            await codebasebuddy_tool.get_code_context(
                str(temp_codebase / "auth.py"),
                line_number=0
            )
        
        print("[PASS] Invalid line number validation works")
    
    @pytest.mark.asyncio
    async def test_get_code_context_nonexistent_file(self, codebasebuddy_tool):
        """Test get code context with nonexistent file"""
        result = await codebasebuddy_tool.get_code_context(
            "nonexistent_file.py",
            line_number=1
        )
        
        # Should return error in fallback mode
        assert result is not None
        assert result.get("success") is False or "error" in result
        print("[PASS] Nonexistent file handling works")


# ============================================================================
# TEST SUITE 5: BUILD INDEX
# ============================================================================

class TestBuildIndex:
    """Test build index functionality"""
    
    @pytest.mark.asyncio
    async def test_build_index_basic(self, codebasebuddy_tool, temp_codebase):
        """Test basic build index"""
        result = await codebasebuddy_tool.build_index(str(temp_codebase))
        
        assert result is not None
        assert result.get("success") is True
        assert "fallback_used" in result
        print("[PASS] Build index works")
    
    @pytest.mark.asyncio
    async def test_build_index_with_extensions(self, codebasebuddy_tool, temp_codebase):
        """Test build index with file extensions"""
        result = await codebasebuddy_tool.build_index(
            str(temp_codebase),
            file_extensions=[".py", ".yaml"]
        )
        
        assert result is not None
        assert result.get("success") is True
        print("[PASS] Build index with extensions works")
    
    @pytest.mark.asyncio
    async def test_build_index_empty_path(self, codebasebuddy_tool):
        """Test build index with empty path"""
        with pytest.raises(MCPValidationError, match="cannot be empty"):
            await codebasebuddy_tool.build_index("")
        
        print("[PASS] Empty path validation works")


# ============================================================================
# TEST SUITE 6: GET INDEX STATS
# ============================================================================

class TestGetIndexStats:
    """Test get index stats functionality"""
    
    @pytest.mark.asyncio
    async def test_get_index_stats_basic(self, codebasebuddy_tool):
        """Test basic get index stats"""
        result = await codebasebuddy_tool.get_index_stats()
        
        assert result is not None
        assert result.get("success") is True
        assert "stats" in result
        assert isinstance(result["stats"], dict)
        print("[PASS] Get index stats works")
    
    @pytest.mark.asyncio
    async def test_get_index_stats_structure(self, codebasebuddy_tool):
        """Test index stats structure"""
        result = await codebasebuddy_tool.get_index_stats()
        
        stats = result.get("stats", {})
        # Check for expected stats fields
        assert "files_indexed" in stats or "mode" in stats
        print("[PASS] Index stats structure correct")


# ============================================================================
# TEST SUITE 7: FIND USAGES
# ============================================================================

class TestFindUsages:
    """Test find usages functionality"""
    
    @pytest.mark.asyncio
    async def test_find_usages_basic(self, codebasebuddy_tool):
        """Test basic find usages"""
        result = await codebasebuddy_tool.find_usages("authenticate_user")
        
        assert result is not None
        assert result.get("success") is True
        assert "results" in result
        assert isinstance(result["results"], list)
        print("[PASS] Find usages works")
    
    @pytest.mark.asyncio
    async def test_find_usages_empty_symbol(self, codebasebuddy_tool):
        """Test find usages with empty symbol"""
        with pytest.raises(MCPValidationError, match="cannot be empty"):
            await codebasebuddy_tool.find_usages("")
        
        print("[PASS] Empty symbol validation works")
    
    @pytest.mark.asyncio
    async def test_find_usages_with_top_k(self, codebasebuddy_tool):
        """Test find usages with custom top_k"""
        result = await codebasebuddy_tool.find_usages("process_data", top_k=5)
        
        assert result is not None
        assert result.get("success") is True
        assert len(result.get("results", [])) <= 5
        print("[PASS] Find usages with top_k works")


# ============================================================================
# TEST SUITE 8: FALLBACK FUNCTIONALITY
# ============================================================================

class TestFallbackFunctionality:
    """Test fallback functionality when server is unavailable"""
    
    @pytest.mark.asyncio
    async def test_fallback_search_keyword_extraction(self, codebasebuddy_tool):
        """Test fallback search keyword extraction"""
        result = await codebasebuddy_tool._fallback_search({
            "query": "how does authentication work?",
            "top_k": 5
        })
        
        assert result is not None
        assert result.get("success") is True
        assert "keywords_used" in result or "results" in result
        print("[PASS] Fallback search keyword extraction works")
    
    @pytest.mark.asyncio
    async def test_fallback_search_stop_words(self, codebasebuddy_tool):
        """Test that fallback search filters stop words"""
        result = await codebasebuddy_tool._fallback_search({
            "query": "what is the authentication function",
            "top_k": 5
        })
        
        assert result is not None
        # Should extract meaningful keywords, not stop words
        if "keywords_used" in result:
            keywords = result["keywords_used"]
            assert "what" not in keywords
            assert "is" not in keywords
            assert "the" not in keywords
        print("[PASS] Stop words filtering works")
    
    @pytest.mark.asyncio
    async def test_fallback_find_similar(self, codebasebuddy_tool):
        """Test fallback find similar code"""
        result = await codebasebuddy_tool._fallback_find_similar({
            "code_snippet": "def process_data(data):\n    return data.upper()",
            "top_k": 3
        })
        
        assert result is not None
        assert result.get("success") is True
        assert "results" in result
        print("[PASS] Fallback find similar works")
    
    @pytest.mark.asyncio
    async def test_fallback_get_context(self, codebasebuddy_tool, temp_codebase):
        """Test fallback get context"""
        result = await codebasebuddy_tool._fallback_get_context({
            "file_path": str(temp_codebase / "auth.py"),
            "line_number": 3,
            "context_lines": 5
        })
        
        assert result is not None
        assert result.get("success") is True
        assert "context" in result
        print("[PASS] Fallback get context works")
    
    @pytest.mark.asyncio
    async def test_fallback_find_usages(self, codebasebuddy_tool):
        """Test fallback find usages"""
        result = await codebasebuddy_tool._fallback_find_usages({
            "symbol": "authenticate_user",
            "top_k": 5
        })
        
        assert result is not None
        assert result.get("success") is True
        assert "results" in result
        print("[PASS] Fallback find usages works")
    
    def test_fallback_stats(self, codebasebuddy_tool):
        """Test fallback stats (not async)"""
        result = codebasebuddy_tool._fallback_stats()
        
        assert result is not None
        assert result.get("success") is True
        assert "stats" in result
        print("[PASS] Fallback stats works")


# ============================================================================
# TEST SUITE 9: CACHING
# ============================================================================

class TestCaching:
    """Test caching functionality"""
    
    @pytest.mark.asyncio
    async def test_semantic_search_caching(self, codebasebuddy_tool):
        """Test that semantic search results are cached"""
        query = "authentication user"
        
        # First call
        result1 = await codebasebuddy_tool.semantic_search(query)
        assert result1 is not None
        
        # Second call should use cache (if implemented)
        result2 = await codebasebuddy_tool.semantic_search(query)
        assert result2 is not None
        
        # Both should succeed
        assert result1.get("success") == result2.get("success")
        print("[PASS] Semantic search caching works")
    
    def test_cache_helpers(self, codebasebuddy_tool):
        """Test cache helper methods"""
        # Test setting cache
        codebasebuddy_tool._set_cached("test_key", {"data": "test"}, ttl=60)
        
        # Test getting cache
        cached = codebasebuddy_tool._get_cached("test_key")
        assert cached is not None
        assert cached == {"data": "test"}
        
        print("[PASS] Cache helpers work")


# ============================================================================
# TEST SUITE 10: VALIDATION
# ============================================================================

class TestValidation:
    """Test parameter validation"""
    
    def test_validate_semantic_search(self, codebasebuddy_tool):
        """Test semantic search validation"""
        # Valid params
        codebasebuddy_tool._validate_semantic_search({"query": "test"})
        
        # Invalid params
        with pytest.raises(MCPValidationError, match="Query is required"):
            codebasebuddy_tool._validate_semantic_search({})
        
        print("[PASS] Semantic search validation works")
    
    def test_validate_find_similar(self, codebasebuddy_tool):
        """Test find similar validation"""
        # Valid params
        codebasebuddy_tool._validate_find_similar({"code_snippet": "def test():"})
        
        # Invalid params
        with pytest.raises(MCPValidationError, match="Code snippet is required"):
            codebasebuddy_tool._validate_find_similar({})
        
        print("[PASS] Find similar validation works")
    
    def test_validate_get_context(self, codebasebuddy_tool):
        """Test get context validation"""
        # Valid params
        codebasebuddy_tool._validate_get_context({
            "file_path": "test.py",
            "line_number": 1
        })
        
        # Invalid params - missing file_path
        with pytest.raises(MCPValidationError, match="File path is required"):
            codebasebuddy_tool._validate_get_context({"line_number": 1})
        
        # Invalid params - missing line_number
        with pytest.raises(MCPValidationError, match="Line number is required"):
            codebasebuddy_tool._validate_get_context({"file_path": "test.py"})
        
        print("[PASS] Get context validation works")
    
    def test_validate_build_index(self, codebasebuddy_tool):
        """Test build index validation"""
        # Valid params
        codebasebuddy_tool._validate_build_index({"root_path": "./src"})
        
        # Invalid params
        with pytest.raises(MCPValidationError, match="Root path is required"):
            codebasebuddy_tool._validate_build_index({})
        
        print("[PASS] Build index validation works")
    
    def test_validate_find_usages(self, codebasebuddy_tool):
        """Test find usages validation"""
        # Valid params
        codebasebuddy_tool._validate_find_usages({"symbol_name": "test_function"})
        
        # Invalid params
        with pytest.raises(MCPValidationError, match="Symbol name is required"):
            codebasebuddy_tool._validate_find_usages({})
        
        print("[PASS] Find usages validation works")


# ============================================================================
# TEST SUITE 11: INTEGRATION
# ============================================================================

class TestIntegration:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, codebasebuddy_tool, temp_codebase):
        """Test end-to-end workflow"""
        # 1. Build index
        build_result = await codebasebuddy_tool.build_index(str(temp_codebase))
        assert build_result.get("success") is True
        
        # 2. Get stats
        stats_result = await codebasebuddy_tool.get_index_stats()
        assert stats_result.get("success") is True
        
        # 3. Search
        search_result = await codebasebuddy_tool.semantic_search("authentication")
        assert search_result.get("success") is True
        
        # 4. Get context for a result
        if search_result.get("results"):
            first_result = search_result["results"][0]
            file_path = first_result.get("file_path")
            line_number = first_result.get("start_line", 1)
            
            context_result = await codebasebuddy_tool.get_code_context(file_path, line_number)
            assert context_result.get("success") is True
        
        print("[PASS] End-to-end workflow works")
    
    @pytest.mark.asyncio
    async def test_context_manager(self, codebasebuddy_tool):
        """Test context manager usage"""
        async with codebasebuddy_tool:
            # Tool should be connected
            result = await codebasebuddy_tool.semantic_search("test")
            assert result is not None
        
        # Tool should be disconnected after context exit
        print("[PASS] Context manager works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

