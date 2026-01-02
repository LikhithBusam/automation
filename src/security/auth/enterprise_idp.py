"""
Enterprise Identity Provider Integration
LDAP/Active Directory, SAML 2.0, Azure AD, Okta
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Optional imports for enterprise IDP features
try:
    import ldap3
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False
    ldap3 = None

try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.utils import OneLogin_Saml2_Utils
    SAML_AVAILABLE = True
except ImportError:
    SAML_AVAILABLE = False
    OneLogin_Saml2_Auth = None
    OneLogin_Saml2_Utils = None

try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False
    msal = None

logger = logging.getLogger(__name__)


class LDAPAuthenticator:
    """LDAP/Active Directory authentication"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LDAP authenticator.
        
        Args:
            config: LDAP configuration
        """
        self.server_url = config["server_url"]
        self.base_dn = config["base_dn"]
        self.bind_dn = config.get("bind_dn")
        self.bind_password = config.get("bind_password")
        self.user_search_base = config.get("user_search_base", self.base_dn)
        self.user_search_filter = config.get("user_search_filter", "(sAMAccountName={username})")
        self.group_search_base = config.get("group_search_base", self.base_dn)
        self.group_search_filter = config.get("group_search_filter", "(member={user_dn})")
        self.attributes = config.get("attributes", ["cn", "mail", "memberOf"])
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user against LDAP/AD"""
        if not LDAP3_AVAILABLE:
            logger.error("ldap3 library not installed. Install with: pip install ldap3")
            return None
        
        try:
            # Connect to LDAP server
            server = ldap3.Server(self.server_url)
            conn = ldap3.Connection(server, user=self.bind_dn, password=self.bind_password)
            
            if not conn.bind():
                logger.error(f"LDAP bind failed: {conn.result}")
                return None
            
            # Search for user
            search_filter = self.user_search_filter.format(username=username)
            conn.search(
                search_base=self.user_search_base,
                search_filter=search_filter,
                attributes=self.attributes,
            )
            
            if not conn.entries:
                logger.warning(f"User not found: {username}")
                return None
            
            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn
            
            # Try to bind as user to verify password
            user_conn = ldap3.Connection(server, user=user_dn, password=password)
            if not user_conn.bind():
                logger.warning(f"LDAP authentication failed for {username}")
                return None
            
            # Get user attributes
            user_attrs = {}
            for attr in self.attributes:
                if hasattr(user_entry, attr):
                    value = getattr(user_entry, attr)
                    if isinstance(value, list):
                        user_attrs[attr] = value[0] if value else None
                    else:
                        user_attrs[attr] = value
            
            # Get user groups
            groups = self._get_user_groups(conn, user_dn)
            user_attrs["groups"] = groups
            
            user_conn.unbind()
            conn.unbind()
            
            return {
                "username": username,
                "dn": user_dn,
                "attributes": user_attrs,
                "groups": groups,
            }
        except Exception as e:
            logger.error(f"LDAP authentication error: {e}")
            return None
    
    def _get_user_groups(self, conn, user_dn: str) -> List[str]:
        """Get user groups"""
        if not LDAP3_AVAILABLE:
            return []
        
        try:
            search_filter = self.group_search_filter.format(user_dn=user_dn)
            conn.search(
                search_base=self.group_search_base,
                search_filter=search_filter,
                attributes=["cn"],
            )
            
            groups = []
            for entry in conn.entries:
                if hasattr(entry, "cn"):
                    groups.append(str(entry.cn))
            
            return groups
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []


class SAMLAuthenticator:
    """SAML 2.0 SSO authentication"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SAML authenticator.
        
        Args:
            config: SAML configuration
        """
        self.config = config
        self.saml_settings = {
            "sp": {
                "entityId": config["sp_entity_id"],
                "assertionConsumerService": {
                    "url": config["acs_url"],
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": config.get("slo_url"),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": config.get("sp_cert"),
                "privateKey": config.get("sp_private_key"),
            },
            "idp": {
                "entityId": config["idp_entity_id"],
                "singleSignOnService": {
                    "url": config["idp_sso_url"],
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": config.get("idp_slo_url"),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": config.get("idp_cert"),
            },
        }
    
    def initiate_login(self, request: Any) -> str:
        """Initiate SAML SSO login"""
        if not SAML_AVAILABLE:
            logger.error("python3-saml library not installed. Install with: pip install python3-saml")
            raise ImportError("python3-saml not available")
        
        auth = OneLogin_Saml2_Auth(self._prepare_request(request), self.saml_settings)
        return auth.login()
    
    def process_response(self, request: Any) -> Optional[Dict[str, Any]]:
        """Process SAML response"""
        if not SAML_AVAILABLE:
            logger.error("python3-saml library not installed. Install with: pip install python3-saml")
            return None
        
        auth = OneLogin_Saml2_Auth(self._prepare_request(request), self.saml_settings)
        auth.process_response()
        
        if auth.is_authenticated():
            attributes = auth.get_attributes()
            return {
                "name_id": auth.get_nameid(),
                "attributes": attributes,
                "session_index": auth.get_session_index(),
            }
        else:
            errors = auth.get_errors()
            logger.error(f"SAML authentication errors: {errors}")
            return None
    
    def _prepare_request(self, request: Any) -> Dict[str, Any]:
        """Prepare request for SAML library"""
        return {
            "https": "on" if request.url.scheme == "https" else "off",
            "http_host": request.url.hostname,
            "script_name": request.url.path,
            "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
            "get_data": dict(request.query_params),
            "post_data": dict(request.form) if hasattr(request, "form") else {},
        }


class AzureADAuthenticator:
    """Azure AD authentication"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure AD authenticator.
        
        Args:
            config: Azure AD configuration
        """
        self.client_id = config["client_id"]
        self.client_secret = config["client_secret"]
        self.tenant_id = config["tenant_id"]
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = config.get("scope", ["User.Read"])
        
        if not MSAL_AVAILABLE:
            logger.warning("msal library not installed. Azure AD features will not work.")
            self.app = None
        else:
            self.app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=self.authority,
            )
    
    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Get Azure AD authorization URL"""
        if not MSAL_AVAILABLE or self.app is None:
            logger.error("msal library not installed. Install with: pip install msal")
            raise ImportError("msal not available")
        
        auth_url = self.app.get_authorization_request_url(
            scopes=self.scope,
            redirect_uri=redirect_uri,
            state=state,
        )
        return auth_url
    
    def acquire_token_by_authorization_code(
        self, code: str, redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """Acquire token using authorization code"""
        if not MSAL_AVAILABLE or self.app is None:
            logger.error("msal library not installed. Install with: pip install msal")
            return None
        
        result = self.app.acquire_token_by_authorization_code(
            code=code,
            scopes=self.scope,
            redirect_uri=redirect_uri,
        )
        
        if "access_token" in result:
            # Get user info
            user_info = self._get_user_info(result["access_token"])
            result["user_info"] = user_info
            return result
        else:
            logger.error(f"Azure AD token acquisition failed: {result.get('error_description')}")
            return None
    
    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Microsoft Graph"""
        import httpx
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response = httpx.get("https://graph.microsoft.com/v1.0/me", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get user info: {response.status_code}")
            return {}


class OktaAuthenticator:
    """Okta authentication"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Okta authenticator.
        
        Args:
            config: Okta configuration
        """
        self.domain = config["domain"]
        self.client_id = config["client_id"]
        self.client_secret = config["client_secret"]
        self.redirect_uri = config["redirect_uri"]
        self.scope = config.get("scope", "openid profile email")
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get Okta authorization URL"""
        from urllib.parse import urlencode
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": self.scope,
            "redirect_uri": self.redirect_uri,
            "state": state or "",
        }
        
        return f"https://{self.domain}/oauth2/default/v1/authorize?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for token"""
        import httpx
        
        token_url = f"https://{self.domain}/oauth2/default/v1/token"
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        response = httpx.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Get user info
            user_info = self._get_user_info(token_data["access_token"])
            token_data["user_info"] = user_info
            
            return token_data
        else:
            logger.error(f"Okta token exchange failed: {response.status_code}")
            return None
    
    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Okta"""
        import httpx
        
        userinfo_url = f"https://{self.domain}/oauth2/default/v1/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = httpx.get(userinfo_url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get Okta user info: {response.status_code}")
            return {}

