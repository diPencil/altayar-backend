#!/usr/bin/env python3
"""
Test membership data consistency across all APIs
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
from modules.admin.routes import get_all_users, get_user_details
from unittest.mock import Mock

def test_membership_data_consistency():
    """Test that membership data is consistent across all APIs"""

    service = UserIntegrationService(SessionLocal())
    try:
        # Create test user with membership
        user_data = {
            'email': f'consistency_test_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'consistency_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Consistency',
            'last_name': 'Test',
            'plan_id': '0ee07da5-3de6-4973-9a4f-2ea3de215c01'  # Silver plan
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        expected_plan_id = '0ee07da5-3de6-4973-9a4f-2ea3de215c01'
        expected_plan_name = 'Silver Membership'

        print(f'✅ Created user with membership: {result["user"]["email"]}')

        # Test 1: get_all_users API
        print('\\n📋 Testing get_all_users API...')
        mock_user = Mock()
        users_response = get_all_users(search=result['user']['email'], current_user=mock_user, db=SessionLocal())

        if users_response['users'] and len(users_response['users']) > 0:
            user_from_list = users_response['users'][0]

            # Check plan data in users list
            plan_data = user_from_list.get('plan')
            if plan_data:
                print(f'✅ Users List - Plan Name: {plan_data.get("name")}')
                print(f'✅ Users List - Plan ID: {plan_data.get("code")}')

                if plan_data.get('name') == expected_plan_name:
                    print('✅ Users List: Plan name matches!')
                else:
                    print(f'❌ Users List: Plan name mismatch: {plan_data.get("name")} ≠ {expected_plan_name}')
                    return False
            else:
                print('❌ Users List: No plan data found!')
                return False
        else:
            print('❌ Users List: No users found!')
            return False

        # Test 2: get_user_details API (for profile)
        print('\\n📋 Testing get_user_details API...')
        details_response = get_user_details(user_id=user_id, current_user=mock_user, db=SessionLocal())

        membership_data = details_response.get('membership')
        if membership_data:
            print(f'✅ User Profile - Plan Name: {membership_data.get("plan_name")}')
            print(f'✅ User Profile - Plan ID: {membership_data.get("plan_id")}')

            if membership_data.get('plan_name') == expected_plan_name:
                print('✅ User Profile: Plan name matches!')
            else:
                print(f'❌ User Profile: Plan name mismatch: {membership_data.get("plan_name")} ≠ {expected_plan_name}')
                return False

            if membership_data.get('plan_id') == expected_plan_id:
                print('✅ User Profile: Plan ID matches!')
            else:
                print(f'❌ User Profile: Plan ID mismatch: {membership_data.get("plan_id")} ≠ {expected_plan_id}')
                return False
        else:
            print('❌ User Profile: No membership data found!')
            return False

        # Test 3: Verify consistency between APIs
        print('\\n📋 Testing API consistency...')

        list_plan_name = user_from_list['plan']['name']
        profile_plan_name = membership_data['plan_name']
        profile_plan_id = membership_data['plan_id']

        if list_plan_name == profile_plan_name:
            print('✅ API Consistency: Plan names match between list and profile!')
        else:
            print(f'❌ API Inconsistency: Plan names differ: List="{list_plan_name}" vs Profile="{profile_plan_name}"')
            return False

        # Test 4: Simulate frontend edit form preloading
        print('\\n📋 Testing Edit Form Preloading...')

        # Simulate what the frontend edit form would receive
        edit_form_data = {
            'plan_id': details_response.get('membership', {}).get('plan_id', ''),
            'plan_name': details_response.get('membership', {}).get('plan_name', ''),
        }

        print(f'✅ Edit Form - Preloaded Plan ID: {edit_form_data["plan_id"]}')
        print(f'✅ Edit Form - Preloaded Plan Name: {edit_form_data["plan_name"]}')

        if edit_form_data['plan_id'] == expected_plan_id:
            print('✅ Edit Form: Plan ID preloaded correctly!')
        else:
            print(f'❌ Edit Form: Plan ID not preloaded: {edit_form_data["plan_id"]} ≠ {expected_plan_id}')
            return False

        if edit_form_data['plan_name'] == expected_plan_name:
            print('✅ Edit Form: Plan name available!')
        else:
            print(f'❌ Edit Form: Plan name incorrect: {edit_form_data["plan_name"]} ≠ {expected_plan_name}')
            return False

        print('\\n🎉 All membership APIs are consistent!')
        print('✅ Users List shows correct membership')
        print('✅ User Profile shows correct membership')
        print('✅ Edit Form preloads correct membership')
        print('✅ No more "No Plan" inconsistencies!')

        return True

    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_membership_data_consistency()
    print(f'\\n🎯 Final Result: {"SUCCESS - All APIs Consistent!" if success else "FAILED - APIs Inconsistent!"}')
    sys.exit(0 if success else 1)
