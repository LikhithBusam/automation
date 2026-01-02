"""
Parallel Processing for Independent Tasks
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class ParallelConfig:
    """Parallel processing configuration"""
    max_workers: int = 4
    use_processes: bool = False  # Use processes instead of threads
    timeout: Optional[float] = None


class ParallelProcessor:
    """
    Parallel processing for independent tasks.
    Supports both thread and process pools.
    """
    
    def __init__(self, config: Optional[ParallelConfig] = None):
        """Initialize parallel processor"""
        self.config = config or ParallelConfig()
        self.executor = None
        self.logger = logging.getLogger("parallel.processor")
        
        if self.config.use_processes:
            self.executor = ProcessPoolExecutor(max_workers=self.config.max_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
    
    async def process_parallel(
        self,
        tasks: List[Callable],
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Process tasks in parallel.
        
        Args:
            tasks: List of functions to execute
            *args: Positional arguments for tasks
            **kwargs: Keyword arguments for tasks
        
        Returns:
            List of results
        """
        # Create coroutines
        coroutines = [self._execute_task(task, *args, **kwargs) for task in tasks]
        
        # Execute in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Filter exceptions
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        if failed:
            self.logger.warning(f"{len(failed)} tasks failed out of {len(tasks)}")
        
        return successful
    
    async def _execute_task(
        self,
        task: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute single task"""
        if self.config.timeout:
            return await asyncio.wait_for(
                asyncio.to_thread(task, *args, **kwargs) if not asyncio.iscoroutinefunction(task) else task(*args, **kwargs),
                timeout=self.config.timeout
            )
        else:
            if asyncio.iscoroutinefunction(task):
                return await task(*args, **kwargs)
            else:
                return await asyncio.to_thread(task, *args, **kwargs)
    
    async def map_parallel(
        self,
        func: Callable,
        items: List[Any],
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Apply function to items in parallel.
        
        Args:
            func: Function to apply
            items: List of items
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        
        Returns:
            List of results
        """
        tasks = [lambda item=item: func(item, *args, **kwargs) for item in items]
        return await self.process_parallel(tasks)
    
    async def process_batches_parallel(
        self,
        items: List[Any],
        processor_func: Callable,
        batch_size: int = 10,
        max_concurrent_batches: int = 5
    ) -> List[Any]:
        """
        Process items in parallel batches.
        
        Args:
            items: Items to process
            processor_func: Function to process batch
            batch_size: Size of each batch
            max_concurrent_batches: Maximum concurrent batches
        
        Returns:
            List of results
        """
        # Create batches
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        # Process batches with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        async def process_batch(batch: List[Any]):
            async with semaphore:
                return await processor_func(batch)
        
        results = await asyncio.gather(*[process_batch(batch) for batch in batches])
        
        # Flatten results
        return [item for batch_result in results for item in batch_result]
    
    def close(self):
        """Close executor"""
        if self.executor:
            self.executor.shutdown(wait=True)


# Global parallel processor instance
_parallel_processor: Optional[ParallelProcessor] = None


def get_parallel_processor() -> ParallelProcessor:
    """Get global parallel processor"""
    global _parallel_processor
    if _parallel_processor is None:
        _parallel_processor = ParallelProcessor()
    return _parallel_processor

