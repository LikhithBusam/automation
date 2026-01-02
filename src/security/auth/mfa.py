"""
Multi-Factor Authentication (MFA)
TOTP, SMS, Email-based MFA
"""

import logging
import secrets
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from io import BytesIO
import base64

# Optional imports for MFA features
try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False
    pyotp = None

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    qrcode = None

logger = logging.getLogger(__name__)


class TOTPProvider:
    """Time-based One-Time Password (TOTP) provider"""
    
    def __init__(self, issuer: str = "AutoGen Assistant"):
        """
        Initialize TOTP provider.
        
        Args:
            issuer: TOTP issuer name
        """
        self.issuer = issuer
    
    def generate_secret(self) -> str:
        """Generate TOTP secret"""
        if not PYOTP_AVAILABLE:
            logger.error("pyotp library not installed. Install with: pip install pyotp")
            raise ImportError("pyotp not available")
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str) -> str:
        """Generate QR code for TOTP setup"""
        if not PYOTP_AVAILABLE:
            logger.error("pyotp library not installed. Install with: pip install pyotp")
            raise ImportError("pyotp not available")
        if not QRCODE_AVAILABLE:
            logger.error("qrcode library not installed. Install with: pip install qrcode[pil]")
            raise ImportError("qrcode not available")
        
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=self.issuer,
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        qr_code_base64 = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{qr_code_base64}"
    
    def verify_token(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token"""
        if not PYOTP_AVAILABLE:
            logger.error("pyotp library not installed. Install with: pip install pyotp")
            raise ImportError("pyotp not available")
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)


class SMSProvider:
    """SMS-based MFA provider"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SMS provider.
        
        Args:
            config: SMS provider configuration (Twilio, AWS SNS, etc.)
        """
        self.config = config
        self.provider = config.get("provider", "twilio")
    
    def send_code(self, phone_number: str) -> str:
        """Send SMS code and return the code"""
        code = self._generate_code()
        
        if self.provider == "twilio":
            self._send_via_twilio(phone_number, code)
        elif self.provider == "aws_sns":
            self._send_via_aws_sns(phone_number, code)
        else:
            logger.warning(f"Unknown SMS provider: {self.provider}")
        
        return code
    
    def _generate_code(self, length: int = 6) -> str:
        """Generate random numeric code"""
        return "".join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def _send_via_twilio(self, phone_number: str, code: str):
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.config["account_sid"], self.config["auth_token"])
            client.messages.create(
                body=f"Your verification code is: {code}",
                from_=self.config["from_number"],
                to=phone_number,
            )
        except Exception as e:
            logger.error(f"Twilio SMS error: {e}")
    
    def _send_via_aws_sns(self, phone_number: str, code: str):
        """Send SMS via AWS SNS"""
        try:
            import boto3
            
            sns = boto3.client(
                "sns",
                aws_access_key_id=self.config["aws_access_key_id"],
                aws_secret_access_key=self.config["aws_secret_access_key"],
                region_name=self.config.get("region", "us-east-1"),
            )
            
            sns.publish(
                PhoneNumber=phone_number,
                Message=f"Your verification code is: {code}",
            )
        except Exception as e:
            logger.error(f"AWS SNS SMS error: {e}")


class EmailMFAProvider:
    """Email-based MFA provider"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email MFA provider.
        
        Args:
            config: Email configuration
        """
        self.config = config
    
    def send_code(self, email: str) -> str:
        """Send email code and return the code"""
        code = self._generate_code()
        
        subject = "Your Verification Code"
        body = f"""
        Your verification code is: {code}
        
        This code will expire in 10 minutes.
        If you didn't request this code, please ignore this email.
        """
        
        self._send_email(email, subject, body)
        return code
    
    def _generate_code(self, length: int = 6) -> str:
        """Generate random numeric code"""
        return "".join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def _send_email(self, email: str, subject: str, body: str):
        """Send email"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg["From"] = self.config["from_email"]
            msg["To"] = email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            server = smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"])
            server.starttls()
            server.login(self.config["smtp_username"], self.config["smtp_password"])
            server.send_message(msg)
            server.quit()
        except Exception as e:
            logger.error(f"Email MFA error: {e}")


class MFAManager:
    """MFA manager coordinating different MFA methods"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MFA manager.
        
        Args:
            config: MFA configuration
        """
        self.config = config
        self.totp = TOTPProvider(issuer=config.get("issuer", "AutoGen Assistant"))
        self.sms = SMSProvider(config.get("sms", {})) if config.get("sms", {}).get("enabled") else None
        self.email = EmailMFAProvider(config.get("email", {})) if config.get("email", {}).get("enabled") else None
        
        # Store active MFA sessions (in production, use Redis/database)
        self.mfa_sessions: Dict[str, Dict[str, Any]] = {}
    
    def setup_totp(self, user_id: str, user_email: str) -> Dict[str, str]:
        """Setup TOTP for user"""
        secret = self.totp.generate_secret()
        qr_code = self.totp.generate_qr_code(user_email, secret)
        
        # Store secret (in production, encrypt and store in database)
        self.mfa_sessions[f"{user_id}_totp_secret"] = {
            "secret": secret,
            "created_at": datetime.utcnow(),
        }
        
        return {
            "secret": secret,
            "qr_code": qr_code,
        }
    
    def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        session_key = f"{user_id}_totp_secret"
        if session_key not in self.mfa_sessions:
            return False
        
        secret = self.mfa_sessions[session_key]["secret"]
        return self.totp.verify_token(secret, token)
    
    def send_sms_code(self, user_id: str, phone_number: str) -> bool:
        """Send SMS verification code"""
        if not self.sms:
            return False
        
        code = self.sms.send_code(phone_number)
        
        # Store code with expiration (in production, use Redis)
        self.mfa_sessions[f"{user_id}_sms_code"] = {
            "code": code,
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
        }
        
        return True
    
    def verify_sms_code(self, user_id: str, code: str) -> bool:
        """Verify SMS code"""
        session_key = f"{user_id}_sms_code"
        if session_key not in self.mfa_sessions:
            return False
        
        session = self.mfa_sessions[session_key]
        
        if datetime.utcnow() > session["expires_at"]:
            del self.mfa_sessions[session_key]
            return False
        
        if session["code"] == code:
            del self.mfa_sessions[session_key]
            return True
        
        return False
    
    def send_email_code(self, user_id: str, email: str) -> bool:
        """Send email verification code"""
        if not self.email:
            return False
        
        code = self.email.send_code(email)
        
        # Store code with expiration
        self.mfa_sessions[f"{user_id}_email_code"] = {
            "code": code,
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
        }
        
        return True
    
    def verify_email_code(self, user_id: str, code: str) -> bool:
        """Verify email code"""
        session_key = f"{user_id}_email_code"
        if session_key not in self.mfa_sessions:
            return False
        
        session = self.mfa_sessions[session_key]
        
        if datetime.utcnow() > session["expires_at"]:
            del self.mfa_sessions[session_key]
            return False
        
        if session["code"] == code:
            del self.mfa_sessions[session_key]
            return True
        
        return False

