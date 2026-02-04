"""
Script to seed membership benefits data
Run this after creating membership plans
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database.base import get_db, engine
from modules.memberships.models import MembershipPlan, MembershipBenefits
import uuid

def seed_benefits():
    db: Session = next(get_db())
    
    # Get all plans
    plans = db.query(MembershipPlan).all()
    
    if not plans:
        print("No membership plans found. Please create plans first.")
        return
    
    # Sample benefits data for each plan
    sample_benefits = {
        "GOLD": {
            "welcome_message_en": "Welcome to AltayarVIP Gold Membership! Enjoy exclusive benefits and premium services.",
            "welcome_message_ar": "مرحباً بك في عضوية AltayarVIP الذهبية! استمتع بمزايا حصرية وخدمات مميزة.",
            "hotel_discounts_en": [
                {"title": "15% off on hotel bookings", "description": "Get 15% discount on all hotel reservations"},
                {"title": "Free night after 5 stays", "description": "Earn a free night after every 5 hotel stays"}
            ],
            "hotel_discounts_ar": [
                {"title": "خصم 15% على حجوزات الفنادق", "description": "احصل على خصم 15% على جميع حجوزات الفنادق"},
                {"title": "ليلة مجانية بعد 5 إقامات", "description": "احصل على ليلة مجانية بعد كل 5 إقامات في الفنادق"}
            ],
            "membership_benefits_en": [
                {"title": "Lifetime membership", "description": "Your membership never expires"},
                {"title": "$250 welcome coupon", "description": "Get $250 coupon upon activation"}
            ],
            "membership_benefits_ar": [
                {"title": "عضوية مدى الحياة", "description": "عضوية لا تنتهي صلاحيتها"},
                {"title": "كوبون ترحيب بقيمة 250 دولار", "description": "احصل على كوبون بقيمة 250 دولار عند التفعيل"}
            ],
            "flight_coupons_en": [
                {"title": "Flight discount coupons", "description": "Save up to 20% on flight bookings"}
            ],
            "flight_coupons_ar": [
                {"title": "كوبونات خصم الطيران", "description": "وفر حتى 20% على حجوزات الطيران"}
            ],
            "free_flight_terms_en": "Free flight tickets available after accumulating 10,000 points",
            "free_flight_terms_ar": "تذاكر طيران مجانية متاحة بعد تجميع 10,000 نقطة",
            "upgrade_info_en": "Upgrade to Platinum for even more exclusive benefits and higher rewards",
            "upgrade_info_ar": "ترقية إلى البلاتينيوم للحصول على مزايا أكثر حصرية ومكافآت أعلى"
        },
        "PLATINUM": {
            "welcome_message_en": "Welcome to AltayarVIP Platinum Membership! Experience luxury travel with premium benefits.",
            "welcome_message_ar": "مرحباً بك في عضوية AltayarVIP البلاتينية! استمتع بالسفر الفاخر مع مزايا مميزة.",
            "hotel_discounts_en": [
                {"title": "25% off on hotel bookings", "description": "Get 25% discount on all hotel reservations"},
                {"title": "Free night after 3 stays", "description": "Earn a free night after every 3 hotel stays"},
                {"title": "Room upgrade priority", "description": "Priority room upgrades at partner hotels"}
            ],
            "hotel_discounts_ar": [
                {"title": "خصم 25% على حجوزات الفنادق", "description": "احصل على خصم 25% على جميع حجوزات الفنادق"},
                {"title": "ليلة مجانية بعد 3 إقامات", "description": "احصل على ليلة مجانية بعد كل 3 إقامات في الفنادق"},
                {"title": "أولوية ترقية الغرف", "description": "أولوية ترقية الغرف في الفنادق الشريكة"}
            ],
            "membership_benefits_en": [
                {"title": "Lifetime membership", "description": "Your membership never expires"},
                {"title": "$500 welcome coupon", "description": "Get $500 coupon upon activation"},
                {"title": "10x $100 coupons", "description": "Receive 10 coupons worth $100 each"}
            ],
            "membership_benefits_ar": [
                {"title": "عضوية مدى الحياة", "description": "عضوية لا تنتهي صلاحيتها"},
                {"title": "كوبون ترحيب بقيمة 500 دولار", "description": "احصل على كوبون بقيمة 500 دولار عند التفعيل"},
                {"title": "10 كوبونات بقيمة 100 دولار", "description": "احصل على 10 كوبونات بقيمة 100 دولار لكل منها"}
            ],
            "flight_coupons_en": [
                {"title": "Flight discount coupons", "description": "Save up to 30% on flight bookings"},
                {"title": "Business class upgrades", "description": "Priority upgrades to business class"}
            ],
            "flight_coupons_ar": [
                {"title": "كوبونات خصم الطيران", "description": "وفر حتى 30% على حجوزات الطيران"},
                {"title": "ترقية درجة رجال الأعمال", "description": "أولوية الترقية إلى درجة رجال الأعمال"}
            ],
            "free_flight_terms_en": "Free flight tickets available after accumulating 7,500 points",
            "free_flight_terms_ar": "تذاكر طيران مجانية متاحة بعد تجميع 7,500 نقطة",
            "upgrade_info_en": "Upgrade to VIP for the ultimate luxury experience",
            "upgrade_info_ar": "ترقية إلى VIP للحصول على تجربة فاخرة لا مثيل لها"
        }
    }
    
    created_count = 0
    updated_count = 0
    
    for plan in plans:
        tier_code = plan.tier_code.upper()
        
        # Check if benefits already exist
        existing = db.query(MembershipBenefits).filter(MembershipBenefits.plan_id == plan.id).first()
        
        # Get sample data for this tier or use defaults
        benefits_data = sample_benefits.get(tier_code, {
            "welcome_message_en": f"Welcome to {plan.tier_name_en} Membership!",
            "welcome_message_ar": f"مرحباً بك في عضوية {plan.tier_name_ar}!",
            "hotel_discounts_en": [{"title": "Hotel discounts available", "description": "Enjoy special rates at partner hotels"}],
            "hotel_discounts_ar": [{"title": "خصومات الفنادق متاحة", "description": "استمتع بأسعار خاصة في الفنادق الشريكة"}],
            "membership_benefits_en": [{"title": "Exclusive benefits", "description": "Access to exclusive membership benefits"}],
            "membership_benefits_ar": [{"title": "مزايا حصرية", "description": "الوصول إلى مزايا العضوية الحصرية"}],
        })
        
        if existing:
            # Update existing
            for key, value in benefits_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            updated_count += 1
            print(f"Updated benefits for {plan.tier_name_en}")
        else:
            # Create new
            new_benefits = MembershipBenefits(
                id=str(uuid.uuid4()),
                plan_id=plan.id,
                **benefits_data
            )
            db.add(new_benefits)
            created_count += 1
            print(f"Created benefits for {plan.tier_name_en}")
    
    db.commit()
    print(f"\n✅ Completed! Created: {created_count}, Updated: {updated_count}")
    print("Membership benefits have been seeded successfully!")

if __name__ == "__main__":
    seed_benefits()
