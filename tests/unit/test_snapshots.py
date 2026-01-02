"""
Snapshot Testing for Configuration Parsing
"""

import pytest
import json
from pathlib import Path

# Note: Import actual config loader when available
# from src.config.config_loader import ConfigLoader


class TestConfigurationSnapshots:
    """Snapshot tests for configuration parsing"""
    
    @pytest.fixture
    def config_loader(self):
        """Create config loader"""
        # Mock config loader
        class MockConfigLoader:
            def load_config(self, path):
                with open(path) as f:
                    return json.load(f)
        
        return MockConfigLoader()
    
    def test_parse_app_config_snapshot(self, config_loader, tmp_path):
        """Test app config parsing matches snapshot"""
        config_content = {
            "app": {
                "name": "Automaton",
                "version": "1.0.0",
                "debug": False
            },
            "database": {
                "url": "postgresql://localhost/automaton",
                "pool_size": 10
            }
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_content))
        
        config = config_loader.load_config(str(config_file))
        
        # Snapshot test - compare with expected structure
        expected_structure = {
            "app": {
                "name": str,
                "version": str,
                "debug": bool
            },
            "database": {
                "url": str,
                "pool_size": int
            }
        }
        
        assert self._validate_structure(config, expected_structure)
    
    def test_parse_workflow_config_snapshot(self, config_loader, tmp_path):
        """Test workflow config parsing matches snapshot"""
        workflow_config = {
            "workflows": [
                {
                    "name": "test_workflow",
                    "steps": [
                        {
                            "id": "step1",
                            "type": "agent",
                            "agent": "test_agent"
                        }
                    ]
                }
            ]
        }
        
        config_file = tmp_path / "workflow_config.json"
        config_file.write_text(json.dumps(workflow_config))
        
        class MockConfigLoader:
            def load_config(self, path):
                with open(path) as f:
                    return json.load(f)
        
        config_loader = MockConfigLoader()
        config = config_loader.load_config(str(config_file))
        
        # Verify structure
        assert "workflows" in config
        assert len(config["workflows"]) == 1
        assert config["workflows"][0]["name"] == "test_workflow"
    
    def test_parse_security_config_snapshot(self, config_loader, tmp_path):
        """Test security config parsing matches snapshot"""
        security_config = {
            "security": {
                "jwt_secret": "test_secret",
                "token_expiry": 3600,
                "rate_limiting": {
                    "enabled": True,
                    "max_requests": 100
                }
            }
        }
        
        config_file = tmp_path / "security_config.json"
        config_file.write_text(json.dumps(security_config))
        
        class MockConfigLoader:
            def load_config(self, path):
                with open(path) as f:
                    return json.load(f)
        
        config_loader = MockConfigLoader()
        config = config_loader.load_config(str(config_file))
        
        # Verify structure
        assert "security" in config
        assert config["security"]["rate_limiting"]["enabled"] is True
    
    def _validate_structure(self, data: dict, structure: dict) -> bool:
        """Validate data structure matches expected structure"""
        for key, expected_type in structure.items():
            if key not in data:
                return False
            
            if isinstance(expected_type, dict):
                if not isinstance(data[key], dict):
                    return False
                if not self._validate_structure(data[key], expected_type):
                    return False
            elif not isinstance(data[key], expected_type):
                return False
        
        return True


class TestYAMLConfigSnapshots:
    """Snapshot tests for YAML configuration"""
    
    def test_parse_yaml_config_snapshot(self, tmp_path):
        """Test YAML config parsing matches snapshot"""
        import yaml
        
        yaml_config = """
app:
  name: Automaton
  version: 1.0.0
database:
  url: postgresql://localhost/automaton
  pool_size: 10
"""
        
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_config)
        
        with open(config_file) as f:
            config = yaml.safe_load(f)
        
        # Verify structure
        assert config["app"]["name"] == "Automaton"
        assert config["database"]["pool_size"] == 10

