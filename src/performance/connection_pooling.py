"""
Connection Pooling for External Services
Efficient connection management for databases, APIs, and other services
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Connection pool configuration"""
    min_size: int = 2
    max_size: int = 10
    max_overflow: int = 5
    timeout: float = 30.0
    recycle: int = 3600  # Recycle connections after 1 hour
    pool_pre_ping: bool = True  # Verify connections before using


class ConnectionPool:
    """Generic connection pool"""
    
    def __init__(self, pool_type: str, config: PoolConfig, factory: Callable):
        """
        Initialize connection pool.
        
        Args:
            pool_type: Type of pool (database, http, etc.)
            config: Pool configuration
            factory: Factory function to create connections
        """
        self.pool_type = pool_type
        self.config = config
        self.factory = factory
        self.pool: asyncio.Queue = asyncio.Queue(maxsize=config.max_size)
        self.active_connections = 0
        self.total_connections = 0
        self.logger = logging.getLogger(f"pool.{pool_type}")
        
        # Initialize pool
        asyncio.create_task(self._initialize_pool())
    
    async def _initialize_pool(self):
        """Initialize pool with minimum connections"""
        for _ in range(self.config.min_size):
            try:
                conn = await self.factory()
                await self.pool.put(conn)
                self.total_connections += 1
            except Exception as e:
                self.logger.error(f"Failed to create initial connection: {e}")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool"""
        conn = None
        try:
            # Try to get from pool
            try:
                conn = await asyncio.wait_for(
                    self.pool.get(),
                    timeout=self.config.timeout
                )
            except asyncio.TimeoutError:
                # Create new connection if under max
                if self.total_connections < self.config.max_size + self.config.max_overflow:
                    conn = await self.factory()
                    self.total_connections += 1
                    self.active_connections += 1
                else:
                    raise Exception("Connection pool exhausted")
            
            self.active_connections += 1
            
            # Verify connection if pre-ping enabled
            if self.config.pool_pre_ping and hasattr(conn, 'ping'):
                try:
                    await conn.ping()
                except Exception:
                    # Connection is dead, create new one
                    conn = await self.factory()
            
            yield conn
        
        finally:
            if conn:
                self.active_connections -= 1
                # Return to pool if not at max
                if self.pool.qsize() < self.config.max_size:
                    await self.pool.put(conn)
                else:
                    # Close excess connection
                    if hasattr(conn, 'close'):
                        await conn.close()
                    self.total_connections -= 1
    
    async def close(self):
        """Close all connections in pool"""
        while not self.pool.empty():
            conn = await self.pool.get()
            if hasattr(conn, 'close'):
                await conn.close()
        self.logger.info(f"Closed {self.pool_type} connection pool")


class ConnectionPoolManager:
    """
    Manages connection pools for all external services.
    Supports databases, HTTP clients, and other services.
    """
    
    def __init__(self):
        """Initialize connection pool manager"""
        self.pools: Dict[str, ConnectionPool] = {}
        self.logger = logging.getLogger("connection.pool.manager")
    
    def register_pool(
        self,
        name: str,
        pool_type: str,
        factory: Callable,
        config: Optional[PoolConfig] = None
    ):
        """Register connection pool"""
        if config is None:
            config = PoolConfig()
        
        pool = ConnectionPool(pool_type, config, factory)
        self.pools[name] = pool
        self.logger.info(f"Registered connection pool: {name}")
    
    async def get_connection(self, pool_name: str):
        """Get connection from pool"""
        pool = self.pools.get(pool_name)
        if not pool:
            raise ValueError(f"Pool {pool_name} not found")
        
        return pool.acquire()
    
    def get_pool(self, pool_name: str) -> Optional[ConnectionPool]:
        """Get pool by name"""
        return self.pools.get(pool_name)
    
    async def close_all(self):
        """Close all pools"""
        for pool in self.pools.values():
            await pool.close()
        self.pools.clear()


# Database connection pool
class DatabasePool:
    """Database connection pool using SQLAlchemy"""
    
    def __init__(self, database_url: str, config: Optional[PoolConfig] = None):
        """Initialize database pool"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        if config is None:
            config = PoolConfig(
                min_size=2,
                max_size=10,
                max_overflow=5
            )
        
        self.engine = create_async_engine(
            database_url,
            pool_size=config.max_size,
            max_overflow=config.max_overflow,
            pool_pre_ping=config.pool_pre_ping,
            pool_recycle=config.recycle
        )
        
        self.Session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.logger = logging.getLogger("pool.database")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session"""
        async with self.Session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def close(self):
        """Close database pool"""
        await self.engine.dispose()


# HTTP connection pool
class HTTPPool:
    """HTTP connection pool using httpx"""
    
    def __init__(self, base_url: str, config: Optional[PoolConfig] = None):
        """Initialize HTTP pool"""
        import httpx
        
        if config is None:
            config = PoolConfig(
                min_size=2,
                max_size=20,
                max_overflow=10
            )
        
        limits = httpx.Limits(
            max_keepalive_connections=config.max_size,
            max_connections=config.max_size + config.max_overflow
        )
        
        self.client = httpx.AsyncClient(
            base_url=base_url,
            limits=limits,
            timeout=httpx.Timeout(config.timeout)
        )
        self.logger = logging.getLogger("pool.http")
    
    async def get_client(self):
        """Get HTTP client"""
        return self.client
    
    async def close(self):
        """Close HTTP pool"""
        await self.client.aclose()


# Global connection pool manager
_connection_pool_manager = ConnectionPoolManager()


def get_connection_pool() -> ConnectionPoolManager:
    """Get global connection pool manager"""
    return _connection_pool_manager

