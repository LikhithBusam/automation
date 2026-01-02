"""
Enterprise Authentication and Authorization Module
"""

from .oauth2_oidc import OAuth2OIDCProvider, JWTTokenHandler
from .rbac import RBACManager, Role, Permission, get_rbac_manager
from .abac import ABACManager, Policy, get_abac_manager
from .enterprise_idp import (
    LDAPAuthenticator,
    SAMLAuthenticator,
    AzureADAuthenticator,
    OktaAuthenticator,
)
from .mfa import MFAManager, TOTPProvider, SMSProvider, EmailMFAProvider
from .api_keys import APIKeyManager, APIKey, get_api_key_manager
from .service_auth import mTLSProvider, ServiceJWTProvider, ServiceAuthMiddleware
from .session_manager import SessionManager, TokenManager

__all__ = [
    # OAuth 2.0 / OIDC
    "OAuth2OIDCProvider",
    "JWTTokenHandler",
    # RBAC
    "RBACManager",
    "Role",
    "Permission",
    "get_rbac_manager",
    # ABAC
    "ABACManager",
    "Policy",
    "get_abac_manager",
    # Enterprise IDP
    "LDAPAuthenticator",
    "SAMLAuthenticator",
    "AzureADAuthenticator",
    "OktaAuthenticator",
    # MFA
    "MFAManager",
    "TOTPProvider",
    "SMSProvider",
    "EmailMFAProvider",
    # API Keys
    "APIKeyManager",
    "APIKey",
    "get_api_key_manager",
    # Service Auth
    "mTLSProvider",
    "ServiceJWTProvider",
    "ServiceAuthMiddleware",
    # Session Management
    "SessionManager",
    "TokenManager",
]

