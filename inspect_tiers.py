
from sqlalchemy import create_engine, text
import os

# Database URL (adjust if needed, assuming local defaults from previous context)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/altayar_db"

def inspect_data():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("--- Membership Plans ---")
        result = conn.execute(text("SELECT tier_code, tier_name_en, perks FROM membership_plans"))
        for row in result:
            print(f"Code: '{row[0]}', Name: {row[1]}, Perks: {row[2]}")

        print("\n--- Users (searching for 'demo' or 'test') ---")
        # Search for users likely to be the one in the screenshot
        result = conn.execute(text("SELECT username, email, membership_tier_code FROM users WHERE username LIKE '%demo%' OR username LIKE '%test%'"))
        for row in result:
            print(f"User: {row[0]}, Email: {row[1]}, Tier Code: '{row[2]}'")

if __name__ == "__main__":
    try:
        inspect_data()
    except Exception as e:
        print(f"Error: {e}")
