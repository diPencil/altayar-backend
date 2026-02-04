
import sqlite3
import os

# CORRECT DATABASE PATH from settings.py
DB_PATH = "d:/Development/altayar/MobileApp/backend/altayarvip.db"

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    # Try alternate path just in case
    DB_PATH = "d:/Development/altayar/MobileApp/backend/altayar.db"
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# The default plans I added
DEFAULT_PLANS = ['BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'VIP', 'DIAMOND']

try:
    print(f"Opening database: {DB_PATH}")
    
    # Check current count
    cursor.execute("SELECT count(*) FROM membership_plans")
    total_before = cursor.fetchone()[0]
    print(f"Total plans before: {total_before}")

    # Delete only default plans
    placeholders = ','.join(['?'] * len(DEFAULT_PLANS))
    query = f"DELETE FROM membership_plans WHERE tier_code IN ({placeholders})"
    
    cursor.execute(query, DEFAULT_PLANS)
    deleted_count = cursor.rowcount
    conn.commit()
    
    print(f"✅ Deleted {deleted_count} default plans ({', '.join(DEFAULT_PLANS)})")
    
    # Check count after
    cursor.execute("SELECT count(*) FROM membership_plans")
    total_after = cursor.fetchone()[0]
    print(f"Remaining plans: {total_after}")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    conn.close()
