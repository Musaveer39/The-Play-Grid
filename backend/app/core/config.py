# backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

class Settings(BaseSettings):
    # App
    APP_NAME: str = "The Play Grid API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Supabase - Using YOUR credentials
    SUPABASE_URL: str = "https://ybtymcznfteidwdjmojv.supabase.co"
    SUPABASE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlidHltY3puZnRlaWR3ZGptb2p2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzMjEyNTUsImV4cCI6MjA5ODg5NzI1NX0.j0vuf-WoMegRdlVWgecUHej-EY9fKpmeZJvzBr_hMV0"
    
    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-this")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Debug
print(f"🔍 Using Supabase URL: {settings.SUPABASE_URL}")