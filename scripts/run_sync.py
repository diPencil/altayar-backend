import sqlite3
import os

db_path = "altayarvip.db"
sql_path = "sync_branding.sql"

if not os.path.exists(db_path):
    print(f"❌ DB not found at {db_path}")
    exit(1)

with open(sql_path, 'r', encoding='utf-8') as f:
    sql = f.read()

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(sql)
    conn.commit()
    print("✅ Database branding and IDs synchronized via SQL successfully!")
    
    # Verify
    cursor.execute("SELECT email, first_name, membership_id_display FROM users WHERE role='ADMIN'")
    admin = cursor.fetchone()
    if admin:
        print(f"📊 Verification: {admin[0]} -> Name: {admin[1]}, ID: {admin[2]}")
        
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
