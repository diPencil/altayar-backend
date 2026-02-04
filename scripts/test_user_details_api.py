#!/usr/bin/env python3
"""
Test the user details API to see if points are returned
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
from modules.admin.routes import get_user_details
from unittest.mock import Mock

def test_user_details_api():
    """Test that get_user_details returns points data"""

    service = UserIntegrationService(SessionLocal())
    try:
        # Create test user with membership
        user_data = {
            'email': f'details_api_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'detailsapi_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Details',
            'last_name': 'API',
            'plan_id': '0ee07da5-3de6-4973-9a4f-2ea3de215c01'  # Silver plan
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f'✅ Created user: {result["user"]["email"]} (ID: {user_id})')
        print(f'⭐ Points awarded: {result.get("points_awarded", 0)}')

        # Test the get_user_details API
        mock_user = Mock()
        response = get_user_details(user_id=user_id, current_user=mock_user, db=SessionLocal())

        print('\n📋 API Response Structure:')

        # Check if response has the expected keys
        expected_keys = ['user', 'membership', 'points', 'wallet', 'recent_payments']
        for key in expected_keys:
            if key in response:
                print(f'✅ {key}: present')
            else:
                print(f'❌ {key}: MISSING')

        # Check points specifically
        points = response.get('points')
        if points:
            print(f'\\n⭐ Points Data:')
            print(f'   - Current Balance: {points.get("current_balance")}')
            print(f'   - Total Earned: {points.get("total_earned")}')

            if points.get('current_balance') == 1500:
                print('✅ Points balance is correct!')
            else:
                print(f'❌ Points balance incorrect: {points.get("current_balance")} (expected: 1500)')
                return False
        else:
            print('\\n❌ CRITICAL: Points data not found in API response!')
            print('This is why the frontend shows 0 points.')

            # Debug: Check if points balance exists in database
            from modules.points.models import PointsBalance
            db = SessionLocal()
            balance = db.query(PointsBalance).filter(PointsBalance.user_id == user_id).first()
            if balance:
                print(f'Points balance exists in DB: {balance.current_balance}')
                print(f'Query used user_id: {user_id} (type: {type(user_id)})')
                print(f'DB user_id: {balance.user_id} (type: {type(balance.user_id)})')
                print(f'Values match: {user_id == balance.user_id}')
            else:
                print('Points balance does not exist in database!')
            db.close()

            return False

        # Check membership
        membership = response.get('membership')
        if membership:
            print(f'\\n🎫 Membership: {membership.get("plan_name")} ({membership.get("status")})')
        else:
            print('\\n❌ No membership data')

        print('\\n🎉 User details API test completed!')
        return True

    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_user_details_api()
    print(f'\\n🎯 Result: {"SUCCESS" if success else "FAILED"}')
    if not success:
        print('\\n🔧 The issue is that get_user_details is not returning points data.')
        print('The frontend will continue to show 0 points until this is fixed.')
    sys.exit(0 if success else 1)

