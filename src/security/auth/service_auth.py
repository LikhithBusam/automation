"""
Service-to-Service Authentication
mTLS and JWT-based service authentication
"""

import logging
import ssl
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import jwt
import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = logging.getLogger(__name__)


class mTLSProvider:
    """Mutual TLS (mTLS) for service-to-service authentication"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize mTLS provider.
        
        Args:
            config: mTLS configuration
        """
        self.config = config
        self.ca_cert_path = config.get("ca_cert_path")
        self.client_cert_path = config.get("client_cert_path")
        self.client_key_path = config.get("client_key_path")
    
    def create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for mTLS"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Load CA certificate
        if self.ca_cert_path:
            context.load_verify_locations(self.ca_cert_path)
        
        # Load client certificate and key
        if self.client_cert_path and self.client_key_path:
            context.load_cert_chain(self.client_cert_path, self.client_key_path)
        
        # Require client certificate
        context.verify_mode = ssl.CERT_REQUIRED
        
        return context
    
    def create_httpx_client(self) -> httpx.AsyncClient:
        """Create httpx client with mTLS"""
        ssl_context = self.create_ssl_context()
        
        return httpx.AsyncClient(
            verify=ssl_context,
            cert=(self.client_cert_path, self.client_key_path) if self.client_cert_path else None,
        )
    
    def verify_client_certificate(self, cert_pem: bytes) -> Dict[str, Any]:
        """Verify and extract client certificate information"""
        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
            
            # Extract subject information
            subject = {}
            for attr in cert.subject:
                if attr.oid == NameOID.COMMON_NAME:
                    subject["cn"] = attr.value
                elif attr.oid == NameOID.ORGANIZATION_NAME:
                    subject["organization"] = attr.value
                elif attr.oid == NameOID.ORGANIZATIONAL_UNIT_NAME:
                    subject["organizational_unit"] = attr.value
            
            return {
                "valid": True,
                "subject": subject,
                "serial_number": str(cert.serial_number),
                "not_valid_before": cert.not_valid_before.isoformat(),
                "not_valid_after": cert.not_valid_after.isoformat(),
            }
        except Exception as e:
            logger.error(f"Certificate verification error: {e}")
            return {"valid": False, "error": str(e)}


class ServiceJWTProvider:
    """JWT-based service-to-service authentication"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize service JWT provider.
        
        Args:
            config: JWT configuration
        """
        self.service_name = config["service_name"]
        self.secret_key = config["secret_key"]
        self.algorithm = config.get("algorithm", "HS256")
        self.issuer = config.get("issuer", "automaton-services")
        self.audience = config.get("audience", "automaton-services")
    
    def generate_service_token(
        self,
        target_service: str,
        scopes: Optional[list] = None,
        expires_in: int = 3600,
    ) -> str:
        """Generate JWT token for service-to-service communication"""
        now = datetime.utcnow()
        
        payload = {
            "iss": self.issuer,
            "sub": self.service_name,
            "aud": target_service,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "service": self.service_name,
            "target_service": target_service,
        }
        
        if scopes:
            payload["scopes"] = scopes
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_service_token(
        self,
        token: str,
        expected_issuer: Optional[str] = None,
        expected_audience: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate service JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=expected_issuer or self.issuer,
                audience=expected_audience or self.audience,
            )
            
            return {
                "valid": True,
                "service": payload.get("service"),
                "target_service": payload.get("target_service"),
                "scopes": payload.get("scopes", []),
            }
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": str(e)}


class ServiceAuthMiddleware:
    """Middleware for service-to-service authentication"""
    
    def __init__(self, auth_method: str = "jwt", config: Optional[Dict[str, Any]] = None):
        """
        Initialize service auth middleware.
        
        Args:
            auth_method: "jwt" or "mtls"
            config: Authentication configuration
        """
        self.auth_method = auth_method
        self.config = config or {}
        
        if auth_method == "jwt":
            self.jwt_provider = ServiceJWTProvider(self.config.get("jwt", {}))
            self.mtls_provider = None
        elif auth_method == "mtls":
            self.mtls_provider = mTLSProvider(self.config.get("mtls", {}))
            self.jwt_provider = None
        else:
            raise ValueError(f"Unknown auth method: {auth_method}")
    
    async def authenticate_request(self, request: Any) -> Optional[Dict[str, Any]]:
        """Authenticate incoming service request"""
        if self.auth_method == "jwt":
            # Extract JWT from Authorization header
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            result = self.jwt_provider.validate_service_token(token)
            
            if result["valid"]:
                return result
            else:
                return None
        
        elif self.auth_method == "mtls":
            # Extract client certificate from request
            # This depends on your web framework
            # For FastAPI/Starlette, certificate is in request.client_cert
            if hasattr(request, "client_cert"):
                cert_pem = request.client_cert
                result = self.mtls_provider.verify_client_certificate(cert_pem)
                
                if result["valid"]:
                    return result
                else:
                    return None
        
        return None

