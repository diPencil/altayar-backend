#!/usr/bin/env python3
"""
Comprehensive test script for User-Membership-Points integration.
Tests the complete flow to ensure all components work together atomically.
"""

import os
import sys
import json
import uuid
from datetime import datetime

# Setup environment
os.environ["DATABASE_URL"] = "sqlite:///d:/Development/altayar/MobileApp/backend/altayarvip.db"
os.environ["JWT_SECRET_KEY"] = "dummy"
os.environ["SECRET_KEY"] = "dummy"
os.environ["FAWATERK_API_KEY"] = "dummy"
os.environ["FAWATERK_VENDOR_KEY"] = "dummy"

sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import all models first
import modules

from database.base import SessionLocal, engine
from shared.user_integration_service import UserIntegrationService
from modules.users.models import User, UserRole, UserStatus
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipStatus
from modules.points.models import PointsBalance, PointsTransaction
from modules.wallet.models import Wallet
from sqlalchemy.orm import Session


def test_user_creation_with_membership():
    """Test creating a user with membership and points"""
    print("🧪 Testing User Creation with Membership Integration...")

    db = SessionLocal()
    try:
        integration_service = UserIntegrationService(db)

        # Test data
        user_data = {
            "email": f"test_integration_{uuid.uuid4().hex[:8]}@example.com",
            "username": f"testuser_{uuid.uuid4().hex[:8]}",
            "password": "TestPass123",
            "first_name": "Test",
            "last_name": "Integration",
            "plan_id": None  # Will test without plan first
        }

        # Create user without membership
        result = integration_service.create_user_with_membership(user_data, created_by_admin=True)
        print(f"✅ User created: {result['user']['email']}")

        user_id = result['user']['id']

        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None, "User should exist"
        assert user.status == UserStatus.ACTIVE, "User should be active"

        # Verify points balance exists
        points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == user_id).first()
        assert points_balance is not None, "Points balance should exist"
        assert points_balance.current_balance == 0, "Initial balance should be 0"

        # Verify wallet exists
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        assert wallet is not None, "Wallet should exist"
        assert wallet.balance == 0.0, "Initial wallet balance should be 0"

        print("✅ Basic user creation verified")

        # Now test with membership plan
        plan = db.query(MembershipPlan).first()
        if plan:
            print(f"🎯 Testing with membership plan: {plan.tier_name_en}")

            user_data_with_plan = {
                "email": f"test_with_plan_{uuid.uuid4().hex[:8]}@example.com",
                "username": f"testplan_{uuid.uuid4().hex[:8]}",
                "password": "TestPass123",
                "first_name": "Test",
                "last_name": "WithPlan",
                "plan_id": str(plan.id)
            }

            result_with_plan = integration_service.create_user_with_membership(user_data_with_plan, created_by_admin=True)
            print(f"✅ User with membership created: {result_with_plan['user']['email']}")

            user_id_with_plan = result_with_plan['user']['id']

            # Verify subscription exists
            subscription = db.query(MembershipSubscription).filter(
                MembershipSubscription.user_id == user_id_with_plan,
                MembershipSubscription.status == MembershipStatus.ACTIVE
            ).first()

            assert subscription is not None, "Subscription should exist"
            assert str(subscription.plan_id) == str(plan.id), "Subscription should link to correct plan"

            # Verify points were awarded if plan has perks
            if plan.perks and result_with_plan.get('points_awarded', 0) > 0:
                points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == user_id_with_plan).first()
                assert points_balance.current_balance > 0, "Points should have been awarded"

                # Check points transaction
                transaction = db.query(PointsTransaction).filter(
                    PointsTransaction.user_id == user_id_with_plan,
                    PointsTransaction.transaction_type == "BONUS"
                ).first()
                assert transaction is not None, "Points transaction should exist"

            print("✅ User with membership creation verified")

        print("🎉 User creation integration test PASSED")
        return True

    except Exception as e:
        print(f"❌ User creation test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_user_update_with_membership_change():
    """Test updating a user and changing their membership"""
    print("🧪 Testing User Update with Membership Change...")

    db = SessionLocal()
    try:
        integration_service = UserIntegrationService(db)

        # Create a test user first
        user_data = {
            "email": f"update_test_{uuid.uuid4().hex[:8]}@example.com",
            "username": f"updatetest_{uuid.uuid4().hex[:8]}",
            "password": "TestPass123",
            "first_name": "Update",
            "last_name": "Test"
        }

        result = integration_service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f"✅ Test user created: {result['user']['email']}")

        # Get available plans
        plans = db.query(MembershipPlan).limit(2).all()
        if len(plans) >= 2:
            plan1, plan2 = plans[0], plans[1]

            # Assign first plan
            update_data = {"plan_id": str(plan1.id)}
            result = integration_service.update_user_with_membership(user_id, update_data)
            print(f"✅ Assigned first plan: {plan1.tier_name_en}")

            # Verify subscription
            sub1 = db.query(MembershipSubscription).filter(
                MembershipSubscription.user_id == user_id,
                MembershipSubscription.status == MembershipStatus.ACTIVE
            ).first()
            assert sub1 is not None, "First subscription should exist"
            assert str(sub1.plan_id) == str(plan1.id), "Should be linked to first plan"

            # Change to second plan
            update_data = {"plan_id": str(plan2.id)}
            result = integration_service.update_user_with_membership(user_id, update_data)
            print(f"✅ Changed to second plan: {plan2.tier_name_en}")

            # Verify old subscription is cancelled
            cancelled_sub = db.query(MembershipSubscription).filter(
                MembershipSubscription.user_id == user_id,
                MembershipSubscription.status == MembershipStatus.CANCELLED
            ).first()
            assert cancelled_sub is not None, "Old subscription should be cancelled"

            # Verify new subscription exists
            sub2 = db.query(MembershipSubscription).filter(
                MembershipSubscription.user_id == user_id,
                MembershipSubscription.status == MembershipStatus.ACTIVE
            ).first()
            assert sub2 is not None, "New subscription should exist"
            assert str(sub2.plan_id) == str(plan2.id), "Should be linked to second plan"

            print("✅ Membership change test verified")

        # Test profile update
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "gender": "MALE"
        }
        result = integration_service.update_user_with_membership(user_id, update_data)
        print("✅ Profile update verified")

        user = db.query(User).filter(User.id == user_id).first()
        assert user.first_name == "Updated", "First name should be updated"
        assert user.last_name == "Name", "Last name should be updated"

        print("🎉 User update integration test PASSED")
        return True

    except Exception as e:
        print(f"❌ User update test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_membership_stats():
    """Test membership statistics calculation"""
    print("🧪 Testing Membership Statistics...")

    db = SessionLocal()
    try:
        integration_service = UserIntegrationService(db)

        stats = integration_service.get_membership_stats()
        print(f"📊 Stats: {stats['total_members']} members, {stats['active_plans']} plans")

        # Verify stats are reasonable
        assert isinstance(stats['total_members'], int), "Total members should be integer"
        assert isinstance(stats['active_plans'], int), "Active plans should be integer"
        assert isinstance(stats['plans'], list), "Plans should be a list"

        for plan_stat in stats['plans']:
            assert 'user_count' in plan_stat, "Plan stats should include user_count"
            assert isinstance(plan_stat['user_count'], int), "User count should be integer"

        print("✅ Membership statistics test PASSED")
        return True

    except Exception as e:
        print(f"❌ Membership stats test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_transaction_rollback():
    """Test that failed operations properly rollback"""
    print("🧪 Testing Transaction Rollback...")

    db = SessionLocal()
    try:
        integration_service = UserIntegrationService(db)

        # Try to create user with duplicate email
        user_data = {
            "email": "admin@altayar.com",  # This should already exist
            "username": f"rollback_test_{uuid.uuid4().hex[:8]}",
            "password": "TestPass123",
            "first_name": "Rollback",
            "last_name": "Test"
        }

        try:
            integration_service.create_user_with_membership(user_data, created_by_admin=True)
            print("❌ Should have failed with duplicate email")
            return False
        except Exception as e:
            if "already registered" in str(e) or "UNIQUE constraint" in str(e):
                print("✅ Properly rejected duplicate email")
            else:
                raise e

        # Verify no partial data was created
        test_user = db.query(User).filter(User.username == user_data['username']).first()
        assert test_user is None, "User should not exist after failed creation"

        print("✅ Transaction rollback test PASSED")
        return True

    except Exception as e:
        print(f"❌ Transaction rollback test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def run_all_tests():
    """Run all integration tests"""
    print("🚀 Starting User-Membership-Points Integration Tests")
    print("=" * 60)

    tests = [
        test_user_creation_with_membership,
        test_user_update_with_membership_change,
        test_membership_stats,
        test_transaction_rollback
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Empty line between tests
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {str(e)}")
            print()

    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL INTEGRATION TESTS PASSED! ✅")
        return True
    else:
        print("❌ SOME TESTS FAILED! Please review the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
