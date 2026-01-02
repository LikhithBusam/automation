"""
Memory Deduplication
"""

import logging
from typing import Any, Dict, List, Set, Tuple
import hashlib
import numpy as np

logger = logging.getLogger(__name__)


class MemoryDeduplicator:
    """Memory deduplication engine"""
    
    def __init__(self, postgres_backend, embedding_model):
        """Initialize deduplicator"""
        self.postgres = postgres_backend
        self.embedding_model = embedding_model
        self.logger = logging.getLogger("memory.deduplication")
    
    def find_duplicates(
        self,
        similarity_threshold: float = 0.95,
        tier: str = None
    ) -> List[Tuple[str, str, float]]:
        """
        Find duplicate memory entries.
        
        Args:
            similarity_threshold: Minimum similarity to consider duplicate
            tier: Filter by tier
        
        Returns:
            List of (entry_id1, entry_id2, similarity) tuples
        """
        session = self.postgres.get_session()
        try:
            # Get entries
            entries = self.postgres.retrieve(tier=tier, include_deleted=False, limit=10000)
            
            duplicates = []
            processed = set()
            
            for i, entry1 in enumerate(entries):
                if entry1["id"] in processed:
                    continue
                
                content1 = entry1.get("content", "")
                embedding1 = self.embedding_model.encode(content1, convert_to_numpy=True)
                
                for j, entry2 in enumerate(entries[i+1:], start=i+1):
                    if entry2["id"] in processed:
                        continue
                    
                    content2 = entry2.get("content", "")
                    embedding2 = self.embedding_model.encode(content2, convert_to_numpy=True)
                    
                    # Calculate similarity
                    similarity = self._cosine_similarity(embedding1, embedding2)
                    
                    if similarity >= similarity_threshold:
                        duplicates.append((entry1["id"], entry2["id"], similarity))
                        processed.add(entry2["id"])
            
            self.logger.info(f"Found {len(duplicates)} duplicate pairs")
            return duplicates
        
        except Exception as e:
            self.logger.error(f"Failed to find duplicates: {e}")
            return []
        finally:
            session.close()
    
    def deduplicate(
        self,
        similarity_threshold: float = 0.95,
        keep_strategy: str = "oldest"  # "oldest", "newest", "most_accessed"
    ) -> Dict[str, Any]:
        """
        Deduplicate memory entries.
        
        Args:
            similarity_threshold: Minimum similarity to consider duplicate
            keep_strategy: Which entry to keep
        
        Returns:
            Deduplication statistics
        """
        duplicates = self.find_duplicates(similarity_threshold)
        
        stats = {
            "duplicate_pairs": len(duplicates),
            "merged": 0,
            "deleted": 0,
            "errors": 0
        }
        
        for entry_id1, entry_id2, similarity in duplicates:
            try:
                # Get both entries
                entries = self.postgres.retrieve(entry_id=entry_id1, limit=1)
                entry1 = entries[0] if entries else None
                
                entries = self.postgres.retrieve(entry_id=entry_id2, limit=1)
                entry2 = entries[0] if entries else None
                
                if not entry1 or not entry2:
                    continue
                
                # Determine which to keep
                keep_id, merge_id = self._choose_keep_entry(
                    entry1, entry2, keep_strategy
                )
                
                # Merge metadata
                keep_entry = self.postgres.retrieve(entry_id=keep_id, limit=1)[0]
                merge_entry = self.postgres.retrieve(entry_id=merge_id, limit=1)[0]
                
                # Merge tags
                tags1 = keep_entry.get("tags", []) or []
                tags2 = merge_entry.get("tags", []) or []
                merged_tags = list(set(tags1 + tags2))
                
                # Merge relationships
                rels1 = keep_entry.get("relationships", []) or []
                rels2 = merge_entry.get("relationships", []) or []
                merged_rels = list(set(rels1 + rels2))
                
                # Update kept entry
                self.postgres.update(keep_id, {
                    "tags": merged_tags,
                    "relationships": merged_rels,
                    "access_count": keep_entry.get("access_count", 0) + merge_entry.get("access_count", 0)
                })
                
                # Soft delete merged entry
                self.postgres.soft_delete(merge_id, backup=True)
                
                stats["merged"] += 1
                stats["deleted"] += 1
            
            except Exception as e:
                self.logger.error(f"Failed to deduplicate pair: {e}")
                stats["errors"] += 1
        
        self.logger.info(f"Deduplication complete: {stats}")
        return stats
    
    def _choose_keep_entry(
        self,
        entry1: Dict[str, Any],
        entry2: Dict[str, Any],
        strategy: str
    ) -> Tuple[str, str]:
        """Choose which entry to keep"""
        if strategy == "oldest":
            date1 = entry1.get("created_at", "")
            date2 = entry2.get("created_at", "")
            if date1 < date2:
                return entry1["id"], entry2["id"]
            return entry2["id"], entry1["id"]
        
        elif strategy == "newest":
            date1 = entry1.get("created_at", "")
            date2 = entry2.get("created_at", "")
            if date1 > date2:
                return entry1["id"], entry2["id"]
            return entry2["id"], entry1["id"]
        
        elif strategy == "most_accessed":
            count1 = entry1.get("access_count", 0)
            count2 = entry2.get("access_count", 0)
            if count1 >= count2:
                return entry1["id"], entry2["id"]
            return entry2["id"], entry1["id"]
        
        # Default to oldest
        return entry1["id"], entry2["id"]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

