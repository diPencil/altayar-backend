import sys
import os

# Robust path setup
current_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/utils
backend_dir = os.path.dirname(current_dir) # .../backend
project_root = os.path.dirname(backend_dir) # .../MobileApp

sys.path.append(project_root)
sys.path.append(backend_dir)

print(f"Added paths: {project_root}, {backend_dir}")

try:
    from sqlalchemy.orm import Session
    from decimal import Decimal
    from database.base import SessionLocal
    from modules.wallet.models import Wallet
    from modules.cashback.models import CashbackRecord, CashbackStatus
    from modules.users.models import User
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def fix_wallet_separation():
    db: Session = SessionLocal()
    try:
        # 1. Get User
        user = db.query(User).filter(User.email == "test1@test1.com").first()
        if not user:
            print("User test1@test1.com not found!")
            return

        print(f"User Found: {user.email} (ID: {user.id})")

        # 2. Reset Wallet Balance to 0
        wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
        if wallet:
            print(f"Current Wallet Balance: {wallet.balance}")
            wallet.balance = 0.0
            db.add(wallet)
            print("✅ Wallet Balance Reset to 0.0")
        else:
            print("No wallet found (Unexpected if user logged in).")

        # 3. Verify Cashback Balance
        # Logic: Sum of all CREDITED cashback records.
        # User requested 500 to be cashback.
        # Check existing records.
        cashback_records = db.query(CashbackRecord).filter(
            CashbackRecord.user_id == user.id,
            CashbackRecord.status == CashbackStatus.CREDITED
        ).all()
        
        total_cashback = sum(record.cashback_amount for record in cashback_records)
        print(f"Total Credited Cashback in DB: {total_cashback}")
        
        # If total is 500, we are good.
        # If total is 0 or different, we might need to adjust.
        # Based on previous context, we had a 500 cashback record.
        
        if total_cashback == 500:
             print("✅ Cashback is exactly 500. Perfect.")
        else:
             print(f"⚠️ Cashback is {total_cashback}, expected 500.")
             # If needed, create fix record here? 
             # Let's see the output first, but for now assuming previous steps worked.
             pass

        db.commit()
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_wallet_separation()
