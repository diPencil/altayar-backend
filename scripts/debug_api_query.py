#!/usr/bin/env python3
"""
Debug the API query to see what's happening
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
from modules.points.models import PointsBalance
from modules.memberships.models import MembershipSubscription, MembershipStatus
from sqlalchemy.orm import joinedload

def debug_api_query():
    """Debug what the API query returns"""

    db = SessionLocal()
    try:
        service = UserIntegrationService(db)

        # Create test user with membership
        user_data = {
            'email': f'debug_query_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'debugquery_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Debug',
            'last_name': 'Query',
            'plan_id': '0ee07da5-3de6-4973-9a4f-2ea3de215c01'
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_email = result['user']['email']
        user_id = result['user']['id']
        print(f'✅ Created user: {user_email}')
        print(f'   User ID: {user_id} (type: {type(user_id)})')

        # Now simulate the get_all_users query
        from modules.users.models import User

        query = db.query(User).options(joinedload(User.subscriptions).joinedload(MembershipSubscription.plan))
        users = query.filter(User.email == user_email).all()

        print(f'\\n🔍 Found {len(users)} users matching email')

        for u in users:
            print(f'\\n👤 User: {u.email}')
            print(f'   ID: {u.id} (type: {type(u.id)})')

            # Find latest subscription
            latest_sub = None
            if u.subscriptions:
                sorted_subs = sorted(u.subscriptions, key=lambda s: s.created_at, reverse=True)
                latest_sub = sorted_subs[0] if sorted_subs else None

            print(f'   Subscriptions count: {len(u.subscriptions) if u.subscriptions else 0}')

            if latest_sub:
                print(f'   Latest subscription: {latest_sub.membership_number}')
                print(f'   Status: {latest_sub.status}')
                print(f'   Expiry: {latest_sub.expiry_date}')

            # Query points balance
            print(f'\\n🔍 Querying points for user_id: {str(u.id)}')
            points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == str(u.id)).first()

            print(f'   Points balance found: {points_balance is not None}')
            if points_balance:
                print(f'   Current balance: {points_balance.current_balance}')
                print(f'   Total earned: {points_balance.total_earned}')
            else:
                print('   ❌ No points balance found!')

                # Try different query formats
                print('   Trying different query formats:')
                pb1 = db.query(PointsBalance).filter(PointsBalance.user_id == u.id).first()
                print(f'   Without str(): {pb1 is not None}')

                if isinstance(u.id, str):
                    pb2 = db.query(PointsBalance).filter(PointsBalance.user_id == uuid.UUID(u.id)).first()
                    print(f'   As UUID: {pb2 is not None}')

                # Check what user_id values exist in points_balances
                all_pb = db.query(PointsBalance).limit(5).all()
                print(f'   Sample existing user_ids in points_balances:')
                for pb in all_pb:
                    print(f'     {pb.user_id} (type: {type(pb.user_id)})')

        return True

    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = debug_api_query()
    print(f'\\n🎉 Debug {"PASSED" if success else "FAILED"}!')
    sys.exit(0 if success else 1)
