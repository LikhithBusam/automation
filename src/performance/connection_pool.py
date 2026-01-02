"""
Connection Pooling for Database and API Connections
Optimizes resource usage and improves performance
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool, NullPool

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """PostgreSQL connection pool using SQLAlchemy"""
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
    ):
        """
        Initialize database connection pool.
        
        Args:
            database_url: PostgreSQL connection URL
            pool_size: Number of connections to maintain
            max_overflow: Maximum overflow connections
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Recycle connections after this many seconds
            pool_pre_ping: Test connections before using
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        
        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            echo=False,  # Set to True for SQL logging
        )
        
        # Add connection pool event listeners
        self._setup_event_listeners()
        
        logger.info(
            f"Database connection pool initialized: "
            f"size={pool_size}, max_overflow={max_overflow}"
        )
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring"""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """Set connection-level settings"""
            # Set statement timeout
            with dbapi_conn.cursor() as cursor:
                cursor.execute("SET statement_timeout = '30s'")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log connection checkout"""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Log connection checkin"""
            logger.debug("Connection returned to pool")
    
    def get_connection(self):
        """Get a connection from the pool"""
        return self.engine.connect()
    
    def get_pool_status(self) -> dict:
        """Get connection pool status"""
        pool = self.engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }
    
    def dispose(self):
        """Close all connections in the pool"""
        self.engine.dispose()
        logger.info("Database connection pool disposed")


class AsyncDatabaseConnectionPool:
    """AsyncPG connection pool for async operations"""
    
    def __init__(
        self,
        database_url: str,
        min_size: int = 10,
        max_size: int = 20,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0,
    ):
        """
        Initialize async database connection pool.
        
        Args:
            database_url: PostgreSQL connection URL
            min_size: Minimum number of connections
            max_size: Maximum number of connections
            max_queries: Maximum queries per connection before recycling
            max_inactive_connection_lifetime: Max seconds before closing idle connections
        """
        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self._pool: Optional[asyncpg.Pool] = None
        
        # Parse database URL for asyncpg
        self._parse_url(database_url)
        
        logger.info(
            f"Async database connection pool configured: "
            f"min_size={min_size}, max_size={max_size}"
        )
    
    def _parse_url(self, url: str):
        """Parse database URL for asyncpg"""
        # asyncpg uses different URL format
        # postgresql://user:pass@host:port/dbname
        import re
        match = re.match(
            r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)",
            url
        )
        if match:
            self.user, self.password, self.host, self.port, self.database = match.groups()
            self.port = int(self.port)
        else:
            raise ValueError(f"Invalid database URL format: {url}")
    
    async def initialize(self):
        """Initialize the connection pool"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=self.min_size,
                max_size=self.max_size,
                max_queries=self.max_queries,
                max_inactive_connection_lifetime=self.max_inactive_connection_lifetime,
            )
            logger.info("Async database connection pool initialized")
    
    async def acquire(self) -> asyncpg.Connection:
        """Acquire a connection from the pool"""
        if self._pool is None:
            await self.initialize()
        return await self._pool.acquire()
    
    async def release(self, connection: asyncpg.Connection):
        """Release a connection back to the pool"""
        await self._pool.release(connection)
    
    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Context manager for connection"""
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await self.release(conn)
    
    async def get_pool_status(self) -> dict:
        """Get connection pool status"""
        if self._pool is None:
            return {"status": "not_initialized"}
        
        return {
            "size": self._pool.get_size(),
            "idle_size": self._pool.get_idle_size(),
            "min_size": self.min_size,
            "max_size": self.max_size,
        }
    
    async def close(self):
        """Close the connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Async database connection pool closed")


class HTTPConnectionPool:
    """HTTP client connection pool using httpx"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        timeout: float = 30.0,
        limits: Optional[httpx.Limits] = None,
    ):
        """
        Initialize HTTP connection pool.
        
        Args:
            base_url: Base URL for all requests
            max_connections: Maximum number of connections
            max_keepalive_connections: Maximum keepalive connections
            timeout: Request timeout in seconds
            limits: Custom connection limits
        """
        self.base_url = base_url
        self.timeout = timeout
        
        if limits is None:
            limits = httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            )
        
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            limits=limits,
            http2=True,  # Enable HTTP/2 for better performance
        )
        
        logger.info(
            f"HTTP connection pool initialized: "
            f"max_connections={max_connections}, "
            f"max_keepalive={max_keepalive_connections}"
        )
    
    async def get(self, url: str, **kwargs):
        """GET request"""
        return await self.client.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        """POST request"""
        return await self.client.post(url, **kwargs)
    
    async def put(self, url: str, **kwargs):
        """PUT request"""
        return await self.client.put(url, **kwargs)
    
    async def delete(self, url: str, **kwargs):
        """DELETE request"""
        return await self.client.delete(url, **kwargs)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.info("HTTP connection pool closed")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Global connection pools
_db_pool: Optional[DatabaseConnectionPool] = None
_async_db_pool: Optional[AsyncDatabaseConnectionPool] = None
_http_pool: Optional[HTTPConnectionPool] = None


def get_db_pool() -> DatabaseConnectionPool:
    """Get global database connection pool"""
    global _db_pool
    if _db_pool is None:
        import os
        database_url = os.getenv("DATABASE_URL", "postgresql://localhost/automaton")
        _db_pool = DatabaseConnectionPool(database_url)
    return _db_pool


def get_async_db_pool() -> AsyncDatabaseConnectionPool:
    """Get global async database connection pool"""
    global _async_db_pool
    if _async_db_pool is None:
        import os
        database_url = os.getenv("DATABASE_URL", "postgresql://localhost/automaton")
        _async_db_pool = AsyncDatabaseConnectionPool(database_url)
    return _async_db_pool


def get_http_pool() -> HTTPConnectionPool:
    """Get global HTTP connection pool"""
    global _http_pool
    if _http_pool is None:
        _http_pool = HTTPConnectionPool()
    return _http_pool

