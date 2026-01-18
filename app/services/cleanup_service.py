import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Deal
from app.config import settings

logger = logging.getLogger(__name__)

class CleanupService:
    @staticmethod
    def cleanup_old_deals():
        """Remove deals older than configured days"""
        db = SessionLocal()
        try:
            cutoff_date = datetime.now() - timedelta(days=settings.CLEANUP_CONFIG['inactive_days'])
            
            # Deactivate old deals instead of deleting
            old_deals = db.query(Deal).filter(
                Deal.is_active == True,
                Deal.scraped_at < cutoff_date
            ).update({"is_active": False})
            
            db.commit()
            logger.info(f"Deactivated {old_deals} old deals")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            db.rollback()
        finally:
            db.close()