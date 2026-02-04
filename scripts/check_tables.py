import sqlite3

# Connect to database
conn = sqlite3.connect('altayar.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("📋 Tables in database:")
print("─" * 40)
if tables:
    for table in tables:
        print(f"  ✓ {table[0]}")
else:
    print("  ❌ No tables found!")

print("\n" + "─" * 40)
print(f"Total tables: {len(tables)}")

conn.close()
