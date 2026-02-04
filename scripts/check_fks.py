import sqlite3
import os

db_path = 'd:/Development/altayar/MobileApp/backend/altayarvip.db'

print(f"Checking FKs in: {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    print("\n--- Validating Subscription FKs ---")
    c.execute("SELECT id, user_id, plan_id FROM membership_subscriptions LIMIT 1")
    sub = c.fetchone()
    
    if sub:
        print(f"Subscription: {sub}")
        sub_id, user_id, plan_id = sub
        
        # Check User
        c.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        print(f"  -> Linked User: {user if user else 'MISSING'}")
        
        # Check Plan
        c.execute("SELECT id, tier_name_en FROM membership_plans WHERE id = ?", (plan_id,))
        plan = c.fetchone()
        print(f"  -> Linked Plan: {plan if plan else 'MISSING'}")
        
    else:
        print("No subscriptions found.")

except Exception as e:
    print(f"Error: {e}")

conn.close()
