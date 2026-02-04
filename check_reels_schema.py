"""
Check reels table schema
"""
import sqlite3
import os
from config.settings import settings

def check_schema():
    # Extract database path
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
    else:
        db_path = db_url.replace('sqlite://', '')

    if not os.path.isabs(db_path):
        backend_dir = os.path.dirname(__file__)
        db_path = os.path.join(backend_dir, db_path)

    print(f"Database path: {db_path}")

    if not os.path.exists(db_path):
        print("Database file not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check table info
    cursor.execute('PRAGMA table_info(reels)')
    columns = cursor.fetchall()

    print("Reels table columns:")
    for col in columns:
        print(f"  {col[1]} - {col[2]} - nullable: {col[3]} - default: {col[4]}")

    # Check if there are any reels
    cursor.execute('SELECT COUNT(*) FROM reels')
    count = cursor.fetchone()[0]
    print(f"\nTotal reels: {count}")

    if count > 0:
        cursor.execute('SELECT id, title, video_url, video_type, status FROM reels LIMIT 3')
        reels = cursor.fetchall()
        print("\nSample reels:")
        for reel in reels:
            print(f"  ID: {reel[0]}")
            print(f"  Title: {reel[1]}")
            print(f"  Video URL: {reel[2]}")
            print(f"  Video Type: {reel[3]}")
            print(f"  Status: {reel[4]}")
            print("  ---")

    conn.close()

if __name__ == "__main__":
    check_schema()
