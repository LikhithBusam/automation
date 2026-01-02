"""
Encryption Manager
At-rest, in-transit, envelope encryption, HSM integration
"""

import logging
import os
import base64
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import ssl

logger = logging.getLogger(__name__)


class AES256Encryption:
    """AES-256 encryption for at-rest data"""
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize AES-256 encryption.
        
        Args:
            key: Encryption key (32 bytes for AES-256). If None, generates new key.
        """
        if key is None:
            key = os.urandom(32)
        
        if len(key) != 32:
            raise ValueError("AES-256 requires 32-byte key")
        
        self.key = key
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt data using AES-256-GCM"""
        # Generate random IV
        iv = os.urandom(12)  # 96-bit IV for GCM
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        
        # Encrypt
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # Combine IV, tag, and ciphertext
        return iv + encryptor.tag + ciphertext
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt data using AES-256-GCM"""
        # Extract IV, tag, and ciphertext
        iv = ciphertext[:12]
        tag = ciphertext[12:28]
        encrypted_data = ciphertext[28:]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv, tag),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        return decryptor.update(encrypted_data) + decryptor.finalize()
    
    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt string and return base64-encoded result"""
        ciphertext = self.encrypt(plaintext.encode("utf-8"))
        return base64.b64encode(ciphertext).decode("utf-8")
    
    def decrypt_string(self, ciphertext_b64: str) -> str:
        """Decrypt base64-encoded ciphertext"""
        ciphertext = base64.b64decode(ciphertext_b64.encode("utf-8"))
        plaintext = self.decrypt(ciphertext)
        return plaintext.decode("utf-8")


class EnvelopeEncryption:
    """Envelope encryption for sensitive data"""
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize envelope encryption.
        
        Args:
            master_key: Master encryption key (RSA public key for key encryption)
        """
        if master_key is None:
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend(),
            )
            self.private_key = private_key
            self.public_key = private_key.public_key()
        else:
            # Load provided key
            self.public_key = serialization.load_pem_public_key(master_key)
            self.private_key = None
    
    def encrypt_data_key(self, data_key: bytes) -> bytes:
        """Encrypt data encryption key with master key"""
        encrypted_key = self.public_key.encrypt(
            data_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return encrypted_key
    
    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt data encryption key"""
        if self.private_key is None:
            raise ValueError("Private key required for decryption")
        
        data_key = self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return data_key
    
    def encrypt_envelope(self, plaintext: bytes) -> Dict[str, bytes]:
        """Encrypt data using envelope encryption"""
        # Generate data encryption key
        data_key = os.urandom(32)
        
        # Encrypt data with data key
        aes = AES256Encryption(data_key)
        ciphertext = aes.encrypt(plaintext)
        
        # Encrypt data key with master key
        encrypted_key = self.encrypt_data_key(data_key)
        
        return {
            "encrypted_key": encrypted_key,
            "ciphertext": ciphertext,
        }
    
    def decrypt_envelope(self, envelope: Dict[str, bytes]) -> bytes:
        """Decrypt data using envelope encryption"""
        # Decrypt data key
        data_key = self.decrypt_data_key(envelope["encrypted_key"])
        
        # Decrypt data
        aes = AES256Encryption(data_key)
        plaintext = aes.decrypt(envelope["ciphertext"])
        
        return plaintext


class TLS13Config:
    """TLS 1.3 configuration for in-transit encryption"""
    
    @staticmethod
    def create_ssl_context(
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        ca_file: Optional[str] = None,
    ) -> ssl.SSLContext:
        """Create SSL context with TLS 1.3"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Set minimum version to TLS 1.3
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # Load certificates if provided
        if cert_file and key_file:
            context.load_cert_chain(cert_file, key_file)
        
        if ca_file:
            context.load_verify_locations(ca_file)
        
        # Security settings
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        return context


class HSMKeyManager:
    """Hardware Security Module (HSM) integration"""
    
    def __init__(self, hsm_config: Dict[str, Any]):
        """
        Initialize HSM key manager.
        
        Args:
            hsm_config: HSM configuration (AWS KMS, Azure Key Vault, etc.)
        """
        self.hsm_type = hsm_config.get("type", "aws_kms")
        self.config = hsm_config
        
        if self.hsm_type == "aws_kms":
            self._init_aws_kms()
        elif self.hsm_type == "azure_keyvault":
            self._init_azure_keyvault()
        elif self.hsm_type == "gcp_kms":
            self._init_gcp_kms()
        else:
            raise ValueError(f"Unknown HSM type: {self.hsm_type}")
    
    def _init_aws_kms(self):
        """Initialize AWS KMS"""
        try:
            import boto3
            self.kms_client = boto3.client(
                "kms",
                region_name=self.config.get("region", "us-east-1"),
                aws_access_key_id=self.config.get("aws_access_key_id"),
                aws_secret_access_key=self.config.get("aws_secret_access_key"),
            )
            self.key_id = self.config["key_id"]
        except ImportError:
            logger.warning("boto3 not installed, AWS KMS unavailable")
            self.kms_client = None
    
    def _init_azure_keyvault(self):
        """Initialize Azure Key Vault"""
        try:
            from azure.keyvault.keys import KeyClient
            from azure.identity import DefaultAzureCredential
            
            credential = DefaultAzureCredential()
            self.key_client = KeyClient(
                vault_url=self.config["vault_url"],
                credential=credential,
            )
            self.key_name = self.config["key_name"]
        except ImportError:
            logger.warning("azure-keyvault-keys not installed, Azure Key Vault unavailable")
            self.key_client = None
    
    def _init_gcp_kms(self):
        """Initialize GCP KMS"""
        try:
            from google.cloud import kms
            
            self.kms_client = kms.KeyManagementServiceClient()
            self.project_id = self.config["project_id"]
            self.location = self.config.get("location", "global")
            self.key_ring = self.config["key_ring"]
            self.key_name = self.config["key_name"]
        except ImportError:
            logger.warning("google-cloud-kms not installed, GCP KMS unavailable")
            self.kms_client = None
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt data using HSM"""
        if self.hsm_type == "aws_kms":
            response = self.kms_client.encrypt(
                KeyId=self.key_id,
                Plaintext=plaintext,
            )
            return response["CiphertextBlob"]
        elif self.hsm_type == "azure_keyvault":
            result = self.key_client.encrypt(self.key_name, "RSA-OAEP", plaintext)
            return result.ciphertext
        elif self.hsm_type == "gcp_kms":
            key_path = self.kms_client.crypto_key_path(
                self.project_id, self.location, self.key_ring, self.key_name
            )
            encrypt_response = self.kms_client.encrypt(
                request={"name": key_path, "plaintext": plaintext}
            )
            return encrypt_response.ciphertext
        else:
            raise ValueError(f"Encryption not supported for HSM type: {self.hsm_type}")
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt data using HSM"""
        if self.hsm_type == "aws_kms":
            response = self.kms_client.decrypt(
                CiphertextBlob=ciphertext,
            )
            return response["Plaintext"]
        elif self.hsm_type == "azure_keyvault":
            result = self.key_client.decrypt(self.key_name, "RSA-OAEP", ciphertext)
            return result.plaintext
        elif self.hsm_type == "gcp_kms":
            key_path = self.kms_client.crypto_key_path(
                self.project_id, self.location, self.key_ring, self.key_name
            )
            decrypt_response = self.kms_client.decrypt(
                request={"name": key_path, "ciphertext": ciphertext}
            )
            return decrypt_response.plaintext
        else:
            raise ValueError(f"Decryption not supported for HSM type: {self.hsm_type}")


class EncryptionManager:
    """Unified encryption manager"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize encryption manager.
        
        Args:
            config: Encryption configuration
        """
        self.config = config
        
        # Initialize encryption methods
        self.aes256 = AES256Encryption(key=config.get("aes_key"))
        self.envelope = EnvelopeEncryption(master_key=config.get("master_key"))
        self.tls13 = TLS13Config()
        
        # Initialize HSM if configured
        if config.get("hsm"):
            self.hsm = HSMKeyManager(config["hsm"])
        else:
            self.hsm = None
    
    def encrypt_at_rest(self, data: bytes) -> bytes:
        """Encrypt data at rest"""
        if self.hsm:
            # Use HSM for key encryption, AES for data encryption
            envelope = self.envelope.encrypt_envelope(data)
            envelope["encrypted_key"] = self.hsm.encrypt(envelope["encrypted_key"])
            return self._serialize_envelope(envelope)
        else:
            return self.aes256.encrypt(data)
    
    def decrypt_at_rest(self, ciphertext: bytes) -> bytes:
        """Decrypt data at rest"""
        if self.hsm:
            envelope = self._deserialize_envelope(ciphertext)
            envelope["encrypted_key"] = self.hsm.decrypt(envelope["encrypted_key"])
            return self.envelope.decrypt_envelope(envelope)
        else:
            return self.aes256.decrypt(ciphertext)
    
    def _serialize_envelope(self, envelope: Dict[str, bytes]) -> bytes:
        """Serialize envelope for storage"""
        import json
        return json.dumps({
            "encrypted_key": base64.b64encode(envelope["encrypted_key"]).decode(),
            "ciphertext": base64.b64encode(envelope["ciphertext"]).decode(),
        }).encode()
    
    def _deserialize_envelope(self, data: bytes) -> Dict[str, bytes]:
        """Deserialize envelope from storage"""
        import json
        envelope_dict = json.loads(data.decode())
        return {
            "encrypted_key": base64.b64decode(envelope_dict["encrypted_key"]),
            "ciphertext": base64.b64decode(envelope_dict["ciphertext"]),
        }

