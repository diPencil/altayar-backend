from database.base import SessionLocal
from modules.users.models import User
from modules.cashback.models import CashbackRecord
from modules.points.models import PointsBalance
from modules.wallet.models import WalletTransaction

def debug_user_balances(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User not found: {email}")
            return

        print(f"👤 User: {user.first_name} {user.last_name} (ID: {user.id})")
        
        # Check Points
        points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == user.id).first()
        if points_balance:
            print(f"✅ Points Balance: {points_balance.current_balance} (Total Earned: {points_balance.total_earned})")
        else:
            print("❌ No Points Balance found")

        # Check Cashback Records
        cashback_records = db.query(CashbackRecord).filter(CashbackRecord.user_id == user.id).all()
        print(f"💰 Cashback Records: {len(cashback_records)}")
        for r in cashback_records:
            print(f"   - {r.created_at} | Status: {r.status} | Amount: {r.cashback_amount} | Type: {r.reference_type}")

        # Check Wallet
        wallet_txs = db.query(WalletTransaction).filter(WalletTransaction.user_id == user.id).all()
        wallet_balance = 0
        if wallet_txs:
             # Calculate balance from transactions if not stored directly on user/wallet model
             # Assuming wallet balance is sum of transactions or last transaction balance
             last_tx = sorted(wallet_txs, key=lambda x: x.created_at, reverse=True)[0]
             wallet_balance = last_tx.balance_after
        
        print(f"💳 Wallet Balance (from last tx): {wallet_balance}")
        print(f"   Total Transactions: {len(wallet_txs)}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_user_balances("test1@test1.com")
