#!/usr/bin/env python3
"""
Simulate what the frontend should receive and display
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
from modules.admin.routes import get_user_details
from unittest.mock import Mock

def simulate_frontend_experience():
    """Simulate what the frontend should receive and display"""

    service = UserIntegrationService(SessionLocal())
    try:
        # Create test user with membership
        user_data = {
            'email': f'frontend_sim_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'frontendsim_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Frontend',
            'last_name': 'Sim',
            'plan_id': '0ee07da5-3de6-4973-9a4f-2ea3de215c01'  # Silver plan
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f'✅ Created user: {result["user"]["email"]}')

        # Simulate frontend calling getUserDetails API
        mock_user = Mock()
        api_response = get_user_details(user_id=user_id, current_user=mock_user, db=SessionLocal())

        print(f'\\n📡 API Response received by frontend:')
        print(json.dumps(api_response, indent=2, ensure_ascii=False, default=str))

        # Simulate what the frontend displays
        print(f'\\n📱 What the frontend should display:')

        # User info
        user_info = api_response.get('user', {})
        print(f'👤 User: {user_info.get("name")} ({user_info.get("email")})')

        # Membership info
        membership = api_response.get('membership')
        if membership:
            end_date = membership.get('end_date')
            if end_date:
                end_date_display = f'Ends on: {end_date}'
            else:
                end_date_display = 'Ends on: N/A'
            print(f'🎫 Membership: {membership.get("plan_name")} ({membership.get("status")})')
            print(f'   {end_date_display}')
        else:
            print('🎫 Membership: Not subscribed')

        # Points info - THIS IS THE CRITICAL PART
        points = api_response.get('points')
        if points:
            current_balance = points.get('current_balance', 0)
            total_earned = points.get('total_earned', 0)
            print(f'⭐ Loyalty Points: {current_balance} PTS')
            print(f'   Total Earned Lifetime: {total_earned} PTS')

            if current_balance > 0:
                print('✅ SUCCESS: Points are showing correctly!')
            else:
                print('❌ FAILURE: Points showing as 0')
                return False
        else:
            print('❌ FAILURE: No points data in API response')
            return False

        # Wallet info
        wallet = api_response.get('wallet')
        if wallet:
            print(f'💰 Wallet: {wallet.get("balance")} {wallet.get("currency")}')

        print(f'\\n🎯 Frontend simulation completed successfully!')
        print(f'Points should appear as: {points.get("current_balance")} PTS')
        return True

    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simulate_frontend_experience()
    print(f'\\n🎯 Simulation Result: {"SUCCESS" if success else "FAILED"}')

    if success:
        print('\\n✅ The backend is working correctly.')
        print('If the frontend still shows 0 points, the issue is on the frontend side:')
        print('1. Restart the frontend development server')
        print('2. Clear browser cache')
        print('3. Check browser network tab for API call errors')
        print('4. Verify the frontend is calling the correct API endpoint')
    else:
        print('\\n❌ The backend has an issue that needs to be fixed.')

    sys.exit(0 if success else 1)

