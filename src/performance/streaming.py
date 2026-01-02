"""
Streaming Responses for Long-Running Operations
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, Optional
from datetime import datetime
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


class StreamingResponse:
    """
    Streaming response handler for long-running operations.
    Supports Server-Sent Events (SSE) and chunked responses.
    """
    
    def __init__(self):
        """Initialize streaming response handler"""
        self.logger = logging.getLogger("streaming")
    
    async def stream_sse(
        self,
        generator: AsyncIterator[Dict[str, Any]],
        event_type: str = "message"
    ) -> StreamingResponse:
        """
        Create Server-Sent Events stream.
        
        Args:
            generator: Async generator yielding data
            event_type: SSE event type
        
        Returns:
            StreamingResponse
        """
        async def event_generator():
            try:
                async for data in generator:
                    # Format as SSE
                    event_data = json.dumps(data)
                    yield f"event: {event_type}\n"
                    yield f"data: {event_data}\n\n"
            except Exception as e:
                self.logger.error(f"Streaming error: {e}")
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                yield "event: close\n"
                yield "data: {}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    
    async def stream_json(
        self,
        generator: AsyncIterator[Dict[str, Any]]
    ) -> StreamingResponse:
        """
        Create JSON streaming response.
        
        Args:
            generator: Async generator yielding JSON-serializable data
        
        Returns:
            StreamingResponse
        """
        async def json_generator():
            yield "["
            first = True
            try:
                async for item in generator:
                    if not first:
                        yield ","
                    yield json.dumps(item)
                    first = False
            except Exception as e:
                self.logger.error(f"Streaming error: {e}")
                if not first:
                    yield ","
                yield json.dumps({"error": str(e)})
            finally:
                yield "]"
        
        return StreamingResponse(
            json_generator(),
            media_type="application/json",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    
    async def stream_text(
        self,
        generator: AsyncIterator[str]
    ) -> StreamingResponse:
        """
        Create text streaming response.
        
        Args:
            generator: Async generator yielding text chunks
        
        Returns:
            StreamingResponse
        """
        return StreamingResponse(
            generator,
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    
    async def stream_workflow_progress(
        self,
        workflow_id: str,
        progress_func: Callable
    ) -> StreamingResponse:
        """
        Stream workflow execution progress.
        
        Args:
            workflow_id: Workflow ID
            progress_func: Function to get progress
        
        Returns:
            StreamingResponse
        """
        async def progress_generator():
            last_progress = 0
            while True:
                progress = await progress_func(workflow_id)
                
                if progress is None:
                    break
                
                yield json.dumps({
                    "workflow_id": workflow_id,
                    "progress": progress,
                    "timestamp": datetime.utcnow().isoformat()
                }) + "\n"
                
                if progress >= 100:
                    break
                
                # Avoid sending duplicate progress
                if progress == last_progress:
                    await asyncio.sleep(1)
                    continue
                
                last_progress = progress
                await asyncio.sleep(0.5)
        
        return self.stream_text(progress_generator())
    
    async def stream_agent_response(
        self,
        agent_name: str,
        response_func: Callable
    ) -> StreamingResponse:
        """
        Stream agent response tokens.
        
        Args:
            agent_name: Agent name
            response_func: Function to get response chunks
        
        Returns:
            StreamingResponse
        """
        async def token_generator():
            async for chunk in response_func(agent_name):
                yield chunk
        
        return self.stream_text(token_generator())


# Global streaming response instance
_streaming_response: Optional[StreamingResponse] = None


def get_streaming_response() -> StreamingResponse:
    """Get global streaming response handler"""
    global _streaming_response
    if _streaming_response is None:
        _streaming_response = StreamingResponse()
    return _streaming_response

