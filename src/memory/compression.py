"""
Memory Compression for Cost Optimization
"""

import logging
import gzip
import zlib
from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CompressionType(Enum):
    """Compression types"""
    GZIP = "gzip"
    ZLIB = "zlib"
    LZMA = "lzma"


class MemoryCompressor:
    """Memory compression for cost optimization"""
    
    def __init__(self, postgres_backend):
        """Initialize compressor"""
        self.postgres = postgres_backend
        self.logger = logging.getLogger("memory.compression")
    
    def compress_entry(
        self,
        entry_id: str,
        compression_type: CompressionType = CompressionType.GZIP,
        min_size_bytes: int = 1000  # Only compress entries larger than this
    ) -> Dict[str, Any]:
        """
        Compress memory entry.
        
        Args:
            entry_id: Entry ID to compress
            compression_type: Type of compression
            min_size_bytes: Minimum size to compress
        
        Returns:
            Compression statistics
        """
        session = self.postgres.get_session()
        try:
            entries = self.postgres.retrieve(entry_id=entry_id, limit=1)
            if not entries:
                return {"success": False, "error": "Entry not found"}
            
            entry = entries[0]
            content = entry.get("content", "")
            original_size = len(content.encode("utf-8"))
            
            if original_size < min_size_bytes:
                return {
                    "success": False,
                    "reason": f"Entry too small ({original_size} bytes < {min_size_bytes} bytes)"
                }
            
            # Compress content
            if compression_type == CompressionType.GZIP:
                compressed = gzip.compress(content.encode("utf-8"))
            elif compression_type == CompressionType.ZLIB:
                compressed = zlib.compress(content.encode("utf-8"))
            else:
                return {"success": False, "error": "Unsupported compression type"}
            
            compressed_size = len(compressed)
            compression_ratio = 1 - (compressed_size / original_size)
            
            # Update entry with compressed content
            # Store compressed data as base64 or binary
            import base64
            compressed_b64 = base64.b64encode(compressed).decode("utf-8")
            
            self.postgres.update(entry_id, {
                "content": compressed_b64,  # Store compressed version
                "compressed": True,
                "compression_ratio": compression_ratio,
                "meta_data": {
                    **(entry.get("meta_data", {}) or {}),
                    "compression_type": compression_type.value,
                    "original_size": original_size,
                    "compressed_size": compressed_size
                }
            })
            
            stats = {
                "success": True,
                "entry_id": entry_id,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "space_saved": original_size - compressed_size,
                "compression_type": compression_type.value
            }
            
            self.logger.info(
                f"Compressed entry {entry_id}: "
                f"{original_size} -> {compressed_size} bytes "
                f"({compression_ratio*100:.1f}% reduction)"
            )
            
            return stats
        
        except Exception as e:
            self.logger.error(f"Compression failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()
    
    def decompress_entry(self, entry_id: str) -> Optional[str]:
        """Decompress memory entry"""
        session = self.postgres.get_session()
        try:
            entries = self.postgres.retrieve(entry_id=entry_id, limit=1)
            if not entries:
                return None
            
            entry = entries[0]
            if not entry.get("compressed"):
                return entry.get("content")
            
            # Get compression metadata
            metadata = entry.get("meta_data", {}) or {}
            compression_type = metadata.get("compression_type", "gzip")
            compressed_b64 = entry.get("content", "")
            
            # Decode and decompress
            import base64
            compressed = base64.b64decode(compressed_b64)
            
            if compression_type == "gzip":
                decompressed = gzip.decompress(compressed)
            elif compression_type == "zlib":
                decompressed = zlib.decompress(compressed)
            else:
                return None
            
            return decompressed.decode("utf-8")
        
        except Exception as e:
            self.logger.error(f"Decompression failed: {e}")
            return None
        finally:
            session.close()
    
    def compress_batch(
        self,
        tier: Optional[str] = None,
        min_size_bytes: int = 1000,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Compress multiple entries"""
        session = self.postgres.get_session()
        try:
            entries = self.postgres.retrieve(tier=tier, include_deleted=False, limit=limit)
            
            stats = {
                "total": len(entries),
                "compressed": 0,
                "skipped": 0,
                "errors": 0,
                "total_space_saved": 0
            }
            
            for entry in entries:
                if entry.get("compressed"):
                    stats["skipped"] += 1
                    continue
                
                result = self.compress_entry(
                    entry["id"],
                    min_size_bytes=min_size_bytes
                )
                
                if result.get("success"):
                    stats["compressed"] += 1
                    stats["total_space_saved"] += result.get("space_saved", 0)
                else:
                    stats["errors"] += 1
            
            self.logger.info(f"Batch compression complete: {stats}")
            return stats
        
        except Exception as e:
            self.logger.error(f"Batch compression failed: {e}")
            return {"error": str(e)}
        finally:
            session.close()

