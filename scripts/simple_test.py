#!/usr/bin/env python3
"""
Simple test for user integration service
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

print('🧪 Testing User Integration Service...')

db = SessionLocal()
try:
    service = UserIntegrationService(db)

    # Test stats
    stats = service.get_membership_stats()
    print(f'✅ Stats loaded: {stats["total_members"]} members, {stats["active_plans"]} plans')

    # Test user creation without membership
    user_data = {
        'email': f'test_{uuid.uuid4().hex[:8]}@example.com',
        'username': f'testuser_{uuid.uuid4().hex[:8]}',
        'password': 'TestPass123',
        'first_name': 'Test',
        'last_name': 'User'
    }

    result = service.create_user_with_membership(user_data, created_by_admin=True)
    print(f'✅ User created successfully: {result["user"]["email"]}')

    print('🎉 Integration service test PASSED!')

except Exception as e:
    print(f'❌ Test failed: {str(e)}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
