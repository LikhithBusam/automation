"""
Memory Analytics and Insights
"""

import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class MemoryAnalytics:
    """Memory analytics and insights"""
    
    def __init__(self, postgres_backend):
        """Initialize analytics"""
        self.postgres = postgres_backend
        self.logger = logging.getLogger("memory.analytics")
    
    def get_insights(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive memory insights.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Analytics insights
        """
        session = self.postgres.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all entries
            entries = self.postgres.retrieve(include_deleted=False, limit=100000)
            
            # Calculate insights
            insights = {
                "summary": self._calculate_summary(entries),
                "tier_distribution": self._tier_distribution(entries),
                "type_distribution": self._type_distribution(entries),
                "agent_activity": self._agent_activity(entries, cutoff_date),
                "project_activity": self._project_activity(entries, cutoff_date),
                "access_patterns": self._access_patterns(entries),
                "growth_trends": self._growth_trends(entries, days),
                "top_tags": self._top_tags(entries),
                "storage_efficiency": self._storage_efficiency(entries),
            }
            
            return insights
        except Exception as e:
            self.logger.error(f"Failed to get insights: {e}")
            return {}
        finally:
            session.close()
    
    def _calculate_summary(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics"""
        total = len(entries)
        total_size = sum(len(e.get("content", "")) for e in entries)
        avg_size = total_size / total if total > 0 else 0
        
        return {
            "total_entries": total,
            "total_size_bytes": total_size,
            "average_entry_size": avg_size,
            "oldest_entry": min(
                (e.get("created_at") for e in entries if e.get("created_at")),
                default=None
            ),
            "newest_entry": max(
                (e.get("created_at") for e in entries if e.get("created_at")),
                default=None
            ),
        }
    
    def _tier_distribution(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate tier distribution"""
        tier_counts = Counter(e.get("tier", "unknown") for e in entries)
        total = len(entries)
        
        return {
            "counts": dict(tier_counts),
            "percentages": {
                tier: (count / total * 100) if total > 0 else 0
                for tier, count in tier_counts.items()
            }
        }
    
    def _type_distribution(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate type distribution"""
        type_counts = Counter(e.get("type", "unknown") for e in entries)
        return dict(type_counts)
    
    def _agent_activity(self, entries: List[Dict[str, Any]], cutoff_date: datetime) -> Dict[str, Any]:
        """Calculate agent activity"""
        recent_entries = [
            e for e in entries
            if e.get("created_at") and datetime.fromisoformat(e["created_at"]) >= cutoff_date
        ]
        
        agent_counts = Counter(e.get("agent") for e in recent_entries if e.get("agent"))
        agent_access = defaultdict(int)
        
        for e in recent_entries:
            if e.get("agent"):
                agent_access[e["agent"]] += e.get("access_count", 0)
        
        return {
            "most_active": dict(agent_counts.most_common(10)),
            "most_accessed": dict(sorted(agent_access.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def _project_activity(self, entries: List[Dict[str, Any]], cutoff_date: datetime) -> Dict[str, Any]:
        """Calculate project activity"""
        recent_entries = [
            e for e in entries
            if e.get("created_at") and datetime.fromisoformat(e["created_at"]) >= cutoff_date
        ]
        
        project_counts = Counter(e.get("project") for e in recent_entries if e.get("project"))
        return dict(project_counts.most_common(10))
    
    def _access_patterns(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze access patterns"""
        access_counts = [e.get("access_count", 0) for e in entries]
        
        if not access_counts:
            return {}
        
        return {
            "average_access_count": sum(access_counts) / len(access_counts),
            "max_access_count": max(access_counts),
            "min_access_count": min(access_counts),
            "highly_accessed": len([c for c in access_counts if c > 10]),
        }
    
    def _growth_trends(self, entries: List[Dict[str, Any]], days: int) -> Dict[str, Any]:
        """Calculate growth trends"""
        daily_counts = defaultdict(int)
        
        for e in entries:
            if e.get("created_at"):
                try:
                    created = datetime.fromisoformat(e["created_at"])
                    day_key = created.strftime("%Y-%m-%d")
                    daily_counts[day_key] += 1
                except:
                    pass
        
        return {
            "daily_counts": dict(daily_counts),
            "average_per_day": len(entries) / days if days > 0 else 0,
        }
    
    def _top_tags(self, entries: List[Dict[str, Any]], limit: int = 20) -> Dict[str, int]:
        """Get top tags"""
        all_tags = []
        for e in entries:
            tags = e.get("tags", [])
            if isinstance(tags, list):
                all_tags.extend(tags)
        
        tag_counts = Counter(all_tags)
        return dict(tag_counts.most_common(limit))
    
    def _storage_efficiency(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate storage efficiency"""
        compressed = [e for e in entries if e.get("compressed")]
        total_size = sum(len(e.get("content", "")) for e in entries)
        compressed_size = sum(
            len(e.get("content", "")) * (1 - e.get("compression_ratio", 0))
            for e in compressed
        )
        
        return {
            "compressed_entries": len(compressed),
            "compression_ratio": compressed_size / total_size if total_size > 0 else 0,
            "space_saved_bytes": compressed_size,
        }

