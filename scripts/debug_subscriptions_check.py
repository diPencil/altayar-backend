import sqlite3

conn = sqlite3.connect('d:/Development/altayar/MobileApp/backend/altayarvip.db')
cursor = conn.cursor()

print("=== Existing Subscriptions ===")
cursor.execute('SELECT user_id, plan_id, membership_number, status FROM membership_subscriptions')
for row in cursor.fetchall():
    print(f"User ID: {row[0]}, Plan ID: {row[1]}, Membership: {row[2]}, Status: {row[3]}")

print("\n=== Total Count ===")
cursor.execute('SELECT COUNT(*) FROM membership_subscriptions')
print(f"Total subscriptions: {cursor.fetchone()[0]}")

conn.close()
