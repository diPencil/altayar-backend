"""
Database Schema Update: Employee-User Assignment & Targeted Offers
Adds necessary columns to support:
1. Assigning customers to employees
2. Targeted offers with creator tracking
"""

from sqlalchemy import create_engine, text
from database.base import Base, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_schema():
    """Add new columns to users and offers tables"""
    
    with engine.connect() as conn:
        try:
            # ============ USERS TABLE ============
            logger.info("Updating users table...")
            
            # Add assigned_employee_id column
            try:
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN assigned_employee_id VARCHAR(36)
                """))
                logger.info("✅ Added assigned_employee_id to users table")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("⚠️ assigned_employee_id already exists in users table")
                else:
                    raise
            
            # Create index for performance
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_assigned_employee 
                    ON users(assigned_employee_id)
                """))
                logger.info("✅ Created index on assigned_employee_id")
            except Exception as e:
                logger.warning(f"⚠️ Index creation skipped: {e}")
            
            # ============ OFFERS TABLE ============
            logger.info("Updating offers table...")
            
            # Add created_by_user_id column
            try:
                conn.execute(text("""
                    ALTER TABLE offers 
                    ADD COLUMN created_by_user_id VARCHAR(36)
                """))
                logger.info("✅ Added created_by_user_id to offers table")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("⚠️ created_by_user_id already exists in offers table")
                else:
                    raise
            
            # Add target_audience column (ALL, ASSIGNED, SPECIFIC)
            try:
                conn.execute(text("""
                    ALTER TABLE offers 
                    ADD COLUMN target_audience VARCHAR(20) DEFAULT 'ALL'
                """))
                logger.info("✅ Added target_audience to offers table")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("⚠️ target_audience already exists in offers table")
                else:
                    raise
            
            # Add target_user_ids column (JSON array)
            try:
                conn.execute(text("""
                    ALTER TABLE offers 
                    ADD COLUMN target_user_ids TEXT
                """))
                logger.info("✅ Added target_user_ids to offers table")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("⚠️ target_user_ids already exists in offers table")
                else:
                    raise
            
            # Create indexes for performance
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_offers_created_by 
                    ON offers(created_by_user_id)
                """))
                logger.info("✅ Created index on created_by_user_id")
            except Exception as e:
                logger.warning(f"⚠️ Index creation skipped: {e}")
            
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_offers_target_audience 
                    ON offers(target_audience)
                """))
                logger.info("✅ Created index on target_audience")
            except Exception as e:
                logger.warning(f"⚠️ Index creation skipped: {e}")
            
            # ============ BOOKINGS TABLE ============
            logger.info("Checking bookings table...")
            
            # Add offer_id column to link bookings to offers
            try:
                conn.execute(text("""
                    ALTER TABLE bookings 
                    ADD COLUMN offer_id VARCHAR(36)
                """))
                logger.info("✅ Added offer_id to bookings table")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("⚠️ offer_id already exists in bookings table")
                else:
                    raise
            
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_bookings_offer 
                    ON bookings(offer_id)
                """))
                logger.info("✅ Created index on offer_id")
            except Exception as e:
                logger.warning(f"⚠️ Index creation skipped: {e}")
            
            conn.commit()
            logger.info("✅ Schema update completed successfully!")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Schema update failed: {e}")
            raise

if __name__ == "__main__":
    logger.info("Starting schema update for Employee-User Assignment & Targeted Offers...")
    update_schema()
    logger.info("Schema update complete!")
