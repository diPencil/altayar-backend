from database.base import SessionLocal
from modules.users.models import User

db = SessionLocal()

# Check if admin exists
admin = db.query(User).filter(User.email == 'admin@altayar.com').first()

if admin:
    print(f"✅ Admin found!")
    print(f"Email: {admin.email}")
    print(f"Username: {admin.username if hasattr(admin, 'username') else 'N/A'}")
    print(f"Role: {admin.role}")
    print(f"First Name: {admin.first_name}")
    print(f"Last Name: {admin.last_name}")
else:
    print("❌ Admin not found! Creating admin account...")
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("Admin123")
    
    new_admin = User(
        email="admin@altayar.com",
        username="AltayarVIP",
        password_hash=hashed_password,
        first_name="Altayar",
        last_name="Admin",
        role="ADMIN",
        language="ar"
    )
    
    db.add(new_admin)
    db.commit()
    print("✅ Admin account created successfully!")

db.close()
