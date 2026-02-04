import sqlite3
import os

# Path to database
db_path = 'altayar.db'

if not os.path.exists(db_path):
    print(f"❌ Database file '{db_path}' not found!")
    exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Update initial_points for each membership tier
updates = [
    ("SILVER", 1500),
    ("GOLD", 4000),
    ("PLATINUM", 8500),
    ("VIP", 18000),
    ("DIAMOND", 47000)
]

print("🔄 Updating initial_points for membership plans...")
print("─" * 60)

try:
    for tier_code, points in updates:
        cursor.execute(
            "UPDATE membership_plans SET initial_points = ? WHERE tier_code = ?",
            (points, tier_code)
        )
        if cursor.rowcount > 0:
            print(f"✅ {tier_code:15} → {points:6} points")
        else:
            print(f"⚠️  {tier_code:15} → Not found (skipped)")
    
    conn.commit()
    
    # Show final results
    print("\n" + "─" * 60)
    print("📊 Final Membership Plans:")
    print("─" * 60)
    
    cursor.execute("""
        SELECT tier_code, tier_name_en, price, initial_points 
        FROM membership_plans 
        ORDER BY tier_order
    """)
    plans = cursor.fetchall()
    
    if plans:
        for plan in plans:
            tier_code, tier_name, price, points = plan
            points_value = price / points if points and points > 0 else 0
            print(f"{tier_code:15} | {tier_name:20} | ${price:8.0f} | {points:6} pts | ${points_value:.2f}/pt")
    else:
        print("⚠️  No membership plans found in database")
    
    print("\n✅ All updates completed successfully!")
    
except sqlite3.Error as e:
    print(f"❌ Database Error: {e}")
    conn.rollback()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
