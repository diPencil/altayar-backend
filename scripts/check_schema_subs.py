import sqlite3
import os

db_path = 'd:/Development/altayar/MobileApp/backend/altayarvip.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print(f"Checking Schema for: membership_subscriptions")
c.execute(f"PRAGMA table_info(membership_subscriptions)")
cols = c.fetchall()
for col in cols:
    print(f"  {col[1]} ({col[2]})")

conn.close()
