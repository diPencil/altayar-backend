"""
Script to create test users in the database
"""
import sys
from sqlalchemy.orm import Session
from database.base import engine, Base
from modules.users.models import User, UserRole, UserStatus
from datetime import datetime
import uuid

def create_test_users():
    """Create test users for all roles"""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = Session(engine)
    
    # Pre-hashed password: "password123"
    hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK"
    
    users_to_create = [
        {
            "email": "admin@altayar.com",
            "password_hash": hashed_password,
            "phone": "+966500000001",
            "first_name": "System",
            "last_name": "Admin",
            "username": "admin",
            "role": UserRole.ADMIN,
            "status": UserStatus.ACTIVE,
            "language": "ar",
            "email_verified": True,
            "email_verified_at": datetime.now().isoformat(),
        },
        {
            "email": "demo@demo.com",
            "password_hash": hashed_password,
            "phone": "+966500000002",
            "first_name": "demo",
            "last_name": "test",
            "username": "demo",
            "role": UserRole.CUSTOMER,
            "status": UserStatus.ACTIVE,
            "language": "ar",
            "email_verified": True,
            "email_verified_at": datetime.now().isoformat(),
        },
        {
            "email": "test@test.com",
            "password_hash": hashed_password,
            "phone": "+966500000003",
            "first_name": "Test",
            "last_name": "User",
            "username": "test",
            "role": UserRole.CUSTOMER,
            "status": UserStatus.ACTIVE,
            "language": "en",
            "email_verified": True,
            "email_verified_at": datetime.now().isoformat(),
        },
    ]
    
    created_count = 0
    
    for user_data in users_to_create:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            print(f"✓ User {user_data['email']} already exists")
            continue
        
        # Create new user
        user = User(**user_data)
        db.add(user)
        created_count += 1
        print(f"✓ Created user: {user_data['email']} ({user_data['role']})")
    
    try:
        db.commit()
        print(f"\n✅ Successfully created {created_count} users!")
        print("\nLogin credentials:")
        print("Email: admin@altayar.com | Password: password123")
        print("Email: demo@demo.com | Password: password123")
        print("Email: test@test.com | Password: password123")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating users: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()

