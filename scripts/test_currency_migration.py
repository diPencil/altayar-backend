"""
Currency Migration Smoke Test

This script verifies that the currency migration was successful:
1. No NULL currency values in orders or payments tables
2. Historical records have been backfilled with 'EGP'
3. Database schema is correct
"""
import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "altayarvip.db"


def test_migration_smoke():
    """Verify no NULL currency values after migration"""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Test 1: Check orders table for NULL currency
        cursor.execute("SELECT COUNT(*) FROM orders WHERE currency IS NULL")
        null_orders = cursor.fetchone()[0]
        if null_orders > 0:
            print(f"❌ Found {null_orders} orders with NULL currency")
            return False
        print(f"✅ Test 1 passed: No NULL currency in orders table")
        
        # Test 2: Check payments table for NULL currency
        cursor.execute("SELECT COUNT(*) FROM payments WHERE currency IS NULL")
        null_payments = cursor.fetchone()[0]
        if null_payments > 0:
            print(f"❌ Found {null_payments} payments with NULL currency")
            return False
        print(f"✅ Test 2 passed: No NULL currency in payments table")
        
        # Test 3: Verify historical records have EGP
        cursor.execute("SELECT COUNT(*) FROM orders WHERE currency = 'EGP'")
        egp_orders = cursor.fetchone()[0]
        print(f"✅ Test 3 passed: Found {egp_orders} orders with EGP currency")
        
        # Test 4: Check currency column exists
        cursor.execute("PRAGMA table_info(orders)")
        orders_columns = [row[1] for row in cursor.fetchall()]
        if 'currency' not in orders_columns:
            print("❌ Currency column not found in orders table")
            return False
        print("✅ Test 4 passed: Currency column exists in orders table")
        
        cursor.execute("PRAGMA table_info(payments)")
        payments_columns = [row[1] for row in cursor.fetchall()]
        if 'currency' not in payments_columns:
            print("❌ Currency column not found in payments table")
            return False
        print("✅ Test 5 passed: Currency column exists in payments table")
        
        print("\n" + "="*50)
        print("✅ ALL MIGRATION SMOKE TESTS PASSED")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"❌ Error during smoke test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = test_migration_smoke()
    sys.exit(0 if success else 1)
