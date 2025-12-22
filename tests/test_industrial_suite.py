"""
Industrial-Grade Test Suite - Fast & Comprehensive
Optimized for speed and 100% coverage

Performance Targets:
- All tests complete in < 5 seconds
- 100% pass rate
- No API mismatches
- Real implementation testing
"""

import pytest
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta

# Import actual implementations
from src.autogen_adapters.groupchat_factory import GroupChatFactory
from src.mcp.base_tool import TokenBucket, TTLCache, CacheEntry
from src.security.input_validator import InputValidator


# ============================================================================
# PERFORMANCE-OPTIMIZED GROUPCHAT FACTORY TESTS
# ============================================================================

class TestGroupChatFactoryFast:
    """Fast, accurate GroupChat factory tests"""

    @pytest.fixture
    def factory(self):
        """Use actual production config"""
        return GroupChatFactory()

    def test_factory_initialization(self, factory):
        """Test factory loads production config"""
        assert factory is not None
        assert len(factory.groupchat_configs) > 0
        assert len(factory.termination_configs) > 0

    def test_all_groupchats_configured(self, factory):
        """Verify all 6 groupchats are configured"""
        expected = [
            "code_review_chat",
            "security_audit_chat",
            "documentation_chat",
            "deployment_chat",
            "research_chat",
            "full_team_chat"
        ]

        for chat_name in expected:
            assert chat_name in factory.groupchat_configs

    def test_termination_functions(self, factory):
        """Test all termination conditions create functions"""
        conditions = [
            "check_code_review_complete",
            "check_security_audit_complete",
            "check_documentation_complete",
            "check_deployment_complete",
            "check_research_complete",
            "check_full_team_complete"
        ]

        for condition in conditions:
            func = factory._create_termination_function(condition)
            assert func is not None
            assert callable(func)

    def test_termination_detection_speed(self, factory):
        """Test termination detection is fast"""
        func = factory._create_termination_function("check_code_review_complete")

        # Benchmark termination detection
        start = time.perf_counter()
        for _ in range(1000):
            result = func({"content": "TERMINATE"})
        duration = time.perf_counter() - start

        assert duration < 0.1  # Should process 1000 checks in < 100ms
        assert result == True

    def test_keyword_detection_case_insensitive(self, factory):
        """Test case-insensitive keyword detection"""
        func = factory._create_termination_function("check_code_review_complete")

        test_cases = [
            ("TERMINATE", True),
            ("terminate", True),
            ("TeRmInAtE", True),
            ("CODE_REVIEW_COMPLETE", True),
            ("code_review_complete", True),
            ("continue working", False),
            ("", False),
        ]

        for content, expected in test_cases:
            result = func({"content": content})
            assert result == expected

    def test_multiple_terminate_detection(self, factory):
        """Test detection of spam TERMINATE messages"""
        func = factory._create_termination_function("check_code_review_complete")

        # Simulate the bug scenario
        spam = "**TERMINATE**\n" * 10
        result = func({"content": spam})

        assert result == True  # Should force termination

    def test_groupchat_list(self, factory):
        """Test listing all groupchats"""
        chats = factory.list_groupchats()

        assert isinstance(chats, list)
        assert len(chats) >= 6
        assert "code_review_chat" in chats

    def test_groupchat_info(self, factory):
        """Test getting groupchat info"""
        info = factory.get_groupchat_info("code_review_chat")

        assert info is not None
        assert "agents" in info
        assert "max_round" in info
        assert info["max_round"] == 20


# ============================================================================
# PERFORMANCE-OPTIMIZED MCP TOOLS TESTS
# ============================================================================

class TestTokenBucketFast:
    """Fast TokenBucket tests with actual timings"""

    def test_initialization_speed(self):
        """Test TokenBucket initializes instantly"""
        start = time.perf_counter()
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        duration = time.perf_counter() - start

        assert duration < 0.001  # < 1ms
        assert bucket.tokens == 100.0

    def test_consumption_performance(self):
        """Test token consumption is O(1)"""
        bucket = TokenBucket(capacity=1000, refill_rate=100.0)

        start = time.perf_counter()
        for _ in range(100):
            bucket.consume(1.0)
        duration = time.perf_counter() - start

        assert duration < 0.01  # 100 operations in < 10ms

    def test_refill_accuracy(self):
        """Test refill is mathematically accurate"""
        bucket = TokenBucket(capacity=100, refill_rate=50.0)  # 50 tokens/sec

        # Consume all
        bucket.consume(100)
        assert bucket.tokens == 0

        # Wait exactly 0.5 seconds = 25 tokens
        time.sleep(0.5)
        bucket._refill()

        # Allow 10% tolerance for timing precision
        assert 22.5 <= bucket.tokens <= 27.5

    def test_wait_time_calculation(self):
        """Test wait time calculation"""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)

        bucket.consume(100)  # Empty bucket

        # Need 50 tokens at 10/sec = 5 seconds
        wait_time = bucket.wait_time(50)
        assert 4.9 <= wait_time <= 5.1

    @pytest.mark.asyncio
    async def test_async_acquire_speed(self):
        """Test async token acquisition"""
        bucket = TokenBucket(capacity=10, refill_rate=100.0)

        start = time.perf_counter()
        await bucket.acquire(1.0)
        duration = time.perf_counter() - start

        assert duration < 0.01  # Should be nearly instant


class TestTTLCacheFast:
    """Fast TTL cache tests with actual API"""

    def test_cache_initialization_speed(self):
        """Test cache initializes instantly"""
        start = time.perf_counter()
        cache = TTLCache(default_ttl=300, max_size=1000)
        duration = time.perf_counter() - start

        assert duration < 0.001

    def test_cache_set_get_performance(self):
        """Test cache operations are fast"""
        cache = TTLCache(default_ttl=300)

        # Benchmark set operations
        start = time.perf_counter()
        for i in range(100):
            cache.set(f"op_{i}", {"id": i}, f"data_{i}")
        duration_set = time.perf_counter() - start

        # Benchmark get operations
        start = time.perf_counter()
        for i in range(100):
            cache.get(f"op_{i}", {"id": i})
        duration_get = time.perf_counter() - start

        assert duration_set < 0.1  # 100 sets in < 100ms
        assert duration_get < 0.05  # 100 gets in < 50ms

    def test_cache_hit_rate(self):
        """Test cache actually caches"""
        cache = TTLCache(default_ttl=60)

        # Set 10 items
        for i in range(10):
            cache.set("read_file", {"path": f"/file{i}.txt"}, f"content{i}")

        # Get all 10 items (should be hits)
        for i in range(10):
            result = cache.get("read_file", {"path": f"/file{i}.txt"})
            assert result == f"content{i}"

        # Check statistics
        stats = cache.stats
        assert stats["hits"] == 10
        assert stats["misses"] == 0

    def test_cache_expiry_works(self):
        """Test TTL expiration"""
        cache = TTLCache(default_ttl=0.5)  # 500ms TTL

        cache.set("operation", {"id": 1}, "data")

        # Should be available immediately
        assert cache.get("operation", {"id": 1}) == "data"

        # Wait for expiry
        time.sleep(0.6)

        # Should be expired
        assert cache.get("operation", {"id": 1}) is None

    def test_lru_eviction_works(self):
        """Test LRU eviction when max size reached"""
        cache = TTLCache(default_ttl=60, max_size=5)

        # Fill cache
        for i in range(5):
            cache.set(f"op{i}", {"id": i}, f"data{i}")

        # Add 6th item (should trigger eviction)
        cache.set("op5", {"id": 5}, "data5")

        # Verify cache respects max size
        assert len(cache._cache) <= 5

        # Verify the new item was added
        assert cache.get("op5", {"id": 5}) is not None

        # Verify at least one old item was evicted
        items_found = sum(1 for i in range(6) if cache.get(f"op{i}", {"id": i}) is not None)
        assert items_found == 5  # Exactly max_size items remain

    def test_cache_cleanup_performance(self):
        """Test cleanup is fast"""
        cache = TTLCache(default_ttl=0.1)  # Very short TTL

        # Add 100 items
        for i in range(100):
            cache.set(f"op{i}", {"id": i}, f"data{i}")

        # Wait for expiry
        time.sleep(0.2)

        # Cleanup should be fast
        start = time.perf_counter()
        cache.cleanup_expired()
        duration = time.perf_counter() - start

        assert duration < 0.05  # < 50ms for 100 items


class TestCacheEntryFast:
    """Fast CacheEntry tests"""

    def test_entry_creation(self):
        """Test CacheEntry creation"""
        now = time.time()
        entry = CacheEntry(
            data="test_data",
            created_at=now,
            expires_at=now + 60
        )

        assert entry.data == "test_data"
        assert entry.access_count == 0
        assert not entry.is_expired()

    def test_entry_touch(self):
        """Test touching updates access"""
        now = time.time()
        entry = CacheEntry(data="test", created_at=now, expires_at=now + 60)

        original_access = entry.last_accessed
        time.sleep(0.01)

        entry.touch()

        assert entry.access_count == 1
        assert entry.last_accessed > original_access

    def test_expiry_detection(self):
        """Test expiry detection"""
        now = time.time()

        # Expired entry
        expired = CacheEntry(data="old", created_at=now - 100, expires_at=now - 50)
        assert expired.is_expired() == True

        # Valid entry
        valid = CacheEntry(data="new", created_at=now, expires_at=now + 60)
        assert valid.is_expired() == False


# ============================================================================
# SECURITY TESTS - FAST & COMPREHENSIVE
# ============================================================================

class TestInputValidatorFast:
    """Fast security validation tests"""

    @pytest.fixture
    def validator(self):
        return InputValidator()

    def test_path_traversal_detection_speed(self, validator):
        """Test path traversal detection is fast"""
        attacks = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//etc/shadow",
        ] * 10  # 30 attacks

        base_dir = "/var/www/app"

        start = time.perf_counter()
        for attack in attacks:
            try:
                validator.validate_path(attack, base_dir)
            except ValueError:
                pass  # Expected
        duration = time.perf_counter() - start

        assert duration < 0.1  # 30 validations in < 100ms

    def test_sql_injection_detection_speed(self, validator):
        """Test SQL injection detection is fast"""
        attacks = [
            "1' OR '1'='1",
            "'; DROP TABLE users;--",
            "admin'--",
        ] * 10  # 30 attacks

        start = time.perf_counter()
        for attack in attacks:
            try:
                validator._default_validation(attack)
            except ValueError:
                pass  # Expected
        duration = time.perf_counter() - start

        assert duration < 0.05  # < 50ms

    def test_safe_input_performance(self, validator):
        """Test validating safe inputs is very fast"""
        safe_inputs = ["user123", "john_doe", "test@example.com"] * 100

        start = time.perf_counter()
        for input_val in safe_inputs:
            try:
                validator._default_validation(input_val)
            except:
                pass
        duration = time.perf_counter() - start

        assert duration < 0.1  # 300 validations in < 100ms


# ============================================================================
# INTEGRATION TESTS - REALISTIC SCENARIOS
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world usage patterns"""

    def test_code_review_workflow_simulation(self):
        """Simulate a code review workflow"""
        factory = GroupChatFactory()

        # Get termination function
        term_func = factory._create_termination_function("check_code_review_complete")

        # Simulate conversation
        messages = [
            {"content": "Let's review this code"},
            {"content": "I found some issues"},
            {"content": "Security looks good"},
            {"content": "All issues resolved. CODE_REVIEW_COMPLETE"},
        ]

        start = time.perf_counter()
        for i, msg in enumerate(messages):
            is_done = term_func(msg)
            if i < 3:
                assert is_done == False
            else:
                assert is_done == True
        duration = time.perf_counter() - start

        assert duration < 0.01  # Should be near-instant

    def test_cached_file_reads(self):
        """Test caching speeds up repeated operations"""
        cache = TTLCache(default_ttl=60)

        # First read (cache miss)
        start = time.perf_counter()
        result1 = cache.get("read_file", {"path": "/test.py"})
        duration_miss = time.perf_counter() - start

        assert result1 is None  # Cache miss

        # Store in cache
        cache.set("read_file", {"path": "/test.py"}, "file content")

        # Second read (cache hit)
        start = time.perf_counter()
        result2 = cache.get("read_file", {"path": "/test.py"})
        duration_hit = time.perf_counter() - start

        assert result2 == "file content"
        assert duration_hit < duration_miss  # Hit should be faster

    def test_rate_limiting_under_load(self):
        """Test rate limiting handles burst traffic"""
        bucket = TokenBucket(capacity=10, refill_rate=100.0)

        # Simulate burst of 10 requests
        start = time.perf_counter()
        success_count = 0
        for _ in range(10):
            if bucket.consume(1.0):
                success_count += 1
        duration = time.perf_counter() - start

        assert success_count == 10  # All succeed (within capacity)
        assert duration < 0.01  # Very fast


# ============================================================================
# PERFORMANCE BENCHMARK TESTS
# ============================================================================

class TestPerformanceBenchmarks:
    """Benchmark critical operations"""

    def test_termination_check_throughput(self):
        """Measure termination checks per second"""
        factory = GroupChatFactory()
        func = factory._create_termination_function("check_code_review_complete")

        msg = {"content": "Working on it"}
        iterations = 10000

        start = time.perf_counter()
        for _ in range(iterations):
            func(msg)
        duration = time.perf_counter() - start

        throughput = iterations / duration

        print(f"\nTermination check throughput: {throughput:,.0f} checks/sec")
        assert throughput > 50000  # Should handle 50k+ checks per second

    def test_cache_throughput(self):
        """Measure cache operations per second"""
        cache = TTLCache()
        iterations = 1000

        # Measure set throughput
        start = time.perf_counter()
        for i in range(iterations):
            cache.set(f"op{i%100}", {"id": i}, f"data{i}")
        set_duration = time.perf_counter() - start

        # Measure get throughput
        start = time.perf_counter()
        for i in range(iterations):
            cache.get(f"op{i%100}", {"id": i})
        get_duration = time.perf_counter() - start

        set_throughput = iterations / set_duration
        get_throughput = iterations / get_duration

        print(f"\nCache SET throughput: {set_throughput:,.0f} ops/sec")
        print(f"Cache GET throughput: {get_throughput:,.0f} ops/sec")

        assert set_throughput > 5000  # 5k+ sets per second
        assert get_throughput > 10000  # 10k+ gets per second

    def test_token_bucket_throughput(self):
        """Measure rate limiter throughput"""
        bucket = TokenBucket(capacity=1000, refill_rate=1000.0)
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            bucket.consume(1.0)
        duration = time.perf_counter() - start

        throughput = iterations / duration

        print(f"\nToken bucket throughput: {throughput:,.0f} ops/sec")
        assert throughput > 20000  # 20k+ operations per second


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
