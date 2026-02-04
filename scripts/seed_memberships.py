import sys
import os
import uuid
import json
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Inject dummy env vars
if "FAWATERK_API_KEY" not in os.environ:
    os.environ["FAWATERK_API_KEY"] = "dummy_key"
if "FAWATERK_VENDOR_KEY" not in os.environ:
    os.environ["FAWATERK_VENDOR_KEY"] = "dummy_vendor"
if "SECRET_KEY" not in os.environ:
    os.environ["SECRET_KEY"] = "dummy_secret"
if "DATABASE_URL" not in os.environ:
    from dotenv import load_dotenv
    load_dotenv()

from database.base import SessionLocal, engine
from sqlalchemy import Table, Column, String, Integer, Float, Boolean, DateTime, MetaData, Text, inspect, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import JSON

# Dialect-agnostic types
def get_json_type(dialect_name):
    if dialect_name == 'postgresql':
        return JSONB
    return JSON

def get_uuid_type(dialect_name):
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    if dialect_name == 'postgresql':
        return PG_UUID(as_uuid=True)
    return String(36) # Fallback for SQLite

def run_seed():
    metadata = MetaData()
    dialect_name = engine.dialect.name
    print(f"🔧 Database Dialect: {dialect_name}")

    # Define Table locally to avoid ORM deps
    membership_plans = Table(
        'membership_plans', metadata,
        Column('id', get_uuid_type(dialect_name), primary_key=True),
        Column('tier_code', String(50), unique=True, nullable=False),
        Column('tier_name_ar', String(100), nullable=False),
        Column('tier_name_en', String(100), nullable=False),
        Column('tier_order', Integer, nullable=False),
        Column('description_ar', String),
        Column('description_en', String),
        Column('price', Float, default=0.0),
        Column('currency', String(3), default='USD'),
        
        # New cols
        Column('plan_type', String(50), default='PAID_INFINITE'),
        Column('duration_days', Integer, nullable=True),
        Column('purchase_limit', Integer, default=0),
        
        Column('cashback_rate', Float, default=0.0),
        Column('points_multiplier', Float, default=1.0),
        Column('perks', get_json_type(dialect_name)),
        Column('upgrade_criteria', get_json_type(dialect_name)),
        Column('color_hex', String(7)),
        Column('icon_url', String),
        Column('is_active', Boolean, default=True),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.utcnow)
    )

    # 1. Create Table if not exists
    try:
        metadata.create_all(engine)
        print("✅ Table `membership_plans` checked/created.")
    except Exception as e:
        print(f"❌ Error creating table: {e}")

    # 2. Check & Add Columns (Migration fallback)
    inspector = inspect(engine)
    existing_cols = [c['name'] for c in inspector.get_columns('membership_plans')]
    
    with engine.connect() as conn:
        new_cols = {
            'plan_type': 'VARCHAR(50) DEFAULT \'PAID_INFINITE\'',
            'duration_days': 'INTEGER',
            'purchase_limit': 'INTEGER DEFAULT 0'
        }
        
        for col, definition in new_cols.items():
            if col not in existing_cols:
                print(f"   + Adding missing column: {col}")
                try:
                    conn.execute(text(f"ALTER TABLE membership_plans ADD COLUMN {col} {definition}"))
                    conn.commit()
                except Exception as e:
                    print(f"   ! Failed to add {col}: {e}")

        # 3. Seed Data
        # Check existing
        try:
            sel = membership_plans.select().where(membership_plans.c.tier_code == "SILVER")
            existing = conn.execute(sel).fetchone()
            
            if existing:
                print("   - Silver plan already exists.")
            else:
                print("   + Creating Silver Membership plan...")
                perks_data = {
                    "points": 1500,
                    "discount_type": "percentage",
                    "discount_value": 5 
                }
                
                # Determine ID format based on dialect (UUID obj or String)
                plan_id = uuid.uuid4()
                if dialect_name != 'postgresql':
                    plan_id = str(plan_id)

                ins = membership_plans.insert().values(
                    id=plan_id,
                    tier_code="SILVER",
                    tier_name_ar="العضوية الفضية",
                    tier_name_en="Silver Membership",
                    tier_order=1,
                    description_ar="استمتع بـ 1500 نقطة وعروض خاصة لمدة سنة",
                    description_en="Enjoy 1,500 Reward Points. Exclusive discounts on all tourism activities. Valid for 12 months.",
                    price=2000.0,
                    currency="USD",
                    plan_type="PAID_INFINITE",
                    duration_days=None,
                    purchase_limit=0,
                    cashback_rate=0.0,
                    points_multiplier=1.0,
                    color_hex="#C0C0C0",
                    is_active=True,
                    perks=perks_data,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                conn.execute(ins)
                conn.commit()
                print("   ✅ Silver Membership plan created successfully.")
        except Exception as e:
            print(f"❌ Error during insert: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_seed()
