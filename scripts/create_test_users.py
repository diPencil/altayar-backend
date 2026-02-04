"""
Simple seed script - creates 3 test users (Admin, Employee, Customer)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.base import SessionLocal
from modules.users.models import User, UserRole, EmployeeType, UserStatus
from datetime import datetime
import uuid

# Simple hash function for testing (NOT for production!)
def simple_hash(password: str) -> str:
    """Simple hash for testing - uses Python's built-in hash"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def create_users():
    db = SessionLocal()
    
    try:
        print("🔧 Creating test users...")
        
        # Check if already exists
        if db.query(User).filter(User.email == "admin@altayar.com").first():
            print("⚠️  Users already exist!")
            return
        
        # 1. Admin
        admin = User(
            id=str(uuid.uuid4()),
            email="admin@altayar.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK",  # Admin123
            phone="+966500000001",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # 2. Employee
        employee = User(
            id=str(uuid.uuid4()),
            email="employee@altayar.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK",  # Employee123
            phone="+966500000002",
            first_name="Employee",
            last_name="User",
            role=UserRole.EMPLOYEE,
            employee_type=EmployeeType.RESERVATION,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        # 3. Customer
        customer = User(
            id=str(uuid.uuid4()),
            email="customer@altayar.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK",  # Customer123
            phone="+966500000003",
            first_name="Customer",
            last_name="User",
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        
        db.add_all([admin, employee, customer])
        db.commit()
        
        print("✅ Users created!")
        print("\n" + "="*50)
        print("👨‍💼 ADMIN:")
        print("   Email: admin@altayar.com")
        print("   Password: Admin123")
        print("\n👔 EMPLOYEE:")
        print("   Email: employee@altayar.com")
        print("   Password: Employee123")
        print("\n👤 CUSTOMER:")
        print("   Email: customer@altayar.com")
        print("   Password: Customer123")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_users()
