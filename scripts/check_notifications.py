#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('altayarvip.db')
cursor = conn.cursor()

try:
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="notifications"')
    table_exists = cursor.fetchone()

    if table_exists:
        print('✅ Notifications table exists')

        cursor.execute('SELECT COUNT(*) FROM notifications')
        count = cursor.fetchone()[0]
        print(f'📊 Total notifications: {count}')

        if count > 0:
            cursor.execute('SELECT id, type, title, message, target_role, is_read, created_at, related_entity_type, related_entity_id, action_url FROM notifications ORDER BY created_at DESC LIMIT 5')
            notifications = cursor.fetchall()

            print('\n📋 Recent notifications:')
            for notif in notifications:
                print(f'  - ID: {notif[0]}')
                print(f'    Type: {notif[1]}')
                print(f'    Title: {notif[2]}')
                print(f'    Message: {notif[3][:100]}...')
                print(f'    Target Role: {notif[4]}')
                print(f'    Read: {notif[5]}')
                print(f'    Related Entity: {notif[7]} (ID: {notif[8]})')
                print(f'    Action URL: {notif[9]}')
                print(f'    Created: {notif[6]}')
                print()
        else:
            print('⚠️  No notifications found in database')
    else:
        print('❌ Notifications table does not exist')

except Exception as e:
    print(f'❌ Error: {e}')

finally:
    conn.close()
