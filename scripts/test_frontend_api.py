#!/usr/bin/env python3
"""
Test the API endpoint that the frontend actually calls
"""

import os
import sys
import uuid

# Setup environment
os.environ["DATABASE_URL"] = "sqlite:///d:/Development/altayar/MobileApp/backend/altayarvip.db"
os.environ["JWT_SECRET_KEY"] = "dummy"
os.environ["SECRET_KEY"] = "dummy"
os.environ["FAWATERK_API_KEY"] = "dummy"
os.environ["FAWATERK_VENDOR_KEY"] = "dummy"

sys.path.append(os.path.dirname(__file__))

# Import all models first
import modules

from server import app
from shared.user_integration_service import UserIntegrationService
from database.base import SessionLocal
from fastapi.testclient import TestClient

def test_frontend_api():
    """Test the API endpoint that the frontend calls"""

    # Create a test user with membership
    service = UserIntegrationService(SessionLocal())
    user_data = {
        'email': f'frontend_api_{uuid.uuid4().hex[:8]}@example.com',
        'username': f'frontendapi_{uuid.uuid4().hex[:8]}',
        'password': 'TestPass123',
        'first_name': 'Frontend',
        'last_name': 'API',
        'plan_id': '0ee07da5-3de6-4973-9a4f-2ea3de215c01'  # Silver plan
    }

    result = service.create_user_with_membership(user_data, created_by_admin=True)
    print(f'✅ Created user: {result["user"]["email"]}')
    print(f'⭐ Points awarded: {result.get("points_awarded", 0)}')

    # Test the API endpoint with FastAPI TestClient
    client = TestClient(app)

    # Call the same endpoint the frontend uses
    response = client.get('/admin/users', params={'search': result['user']['email']})

    print(f'\n📡 API Response Status: {response.status_code}')

    if response.status_code == 200:
        data = response.json()
        print(f'Total users found: {len(data.get("users", []))}')

        if data.get('users') and len(data['users']) > 0:
            user = data['users'][0]
            print('\n📋 Data received by frontend:')
            print(f'Email: {user.get("email")}')

            # Check membership data
            membership = user.get('membership')
            if membership:
                print('🎫 Membership Data:')
                print(f'  - Name: {membership.get("name")}')
                print(f'  - Status: {membership.get("status")}')
                print(f'  - End Date: {membership.get("end_date")}')
                print(f'  - Membership ID: {membership.get("membership_id")}')
            else:
                print('❌ No membership data found!')

            # Check points data
            points = user.get('points')
            if points:
                print('⭐ Points Data:')
                print(f'  - Current Balance: {points.get("current_balance")}')
                print(f'  - Total Earned: {points.get("total_earned")}')
                print(f'  - Total Redeemed: {points.get("total_redeemed")}')
            else:
                print('❌ No points data found!')
                print('This explains why frontend shows 0 points!')
                return False

            # Verify data integrity
            success = True

            if not membership:
                print('❌ Membership data missing')
                success = False

            if not points:
                print('❌ Points data missing')
                success = False
            elif points.get('current_balance') != 1500:
                print(f'❌ Wrong points balance: {points.get("current_balance")}')
                success = False

            if membership and membership.get('name') != 'Silver Membership':
                print(f'❌ Wrong membership name: {membership.get("name")}')
                success = False

            return success
        else:
            print('❌ No users returned by API')
            return False
    else:
        print(f'❌ API Error: {response.status_code}')
        print(f'Response: {response.text}')
        return False

if __name__ == "__main__":
    success = test_frontend_api()
    print(f'\n🎉 Frontend API test {"PASSED" if success else "FAILED"}!')
    if not success:
        print('\n🔍 This explains why the frontend shows 0 points!')
        print('The API is not returning points data to the frontend.')
    sys.exit(0 if success else 1)
