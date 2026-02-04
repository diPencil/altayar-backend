"""
Direct test of bookings endpoint - needs admin token
"""
import sys
sys.path.insert(0, '.')

# Create a test admin token
from modules.auth.utils import create_access_token
from modules.users.models import User
from database.base import SessionLocal

db = SessionLocal()

try:
    # Get admin user
    admin = db.query(User).filter(User.role == 'ADMIN').first()
    
    if not admin:
        print("No admin user found!")
        sys.exit(1)
    
    # Create token
    token = create_access_token({"sub": str(admin.id)})
    
    print("=" * 60)
    print(f"Admin: {admin.email}")
    print(f"Token: {token[:50]}...")
    print("=" * 60)
    
    # Now test the API
    import requests
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\nTesting GET /api/bookings...")
    response = requests.get(
        "http://localhost:8082/api/bookings",
        headers=headers,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Got {len(data)} bookings")
        if data:
            print(f"\nFirst booking keys: {list(data[0].keys())}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
