"""
Slack MCP Tool Wrapper
Wraps Slack MCP server functions for CrewAI agents
"""

from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime
from src.mcp.base_tool import BaseMCPTool


class SlackMCPTool(BaseMCPTool):
    """
    Slack MCP Tool Wrapper
    
    Provides team communication capabilities:
    - Send messages and notifications
    - Create threads
    - Format messages
    - Upload files
    """

    def __init__(self, server_url: str, config: Dict[str, Any]):
        super().__init__(
            name="slack",
            server_url=server_url,
            config=config
        )
        
        self.bot_token = config.get("bot_token", "")
        self.default_channel = config.get("default_channel", "general")

    def validate_params(self, operation: str, params: Dict[str, Any]):
        """Basic parameter validation to satisfy BaseMCPTool contract."""
        if not isinstance(params, dict):
            raise ValueError("Params must be a dict")

        if operation in {"send_message", "send_notification", "create_thread", "upload_file"}:
            # Require some text content for messages
            if operation == "send_message" and not params.get("text") and not params.get("blocks"):
                raise ValueError("send_message requires 'text' or 'blocks'")
            if operation == "send_notification" and not params.get("message") and not params.get("title"):
                raise ValueError("send_notification requires 'message' or 'title'")
            if operation == "create_thread" and not params.get("parent_text"):
                raise ValueError("create_thread requires 'parent_text'")
            if operation == "upload_file" and not params.get("file_content"):
                raise ValueError("upload_file requires 'file_content'")

        # For other ops (format_code_block, health_check), no required params

    async def _execute_operation(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute Slack operation"""
        
        handlers = {
            "send_message": self._send_message,
            "send_notification": self._send_notification,
            "create_thread": self._create_thread,
            "upload_file": self._upload_file,
            "format_code_block": self._format_code_block,
            "health_check": self._health_check,
        }
        
        handler = handlers.get(operation)
        if not handler:
            raise ValueError(f"Unknown operation: {operation}")
        
        return await handler(params)

    async def _send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to Slack"""
        message_data = {
            "channel": params.get("channel", self.default_channel),
            "text": params.get("text"),
            "blocks": params.get("blocks"),
            "thread_ts": params.get("thread_ts")
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/send_message",
                json=message_data,
                headers={"Authorization": f"Bearer {self.bot_token}"}
            )
            response.raise_for_status()
            return response.json()

    async def _send_notification(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a formatted notification"""
        notification_type = params.get("type", "info")
        
        # Format based on notification type
        formatted = self._format_notification(
            notification_type,
            params.get("title"),
            params.get("message"),
            params.get("details", {})
        )
        
        return await self._send_message({
            "channel": params.get("channel"),
            "blocks": formatted
        })

    async def _create_thread(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a threaded conversation"""
        # Send parent message
        parent = await self._send_message({
            "channel": params.get("channel"),
            "text": params.get("parent_text")
        })
        
        # Send replies
        thread_ts = parent.get("ts")
        replies = []
        for reply_text in params.get("replies", []):
            reply = await self._send_message({
                "channel": params.get("channel"),
                "text": reply_text,
                "thread_ts": thread_ts
            })
            replies.append(reply)
        
        return {
            "thread_ts": thread_ts,
            "parent": parent,
            "replies": replies
        }

    async def _upload_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a file to Slack"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/upload_file",
                json=params,
                headers={"Authorization": f"Bearer {self.bot_token}"}
            )
            response.raise_for_status()
            return response.json()

    def _format_code_block(self, params: Dict[str, Any]) -> str:
        """Format code for Slack"""
        code = params.get("code")
        language = params.get("language", "")
        
        return f"```{language}\n{code}\n```"

    async def _health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Health check"""
        return {"status": "ok"}

    def _format_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format notification blocks"""
        
        # Color based on type
        colors = {
            "success": "#36a64f",
            "error": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8"
        }
        
        # Emoji based on type
        emojis = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emojis.get(notification_type, '')} {title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
        # Add details if provided
        if details:
            detail_text = "\n".join([f"*{k}:* {v}" for k, v in details.items()])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": detail_text
                }
            })
        
        return blocks


# Notification templates for different scenarios
SLACK_NOTIFICATION_TEMPLATES = {
    "deployment_started": {
        "type": "info",
        "title": "Deployment Started",
        "template": "Deploying version {version} to {environment}",
        "details": ["version", "environment", "strategy", "started_by"]
    },
    
    "deployment_completed": {
        "type": "success",
        "title": "Deployment Successful",
        "template": "Successfully deployed version {version} to {environment}",
        "details": ["version", "environment", "duration", "health_status"]
    },
    
    "deployment_failed": {
        "type": "error",
        "title": "Deployment Failed",
        "template": "Deployment to {environment} failed",
        "details": ["version", "environment", "error", "rollback_status"]
    },
    
    "pr_review_ready": {
        "type": "info",
        "title": "PR Review Complete",
        "template": "Code review completed for PR #{pr_number}",
        "details": ["pr_number", "issues_found", "recommendations"]
    },
    
    "security_alert": {
        "type": "warning",
        "title": "Security Vulnerability Detected",
        "template": "Security issue found in {file}",
        "details": ["file", "severity", "vulnerability_type", "recommendation"]
    },
    
    "build_failed": {
        "type": "error",
        "title": "Build Failed",
        "template": "Build failed for {branch}",
        "details": ["branch", "commit", "error", "logs_url"]
    }
}


# Tool documentation for CrewAI agents
SLACK_TOOL_DESCRIPTIONS = {
    "send_message": """
    Send a message to a Slack channel.
    
    Parameters:
    - channel (str): Channel name or ID
    - text (str): Message text (Slack mrkdwn format)
    - thread_ts (str, optional): Reply in thread
    
    Returns:
    - ts (str): Message timestamp
    - channel (str): Channel ID
    """,
    
    "send_notification": """
    Send a formatted notification.
    
    Parameters:
    - type (str): Notification type (success/error/warning/info)
    - title (str): Notification title
    - message (str): Notification message
    - details (dict, optional): Additional details
    - channel (str, optional): Target channel
    
    Returns:
    - ts (str): Message timestamp
    - formatted (bool): True if formatting applied
    """
}
