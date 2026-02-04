import sqlite3

def add_column():
    conn = sqlite3.connect('backend/altayarvip.db')
    cursor = conn.cursor()
    
    try:
        print("Adding 'username' column...")
        cursor.execute("ALTER TABLE users ADD COLUMN username VARCHAR(100)")
        print("✅ Column 'username' added successfully!")
    except Exception as e:
        print(f"⚠️ Error (column might already exist): {e}")

    # Verify
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "username" in columns:
        print("✅ Verification: 'username' column exists.")
    else:
        print("❌ Verification FAILED: 'username' column missing.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_column()
