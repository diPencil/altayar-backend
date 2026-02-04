#!/usr/bin/env python3
"""
Test script for cashback functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from database.base import engine, get_db
from modules.wallet.service import WalletService
import uuid

def test_cashback_functionality():
    """Test the cashback functionality"""
    print("Testing Cashback Functionality")

    # Create a test user ID
    test_user_id = str(uuid.uuid4())

    # Create database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        wallet_service = WalletService(db)

        # First, add some cashback to the user
        print("1. Adding initial cashback...")
        transaction = wallet_service.add_cashback(
            user_id=test_user_id,
            amount=100.50,
            reference_type="TEST_CREDIT",
            reference_id=str(uuid.uuid4()),
            description_en="Test cashback credit"
        )
        print(f"SUCCESS: Added 100.50 EGP cashback. New balance: {transaction.balance_after}")

        # Check current balance
        wallet = wallet_service.get_or_create_wallet(test_user_id)
        print(f"SUCCESS: Current balance: {wallet.balance}")

        # Now try to deduct cashback (withdraw)
        print("2. Deducting cashback...")
        debit_transaction = wallet_service.withdraw(
            user_id=test_user_id,
            amount=25.75,
            reference_type="TEST_DEBIT",
            reference_id=str(uuid.uuid4()),
            description_en="Test cashback debit"
        )
        print(f"SUCCESS: Deducted 25.75 EGP cashback. New balance: {debit_transaction.balance_after}")

        # Check final balance
        final_wallet = wallet_service.get_or_create_wallet(test_user_id)
        print(f"SUCCESS: Final balance check: {final_wallet.balance}")

        # Try to deduct more than available (should fail)
        print("3. Testing insufficient funds...")
        try:
            wallet_service.withdraw(
                user_id=test_user_id,
                amount=1000.00,  # More than available
                reference_type="TEST_OVERDRAFT",
                reference_id=str(uuid.uuid4()),
                description_en="Should fail"
            )
            print("ERROR: Should have failed but didn't!")
        except Exception as e:
            print(f"SUCCESS: Correctly prevented overdraft: {str(e)}")

        print("All cashback tests passed!")

    except Exception as e:
        print(f"ERROR: Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.rollback()
        db.close()

if __name__ == "__main__":
    test_cashback_functionality()
