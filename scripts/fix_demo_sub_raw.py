import sqlite3
import os
import uuid
import datetime

db_path = 'd:/Development/altayar/MobileApp/backend/altayarvip.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    print("\n--- Manually Adding Subscription (Raw SQL) ---")
    
    # 1. Get User ID
    c.execute("SELECT id FROM users WHERE email = 'demo@altayar.com'")
    user_row = c.fetchone()
    if not user_row:
        print("User demo@altayar.com not found!")
        exit(1)
    user_id = user_row[0]
    print(f"User ID: {user_id}")

    # 2. Get Plan ID
    c.execute("SELECT id, price FROM membership_plans LIMIT 1")
    plan_row = c.fetchone()
    if not plan_row:
        print("No plans found!")
        exit(1)
    plan_id, price = plan_row
    print(f"Plan ID: {plan_id}, Price: {price}")
    
    # 3. Insert Subscription
    sub_id = str(uuid.uuid4())
    mem_num = f"MEM-{uuid.uuid4().hex[:8].upper()}"
    start_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    # Add 1 year
    end_date = (datetime.datetime.utcnow() + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    
    insert_sql = """
    INSERT INTO membership_subscriptions 
    (id, user_id, plan_id, membership_number, start_date, expiry_date, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', datetime('now'), datetime('now'))
    """
    
    c.execute(insert_sql, (sub_id, user_id, plan_id, mem_num, start_date, end_date))
    conn.commit()
    print("SUCCESS: Subscription inserted!")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
