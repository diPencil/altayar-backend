#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('altayarvip.db')
cursor = conn.cursor()

try:
    # Update the action_url to remove /admin prefix
    cursor.execute('UPDATE notifications SET action_url = REPLACE(action_url, "/admin/users/", "/users/") WHERE action_url LIKE "/admin/users/%"')
    conn.commit()

    print('✅ Updated notification action_url')

    # Check the updated notification
    cursor.execute('SELECT action_url FROM notifications WHERE id="1f0d51a9-9167-4076-8d30-e2f480a0c8d6"')
    result = cursor.fetchone()
    print(f'New action_url: {result[0] if result else "Not found"}')

except Exception as e:
    print(f'❌ Error: {e}')

finally:
    conn.close()
