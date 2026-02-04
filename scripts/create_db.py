"""
Create database tables directly from models without migrations
"""
from database.base import Base, engine
import sqlite3

print("🔨 Creating all database tables from models...")
print("─" * 60)

try:
    # Import all models
    print("📦 Importing models...")
    try:
        from modules.users.models import *
        print("  ✓ users")
    except ImportError as e:
        print(f"  ⚠️  users: {e}")
    
    try:
        from modules.memberships.models import *
        print("  ✓ memberships")
    except ImportError as e:
        print(f"  ⚠️  memberships: {e}")
    
    try:
        from modules.orders.models import *
        print("  ✓ orders")
    except ImportError as e:
        print(f"  ⚠️  orders: {e}")
    
    try:
        from modules.payments.models import *
        print("  ✓ payments")
    except ImportError as e:
        print(f"  ⚠️  payments: {e}")
    
    try:
        from modules.points.models import *
        print("  ✓ points")
    except ImportError as e:
        print(f"  ⚠️  points: {e}")
    
    try:
        from modules.notifications.models import *
        print("  ✓ notifications")
    except ImportError as e:
        print(f"  ⚠️  notifications: {e}")
    
    print("\n" + "─" * 60)
    
    # Drop all existing tables
    Base.metadata.drop_all(bind=engine)
    print("✅ Dropped existing tables")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Created all tables from models")
    
    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print("\n📋 Created tables:")
    print("─" * 60)
    for table in sorted(tables):
        print(f"  ✓ {table}")
    
    print("\n" + "─" * 60)
    print(f"✅ Total tables created: {len(tables)}")
    
    # Check if membership_plans has initial_points
    if 'membership_plans' in tables:
        columns = [col['name'] for col in inspector.get_columns('membership_plans')]
        if 'initial_points' in columns:
            print("✅ membership_plans.initial_points column exists!")
        else:
            print("❌ membership_plans.initial_points column missing!")
    
    # NOW UPDATE MEMBERSHIP POINTS
    print("\n" + "─" * 60)
    print("🔄 Updating initial_points for membership plans...")
    print("─" * 60)
    
    # Use sqlite3 directly for updates
    conn = sqlite3.connect('altayar.db')
    cursor = conn.cursor()
    
    updates = [
        ("SILVER", 1500),
        ("GOLD", 4000),
        ("PLATINUM", 8500),
        ("VIP", 18000),
        ("DIAMOND", 47000)
    ]
    
    for tier_code, points in updates:
        cursor.execute(
            "UPDATE membership_plans SET initial_points = ? WHERE tier_code = ?",
            (points, tier_code)
        )
        if cursor.rowcount > 0:
            print(f"✅ {tier_code:15} → {points:6} points")
        else:
            print(f"⚠️  {tier_code:15} → Not found (will be set when created)")
    
    conn.commit()
    
    # Show final results
    print("\n" + "─" * 60)
    print("📊 Membership Plans (if any exist):")
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
        print("ℹ️  No membership plans in database yet")
        print("   (They will be created when you add them via admin panel)")
    
    conn.close()
    
    print("\n" + "─" * 60)
    print("✅ Database setup completed successfully!")
    print("   You can now start the server with: python server.py")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
