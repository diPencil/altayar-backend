"""
Script to create benefits pages for all existing membership plans
This will create empty benefits pages that can be filled later
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database.base import get_db
from modules.memberships.models import MembershipPlan, MembershipBenefits
import uuid

def create_all_benefits_pages():
    db: Session = next(get_db())
    
    # Get all plans
    plans = db.query(MembershipPlan).all()
    
    if not plans:
        print("❌ No membership plans found. Please create plans first.")
        return
    
    created_count = 0
    skipped_count = 0
    
    print(f"📋 Found {len(plans)} membership plans\n")
    
    for plan in plans:
        # Check if benefits already exist
        existing = db.query(MembershipBenefits).filter(MembershipBenefits.plan_id == plan.id).first()
        
        if existing:
            print(f"⏭️  Skipping {plan.tier_name_en} ({plan.tier_code}) - Benefits page already exists")
            skipped_count += 1
        else:
            # Create new empty benefits page
            new_benefits = MembershipBenefits(
                id=str(uuid.uuid4()),
                plan_id=plan.id,
                welcome_message_en="",
                welcome_message_ar="",
                hotel_discounts_en=[],
                hotel_discounts_ar=[],
                membership_benefits_en=[],
                membership_benefits_ar=[],
                flight_coupons_en=[],
                flight_coupons_ar=[],
                free_flight_terms_en="",
                free_flight_terms_ar="",
                car_rental_services_en=[],
                car_rental_services_ar=[],
                restaurant_benefits_en=[],
                restaurant_benefits_ar=[],
                immediate_coupons_en=[],
                immediate_coupons_ar=[],
                tourism_services_en=[],
                tourism_services_ar=[],
                terms_conditions_en="",
                terms_conditions_ar="",
                comparison_guarantee_en="",
                comparison_guarantee_ar="",
                availability_terms_en="",
                availability_terms_ar="",
                coupon_usage_terms_en="",
                coupon_usage_terms_ar="",
                upgrade_info_en="",
                upgrade_info_ar="",
            )
            db.add(new_benefits)
            created_count += 1
            print(f"✅ Created benefits page for {plan.tier_name_en} ({plan.tier_code})")
    
    db.commit()
    
    print(f"\n{'='*50}")
    print(f"✅ Completed!")
    print(f"   Created: {created_count} new benefits pages")
    print(f"   Skipped: {skipped_count} (already exist)")
    print(f"   Total plans: {len(plans)}")
    print(f"{'='*50}\n")
    
    if created_count > 0:
        print("💡 You can now edit these pages from the Admin dashboard:")
        print("   Admin → Membership Benefits → Select a plan")

if __name__ == "__main__":
    try:
        create_all_benefits_pages()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
