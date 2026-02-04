"""
Debug admin user in database
"""
import sqlite3

conn = sqlite3.connect('altayar.db')
cursor = conn.cursor()

try:
    cursor.execute("""
        SELECT id, email, username, password_hash, role, status, first_name, last_name
        FROM users 
        WHERE email = 'admin@altayar.com'
    """)
    
    user = cursor.fetchone()
    
    if user:
        print("✅ Admin user found in database!")
        print("─" * 70)
        print(f"ID:            {user[0]}")
        print(f"Email:         {user[1]}")
        print(f"Username:      {user[2]}")
        print(f"Password Hash: {user[3][:50]}...")
        print(f"Role:          {user[4]}")
        print(f"Status:        {user[5]}")
        print(f"First Name:    {user[6]}")
        print(f"Last Name:     {user[7]}")
        print("─" * 70)
        
        # Test password verification
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        test_password = "Admin123"
        is_valid = pwd_context.verify(test_password, user[3])
        
        print(f"\n🔐 Password Test:")
        print(f"Testing password: {test_password}")
        print(f"Result: {'✅ VALID' if is_valid else '❌ INVALID'}")
        
    else:
        print("❌ Admin user NOT found in database!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
