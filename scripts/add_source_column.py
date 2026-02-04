import sqlite3
import os

DB_PATH = "altayarvip.db"

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(offers)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "offer_source" in columns:
            print("Column 'offer_source' already exists.")
        else:
            print("Adding 'offer_source' column...")
            cursor.execute("ALTER TABLE offers ADD COLUMN offer_source VARCHAR(20) DEFAULT 'ADMIN'")
            conn.commit()
            print("Column added successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
