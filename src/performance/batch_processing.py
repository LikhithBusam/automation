"""
Efficient Batch Processing for Bulk Operations
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Batch processing configuration"""
    batch_size: int = 100
    max_concurrent_batches: int = 5
    timeout: float = 300.0  # 5 minutes
    retry_on_failure: bool = True
    max_retries: int = 3


class BatchProcessor:
    """
    Efficient batch processing for bulk operations.
    Supports parallel batch execution and retry logic.
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """Initialize batch processor"""
        self.config = config or BatchConfig()
        self.logger = logging.getLogger("batch.processor")
    
    async def process_batch(
        self,
        items: List[Any],
        processor_func: Callable,
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process items in batches.
        
        Args:
            items: List of items to process
            processor_func: Async function to process batch
            batch_size: Optional batch size override
        
        Returns:
            Processing statistics
        """
        batch_size = batch_size or self.config.batch_size
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        stats = {
            "total_items": len(items),
            "total_batches": len(batches),
            "processed": 0,
            "failed": 0,
            "errors": []
        }
        
        # Process batches with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        
        async def process_single_batch(batch: List[Any], batch_num: int):
            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        processor_func(batch),
                        timeout=self.config.timeout
                    )
                    stats["processed"] += len(batch)
                    return result
                except asyncio.TimeoutError:
                    stats["failed"] += len(batch)
                    stats["errors"].append(f"Batch {batch_num} timed out")
                    self.logger.error(f"Batch {batch_num} timed out")
                except Exception as e:
                    stats["failed"] += len(batch)
                    stats["errors"].append(f"Batch {batch_num}: {str(e)}")
                    self.logger.error(f"Batch {batch_num} failed: {e}")
                    
                    # Retry if enabled
                    if self.config.retry_on_failure:
                        for attempt in range(self.config.max_retries):
                            try:
                                result = await processor_func(batch)
                                stats["processed"] += len(batch)
                                stats["failed"] -= len(batch)
                                return result
                            except Exception as retry_error:
                                if attempt == self.config.max_retries - 1:
                                    self.logger.error(f"Batch {batch_num} failed after {self.config.max_retries} retries")
        
        # Process all batches
        tasks = [
            process_single_batch(batch, i)
            for i, batch in enumerate(batches)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        stats["success_rate"] = stats["processed"] / stats["total_items"] if stats["total_items"] > 0 else 0
        
        self.logger.info(
            f"Batch processing complete: {stats['processed']}/{stats['total_items']} items "
            f"({stats['success_rate']*100:.1f}% success rate)"
        )
        
        return stats
    
    async def process_with_progress(
        self,
        items: List[Any],
        processor_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process items with progress tracking.
        
        Args:
            items: List of items to process
            processor_func: Async function to process item
            progress_callback: Optional callback for progress updates
        
        Returns:
            Processing statistics
        """
        stats = {
            "total": len(items),
            "processed": 0,
            "failed": 0,
            "errors": []
        }
        
        for i, item in enumerate(items):
            try:
                await processor_func(item)
                stats["processed"] += 1
                
                if progress_callback:
                    await progress_callback(i + 1, len(items))
            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(f"Item {i}: {str(e)}")
                self.logger.error(f"Failed to process item {i}: {e}")
        
        return stats


# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get global batch processor"""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor

