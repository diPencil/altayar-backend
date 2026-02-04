"""
Database Migration: Fix Schema Issues
- Fix tier_post_comments table (currently has 0 columns)
- Add cashback_balance column to users table
- Add offer_ratings table for offer star ratings
"""
import sqlite3
from datetime import datetime

def migrate():
    conn = sqlite3.connect('altayarvip.db')
    cursor = conn.cursor()
    
    print("=" * 60)
    print("DATABASE MIGRATION - FIXING SCHEMA ISSUES")
    print("=" * 60)
    
    # 1. Fix tier_post_comments table
    print("\n[1/3] Fixing tier_post_comments table...")
    try:
        # Drop broken table if exists
        cursor.execute("DROP TABLE IF EXISTS tier_post_comments")
        
        # Recreate with proper structure
        cursor.execute("""
            CREATE TABLE tier_post_comments (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES tier_posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        print("✅ tier_post_comments table recreated successfully")
    except Exception as e:
        print(f"❌ Error fixing tier_post_comments: {e}")
        conn.rollback()
    
    # 2. Add cashback_balance to users table
    print("\n[2/3] Adding cashback_balance column to users table...")
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'cashback_balance' not in columns:
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN cashback_balance REAL DEFAULT 0.0
            """)
            conn.commit()
            print("✅ cashback_balance column added successfully")
        else:
            print("ℹ️  cashback_balance column already exists")
    except Exception as e:
        print(f"❌ Error adding cashback_balance: {e}")
        conn.rollback()

    # 3. Add offer_ratings table
    print("\n[3/3] Ensuring offer_ratings table exists...")
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='offer_ratings'")
        exists = cursor.fetchone() is not None

        if not exists:
            cursor.execute("""
                CREATE TABLE offer_ratings (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    offer_id TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
                    UNIQUE (user_id, offer_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_offer_ratings_user_id ON offer_ratings(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_offer_ratings_offer_id ON offer_ratings(offer_id)")
            conn.commit()
            print("✅ offer_ratings table created successfully")
        else:
            print("ℹ️  offer_ratings table already exists")
    except Exception as e:
        print(f"❌ Error creating offer_ratings table: {e}")
        conn.rollback()
    
    # Verify changes
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    # Check tier_post_comments
    cursor.execute("PRAGMA table_info(tier_post_comments)")
    columns = cursor.fetchall()
    print(f"\n✓ tier_post_comments: {len(columns)} columns")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Check users table
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    has_cashback = any(col[1] == 'cashback_balance' for col in columns)
    if has_cashback:
        print(f"\n✓ users table: cashback_balance column exists")
    else:
        print(f"\n✗ users table: cashback_balance column MISSING")

    # Check offer_ratings table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='offer_ratings'")
    has_offer_ratings = cursor.fetchone() is not None
    if has_offer_ratings:
        cursor.execute("PRAGMA table_info(offer_ratings)")
        cols = cursor.fetchall()
        print(f"\n✓ offer_ratings: {len(cols)} columns")
        for col in cols:
            print(f"  - {col[1]} ({col[2]})")
    else:
        print(f"\n✗ offer_ratings table MISSING")
    
    conn.close()
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    migrate()
