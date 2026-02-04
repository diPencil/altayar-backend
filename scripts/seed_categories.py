import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from database.base import SessionLocal
from modules.offers.models import Category
import uuid

def seed_categories():
    db = SessionLocal()
    
    categories = [
        {"name_en": "Summer Offers", "name_ar": "عروض الصيف", "slug": "summer-offers", "icon": "sunny"},
        {"name_en": "Winter Offers", "name_ar": "عروض الشتاء", "slug": "winter-offers", "icon": "snow"},
        {"name_en": "Spring Offers", "name_ar": "عروض الربيع", "slug": "spring-offers", "icon": "flower"},
        {"name_en": "Autumn Offers", "name_ar": "عروض الخريف", "slug": "autumn-offers", "icon": "leaf"},
        {"name_en": "Ramadan Offers", "name_ar": "عروض رمضان", "slug": "ramadan-offers", "icon": "moon"},
        {"name_en": "Eid Al-Fitr Offers", "name_ar": "عروض عيد الفطر", "slug": "eid-al-fitr-offers", "icon": "gift"},
        {"name_en": "Eid Al-Adha Offers", "name_ar": "عروض عيد الأضحى", "slug": "eid-al-adha-offers", "icon": "gift"},
        {"name_en": "Saudi National Day", "name_ar": "اليوم الوطني السعودي", "slug": "saudi-national-day", "icon": "flag"},
        {"name_en": "Founding Day", "name_ar": "يوم التأسيس", "slug": "founding-day", "icon": "star"},
        {"name_en": "National Holidays", "name_ar": "الأعياد الوطنية", "slug": "national-holidays", "icon": "calendar"},
        {"name_en": "Black Friday", "name_ar": "الجمعة البيضاء", "slug": "black-friday", "icon": "pricetag"},
        {"name_en": "White Friday", "name_ar": "الجمعة البيضاء", "slug": "white-friday", "icon": "cart"},
        {"name_en": "New Year", "name_ar": "رأس السنة", "slug": "new-year", "icon": "calendar"},
        {"name_en": "Back to School", "name_ar": "العودة للمدارس", "slug": "back-to-school", "icon": "school"},
        {"name_en": "Mid-Year Break", "name_ar": "إجازة منتصف العام", "slug": "mid-year-break", "icon": "airplane"},
        {"name_en": "Weekend Getaways", "name_ar": "رحلات نهاية الأسبوع", "slug": "weekend-getaways", "icon": "time"},
        {"name_en": "Honeymoon Packages", "name_ar": "باقات شهر العسل", "slug": "honeymoon-packages", "icon": "heart"},
        {"name_en": "Family Packages", "name_ar": "باقات العائلة", "slug": "family-packages", "icon": "people"},
        {"name_en": "Last Minute Deals", "name_ar": "عروض اللحظة الأخيرة", "slug": "last-minute-deals", "icon": "flash"},
        {"name_en": "Early Bird Offers", "name_ar": "عروض الحجز المبكر", "slug": "early-bird-offers", "icon": "time"},
        {"name_en": "Special Campaigns", "name_ar": "حملات خاصة", "slug": "special-campaigns", "icon": "megaphone"},
        {"name_en": "Other / General", "name_ar": "أخرى / عام", "slug": "general", "icon": "grid"}
    ]
    
    try:
        print("Seeding categories...")
        for cat_data in categories:
            # Check if exists
            existing = db.query(Category).filter_by(slug=cat_data["slug"]).first()
            if not existing:
                new_cat = Category(
                    id=str(uuid.uuid4()),
                    name_en=cat_data["name_en"],
                    name_ar=cat_data["name_ar"],
                    slug=cat_data["slug"],
                    icon=cat_data["icon"],
                    is_active=True,
                    sort_order=0
                )
                db.add(new_cat)
                print(f"Added: {cat_data['name_en']}")
            else:
                print(f"Skipped (Exists): {cat_data['name_en']}")
        
        db.commit()
        print("Categories seeded successfully!")
        
    except Exception as e:
        print(f"Error seeding categories: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_categories()
