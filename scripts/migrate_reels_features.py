"""
Add creator and comment features to reels

This migration adds:
1. created_by_user_id to reels table
2. parent_id and likes_count to reel_interactions table
"""

import sqlite3
import os

# Get database path
db_path = os.path.join(os.path.dirname(__file__), '..', 'altayarvip.db')

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add created_by_user_id to reels table
        print("Adding created_by_user_id to reels table...")
        try:
            cursor.execute("""
                ALTER TABLE reels 
                ADD COLUMN created_by_user_id VARCHAR(36)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_reels_created_by_user_id 
                ON reels(created_by_user_id)
            """)
            print("✅ Added created_by_user_id column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️  created_by_user_id column already exists")
            else:
                raise
        
        # Add parent_id to reel_interactions table
        print("\nAdding parent_id to reel_interactions table...")
        try:
            cursor.execute("""
                ALTER TABLE reel_interactions 
                ADD COLUMN parent_id VARCHAR(36)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_reel_interactions_parent_id 
                ON reel_interactions(parent_id)
            """)
            print("✅ Added parent_id column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️  parent_id column already exists")
            else:
                raise
        
        # Add likes_count to reel_interactions table
        print("\nAdding likes_count to reel_interactions table...")
        try:
            cursor.execute("""
                ALTER TABLE reel_interactions 
                ADD COLUMN likes_count INTEGER DEFAULT 0
            """)
            print("✅ Added likes_count column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️  likes_count column already exists")
            else:
                raise
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
