"""
Direct SQL script to add initial_points column to membership_plans table
This bypasses migration issues and adds the column directly
"""

import sqlite3
import os

# Path to your database
DB_PATH = os.path.join(os.path.dirname(__file__), 'altayar.db')

def add_initial_points_column():
    """Add initial_points column to membership_plans table if it doesn't exist"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(membership_plans)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'initial_points' in columns:
            print("✅ Column 'initial_points' already exists in membership_plans table")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE membership_plans 
                ADD COLUMN initial_points INTEGER NOT NULL DEFAULT 0
            """)
            conn.commit()
            print("✅ Successfully added 'initial_points' column to membership_plans table")
        
        # Show current structure
        cursor.execute("PRAGMA table_info(membership_plans)")
        print("\n📋 Current membership_plans table structure:")
        for column in cursor.fetchall():
            print(f"  - {column[1]} ({column[2]})")
            
    except sqlite3.Error as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_initial_points_column()
