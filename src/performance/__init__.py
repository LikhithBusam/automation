"""
Performance Optimization Module
Connection pooling, batch processing, query optimization, caching, streaming
"""

from src.performance.connection_pooling import (
    ConnectionPoolManager,
    get_connection_pool,
)
from src.performance.batch_processing import (
    BatchProcessor,
    get_batch_processor,
)
from src.performance.pagination import (
    Paginator,
    CursorPaginator,
    get_paginator,
)
from src.performance.query_optimization import (
    QueryOptimizer,
    get_query_optimizer,
)
from src.performance.prompt_optimization import (
    PromptOptimizer,
    get_prompt_optimizer,
)
from src.performance.streaming import (
    StreamingResponse,
    get_streaming_response,
)
from src.performance.parallel_processing import (
    ParallelProcessor,
    get_parallel_processor,
)
from src.performance.benchmarking import (
    PerformanceBenchmark,
    get_benchmark,
)

__all__ = [
    "ConnectionPoolManager",
    "get_connection_pool",
    "BatchProcessor",
    "get_batch_processor",
    "Paginator",
    "CursorPaginator",
    "get_paginator",
    "QueryOptimizer",
    "get_query_optimizer",
    "PromptOptimizer",
    "get_prompt_optimizer",
    "StreamingResponse",
    "get_streaming_response",
    "ParallelProcessor",
    "get_parallel_processor",
    "PerformanceBenchmark",
    "get_benchmark",
]
