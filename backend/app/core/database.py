# backend/app/core/database.py
from supabase import create_client, Client
from app.core.config import settings
from typing import Optional
import logging
import json
from datetime import date, datetime

logger = logging.getLogger(__name__)

class DatabaseClient:
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            try:
                supabase_url = settings.SUPABASE_URL
                supabase_key = settings.SUPABASE_KEY
                
                if not supabase_url:
                    raise ValueError("SUPABASE_URL is not set in .env file")
                
                if not supabase_key:
                    raise ValueError("SUPABASE_KEY is not set in .env file")
                
                supabase_url = supabase_url.strip()
                if not supabase_url.startswith(('http://', 'https://')):
                    supabase_url = f"https://{supabase_url}"
                
                logger.info(f"Connecting to Supabase at: {supabase_url}")
                
                cls._instance = create_client(
                    supabase_url,
                    supabase_key.strip()
                )
                
                # Test connection
                test_response = cls._instance.table('profiles').select('count').limit(1).execute()
                logger.info("✅ Supabase client connected successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to create Supabase client: {str(e)}")
                raise
                
        return cls._instance

    @classmethod
    def serialize_data(cls, data: dict) -> dict:
        """Convert date/datetime objects to strings for JSON serialization"""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, (date, datetime)):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = cls.serialize_data(value)
            elif isinstance(value, list):
                serialized[key] = [
                    cls.serialize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                serialized[key] = value
        return serialized

def get_db():
    return DatabaseClient.get_client()

def serialize_for_json(data):
    """Helper function to serialize any data for JSON"""
    return DatabaseClient.serialize_data(data)