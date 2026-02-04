#!/usr/bin/env python3
"""
Script to manually create the notifications table.
Run this after the server starts and creates other tables.
"""

import sqlite3
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def create_notifications_table():
    # Connect to the database
    db_path = 'altayarvip.db'
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found. Please run the server first to create the database.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create the notifications table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS notifications (
            id VARCHAR(36) PRIMARY KEY,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            deleted_at DATETIME,

            -- Notification content
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,

            -- Related entity
            related_entity_id VARCHAR(36),
            related_entity_type VARCHAR(20),

            -- Target audience
            target_role VARCHAR(20) NOT NULL,
            target_user_id VARCHAR(36),

            -- Status
            is_read BOOLEAN DEFAULT 0,
            read_at DATETIME,

            -- Additional metadata
            priority VARCHAR(20) DEFAULT 'NORMAL',
            action_url VARCHAR(500),

            -- Trigger info
            triggered_by_id VARCHAR(36),
            triggered_by_role VARCHAR(20),

            -- Foreign keys
            FOREIGN KEY (target_user_id) REFERENCES users(id),
            FOREIGN KEY (triggered_by_id) REFERENCES users(id)
        );
        """

        # Create indexes
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS ix_notifications_type ON notifications(type);",
            "CREATE INDEX IF NOT EXISTS ix_notifications_target_role ON notifications(target_role);",
            "CREATE INDEX IF NOT EXISTS ix_notifications_target_user_id ON notifications(target_user_id);",
            "CREATE INDEX IF NOT EXISTS ix_notifications_related_entity_id ON notifications(related_entity_id);",
            "CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read);",
            "CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at);",
            "CREATE INDEX IF NOT EXISTS ix_notifications_deleted_at ON notifications(deleted_at);"
        ]

        cursor.execute(create_table_sql)
        print("✅ Created notifications table")

        for index_sql in indexes_sql:
            cursor.execute(index_sql)
        print("✅ Created indexes on notifications table")

        conn.commit()
        print("✅ Notifications table setup complete!")

    except Exception as e:
        print(f"❌ Error creating notifications table: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_notifications_table()
