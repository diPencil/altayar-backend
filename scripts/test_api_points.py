#!/usr/bin/env python3
"""
Test API points response
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

from shared.user_integration_service import UserIntegrationService
from database.base import SessionLocal

def test_api_points_response():
    """Test that the API returns correct points data"""

    service = UserIntegrationService(SessionLocal())
    try:
        # Create test user
        user_data = {
            'email': f'api_points_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'apipoints_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'API',
            'last_name': 'Points',
            'plan_id': '0ee07da5-3de6-4973-9a4f-2ea3de215c01'  # Silver plan
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f'✅ Created user: {result["user"]["email"]}')
        print(f'⭐ Points awarded: {result.get("points_awarded", 0)}')

        # Test the API response structure
        from modules.admin.routes import get_all_users
        from unittest.mock import Mock

        # Mock current_user
        mock_user = Mock()

        # Call get_all_users for this user
        response = get_all_users(
            search=result['user']['email'],
            current_user=mock_user,
            db=SessionLocal()
        )

        if response['users']:
            user_data = response['users'][0]
            print('\n📋 API Response Structure:')
            print(f'Email: {user_data["email"]}')

            membership = user_data.get('membership')
            points = user_data.get('points')

            if membership:
                print('🎫 Membership:')
                print(f'  - Name: {membership.get("name")}')
                print(f'  - Status: {membership.get("status")}')
                print(f'  - End Date: {membership.get("end_date")}')
                print(f'  - Membership ID: {membership.get("membership_id")}')
            else:
                print('❌ No membership data')

            if points:
                print('⭐ Points:')
                print(f'  - Current Balance: {points.get("current_balance")}')
                print(f'  - Total Earned: {points.get("total_earned")}')
                print(f'  - Total Redeemed: {points.get("total_redeemed")}')
            else:
                print('❌ No points data')

            # Verify the data
            success = True
            if not membership:
                print('❌ API does not return membership data')
                success = False
            elif membership.get('name') != 'Silver Membership':
                print(f'❌ Wrong membership name: {membership.get("name")}')
                success = False

            if not points:
                print('❌ API does not return points data')
                success = False
            elif points.get('current_balance') != 1500:
                print(f'❌ Wrong points balance: {points.get("current_balance")}')
                success = False

            return success
        else:
            print('❌ No users found in API response')
            return False

    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_points_response()
    print(f'\n🎉 API test {"PASSED" if success else "FAILED"}!')
    sys.exit(0 if success else 1)
