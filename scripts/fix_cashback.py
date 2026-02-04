import sys
import os

sys.path.append(os.getcwd())

try:
    from database.base import SessionLocal
    from modules.users.models import User
    from modules.cashback.models import CashbackRecord, CashbackStatus
    from modules.wallet.models import WalletTransaction
    from modules.wallet.service import WalletService
    import uuid
    from datetime import datetime

    def fix_cashback(email: str):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                print(f"User not found: {email}")
                return

            print(f"Fixing cashback for user: {user.first_name} (ID: {user.id})")
            
            # Find APPROVED records
            records = db.query(CashbackRecord).filter(
                CashbackRecord.user_id == user.id,
                CashbackRecord.status == CashbackStatus.APPROVED
            ).all()

            print(f"Found {len(records)} APPROVED records.")

            for r in records:
                print(f"Processing record {r.id}: {r.cashback_amount} USD")
                
                # Check if wallet transaction already exists?
                if r.wallet_transaction_id:
                     print("   Record already has wallet tx id? weird.")
                
                # Credit to wallet MANUAL
                wallet_service = WalletService(db)
                transaction = wallet_service.add_cashback(
                    user_id=r.user_id,
                    amount=r.cashback_amount,
                    reference_type="CASHBACK_FIX",
                    reference_id=str(r.id),
                    description_en=f"Cashback Release (Fix)",
                    description_ar=f"إفراج عن الكاش باك"
                )
                
                # Update status
                r.status = CashbackStatus.CREDITED
                r.credited_at = datetime.utcnow()
                r.wallet_transaction_id = transaction.id
                
                print(f"   updated to CREDITED. Wallet Tx: {transaction.id}")

            db.commit()
            print("Done committing changes.")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()

    if __name__ == "__main__":
        fix_cashback("test1@test1.com")

except Exception as e:
    print(f"Import Error: {e}")
