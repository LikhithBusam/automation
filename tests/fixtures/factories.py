"""
Test Factories for Common Scenarios
"""

import uuid
from typing import Any, Dict, Optional
from datetime import datetime

# Note: Import actual classes when available
# from src.agents.base_agent import BaseAgent
# from src.workflow_management.versioning import WorkflowVersion
# from src.user_management.registration import UserAccount
from src.billing.usage_tracking import UsageRecord, UsageType


class AgentFactory:
    """Factory for creating test agents"""
    
    @staticmethod
    def create_agent(
        name: str = None,
        agent_type: str = "base",
        llm_client=None,
        tools=None
    ):
        """Create test agent"""
        if name is None:
            name = f"test_agent_{uuid.uuid4().hex[:8]}"
        
        # Mock agent class
        class MockAgent:
            def __init__(self, name, llm_client, tools=None):
                self.name = name
                self.llm_client = llm_client
                self.tools = tools or []
        
        return MockAgent(
            name=name,
            llm_client=llm_client,
            tools=tools or []
        )


class WorkflowFactory:
    """Factory for creating test workflows"""
    
    @staticmethod
    def create_workflow_definition(
        name: str = None,
        steps: Optional[list] = None
    ) -> Dict[str, Any]:
        """Create test workflow definition"""
        if name is None:
            name = f"test_workflow_{uuid.uuid4().hex[:8]}"
        
        if steps is None:
            steps = [
                {
                    "id": "step1",
                    "type": "agent",
                    "agent": "test_agent",
                    "task": "test_task"
                }
            ]
        
        return {
            "name": name,
            "description": f"Test workflow: {name}",
            "steps": steps,
            "metadata": {}
        }
    
    @staticmethod
    def create_workflow_version(
        workflow_id: str = None,
        version_number: str = "1.0.0",
        definition: Optional[Dict[str, Any]] = None
    ):
        """Create test workflow version"""
        from src.workflow_management.versioning import WorkflowVersion
        
        if workflow_id is None:
            workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        if definition is None:
            definition = WorkflowFactory.create_workflow_definition()
        
        return WorkflowVersion(
            version_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            version_number=version_number,
            definition=definition,
            created_by="test_user"
        )


class UserFactory:
    """Factory for creating test users"""
    
    @staticmethod
    def create_user(
        email: str = None,
        user_id: str = None
    ):
        """Create test user"""
        from src.user_management.registration import UserAccount
        
        if user_id is None:
            user_id = str(uuid.uuid4())
        
        if email is None:
            email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        
        return UserAccount(
            user_id=user_id,
            email=email,
            password_hash="hashed_password",
            first_name="Test",
            last_name="User"
        )


class UsageRecordFactory:
    """Factory for creating test usage records"""
    
    @staticmethod
    def create_usage_record(
        usage_type: UsageType = UsageType.API_CALLS,
        quantity: float = 1.0,
        user_id: str = None,
        tenant_id: str = None
    ) -> UsageRecord:
        """Create test usage record"""
        return UsageRecord(
            record_id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            usage_type=usage_type,
            quantity=quantity
        )


class MockLLMFactory:
    """Factory for creating mock LLM clients"""
    
    @staticmethod
    def create_mock_llm(
        response: str = "Mock response",
        tokens_used: int = 100
    ):
        """Create mock LLM client"""
        from unittest.mock import AsyncMock
        
        mock = AsyncMock()
        mock.generate.return_value = {
            "content": response,
            "tokens_used": tokens_used,
            "model": "gpt-4"
        }
        mock.chat.return_value = {
            "content": response,
            "tokens_used": tokens_used
        }
        return mock


class MockToolFactory:
    """Factory for creating mock tools"""
    
    @staticmethod
    def create_mock_tool(
        result: Any = {"success": True},
        error: Optional[Exception] = None
    ):
        """Create mock tool"""
        from unittest.mock import AsyncMock
        
        mock = AsyncMock()
        if error:
            mock.execute.side_effect = error
        else:
            mock.execute.return_value = result
        return mock

