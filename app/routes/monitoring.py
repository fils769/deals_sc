from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.scrapers.scraper_manager import ScraperManager
from app.config import settings

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/status")
def get_scraper_status(db: Session = Depends(get_db)):
    """Get current scraper status"""
    scraper_manager = ScraperManager()
    
    status = {
        "enabled_scrapers": scraper_manager.get_enabled_scrapers_list(),
        "total_scrapers": len(scraper_manager.get_available_scrapers()),
        "website_configs": {},
        "database_stats": {
            "total_deals": db.query(Deal).count(),
            "active_deals": db.query(Deal).filter(Deal.is_active == True).count(),
        }
    }
    
    # Add config for each scraper
    for scraper_name in scraper_manager.get_available_scrapers():
        config = scraper_manager.get_scraper_config(scraper_name)
        status["website_configs"][scraper_name] = {
            "enabled": scraper_name in scraper_manager.get_enabled_scrapers_list(),
            "max_pages": config.get('max_pages'),
            "category": config.get('category'),
            "base_url": config.get('base_url'),
        }
    
    return status