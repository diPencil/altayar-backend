"""
Seed sample reels for testing
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from database.base import SessionLocal
from modules.reels.models import Reel, ReelStatus
from modules.users.models import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample reels data
SAMPLE_REELS = [
    {
        "title": "Welcome to AltayarVIP",
        "description": "Discover luxury travel experiences with AltayarVIP. Your gateway to premium destinations.",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_type": "YOUTUBE",
        "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
        "status": ReelStatus.ACTIVE
    },
    {
        "title": "Luxury Hotels Collection",
        "description": "Explore our handpicked selection of 5-star hotels around the world.",
        "video_url": "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
        "video_type": "YOUTUBE",
        "thumbnail_url": "https://img.youtube.com/vi/3JZ_D3ELwOQ/maxresdefault.jpg",
        "status": ReelStatus.ACTIVE
    },
    {
        "title": "مرحباً بك في الطيار VIP",
        "description": "اكتشف تجارب السفر الفاخرة مع الطيار VIP. بوابتك للوجهات المميزة.",
        "video_url": "https://www.youtube.com/watch?v=ZJDMWVZta3M",
        "video_type": "YOUTUBE",
        "thumbnail_url": "https://img.youtube.com/vi/ZJDMWVZta3M/maxresdefault.jpg",
        "status": ReelStatus.ACTIVE
    },
    {
        "title": "VIP Membership Benefits",
        "description": "Learn about exclusive perks and rewards for our VIP members.",
        "video_url": "https://www.youtube.com/watch?v=2Vv-BfVoq4g",
        "video_type": "YOUTUBE",
        "thumbnail_url": "https://img.youtube.com/vi/2Vv-BfVoq4g/maxresdefault.jpg",
        "status": ReelStatus.ACTIVE
    },
    {
        "title": "مزايا العضوية المميزة",
        "description": "تعرف على المزايا والمكافآت الحصرية لأعضائنا المميزين.",
        "video_url": "https://www.youtube.com/watch?v=M7lc1UVf-VE",
        "video_type": "YOUTUBE",
        "thumbnail_url": "https://img.youtube.com/vi/M7lc1UVf-VE/maxresdefault.jpg",
        "status": ReelStatus.ACTIVE
    }
]

def seed_reels():
    db = SessionLocal()
    try:
        # Check if reels already exist
        existing_reels = db.query(Reel).count()
        if existing_reels > 0:
            logger.info(f"✅ Database already has {existing_reels} reels. Skipping seed.")
            return

        # Get first admin user
        admin = db.query(User).filter(
            (User.role == "ADMIN") | (User.role == "SUPER_ADMIN")
        ).first()

        if not admin:
            logger.error("❌ No admin user found. Please create an admin user first.")
            return

        logger.info(f"Creating sample reels assigned to admin: {admin.email}")

        # Create sample reels
        for reel_data in SAMPLE_REELS:
            reel = Reel(
                title=reel_data["title"],
                description=reel_data["description"],
                video_url=reel_data["video_url"],
                video_type=reel_data["video_type"],
                thumbnail_url=reel_data.get("thumbnail_url"),
                status=reel_data["status"],
                created_by_user_id=admin.id
            )
            db.add(reel)
            logger.info(f"  ✅ Created reel: {reel.title}")

        db.commit()
        logger.info(f"\n✅ Successfully created {len(SAMPLE_REELS)} sample reels!")
        logger.info("You can now view them in the Reels page.")

    except Exception as e:
        logger.error(f"❌ Error seeding reels: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_reels()
