"""
Seed script to create test users for development
Run this script to populate the database with test accounts
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.base import SessionLocal
from modules.users.models import User, UserRole, EmployeeType, UserStatus
from shared.utils import hash_password
from datetime import datetime
import uuid

def create_test_users():
    """Create test users for each role"""
    db = SessionLocal()
    
    try:
        # Check if users already exist
        existing_admin = db.query(User).filter(User.email == "admin@altayar.com").first()
        if existing_admin:
            print("⚠️  Test users already exist. Skipping...")
            return
        
        print("🔧 Creating test users...")
        
        # 1. Super Admin
        super_admin = User(
            id=str(uuid.uuid4()),
            email="superadmin@altayar.com",
            password_hash=hash_password("Admin123"),
            phone="+966500000001",
            first_name="Ahmad",
            last_name="Manager",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # 2. Admin
        admin = User(
            id=str(uuid.uuid4()),
            email="admin@altayar.com",
            password_hash=hash_password("Admin123"),
            phone="+966500000002",
            first_name="Mohammed",
            last_name="Admin",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # 3. Employee - Reservation
        employee_reservation = User(
            id=str(uuid.uuid4()),
            email="reservation@altayar.com",
            password_hash=hash_password("Employee123"),
            phone="+966500000003",
            first_name="Khaled",
            last_name="Reservation",
            role=UserRole.EMPLOYEE,
            employee_type=EmployeeType.RESERVATION,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # 4. Employee - Sales
        employee_sales = User(
            id=str(uuid.uuid4()),
            email="sales@altayar.com",
            password_hash=hash_password("Employee123"),
            phone="+966500000004",
            first_name="Fatima",
            last_name="Sales",
            role=UserRole.EMPLOYEE,
            employee_type=EmployeeType.SALES,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # 5. Employee - Accounting
        employee_accounting = User(
            id=str(uuid.uuid4()),
            email="accounting@altayar.com",
            password_hash=hash_password("Employee123"),
            phone="+966500000005",
            first_name="Omar",
            last_name="Accounting",
            role=UserRole.EMPLOYEE,
            employee_type=EmployeeType.ACCOUNTING,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # 6. Customer 1
        customer1 = User(
            id=str(uuid.uuid4()),
            email="customer@altayar.com",
            password_hash=hash_password("Customer123"),
            phone="+966500000006",
            first_name="Sara",
            last_name="Customer",
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # 7. Customer 2
        customer2 = User(
            id=str(uuid.uuid4()),
            email="customer2@altayar.com",
            password_hash=hash_password("Customer123"),
            phone="+966500000007",
            first_name="Ali",
            last_name="Client",
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # Add all users
        users = [
            super_admin,
            admin,
            employee_reservation,
            employee_sales,
            employee_accounting,
            customer1,
            customer2,
        ]
        
        db.add_all(users)
        db.commit()
        
        print("✅ Test users created successfully!")
        print("\n" + "="*60)
        print("📋 Test Accounts:")
        print("="*60)
        print("\n👨‍💼 SUPER ADMIN:")
        print("   Email: superadmin@altayar.com")
        print("   Password: Admin123")
        print("\n👨‍💼 ADMIN:")
        print("   Email: admin@altayar.com")
        print("   Password: Admin123")
        print("\n👔 EMPLOYEE (Reservation):")
        print("   Email: reservation@altayar.com")
        print("   Password: Employee123")
        print("\n👔 EMPLOYEE (Sales):")
        print("   Email: sales@altayar.com")
        print("   Password: Employee123")
        print("\n👔 EMPLOYEE (Accounting):")
        print("   Email: accounting@altayar.com")
        print("   Password: Employee123")
        print("\n👤 CUSTOMER 1:")
        print("   Email: customer@altayar.com")
        print("   Password: Customer123")
        print("\n👤 CUSTOMER 2:")
        print("   Email: customer2@altayar.com")
        print("   Password: Customer123")
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"❌ Error creating users: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting seed script...")
    create_test_users()
    print("✅ Seed script completed!")
