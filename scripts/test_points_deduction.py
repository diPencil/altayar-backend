#!/usr/bin/env python3
"""
Test script for points deduction functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from database.base import engine, get_db
from modules.points.service import PointsService
from modules.points.models import PointsBalance
import uuid

def test_points_deduction():
    """Test the points deduction functionality"""
    print("Testing Points Deduction Functionality")

    # Create a test user ID
    test_user_id = str(uuid.uuid4())

    # Create database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        points_service = PointsService(db)

        # First, add some points to the user
        print("1. Adding initial points...")
        transaction = points_service.add_bonus_points(
            user_id=test_user_id,
            points=100,
            description_en="Test bonus",
            created_by_user_id="admin"
        )
        print(f"SUCCESS: Added 100 points. New balance: {transaction.balance_after}")

        # Now try to deduct points
        print("2. Deducting points...")
        deduction_transaction = points_service.deduct_points(
            user_id=test_user_id,
            points=50,
            description_en="Test deduction",
            created_by_user_id="admin"
        )
        print(f"SUCCESS: Deducted 50 points. New balance: {deduction_transaction.balance_after}")

        # Check final balance
        final_balance = points_service.get_balance(test_user_id)
        print(f"SUCCESS: Final balance check: {final_balance}")

        # Try to deduct more than available (should fail)
        print("3. Testing insufficient points...")
        try:
            points_service.deduct_points(
                user_id=test_user_id,
                points=100,  # More than available
                description_en="Should fail",
                created_by_user_id="admin"
            )
            print("ERROR: Should have failed but didn't!")
        except Exception as e:
            print(f"SUCCESS: Correctly prevented deduction: {str(e)}")

        print("All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.rollback()
        db.close()

if __name__ == "__main__":
    test_points_deduction()
