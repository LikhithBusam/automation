"""
Advanced Input Validation
JSON Schema, XML validation, parameterized queries, CSP headers
"""

import logging
import json
import re
from typing import Any, Dict, Optional, List
from xml.etree import ElementTree
from xml.etree.ElementTree import XMLParser

import jsonschema
from jsonschema import validate, ValidationError
import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)


class JSONSchemaValidator:
    """JSON Schema validation"""
    
    def __init__(self):
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self._load_default_schemas()
    
    def _load_default_schemas(self):
        """Load default JSON schemas"""
        # Workflow execution schema
        self.schemas["workflow_execute"] = {
            "type": "object",
            "required": ["workflow_name"],
            "properties": {
                "workflow_name": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9_-]+$",
                    "minLength": 1,
                    "maxLength": 100,
                },
                "parameters": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        }
        
        # Memory storage schema
        self.schemas["memory_store"] = {
            "type": "object",
            "required": ["content", "type"],
            "properties": {
                "content": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 10000,
                },
                "type": {
                    "type": "string",
                    "enum": ["context", "error", "pattern", "solution"],
                },
                "tier": {
                    "type": "string",
                    "enum": ["short", "medium", "long"],
                },
            },
        }
    
    def register_schema(self, name: str, schema: Dict[str, Any]):
        """Register a JSON schema"""
        # Validate schema itself
        jsonschema.Draft7Validator.check_schema(schema)
        self.schemas[name] = schema
    
    def validate(self, data: Any, schema_name: str) -> tuple[bool, Optional[str]]:
        """
        Validate data against schema.
        
        Returns:
            (is_valid, error_message)
        """
        if schema_name not in self.schemas:
            return False, f"Schema '{schema_name}' not found"
        
        try:
            validate(instance=data, schema=self.schemas[schema_name])
            return True, None
        except ValidationError as e:
            return False, str(e.message)
    
    def validate_with_schema(self, data: Any, schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate data against provided schema"""
        try:
            validate(instance=data, schema=schema)
            return True, None
        except ValidationError as e:
            return False, str(e.message)


class XMLValidator:
    """XML validation and sanitization"""
    
    def __init__(self):
        self.allowed_tags: set = set()
        self.allowed_attributes: Dict[str, set] = {}
        self.max_depth: int = 10
        self.max_size: int = 10 * 1024 * 1024  # 10MB
    
    def validate(self, xml_string: str) -> tuple[bool, Optional[str], Optional[ElementTree.Element]]:
        """
        Validate XML string.
        
        Returns:
            (is_valid, error_message, parsed_element)
        """
        # Check size
        if len(xml_string) > self.max_size:
            return False, f"XML size exceeds maximum ({self.max_size} bytes)", None
        
        try:
            # Use defusedxml for safe parsing
            parser = ET.XMLParser(forbid_dtd=True, forbid_entities=True)
            root = ET.fromstring(xml_string, parser=parser)
            
            # Check depth
            if self._get_depth(root) > self.max_depth:
                return False, f"XML depth exceeds maximum ({self.max_depth})", None
            
            # Validate tags and attributes
            if self.allowed_tags:
                if not self._validate_tags(root):
                    return False, "XML contains disallowed tags", None
            
            if self.allowed_attributes:
                if not self._validate_attributes(root):
                    return False, "XML contains disallowed attributes", None
            
            return True, None, root
        except ET.ParseError as e:
            return False, f"XML parsing error: {str(e)}", None
        except Exception as e:
            return False, f"XML validation error: {str(e)}", None
    
    def sanitize(self, xml_string: str) -> str:
        """Sanitize XML by removing dangerous elements"""
        try:
            parser = ET.XMLParser(forbid_dtd=True, forbid_entities=True)
            root = ET.fromstring(xml_string, parser=parser)
            
            # Remove script tags and dangerous attributes
            self._remove_dangerous_elements(root)
            
            # Convert back to string
            return ET.tostring(root, encoding="unicode")
        except Exception as e:
            logger.error(f"XML sanitization error: {e}")
            return ""
    
    def _get_depth(self, element: ElementTree.Element, current_depth: int = 0) -> int:
        """Get maximum depth of XML tree"""
        if not element:
            return current_depth
        
        max_depth = current_depth
        for child in element:
            child_depth = self._get_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _validate_tags(self, element: ElementTree.Element) -> bool:
        """Validate XML tags"""
        if self.allowed_tags and element.tag not in self.allowed_tags:
            return False
        
        for child in element:
            if not self._validate_tags(child):
                return False
        
        return True
    
    def _validate_attributes(self, element: ElementTree.Element) -> bool:
        """Validate XML attributes"""
        for attr_name in element.attrib:
            if attr_name in ["onclick", "onerror", "onload"]:  # Dangerous attributes
                return False
            
            if self.allowed_attributes:
                allowed = self.allowed_attributes.get(element.tag, set())
                if allowed and attr_name not in allowed:
                    return False
        
        for child in element:
            if not self._validate_attributes(child):
                return False
        
        return True
    
    def _remove_dangerous_elements(self, element: ElementTree.Element):
        """Remove dangerous XML elements"""
        dangerous_tags = ["script", "iframe", "object", "embed"]
        dangerous_attrs = ["onclick", "onerror", "onload", "javascript:"]
        
        # Remove dangerous attributes
        for attr in list(element.attrib.keys()):
            if any(danger in attr.lower() for danger in dangerous_attrs):
                del element.attrib[attr]
        
        # Remove dangerous elements
        for child in list(element):
            if child.tag.lower() in dangerous_tags:
                element.remove(child)
            else:
                self._remove_dangerous_elements(child)


class ParameterizedQueryBuilder:
    """Parameterized query builder for safe database operations"""
    
    @staticmethod
    def build_select(table: str, columns: List[str], where_clauses: Dict[str, Any]) -> tuple[str, List[Any]]:
        """Build parameterized SELECT query"""
        column_list = ", ".join(columns)
        query = f"SELECT {column_list} FROM {table}"
        
        params = []
        if where_clauses:
            conditions = []
            for column, value in where_clauses.items():
                conditions.append(f"{column} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        return query, params
    
    @staticmethod
    def build_insert(table: str, data: Dict[str, Any]) -> tuple[str, List[Any]]:
        """Build parameterized INSERT query"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        params = list(data.values())
        
        return query, params
    
    @staticmethod
    def build_update(table: str, data: Dict[str, Any], where_clauses: Dict[str, Any]) -> tuple[str, List[Any]]:
        """Build parameterized UPDATE query"""
        set_clauses = [f"{col} = %s" for col in data.keys()]
        query = f"UPDATE {table} SET {', '.join(set_clauses)}"
        
        params = list(data.values())
        
        if where_clauses:
            conditions = []
            for column, value in where_clauses.items():
                conditions.append(f"{column} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        return query, params
    
    @staticmethod
    def build_delete(table: str, where_clauses: Dict[str, Any]) -> tuple[str, List[Any]]:
        """Build parameterized DELETE query"""
        query = f"DELETE FROM {table}"
        params = []
        
        if where_clauses:
            conditions = []
            for column, value in where_clauses.items():
                conditions.append(f"{column} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        else:
            raise ValueError("DELETE queries must have WHERE clauses")
        
        return query, params


class CSPHeaderBuilder:
    """Content Security Policy header builder"""
    
    def __init__(self):
        self.default_policy = {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "data:"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
        }
    
    def build_header(self, custom_policy: Optional[Dict[str, List[str]]] = None) -> str:
        """Build CSP header string"""
        policy = {**self.default_policy}
        if custom_policy:
            policy.update(custom_policy)
        
        directives = []
        for directive, sources in policy.items():
            sources_str = " ".join(sources)
            directives.append(f"{directive} {sources_str}")
        
        return "; ".join(directives)
    
    def build_strict_policy(self) -> str:
        """Build strict CSP policy"""
        strict_policy = {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'"],
            "img-src": ["'self'", "data:"],
            "font-src": ["'self'"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "object-src": ["'none'"],
            "media-src": ["'none'"],
            "frame-src": ["'none'"],
        }
        return self.build_header(strict_policy)

