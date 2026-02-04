from database.base import SessionLocal
from modules.users.models import User

db = SessionLocal()
users = db.query(User).all()

print(f"{'Name':<20} | {'Email':<30} | {'Role':<10}")
print("-" * 65)
for u in users:
    print(f"{u.first_name + ' ' + u.last_name:<20} | {u.email:<30} | {u.role}")
