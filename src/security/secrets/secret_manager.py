"""
Secret Management System
HashiCorp Vault, AWS Secrets Manager, Azure Key Vault integration
"""

import logging
import os
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SecretManagerType(str, Enum):
    """Secret manager types"""
    VAULT = "vault"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AZURE_KEY_VAULT = "azure_key_vault"
    LOCAL = "local"  # For development


class SecretManager:
    """Unified secret manager interface"""
    
    def __init__(self, manager_type: SecretManagerType, config: Dict[str, Any]):
        """
        Initialize secret manager.
        
        Args:
            manager_type: Type of secret manager
            config: Configuration for secret manager
        """
        self.manager_type = manager_type
        self.config = config
        
        if manager_type == SecretManagerType.VAULT:
            self._init_vault()
        elif manager_type == SecretManagerType.AWS_SECRETS_MANAGER:
            self._init_aws_secrets_manager()
        elif manager_type == SecretManagerType.AZURE_KEY_VAULT:
            self._init_azure_key_vault()
        elif manager_type == SecretManagerType.LOCAL:
            self._init_local()
        else:
            raise ValueError(f"Unknown secret manager type: {manager_type}")
    
    def _init_vault(self):
        """Initialize HashiCorp Vault"""
        try:
            import hvac
            
            vault_url = self.config.get("vault_url", os.getenv("VAULT_ADDR"))
            vault_token = self.config.get("vault_token", os.getenv("VAULT_TOKEN"))
            
            self.client = hvac.Client(url=vault_url, token=vault_token)
            self.mount_point = self.config.get("mount_point", "secret")
        except ImportError:
            logger.warning("hvac not installed, Vault unavailable")
            self.client = None
    
    def _init_aws_secrets_manager(self):
        """Initialize AWS Secrets Manager"""
        try:
            import boto3
            
            self.client = boto3.client(
                "secretsmanager",
                region_name=self.config.get("region", "us-east-1"),
                aws_access_key_id=self.config.get("aws_access_key_id"),
                aws_secret_access_key=self.config.get("aws_secret_access_key"),
            )
        except ImportError:
            logger.warning("boto3 not installed, AWS Secrets Manager unavailable")
            self.client = None
    
    def _init_azure_key_vault(self):
        """Initialize Azure Key Vault"""
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential
            
            vault_url = self.config["vault_url"]
            credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=vault_url, credential=credential)
        except ImportError:
            logger.warning("azure-keyvault-secrets not installed, Azure Key Vault unavailable")
            self.client = None
    
    def _init_local(self):
        """Initialize local secret storage (development only)"""
        self.secrets: Dict[str, str] = {}
        self.client = None
    
    def get_secret(self, secret_name: str, key: Optional[str] = None) -> Optional[str]:
        """Get secret value"""
        if self.manager_type == SecretManagerType.VAULT:
            return self._get_vault_secret(secret_name, key)
        elif self.manager_type == SecretManagerType.AWS_SECRETS_MANAGER:
            return self._get_aws_secret(secret_name, key)
        elif self.manager_type == SecretManagerType.AZURE_KEY_VAULT:
            return self._get_azure_secret(secret_name)
        elif self.manager_type == SecretManagerType.LOCAL:
            return self.secrets.get(secret_name)
        return None
    
    def _get_vault_secret(self, secret_name: str, key: Optional[str] = None) -> Optional[str]:
        """Get secret from Vault"""
        if not self.client:
            return None
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=secret_name,
                mount_point=self.mount_point,
            )
            secret_data = response["data"]["data"]
            
            if key:
                return secret_data.get(key)
            return str(secret_data)
        except Exception as e:
            logger.error(f"Error reading Vault secret {secret_name}: {e}")
            return None
    
    def _get_aws_secret(self, secret_name: str, key: Optional[str] = None) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        if not self.client:
            return None
        
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_string = response["SecretString"]
            
            # Parse JSON if it's JSON
            import json
            try:
                secret_data = json.loads(secret_string)
                if key:
                    return secret_data.get(key)
                return secret_string
            except json.JSONDecodeError:
                return secret_string
        except Exception as e:
            logger.error(f"Error reading AWS secret {secret_name}: {e}")
            return None
    
    def _get_azure_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Azure Key Vault"""
        if not self.client:
            return None
        
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.error(f"Error reading Azure secret {secret_name}: {e}")
            return None
    
    def set_secret(self, secret_name: str, secret_value: str, key: Optional[str] = None):
        """Set secret value"""
        if self.manager_type == SecretManagerType.VAULT:
            self._set_vault_secret(secret_name, secret_value, key)
        elif self.manager_type == SecretManagerType.AWS_SECRETS_MANAGER:
            self._set_aws_secret(secret_name, secret_value)
        elif self.manager_type == SecretManagerType.AZURE_KEY_VAULT:
            self._set_azure_secret(secret_name, secret_value)
        elif self.manager_type == SecretManagerType.LOCAL:
            self.secrets[secret_name] = secret_value
    
    def _set_vault_secret(self, secret_name: str, secret_value: str, key: Optional[str] = None):
        """Set secret in Vault"""
        if not self.client:
            return
        
        try:
            if key:
                # Read existing secret, update key
                try:
                    existing = self.client.secrets.kv.v2.read_secret_version(
                        path=secret_name,
                        mount_point=self.mount_point,
                    )
                    secret_data = existing["data"]["data"]
                    secret_data[key] = secret_value
                except:
                    secret_data = {key: secret_value}
            else:
                secret_data = {"value": secret_value}
            
            self.client.secrets.kv.v2.create_or_update_secret(
                path=secret_name,
                secret=secret_data,
                mount_point=self.mount_point,
            )
        except Exception as e:
            logger.error(f"Error writing Vault secret {secret_name}: {e}")
    
    def _set_aws_secret(self, secret_name: str, secret_value: str):
        """Set secret in AWS Secrets Manager"""
        if not self.client:
            return
        
        try:
            self.client.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_value,
            )
        except Exception as e:
            logger.error(f"Error writing AWS secret {secret_name}: {e}")
    
    def _set_azure_secret(self, secret_name: str, secret_value: str):
        """Set secret in Azure Key Vault"""
        if not self.client:
            return
        
        try:
            self.client.set_secret(secret_name, secret_value)
        except Exception as e:
            logger.error(f"Error writing Azure secret {secret_name}: {e}")
    
    def delete_secret(self, secret_name: str):
        """Delete secret"""
        if self.manager_type == SecretManagerType.VAULT:
            if self.client:
                try:
                    self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                        path=secret_name,
                        mount_point=self.mount_point,
                    )
                except Exception as e:
                    logger.error(f"Error deleting Vault secret {secret_name}: {e}")
        elif self.manager_type == SecretManagerType.AWS_SECRETS_MANAGER:
            if self.client:
                try:
                    self.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
                except Exception as e:
                    logger.error(f"Error deleting AWS secret {secret_name}: {e}")
        elif self.manager_type == SecretManagerType.AZURE_KEY_VAULT:
            if self.client:
                try:
                    self.client.begin_delete_secret(secret_name)
                except Exception as e:
                    logger.error(f"Error deleting Azure secret {secret_name}: {e}")
        elif self.manager_type == SecretManagerType.LOCAL:
            self.secrets.pop(secret_name, None)

