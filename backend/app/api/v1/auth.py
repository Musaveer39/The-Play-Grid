# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.core.database import get_db
from app.core.security import SecurityService, create_access_token, get_current_user
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# =============== SCHEMAS ===============

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=10)
    role: Optional[str] = "customer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str
    role: str
    is_verified: bool
    created_at: str

# =============== ENDPOINTS ===============

@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    db = get_db()
    
    try:
        # Check if user exists
        existing = db.table("profiles") \
            .select("id") \
            .eq("email", user_data.email) \
            .execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user in Supabase Auth
        auth_response = db.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name,
                    "phone": user_data.phone,
                    "role": user_data.role
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Please try again."
            )
        
        # Create profile
        profile_data = {
            "id": auth_response.user.id,
            "full_name": user_data.full_name,
            "phone": user_data.phone,
            "role": user_data.role,
            "email": user_data.email,
            "is_verified": False
        }
        
        db.table("profiles").insert(profile_data).execute()
        
        # Generate token
        access_token = create_access_token(
            data={"sub": auth_response.user.id, "email": user_data.email}
        )
        
        return AuthResponse(
            access_token=access_token,
            user={
                "id": auth_response.user.id,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "role": user_data.role,
                "phone": user_data.phone,
                "is_verified": False
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin):
    """Login user"""
    db = get_db()
    
    try:
        # Authenticate with Supabase
        auth_response = db.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Get user profile
        profile = db.table("profiles") \
            .select("*") \
            .eq("id", auth_response.user.id) \
            .execute()
        
        if not profile.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        user_data = profile.data[0]
        
        # Generate token
        access_token = create_access_token(
            data={"sub": auth_response.user.id, "email": credentials.email}
        )
        
        return AuthResponse(
            access_token=access_token,
            user={
                "id": user_data["id"],
                "email": credentials.email,
                "full_name": user_data.get("full_name", ""),
                "role": user_data.get("role", "customer"),
                "phone": user_data.get("phone", ""),
                "is_verified": user_data.get("is_verified", False)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user"""
    db = get_db()
    db.auth.sign_out()
    return {"message": "Logged out successfully"}