"""
Reset admin password
"""
import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

conn = sqlite3.connect('altayar.db')
cursor = conn.cursor()

try:
    # New password
    new_password = "Admin123"
    hashed = pwd_context.hash(new_password)
    
    # Update admin password
    cursor.execute("""
        UPDATE users 
        SET hashed_password = ? 
        WHERE email = 'admin@altayar.com'
    """, (hashed,))
    
    conn.commit()
    
    if cursor.rowcount > 0:
        print("✅ Admin password reset successfully!")
        print("─" * 60)
        print("📧 Email:    admin@altayar.com")
        print("🔑 Password: Admin123")
        print("─" * 60)
    else:
        print("❌ Admin user not found!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
