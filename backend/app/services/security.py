import os
import re
import time
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("app.services.security")

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-enterprise-key-do-not-share-12345")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Bearer token helper
security_scheme = HTTPBearer(auto_error=False)

# Role models
class User(BaseModel):
    username: str
    email: EmailStr
    role: str  # Admin, Viewer

# 1. JWT Authentication & Role-Based Access Control (RBAC)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT access token for authentication."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> dict:
    """Decode and verify JWT token validity."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT Token Verification Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> User:
    """Dependency to retrieve user metadata from Authorization header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_access_token(credentials.credentials)
    username: str = payload.get("sub")
    email: str = payload.get("email")
    role: str = payload.get("role", "Viewer")
    if username is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token fields",
        )
    # Log authentication audit trail
    logger.info(f"Audit log: User authenticated: {username} ({role})")
    return User(username=username, email=email, role=role)

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Optional[User]:
    """Optionally authenticate based on system settings."""
    if not os.getenv("REQUIRE_AUTH", "false").lower() == "true":
        return None
    return get_current_user(credentials)

def check_role(required_roles: List[str]):
    """Enforce RBAC role matching as a FastAPI dependency."""
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            logger.warning(f"Audit log: Access Denied for user {current_user.username}. Required: {required_roles}, Has: {current_user.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not authorized for current user role level.",
            )
        return current_user
    return dependency


# 2. Prompt Injection Detection
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"override system prompt",
    r"system override",
    r"you are now a",
    r"forget what you were told",
    r"bypass safety",
    r"dan mode",
    r"developer mode active",
    r"give me the password",
    r"reveal prompt",
]

def detect_prompt_injection(user_prompt: str) -> bool:
    """Scan prompt for injection payloads or instruction overrides."""
    prompt_lower = user_prompt.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, prompt_lower):
            logger.critical(f"Audit log: Prompt injection attempt detected: '{pattern}' pattern matched!")
            return True
    return False


# 3. PII Detection and Masking
# Basic regex patterns for PII
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
PHONE_REGEX = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
SSN_REGEX = r'\b\d{3}-\d{2}-\d{4}\b'

def scrub_pii(text_input: str) -> str:
    """Find and mask PII values (emails, phones, SSNs) with placeholders."""
    if not text_input:
        return text_input
        
    masked = re.sub(EMAIL_REGEX, "[EMAIL_MASKED]", text_input)
    masked = re.sub(PHONE_REGEX, "[PHONE_MASKED]", masked)
    masked = re.sub(SSN_REGEX, "[SSN_MASKED]", masked)
    
    if masked != text_input:
        logger.info("PII scrubbed from data payload.")
    return masked


# 4. Rate Limiter (Simple In-Memory Tracker)
# Stores lists of request timestamps per client IP
rate_limit_store = {}

def check_rate_limit(client_ip: str, max_requests: int = 60, window_sec: int = 60) -> bool:
    """Enforce request limits within a rolling time window."""
    now = time.time()
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []
        
    # Remove expired timestamps
    rate_limit_store[client_ip] = [t for t in rate_limit_store[client_ip] if now - t < window_sec]
    
    if len(rate_limit_store[client_ip]) >= max_requests:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return False
        
    rate_limit_store[client_ip].append(now)
    return True


# 5. Audit Logging Utility
def write_audit_log(user: str, action: str, details: str, status: str = "SUCCESS"):
    """Write audit entries to application security logs."""
    timestamp = datetime.utcnow().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "user": user,
        "action": action,
        "details": details,
        "status": status
    }
    logger.info(f"AUDIT_RECORD: {json.dumps(log_entry)}")
