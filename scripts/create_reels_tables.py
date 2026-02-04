from database.base import engine, Base
from modules.reels.models import Reel, ReelInteraction
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    logger.info("Creating Reels tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created successfully.")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()
