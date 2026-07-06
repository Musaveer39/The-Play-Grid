# backend/app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class SecurityService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict) -> str:
        """Create a refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict:
        """Decode and verify a JWT token"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"Token decode error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """Get current user from token"""
    token = credentials.credentials
    payload = SecurityService.decode_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get user from database
    db = get_db()
    try:
        result = db.table("profiles").select("*").eq("id", user_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return result.data[0]
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user data"
        )

async def get_current_owner(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Ensure user is an owner"""
    if current_user.get("role") not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner privileges required"
        )
    return current_user

async def get_admin_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Ensure user is an admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# Create a function that can be imported directly
def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """Convenience function to create access token"""
    return SecurityService.create_access_token(data, expires_delta)