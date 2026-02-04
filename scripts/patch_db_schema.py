import sqlite3
import os

DB_PATH = "backend/altayarvip.db"

def patch_database():
    if not os.path.exists(DB_PATH):
        print("Database not found. It will be created fresh by the app.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get existing columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Existing columns: {columns}")
        
        # New columns to add
        new_columns = {
            "username": "TEXT UNIQUE",
            "gender": "TEXT",
            "country": "TEXT",
            "birthdate": "DATETIME",
            "membership_id_display": "TEXT"
        }
        
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                print(f"Adding column: {col_name}...")
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added {col_name}")
                except Exception as e:
                    print(f"❌ Failed to add {col_name}: {e}")
            else:
                print(f"Column {col_name} already exists.")
                
        conn.commit()
        print("Database patch completed successfully.")
        
    except Exception as e:
        print(f"Error patching database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    patch_database()
