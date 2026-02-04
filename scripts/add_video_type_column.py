"""
Migration script to add video_type column to reels table
Run this script to update the database schema
"""
import sqlite3
import os
import logging
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_video_type_column():
    """
    Add video_type column to reels table if it doesn't exist.
    """
    # Extract database path from DATABASE_URL
    # Format: sqlite:///path/to/database.db
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
    elif db_url.startswith('sqlite://'):
        db_path = db_url.replace('sqlite://', '')
    else:
        logger.error(f"Unsupported database URL format: {db_url}")
        return False
    
    # Handle absolute paths
    if not os.path.isabs(db_path):
        # If relative path, make it relative to backend directory
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        db_path = os.path.join(backend_dir, db_path)
    
    logger.info(f"Connecting to database: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(reels)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'video_type' in columns:
            logger.info("✅ Column 'video_type' already exists in reels table")
            conn.close()
            return True
        
        logger.info("Adding 'video_type' column to reels table...")
        
        # Add the column with default value 'URL' for existing rows
        cursor.execute("""
            ALTER TABLE reels 
            ADD COLUMN video_type VARCHAR(50) NOT NULL DEFAULT 'URL'
        """)
        
        # Update existing rows to have 'URL' as default (should already be set by DEFAULT, but be safe)
        cursor.execute("""
            UPDATE reels 
            SET video_type = 'URL' 
            WHERE video_type IS NULL OR video_type = ''
        """)
        
        conn.commit()
        logger.info("✅ Successfully added 'video_type' column to reels table")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(reels)")
        columns_after = [column[1] for column in cursor.fetchall()]
        if 'video_type' in columns_after:
            logger.info("✅ Verification: Column 'video_type' is now in the table")
        else:
            logger.error("❌ Verification failed: Column 'video_type' not found after migration")
            conn.close()
            return False
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ SQLite error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Migration: Adding video_type column to reels table")
    logger.info("=" * 50)
    
    success = add_video_type_column()
    
    if success:
        logger.info("=" * 50)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 50)
    else:
        logger.error("=" * 50)
        logger.error("❌ Migration failed!")
        logger.error("=" * 50)
        exit(1)

