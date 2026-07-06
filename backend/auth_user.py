# auth_user_continue.py
from supabase import create_client
import time

SUPABASE_URL = "https://ybtymcznfteidwdjmojv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlidHltY3puZnRlaWR3ZGptb2p2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzMjEyNTUsImV4cCI6MjA5ODg5NzI1NX0.j0vuf-WoMegRdlVWgecUHej-EY9fKpmeZJvzBr_hMV0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Supabase client created!")

# Remaining users to create
remaining_users = [
    ("amit@playgrid.com", "Test@123", {"full_name": "Amit Kumar", "phone": "+919999999993", "role": "owner"}),
    ("sneha@playgrid.com", "Test@123", {"full_name": "Sneha Reddy", "phone": "+919999999994", "role": "owner"}),
    ("vikram@playgrid.com", "Test@123", {"full_name": "Vikram Singh", "phone": "+919999999995", "role": "owner"}),
    ("customer1@email.com", "Test@123", {"full_name": "Customer One", "phone": "+919999999996", "role": "customer"}),
    ("customer2@email.com", "Test@123", {"full_name": "Customer Two", "phone": "+919999999997", "role": "customer"}),
    ("customer3@email.com", "Test@123", {"full_name": "Customer Three", "phone": "+919999999998", "role": "customer"}),
    ("customer4@email.com", "Test@123", {"full_name": "Customer Four", "phone": "+919999999999", "role": "customer"}),
]

print("🔄 Creating remaining users with delays...")
user_ids = []

for email, password, metadata in remaining_users:
    try:
        print(f"⏳ Creating: {metadata['full_name']} - {email}")
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": metadata}
        })
        user_ids.append((response.user.id, metadata["full_name"]))
        print(f"✅ Created: {metadata['full_name']} - {email}")
        time.sleep(5)  # Wait 5 seconds between attempts
    except Exception as e:
        print(f"❌ Failed: {email} - {e}")
        time.sleep(10)  # Wait longer if failed

print("\n📋 All User IDs:")
for user_id, name in user_ids:
    print(f"'{user_id}' -- {name}")