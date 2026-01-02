"""
Elasticsearch Backend for Semantic Search
Handles full-text and semantic search capabilities
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from elasticsearch import AsyncElasticsearch
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    logger.warning("Elasticsearch not available")


class ElasticsearchBackend:
    """Elasticsearch backend for semantic search"""
    
    def __init__(self, hosts: List[str], index_name: str = "automaton-memory"):
        """
        Initialize Elasticsearch backend.
        
        Args:
            hosts: List of Elasticsearch host URLs
            index_name: Index name for memory entries
        """
        if not ELASTICSEARCH_AVAILABLE:
            raise ImportError("Elasticsearch client not installed")
        
        self.hosts = hosts
        self.index_name = index_name
        self.client: Optional[AsyncElasticsearch] = None
        logger.info("Elasticsearch backend initialized")
    
    async def connect(self):
        """Connect to Elasticsearch"""
        try:
            self.client = AsyncElasticsearch(hosts=self.hosts)
            # Create index if it doesn't exist
            if not await self.client.indices.exists(index=self.index_name):
                await self._create_index()
            logger.info("Connected to Elasticsearch")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            self.client = None
    
    async def disconnect(self):
        """Disconnect from Elasticsearch"""
        if self.client:
            await self.client.close()
            self.client = None
    
    async def _create_index(self):
        """Create Elasticsearch index with mapping"""
        if not self.client:
            return
        
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "summary": {"type": "text"},
                    "tier": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "agent": {"type": "keyword"},
                    "project": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "last_accessed_at": {"type": "date"},
                    "relevance_score": {"type": "float"},
                }
            }
        }
        
        await self.client.indices.create(index=self.index_name, body=mapping)
    
    async def index(self, entry_data: Dict[str, Any]) -> bool:
        """Index memory entry"""
        if not self.client:
            return False
        
        try:
            doc = {
                "id": entry_data["id"],
                "content": entry_data.get("content", ""),
                "summary": entry_data.get("summary"),
                "tier": entry_data.get("tier"),
                "type": entry_data.get("type"),
                "agent": entry_data.get("agent"),
                "project": entry_data.get("project"),
                "tags": entry_data.get("tags", []),
                "created_at": entry_data.get("created_at"),
                "last_accessed_at": entry_data.get("last_accessed_at"),
                "relevance_score": entry_data.get("relevance_score", 1.0),
            }
            
            await self.client.index(
                index=self.index_name,
                id=entry_data["id"],
                document=doc
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index entry: {e}")
            return False
    
    async def search(
        self,
        query: str,
        tier: Optional[str] = None,
        agent: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memory entries"""
        if not self.client:
            return []
        
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["content^2", "summary"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "size": limit
            }
            
            # Add filters
            filters = []
            if tier:
                filters.append({"term": {"tier": tier}})
            if agent:
                filters.append({"term": {"agent": agent}})
            
            if filters:
                search_body["query"]["bool"]["filter"] = filters
            
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    **hit["_source"]
                })
            
            return results
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return []
    
    async def delete(self, entry_id: str) -> bool:
        """Delete entry from index"""
        if not self.client:
            return False
        
        try:
            await self.client.delete(index=self.index_name, id=entry_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete from Elasticsearch: {e}")
            return False

