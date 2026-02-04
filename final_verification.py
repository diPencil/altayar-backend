"""
Final System Verification
Confirms all database schema issues are resolved
"""
import sqlite3

def final_check():
    conn = sqlite3.connect('altayarvip.db')
    cursor = conn.cursor()
    
    print("=" * 70)
    print("🔍 FINAL SYSTEM VERIFICATION")
    print("=" * 70)
    
    all_good = True
    
    # 1. Check tier_post_comments
    print("\n[1/4] Checking tier_post_comments table...")
    cursor.execute("PRAGMA table_info(tier_post_comments)")
    columns = cursor.fetchall()
    if len(columns) >= 8:
        print(f"✅ PASS: tier_post_comments has {len(columns)} columns")
        required_cols = ['id', 'post_id', 'user_id', 'content', 'status']
        col_names = [col[1] for col in columns]
        for req_col in required_cols:
            if req_col in col_names:
                print(f"   ✓ {req_col}")
            else:
                print(f"   ✗ {req_col} MISSING")
                all_good = False
    else:
        print(f"❌ FAIL: tier_post_comments has only {len(columns)} columns")
        all_good = False
    
    # 2. Check users.cashback_balance
    print("\n[2/4] Checking users.cashback_balance column...")
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    col_names = [col[1] for col in columns]
    if 'cashback_balance' in col_names:
        print("✅ PASS: cashback_balance column exists")
    else:
        print("❌ FAIL: cashback_balance column NOT FOUND")
        all_good = False
    
    # 3. Check notifications table
    print("\n[3/4] Checking notifications table...")
    cursor.execute("PRAGMA table_info(notifications)")
    columns = cursor.fetchall()
    if len(columns) > 0:
        print(f"✅ PASS: notifications table exists with {len(columns)} columns")
    else:
        print("❌ FAIL: notifications table has issues")
        all_good = False
    
    # 4. Check points_balances table
    print("\n[4/4] Checking points_balances table...")
    cursor.execute("PRAGMA table_info(points_balances)")
    columns = cursor.fetchall()
    if len(columns) > 0:
        print(f"✅ PASS: points_balances table exists with {len(columns)} columns")
    else:
        print("❌ FAIL: points_balances table has issues")
        all_good = False
    
    conn.close()
    
    print("\n" + "=" * 70)
    if all_good:
        print("🎉 ALL CHECKS PASSED - SYSTEM READY!")
    else:
        print("⚠️  SOME CHECKS FAILED - REVIEW REQUIRED")
    print("=" * 70)
    
    return all_good

if __name__ == "__main__":
    final_check()
