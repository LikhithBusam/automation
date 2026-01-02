"""
Contract Testing for Service Boundaries
Tests contracts between services to ensure compatibility
"""

import pytest
import json
from typing import Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class ServiceContract:
    """Service contract definition"""
    service_name: str
    version: str
    endpoints: List[Dict[str, Any]]
    schemas: Dict[str, Any]


class TestServiceContracts:
    """Test service contracts"""
    
    @pytest.fixture
    def workflow_service_contract(self):
        """Define workflow service contract"""
        return ServiceContract(
            service_name="workflow_service",
            version="1.0.0",
            endpoints=[
                {
                    "path": "/workflows",
                    "method": "POST",
                    "request_schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string", "enum": ["group_chat", "two_agent", "nested_chat"]},
                            "agents": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name", "type"]
                    },
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "workflow_id": {"type": "string"},
                            "status": {"type": "string"}
                        },
                        "required": ["workflow_id", "status"]
                    }
                }
            ],
            schemas={}
        )
    
    @pytest.fixture
    def agent_service_contract(self):
        """Define agent service contract"""
        return ServiceContract(
            service_name="agent_service",
            version="1.0.0",
            endpoints=[
                {
                    "path": "/agents",
                    "method": "POST",
                    "request_schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "tools": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name", "type"]
                    },
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string"},
                            "status": {"type": "string"}
                        },
                        "required": ["agent_id", "status"]
                    }
                }
            ],
            schemas={}
        )
    
    def test_contract_validation(self, workflow_service_contract):
        """Test contract validation"""
        contract = workflow_service_contract
        
        # Validate contract structure
        assert contract.service_name == "workflow_service"
        assert contract.version == "1.0.0"
        assert len(contract.endpoints) > 0
        
        # Validate endpoint structure
        endpoint = contract.endpoints[0]
        assert "path" in endpoint
        assert "method" in endpoint
        assert "request_schema" in endpoint
        assert "response_schema" in endpoint
    
    def test_request_schema_validation(self, workflow_service_contract):
        """Test request schema validation"""
        contract = workflow_service_contract
        endpoint = contract.endpoints[0]
        schema = endpoint["request_schema"]
        
        # Valid request
        valid_request = {
            "name": "test_workflow",
            "type": "group_chat",
            "agents": ["agent1", "agent2"]
        }
        
        # Validate required fields
        required_fields = schema.get("required", [])
        assert all(field in valid_request for field in required_fields)
        
        # Validate field types
        properties = schema.get("properties", {})
        for field, value in valid_request.items():
            if field in properties:
                field_type = properties[field].get("type")
                if field_type == "string":
                    assert isinstance(value, str)
                elif field_type == "array":
                    assert isinstance(value, list)
    
    def test_response_schema_validation(self, workflow_service_contract):
        """Test response schema validation"""
        contract = workflow_service_contract
        endpoint = contract.endpoints[0]
        schema = endpoint["response_schema"]
        
        # Valid response
        valid_response = {
            "workflow_id": "123",
            "status": "created"
        }
        
        # Validate required fields
        required_fields = schema.get("required", [])
        assert all(field in valid_response for field in required_fields)
    
    def test_contract_compatibility(self, workflow_service_contract, agent_service_contract):
        """Test contract compatibility between services"""
        # Services should be able to communicate
        workflow_contract = workflow_service_contract
        agent_contract = agent_service_contract
        
        # Both should have valid contracts
        assert workflow_contract.version is not None
        assert agent_contract.version is not None
        
        # Contracts should be compatible (same version format)
        assert workflow_contract.version.split(".")[0] == agent_contract.version.split(".")[0]
    
    def test_contract_versioning(self):
        """Test contract versioning"""
        # Create contracts with different versions
        v1_contract = ServiceContract(
            service_name="test_service",
            version="1.0.0",
            endpoints=[],
            schemas={}
        )
        
        v2_contract = ServiceContract(
            service_name="test_service",
            version="2.0.0",
            endpoints=[],
            schemas={}
        )
        
        # Versions should be different
        assert v1_contract.version != v2_contract.version
        
        # Major version should be different
        v1_major = v1_contract.version.split(".")[0]
        v2_major = v2_contract.version.split(".")[0]
        assert v1_major != v2_major
    
    def test_backward_compatibility(self, workflow_service_contract):
        """Test backward compatibility"""
        contract = workflow_service_contract
        
        # Old client should be able to use new service if compatible
        old_request = {
            "name": "test_workflow",
            "type": "group_chat"
        }
        
        # Should still work with new contract
        endpoint = contract.endpoints[0]
        schema = endpoint["request_schema"]
        required_fields = schema.get("required", [])
        
        # Old request should have all required fields
        assert all(field in old_request for field in required_fields)
    
    def test_contract_breaking_changes(self):
        """Test detection of breaking changes"""
        v1_contract = ServiceContract(
            service_name="test_service",
            version="1.0.0",
            endpoints=[{
                "path": "/test",
                "method": "POST",
                "request_schema": {
                    "required": ["field1", "field2"]
                },
                "response_schema": {}
            }],
            schemas={}
        )
        
        v2_contract = ServiceContract(
            service_name="test_service",
            version="2.0.0",
            endpoints=[{
                "path": "/test",
                "method": "POST",
                "request_schema": {
                    "required": ["field1", "field2", "field3"]  # New required field
                },
                "response_schema": {}
            }],
            schemas={}
        )
        
        # Detect breaking change
        v1_required = set(v1_contract.endpoints[0]["request_schema"]["required"])
        v2_required = set(v2_contract.endpoints[0]["request_schema"]["required"])
        
        breaking_changes = v2_required - v1_required
        assert len(breaking_changes) > 0  # Breaking change detected


class TestAPIContracts:
    """Test API contracts"""
    
    def test_api_request_contract(self):
        """Test API request contract"""
        # Define expected request structure
        expected_request = {
            "name": str,
            "type": str,
            "agents": list
        }
        
        # Valid request
        actual_request = {
            "name": "test",
            "type": "group_chat",
            "agents": ["agent1"]
        }
        
        # Validate structure
        assert all(key in actual_request for key in expected_request.keys())
        assert all(isinstance(actual_request[key], expected_request[key]) 
                  for key in expected_request.keys())
    
    def test_api_response_contract(self):
        """Test API response contract"""
        # Define expected response structure
        expected_response = {
            "workflow_id": str,
            "status": str,
            "created_at": str
        }
        
        # Valid response
        actual_response = {
            "workflow_id": "123",
            "status": "created",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        # Validate structure
        assert all(key in actual_response for key in expected_response.keys())
        assert all(isinstance(actual_response[key], expected_response[key]) 
                  for key in expected_response.keys())
    
    def test_error_response_contract(self):
        """Test error response contract"""
        # Define expected error structure
        expected_error = {
            "error": str,
            "message": str,
            "code": int
        }
        
        # Valid error response
        actual_error = {
            "error": "ValidationError",
            "message": "Invalid request",
            "code": 400
        }
        
        # Validate structure
        assert all(key in actual_error for key in expected_error.keys())
        assert isinstance(actual_error["code"], int)

