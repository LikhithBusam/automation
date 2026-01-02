"""
Lazy Loading and Pagination for Large Datasets
"""

import logging
from typing import Any, Dict, List, Optional, Generic, TypeVar, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class Page(Generic[T]):
    """Paginated result"""
    items: List[T]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


@dataclass
class CursorPage(Generic[T]):
    """Cursor-based paginated result"""
    items: List[T]
    next_cursor: Optional[str]
    previous_cursor: Optional[str]
    has_next: bool
    has_previous: bool


class Paginator:
    """
    Offset-based pagination for large datasets.
    """
    
    def __init__(self, page_size: int = 50, max_page_size: int = 1000):
        """
        Initialize paginator.
        
        Args:
            page_size: Default page size
            max_page_size: Maximum allowed page size
        """
        self.page_size = page_size
        self.max_page_size = max_page_size
        self.logger = logging.getLogger("pagination")
    
    def paginate(
        self,
        query_func: Callable,
        page: int = 1,
        page_size: Optional[int] = None
    ) -> Page:
        """
        Paginate query results.
        
        Args:
            query_func: Function that returns queryable object
            page: Page number (1-indexed)
            page_size: Optional page size override
        
        Returns:
            Paginated result
        """
        page_size = min(page_size or self.page_size, self.max_page_size)
        offset = (page - 1) * page_size
        
        # Execute query with limit and offset
        query = query_func()
        total = query.count()
        items = query.offset(offset).limit(page_size).all()
        
        total_pages = (total + page_size - 1) // page_size
        
        return Page(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    
    async def paginate_async(
        self,
        query_func: Callable,
        page: int = 1,
        page_size: Optional[int] = None
    ) -> Page:
        """Async pagination"""
        import asyncio
        
        page_size = min(page_size or self.page_size, self.max_page_size)
        offset = (page - 1) * page_size
        
        query = query_func()
        total = await query.count()
        items = await query.offset(offset).limit(page_size).all()
        
        total_pages = (total + page_size - 1) // page_size
        
        return Page(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )


class CursorPaginator:
    """
    Cursor-based pagination for efficient large dataset navigation.
    Avoids offset-based pagination issues with large datasets.
    """
    
    def __init__(self, page_size: int = 50):
        """
        Initialize cursor paginator.
        
        Args:
            page_size: Page size
        """
        self.page_size = page_size
        self.logger = logging.getLogger("pagination.cursor")
    
    def paginate(
        self,
        query_func: Callable,
        cursor: Optional[str] = None,
        direction: str = "next"  # "next" or "previous"
    ) -> CursorPage:
        """
        Paginate with cursor.
        
        Args:
            query_func: Function that returns queryable object
            cursor: Optional cursor for pagination
            direction: Pagination direction
        
        Returns:
            Cursor-based paginated result
        """
        query = query_func()
        
        # Apply cursor filter
        if cursor:
            # Decode cursor (typically contains last item's ID or timestamp)
            cursor_value = self._decode_cursor(cursor)
            if direction == "next":
                query = query.filter(query.id > cursor_value)
            else:
                query = query.filter(query.id < cursor_value)
                query = query.order_by(query.id.desc())
        
        # Get items
        items = query.limit(self.page_size + 1).all()
        
        # Check if there are more items
        has_next = len(items) > self.page_size
        if has_next:
            items = items[:-1]  # Remove extra item
        
        # Generate cursors
        next_cursor = None
        previous_cursor = None
        
        if items:
            if has_next:
                next_cursor = self._encode_cursor(items[-1].id)
            if cursor:
                previous_cursor = self._encode_cursor(items[0].id)
        
        return CursorPage(
            items=items,
            next_cursor=next_cursor,
            previous_cursor=previous_cursor,
            has_next=has_next,
            has_previous=cursor is not None
        )
    
    def _encode_cursor(self, value: Any) -> str:
        """Encode cursor value"""
        import base64
        import json
        return base64.b64encode(json.dumps(str(value)).encode()).decode()
    
    def _decode_cursor(self, cursor: str) -> Any:
        """Decode cursor value"""
        import base64
        import json
        return json.loads(base64.b64decode(cursor.encode()).decode())


# Global paginator instance
_paginator: Optional[Paginator] = None


def get_paginator() -> Paginator:
    """Get global paginator"""
    global _paginator
    if _paginator is None:
        _paginator = Paginator()
    return _paginator

