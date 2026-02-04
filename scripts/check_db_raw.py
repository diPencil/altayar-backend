import sqlite3
import os

db_path = 'd:/Development/altayar/MobileApp/backend/altayarvip.db'

print(f"Checking database at: {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()

def print_table_info(table_name):
    print(f"\n--- Table: {table_name} ---")
    try:
        c.execute(f"PRAGMA table_info({table_name})")
        cols = c.fetchall()
        for col in cols:
            print(f"  {col[1]} ({col[2]})")
            
        c.execute(f"SELECT count(*) FROM {table_name}")
        count = c.fetchone()[0]
        print(f"  Row Count: {count}")
        
        if count > 0:
            print("  First 5 rows:")
            c.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = c.fetchall()
            for row in rows:
                print(f"    {row}")
    except Exception as e:
        print(f"  Error: {e}")

print_table_info('membership_subscriptions')
print_table_info('users')
print_table_info('membership_plans')

conn.close()
