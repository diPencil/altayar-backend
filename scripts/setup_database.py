"""
Complete database setup: Create tables + Insert membership plans
"""
from database.base import Base, engine
import sqlite3
from datetime import datetime

print("🔨 Setting up complete database...")
print("=" * 70)

try:
    # Import all models
    print("\n📦 Step 1: Importing models...")
    print("─" * 70)
    
    from modules.users.models import *
    print("  ✓ users")
    from modules.memberships.models import *
    print("  ✓ memberships")
    from modules.orders.models import *
    print("  ✓ orders")
    from modules.payments.models import *
    print("  ✓ payments")
    from modules.points.models import *
    print("  ✓ points")
    from modules.notifications.models import *
    print("  ✓ notifications")
    
    # Drop and create tables
    print("\n🏗️  Step 2: Building database tables...")
    print("─" * 70)
    Base.metadata.drop_all(bind=engine)
    print("  ✓ Dropped existing tables")
    
    Base.metadata.create_all(bind=engine)
    print("  ✓ Created all tables")
    
    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"  ✓ Total tables: {len(tables)}")
    
    # Insert membership plans
    print("\n💎 Step 3: Creating 6 Membership Plans...")
    print("─" * 70)
    
    conn = sqlite3.connect('altayar.db')
    cursor = conn.cursor()
    
    # Define 6 membership plans
    memberships = [
        {
            "tier_code": "BRONZE",
            "tier_name_ar": "برونزي",
            "tier_name_en": "Bronze",
            "tier_order": 1,
            "price": 1000.00,
            "initial_points": 1000,
            "currency": "USD",
            "duration_days": 365,
            "cashback_rate": 0.02,
            "points_multiplier": 1.0,
            "color_hex": "#CD7F32"
        },
        {
            "tier_code": "SILVER",
            "tier_name_ar": "فضي",
            "tier_name_en": "Silver",
            "tier_order": 2,
            "price": 2000.00,
            "initial_points": 1500,
            "currency": "USD",
            "duration_days": 365,
            "cashback_rate": 0.03,
            "points_multiplier": 1.2,
            "color_hex": "#C0C0C0"
        },
        {
            "tier_code": "GOLD",
            "tier_name_ar": "ذهبي",
            "tier_name_en": "Gold",
            "tier_order": 3,
            "price": 5000.00,
            "initial_points": 4000,
            "currency": "USD",
            "duration_days": 365,
            "cashback_rate": 0.05,
            "points_multiplier": 1.5,
            "color_hex": "#FFD700"
        },
        {
            "tier_code": "PLATINUM",
            "tier_name_ar": "بلاتيني",
            "tier_name_en": "Platinum",
            "tier_order": 4,
            "price": 10000.00,
            "initial_points": 8500,
            "currency": "USD",
            "duration_days": 365,
            "cashback_rate": 0.07,
            "points_multiplier": 2.0,
            "color_hex": "#E5E4E2"
        },
        {
            "tier_code": "VIP",
            "tier_name_ar": "في آي بي",
            "tier_name_en": "VIP",
            "tier_order": 5,
            "price": 20000.00,
            "initial_points": 18000,
            "currency": "USD",
            "duration_days": 365,
            "cashback_rate": 0.10,
            "points_multiplier": 2.5,
            "color_hex": "#9B59B6"
        },
        {
            "tier_code": "DIAMOND",
            "tier_name_ar": "ماسي",
            "tier_name_en": "Diamond",
            "tier_order": 6,
            "price": 50000.00,
            "initial_points": 47000,
            "currency": "USD",
            "duration_days": 365,
            "cashback_rate": 0.15,
            "points_multiplier": 3.0,
            "color_hex": "#B9F2FF"
        }
    ]
    
    # Insert each membership
    for membership in memberships:
        cursor.execute("""
            INSERT INTO membership_plans (
                id, tier_code, tier_name_ar, tier_name_en, tier_order,
                price, initial_points, currency, duration_days,
                cashback_rate, points_multiplier, color_hex,
                is_active, created_at, updated_at
            ) VALUES (
                lower(hex(randomblob(16))),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1,
                datetime('now'), datetime('now')
            )
        """, (
            membership["tier_code"],
            membership["tier_name_ar"],
            membership["tier_name_en"],
            membership["tier_order"],
            membership["price"],
            membership["initial_points"],
            membership["currency"],
            membership["duration_days"],
            membership["cashback_rate"],
            membership["points_multiplier"],
            membership["color_hex"]
        ))
        
        points_value = membership["price"] / membership["initial_points"]
        print(f"  ✓ {membership['tier_code']:10} | ${membership['price']:8,.0f} | {membership['initial_points']:6,} pts | ${points_value:.2f}/pt")
    
    conn.commit()
    
    # Verify insertion
    print("\n📊 Step 4: Verification...")
    print("─" * 70)
    
    cursor.execute("SELECT COUNT(*) FROM membership_plans")
    count = cursor.fetchone()[0]
    print(f"  ✓ Total membership plans in database: {count}")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ Database setup completed successfully!")
    print("=" * 70)
    print("\n🚀 Next steps:")
    print("  1. Start the server: python server.py")
    print("  2. Test points calculation with different membership tiers")
    print("  3. Verify logs show correct points rate calculation")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
