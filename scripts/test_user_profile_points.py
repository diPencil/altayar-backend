#!/usr/bin/env python3
"""
Test that user profile/details API returns points data correctly
"""

import os
import sys
import uuid
import json

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

def test_user_profile_points():
    """Test that user profile API returns points data"""

    service = UserIntegrationService(SessionLocal())
    try:
        # Create test user with membership
        user_data = {
            'email': f'profile_test_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'profiletest_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Profile',
            'last_name': 'Test',
            'plan_id': '0ee07da5-3de6-4973-9a4f-2ea3de215c01'  # Silver plan
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f'✅ Created user: {result["user"]["email"]}')
        print(f'⭐ Points awarded: {result.get("points_awarded", 0)}')

        # Test the user details API
        from modules.admin.routes import get_user_details
        from unittest.mock import Mock

        mock_user = Mock()
        response = get_user_details(user_id=user_id, current_user=mock_user, db=SessionLocal())

        print('\n📋 User Profile API Response:')

        # Check user data
        user = response.get('user')
        if user:
            print(f'👤 User: {user.get("name")} ({user.get("email")})')
        else:
            print('❌ No user data')
            return False

        # Check membership data
        membership = response.get('membership')
        if membership:
            print(f'🎫 Membership: {membership.get("plan_name")} ({membership.get("status")})')
            print(f'📅 End Date: {membership.get("end_date")}')
        else:
            print('❌ No membership data')

        # Check points data - THIS IS THE CRITICAL PART
        points = response.get('points')
        if points:
            print('⭐ Points Data:')
            print(f'   - Current Balance: {points.get("current_balance")}')
            print(f'   - Total Earned: {points.get("total_earned")}')

            # Verify the data
            expected_points = 1500  # Silver membership welcome points
            if points.get('current_balance') == expected_points:
                print(f'✅ Points balance correct: {expected_points} PTS')
            else:
                print(f'❌ Points balance incorrect: {points.get("current_balance")} (expected: {expected_points})')
                return False

            if points.get('total_earned') == expected_points:
                print(f'✅ Total earned correct: {expected_points} PTS')
            else:
                print(f'❌ Total earned incorrect: {points.get("total_earned")} (expected: {expected_points})')
                return False
        else:
            print('❌ CRITICAL: No points data in user profile API response!')
            print('This explains why the frontend shows 0 points.')
            return False

        # Check wallet data
        wallet = response.get('wallet')
        if wallet:
            print(f'💰 Wallet: {wallet.get("balance")} {wallet.get("currency")}')
        else:
            print('❌ No wallet data')

        print('\n🎉 User profile API test PASSED!')
        print('✅ Points data is now included in user profile response')
        print('✅ Frontend should now display the correct loyalty points')

        return True

    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_user_profile_points()
    print(f'\n🎯 Final Result: {"SUCCESS" if success else "FAILED"}')
    if success:
        print('The user profile will now show loyalty points correctly!')
    else:
        print('The user profile points issue is not yet resolved.')
    sys.exit(0 if success else 1)

