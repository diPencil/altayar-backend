import sqlite3

# Connect to database
conn = sqlite3.connect('altayarvip.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 50)
print("DATABASE TABLES")
print("=" * 50)
for table in tables:
    print(f"✓ {table[0]}")

print("\n" + "=" * 50)
print("CHECKING KEY TABLES")
print("=" * 50)

# Check notifications table
try:
    cursor.execute("PRAGMA table_info(notifications)")
    columns = cursor.fetchall()
    print("\n✓ notifications table exists")
    print(f"  Columns: {len(columns)}")
except:
    print("\n✗ notifications table NOT FOUND")

# Check tier_post_comments table
try:
    cursor.execute("PRAGMA table_info(tier_post_comments)")
    columns = cursor.fetchall()
    print("\n✓ tier_post_comments table exists")
    print(f"  Columns: {len(columns)}")
except:
    print("\n✗ tier_post_comments table NOT FOUND")

# Check users table for points/cashback
try:
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    print("\n✓ users table exists")
    col_names = [col[1] for col in columns]
    if 'cashback_balance' in col_names:
        print("  ✓ cashback_balance column exists")
    else:
        print("  ✗ cashback_balance column NOT FOUND")
except:
    print("\n✗ users table NOT FOUND")

# Check points_balances table
try:
    cursor.execute("PRAGMA table_info(points_balances)")
    columns = cursor.fetchall()
    print("\n✓ points_balances table exists")
    print(f"  Columns: {len(columns)}")
except:
    print("\n✗ points_balances table NOT FOUND")

conn.close()
print("\n" + "=" * 50)
