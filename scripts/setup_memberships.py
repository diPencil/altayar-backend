"""
Complete database setup using pure SQL
No SQLAlchemy models - just raw SQL to avoid conflicts
"""
import sqlite3
import os

DB_PATH = 'altayar.db'

print("🔨 Setting up database with pure SQL...")
print("=" * 70)

# Delete old database
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("✓ Removed old database")

# Create new database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Create membership_plans table
    print("\n📋 Creating membership_plans table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS membership_plans (
            id TEXT PRIMARY KEY,
            tier_code TEXT UNIQUE NOT NULL,
            tier_name_ar TEXT NOT NULL,
            tier_name_en TEXT NOT NULL,
            tier_order INTEGER NOT NULL,
            description_ar TEXT,
            description_en TEXT,
            price REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD',
            plan_type TEXT,
            duration_days INTEGER,
            purchase_limit INTEGER,
            cashback_rate REAL DEFAULT 0.0,
            points_multiplier REAL DEFAULT 1.0,
            initial_points INTEGER DEFAULT 0,
            perks TEXT,
            upgrade_criteria TEXT,
            color_hex TEXT,
            icon_url TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Table created")
    
    # Insert 6 membership plans
    print("\n💎 Inserting 6 membership plans...")
    print("─" * 70)
    
    memberships = [
        ("BRONZE", "برونزي", "Bronze", 1, 1000.00, 1000, 0.02, 1.0, "#CD7F32"),
        ("SILVER", "فضي", "Silver", 2, 2000.00, 1500, 0.03, 1.2, "#C0C0C0"),
        ("GOLD", "ذهبي", "Gold", 3, 5000.00, 4000, 0.05, 1.5, "#FFD700"),
        ("PLATINUM", "بلاتيني", "Platinum", 4, 10000.00, 8500, 0.07, 2.0, "#E5E4E2"),
        ("VIP", "في آي بي", "VIP", 5, 20000.00, 18000, 0.10, 2.5, "#9B59B6"),
        ("DIAMOND", "ماسي", "Diamond", 6, 50000.00, 47000, 0.15, 3.0, "#B9F2FF")
    ]
    
    for tier_code, name_ar, name_en, order, price, points, cashback, multiplier, color in memberships:
        cursor.execute("""
            INSERT INTO membership_plans (
                id, tier_code, tier_name_ar, tier_name_en, tier_order,
                price, initial_points, currency, duration_days,
                cashback_rate, points_multiplier, color_hex, is_active
            ) VALUES (
                lower(hex(randomblob(16))), ?, ?, ?, ?, ?, ?, 'USD', 365, ?, ?, ?, 1
            )
        """, (tier_code, name_ar, name_en, order, price, points, cashback, multiplier, color))
        
        points_value = price / points
        print(f"✓ {tier_code:10} | ${price:8,.0f} | {points:6,} pts | ${points_value:.2f}/pt")
    
    conn.commit()
    
    # Verify
    print("\n📊 Verification...")
    print("─" * 70)
    cursor.execute("SELECT COUNT(*) FROM membership_plans")
    count = cursor.fetchone()[0]
    print(f"✓ Total plans in database: {count}")
    
    cursor.execute("SELECT tier_code, price, initial_points FROM membership_plans ORDER BY tier_order")
    plans = cursor.fetchall()
    
    print("\n📋 All membership plans:")
    print("─" * 70)
    for tier, price, points in plans:
        value = price / points if points > 0 else 0
        print(f"  {tier:10} → ${price:8,.0f} / {points:6,} pts = ${value:.2f} per point")
    
    print("\n" + "=" * 70)
    print("✅ Database setup completed!")
    print("=" * 70)
    print("\n🚀 Next: Start server with: python server.py")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
