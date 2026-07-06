# backend/test_connection.py
from supabase import create_client
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Your credentials
SUPABASE_URL = "https://ybtymcznfteidwdjmojv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlidHltY3puZnRlaWR3ZGptb2p2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzMjEyNTUsImV4cCI6MjA5ODg5NzI1NX0.j0vuf-WoMegRdlVWgecUHej-EY9fKpmeZJvzBr_hMV0"

print(f"🔍 Connecting to: {SUPABASE_URL}")
print(f"🔑 Using key: {SUPABASE_KEY[:20]}...")

try:
    # Create client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Test connection - try to get profiles
    response = supabase.table('profiles').select('*').limit(1).execute()
    print("✅ Connection successful!")
    print(f"📊 Data: {response.data}")
    
except Exception as e:
    print(f"❌ Error: {e}")