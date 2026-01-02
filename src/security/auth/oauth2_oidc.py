"""
OAuth 2.0 and OpenID Connect Integration
Enterprise-grade authentication support
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from starlette.requests import Request
from starlette.responses import RedirectResponse

logger = logging.getLogger(__name__)


class OAuth2OIDCProvider:
    """OAuth 2.0 / OpenID Connect provider integration"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OAuth 2.0 / OIDC provider.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.oauth = OAuth()
        self._register_providers()
    
    def _register_providers(self):
        """Register OAuth providers"""
        # Google OAuth
        if self.config.get("google", {}).get("enabled"):
            self.oauth.register(
                name="google",
                client_id=self.config["google"]["client_id"],
                client_secret=self.config["google"]["client_secret"],
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
        
        # GitHub OAuth
        if self.config.get("github", {}).get("enabled"):
            self.oauth.register(
                name="github",
                client_id=self.config["github"]["client_id"],
                client_secret=self.config["github"]["client_secret"],
                server_metadata_url="https://github.com/login/oauth/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
        
        # Generic OIDC provider
        if self.config.get("oidc", {}).get("enabled"):
            self.oauth.register(
                name="oidc",
                client_id=self.config["oidc"]["client_id"],
                client_secret=self.config["oidc"]["client_secret"],
                server_metadata_url=self.config["oidc"]["metadata_url"],
                client_kwargs={"scope": self.config["oidc"].get("scope", "openid email profile")},
            )
    
    async def authorize(self, request: Request, provider: str) -> RedirectResponse:
        """Initiate OAuth authorization flow"""
        try:
            redirect_uri = request.url_for("oauth_callback", provider=provider)
            return await self.oauth.providers[provider].authorize_redirect(
                request, redirect_uri
            )
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth provider '{provider}' not configured"
            )
    
    async def callback(self, request: Request, provider: str) -> Dict[str, Any]:
        """Handle OAuth callback"""
        try:
            token = await self.oauth.providers[provider].authorize_access_token(request)
            
            # Get user info
            user_info = await self._get_user_info(provider, token)
            
            return {
                "access_token": token.get("access_token"),
                "id_token": token.get("id_token"),
                "user_info": user_info,
                "expires_at": datetime.utcnow() + timedelta(seconds=token.get("expires_in", 3600)),
            }
        except Exception as e:
            logger.error(f"OAuth callback error for {provider}: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth authentication failed"
            )
    
    async def _get_user_info(self, provider: str, token: Dict[str, Any]) -> Dict[str, Any]:
        """Get user information from provider"""
        if provider == "google":
            async with self.oauth.providers[provider].get("https://www.googleapis.com/oauth2/v2/userinfo", token=token) as resp:
                return await resp.json()
        elif provider == "github":
            async with self.oauth.providers[provider].get("https://api.github.com/user", token=token) as resp:
                return await resp.json()
        else:
            # Generic OIDC userinfo endpoint
            userinfo_url = self.config.get("oidc", {}).get("userinfo_url")
            if userinfo_url:
                async with self.oauth.providers[provider].get(userinfo_url, token=token) as resp:
                    return await resp.json()
            return {}


class JWTTokenHandler:
    """JWT token generation and validation"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize JWT token handler.
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def generate_token(
        self,
        user_id: str,
        email: str,
        roles: list,
        expires_in: int = 3600,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate JWT token"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "email": email,
            "roles": roles,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def refresh_token(self, token: str, expires_in: int = 3600) -> str:
        """Refresh JWT token"""
        payload = self.validate_token(token)
        
        # Remove exp and iat
        payload.pop("exp", None)
        payload.pop("iat", None)
        
        # Generate new token
        return self.generate_token(
            user_id=payload["sub"],
            email=payload["email"],
            roles=payload["roles"],
            expires_in=expires_in,
            additional_claims={k: v for k, v in payload.items() if k not in ["sub", "email", "roles"]},
        )

