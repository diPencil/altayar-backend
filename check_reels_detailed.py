import sqlite3
import json

conn = sqlite3.connect('altayarvip.db')
cursor = conn.cursor()

# Get all reels with full details
cursor.execute('''
    SELECT id, title, status, video_type, video_url, thumbnail_url, 
           views_count, likes_count, created_at 
    FROM reels 
    ORDER BY created_at DESC
''')

reels = cursor.fetchall()

print(f"=== Total Reels in Database: {len(reels)} ===\n")

for i, reel in enumerate(reels, 1):
    print(f"Reel #{i}")
    print(f"  ID: {reel[0]}")
    print(f"  Title: {reel[1]}")
    print(f"  Status: {reel[2]}")
    print(f"  Video Type: {reel[3]}")
    print(f"  Video URL: {reel[4]}")
    print(f"  Thumbnail: {reel[5]}")
    print(f"  Views: {reel[6]}, Likes: {reel[7]}")
    print(f"  Created: {reel[8]}")
    print("-" * 80)

# Check ACTIVE reels only
cursor.execute('''
    SELECT COUNT(*) FROM reels 
    WHERE status = 'ACTIVE' AND video_url IS NOT NULL
''')
active_count = cursor.fetchone()[0]
print(f"\n=== ACTIVE Reels with Video URL: {active_count} ===")

conn.close()
