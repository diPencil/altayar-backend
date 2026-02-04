import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from database.base import SessionLocal
    from modules.users.models import User
    from modules.cashback.models import CashbackRecord
    from modules.points.models import PointsBalance
    from modules.wallet.models import WalletTransaction
    from modules.memberships.models import MembershipSubscription

    def debug_user_balances(email: str):
        with open("inner_debug_log.txt", "w", encoding="utf-8") as f:
            def log(msg):
                print(msg)
                f.write(str(msg) + "\n")
                f.flush()

            log(f"Searching for user: {email}")
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    log(f"User not found: {email}")
                    return

                log(f"User Found: {user.first_name} {user.last_name}")
                log(f"   ID: {user.id}")
                # if user.membership:
                #    log(f"   Membership: {user.membership.membership_number} (Display: {user.membership_id_display})")

                log("-" * 30)
                
                # Check Points
                log("checking POINTS...")
                points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == user.id).first()
                if points_balance:
                    log(f"   Points Balance: {points_balance.current_balance}")
                    log(f"   Total Earned: {points_balance.total_earned}")
                else:
                    log("   No Points Balance record found.")

                log("-" * 30)

                # Check Cashback
                log("checking CASHBACK...")
                cashback_records = db.query(CashbackRecord).filter(CashbackRecord.user_id == user.id).all()
                log(f"   Total Records: {len(cashback_records)}")
                
                total_credited = 0
                for r in cashback_records:
                    log(f"   - Amount: {r.cashback_amount} | Status: {r.status} | Type: {r.reference_type}")
                    if str(r.status) == "CashbackStatus.CREDITED" or str(r.status) == "CREDITED":
                        total_credited += r.cashback_amount
                
                log(f"   Calculated CREDITED Total: {total_credited}")

                log("-" * 30)

                # Check Wallet
                log("checking WALLET...")
                wallet_txs = db.query(WalletTransaction).filter(WalletTransaction.user_id == user.id).all()
                log(f"   Total Transactions: {len(wallet_txs)}")
                
                if wallet_txs:
                     last_tx = sorted(wallet_txs, key=lambda x: x.created_at, reverse=True)[0]
                     log(f"   Last Wallet Balance: {last_tx.balance_after} {last_tx.currency}")
                else:
                     log("   No wallet transactions found.")

            except Exception as e:
                log(f"Error querying logic: {e}")
                import traceback
                traceback.print_exc(file=f)
            finally:
                db.close()

    if __name__ == "__main__":
        debug_user_balances("test1@test1.com")

except Exception as e:
    print(f"Import Error: {e}")
    import traceback
    traceback.print_exc()
