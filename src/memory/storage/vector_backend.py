"""
Vector Database Backend for Embeddings
Supports Pinecone and Weaviate
"""

import logging
from typing import Any, Dict, List, Optional
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class VectorBackendType(Enum):
    """Vector database types"""
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"


class VectorBackend:
    """Vector database backend for embeddings"""
    
    def __init__(self, backend_type: VectorBackendType, config: Dict[str, Any]):
        """
        Initialize vector backend.
        
        Args:
            backend_type: Type of vector database
            config: Configuration dictionary
        """
        self.backend_type = backend_type
        self.config = config
        self.client = None
        self.index_name = config.get("index_name", "automaton-memory")
        logger.info(f"Vector backend initialized: {backend_type.value}")
    
    async def connect(self):
        """Connect to vector database"""
        try:
            if self.backend_type == VectorBackendType.PINECONE:
                await self._connect_pinecone()
            elif self.backend_type == VectorBackendType.WEAVIATE:
                await self._connect_weaviate()
            elif self.backend_type == VectorBackendType.QDRANT:
                await self._connect_qdrant()
            logger.info(f"Connected to {self.backend_type.value}")
        except Exception as e:
            logger.error(f"Failed to connect to vector database: {e}")
            self.client = None
    
    async def _connect_pinecone(self):
        """Connect to Pinecone"""
        try:
            import pinecone
            api_key = self.config.get("api_key")
            environment = self.config.get("environment", "us-east-1")
            
            pinecone.init(api_key=api_key, environment=environment)
            self.client = pinecone.Index(self.index_name)
        except ImportError:
            raise ImportError("Pinecone client not installed")
    
    async def _connect_weaviate(self):
        """Connect to Weaviate"""
        try:
            import weaviate
            url = self.config.get("url", "http://localhost:8080")
            self.client = weaviate.Client(url)
        except ImportError:
            raise ImportError("Weaviate client not installed")
    
    async def _connect_qdrant(self):
        """Connect to Qdrant"""
        try:
            from qdrant_client import QdrantClient
            url = self.config.get("url", "http://localhost:6333")
            self.client = QdrantClient(url=url)
        except ImportError:
            raise ImportError("Qdrant client not installed")
    
    async def upsert(self, entry_id: str, embedding: np.ndarray, metadata: Dict[str, Any]) -> bool:
        """Upsert embedding vector"""
        if not self.client:
            return False
        
        try:
            if self.backend_type == VectorBackendType.PINECONE:
                self.client.upsert(
                    vectors=[(entry_id, embedding.tolist(), metadata)]
                )
            elif self.backend_type == VectorBackendType.WEAVIATE:
                self.client.data_object.create(
                    data_object=metadata,
                    class_name=self.index_name,
                    vector=embedding.tolist()
                )
            elif self.backend_type == VectorBackendType.QDRANT:
                self.client.upsert(
                    collection_name=self.index_name,
                    points=[{
                        "id": entry_id,
                        "vector": embedding.tolist(),
                        "payload": metadata
                    }]
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to upsert vector: {e}")
            return False
    
    async def query(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query similar vectors"""
        if not self.client:
            return []
        
        try:
            if self.backend_type == VectorBackendType.PINECONE:
                results = self.client.query(
                    vector=query_embedding.tolist(),
                    top_k=top_k,
                    include_metadata=True,
                    filter=filter_metadata
                )
                return [
                    {
                        "id": match["id"],
                        "score": match["score"],
                        "metadata": match.get("metadata", {})
                    }
                    for match in results.get("matches", [])
                ]
            elif self.backend_type == VectorBackendType.WEAVIATE:
                # Weaviate query implementation
                pass
            elif self.backend_type == VectorBackendType.QDRANT:
                results = self.client.search(
                    collection_name=self.index_name,
                    query_vector=query_embedding.tolist(),
                    limit=top_k,
                    query_filter=filter_metadata
                )
                return [
                    {
                        "id": result.id,
                        "score": result.score,
                        "metadata": result.payload
                    }
                    for result in results
                ]
            
            return []
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []
    
    async def delete(self, entry_id: str) -> bool:
        """Delete vector"""
        if not self.client:
            return False
        
        try:
            if self.backend_type == VectorBackendType.PINECONE:
                self.client.delete(ids=[entry_id])
            elif self.backend_type == VectorBackendType.WEAVIATE:
                self.client.data_object.delete(
                    uuid=entry_id,
                    class_name=self.index_name
                )
            elif self.backend_type == VectorBackendType.QDRANT:
                self.client.delete(
                    collection_name=self.index_name,
                    points_selector=[entry_id]
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete vector: {e}")
            return False

