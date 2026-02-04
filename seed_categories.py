
import sys
import os
import uuid

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from database.base import SessionLocal
from modules.offers.models import Category

def seed_categories():
    db = SessionLocal()
    
    categories_data = [
        {"name_en": "Package", "name_ar": "باقة", "slug": "package", "icon": "cube", "sort_order": 1},
        {"name_en": "Hotel", "name_ar": "فندق", "slug": "hotel", "icon": "bed", "sort_order": 2},
        {"name_en": "Flight", "name_ar": "طيران", "slug": "flight", "icon": "airplane", "sort_order": 3},
        {"name_en": "Activity", "name_ar": "نشاط", "slug": "activity", "icon": "bicycle", "sort_order": 4},
        {"name_en": "Transfer", "name_ar": "تنقلات", "slug": "transfer", "icon": "car", "sort_order": 5},
        {"name_en": "Cruise", "name_ar": "رحلة بحرية", "slug": "cruise", "icon": "boat", "sort_order": 6},
        {"name_en": "Voucher", "name_ar": "قسيمة", "slug": "voucher", "icon": "receipt", "sort_order": 7},
        {"name_en": "Other", "name_ar": "أخرى", "slug": "other", "icon": "ellipsis-horizontal", "sort_order": 8},
    ]

    try:
        count = 0
        for data in categories_data:
            existing = db.query(Category).filter(Category.slug == data["slug"]).first()
            if not existing:
                cat = Category(
                    id=str(uuid.uuid4()),
                    name_en=data["name_en"],
                    name_ar=data["name_ar"],
                    slug=data["slug"],
                    icon=data["icon"],
                    sort_order=data["sort_order"],
                    is_active=True
                )
                db.add(cat)
                print(f"Adding category: {data['name_en']}")
                count += 1
            else:
                print(f"Category already exists: {data['name_en']}")
        
        db.commit()
        print(f"\nSuccessfully added {count} new categories.")
        
    except Exception as e:
        print(f"Error seeding categories: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_categories()
