import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "d:/Development/altayar/MobileApp/backend/altayarvip.db"

def add_creator_column():
    conn = None
    try:
        logger.info("==================================================")
        logger.info("Migration: Adding created_by_user_id column to reels table")
        logger.info("==================================================")
        logger.info(f"Connecting to database: {DATABASE_URL}")
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(reels)")
        columns = [col[1] for col in cursor.fetchall()]

        if "created_by_user_id" not in columns:
            logger.info("Adding 'created_by_user_id' column to reels table...")
            cursor.execute("ALTER TABLE reels ADD COLUMN created_by_user_id VARCHAR(36)")
            conn.commit()
            logger.info("✅ Successfully added 'created_by_user_id' column to reels table")

            # Get first admin user ID to assign to existing reels
            cursor.execute("SELECT id FROM users WHERE role = 'ADMIN' OR role = 'SUPER_ADMIN' LIMIT 1")
            admin_user = cursor.fetchone()
            
            if admin_user:
                admin_id = admin_user[0]
                logger.info(f"Updating existing reels to assign to admin user: {admin_id}")
                cursor.execute("""
                    UPDATE reels
                    SET created_by_user_id = ?
                    WHERE created_by_user_id IS NULL
                """, (admin_id,))
                conn.commit()
                logger.info("✅ Existing reels updated with creator")
            else:
                logger.warning("⚠️ No admin user found. Existing reels will have NULL creator.")
        else:
            logger.info("Column 'created_by_user_id' already exists in reels table. Skipping.")

        # Verification
        cursor.execute("PRAGMA table_info(reels)")
        columns_after = [col[1] for col in cursor.fetchall()]
        if "created_by_user_id" in columns_after:
            logger.info("✅ Verification: Column 'created_by_user_id' is now in the table")
        else:
            logger.error("❌ Verification FAILED: Column 'created_by_user_id' is NOT in the table")

        logger.info("==================================================")
        logger.info("✅ Migration completed successfully!")
        logger.info("==================================================")
        return True

    except sqlite3.OperationalError as e:
        logger.error(f"❌ SQLite Operational Error during migration: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred during migration: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_creator_column()

