from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import List, Optional
import logging
import logging.handlers
from datetime import datetime
import os
import sys

from app.database import get_db, SessionLocal, engine
from app.models import Base, Deal
from app.scrapers.scraper_manager import ScraperManager
from app.config import settings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger_config import setup_logging


# ------------------------------------------------------------------------------
# LOGGING SETUP
# ------------------------------------------------------------------------------
setup_logging()
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("deals-api")
logger.setLevel(settings.LOG_LEVEL)
logger.propagate = False

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(log_dir, "app.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ------------------------------------------------------------------------------
# DATABASE INIT
# ------------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)
logger.info("✓ Database initialized")

# ------------------------------------------------------------------------------
# FASTAPI APP
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Multi-Site Deals API",
    version="2.0.0",
    description="Manual scraping API (no auto scraping on startup)"
)

# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------
def save_deals_to_db(deals: List[dict]):
    db = SessionLocal()
    try:
        for deal_data in deals:
            existing = db.query(Deal).filter(
                Deal.product_id == deal_data["product_id"],
                Deal.source == deal_data["source"]
            ).first()

            if existing:
                for k, v in deal_data.items():
                    if hasattr(existing, k) and k not in ("id", "created_at"):
                        setattr(existing, k, v)
                existing.updated_at = datetime.utcnow()
                existing.is_active = True
            else:
                db.add(Deal(**deal_data))

        db.commit()
        logger.info(f"✓ Saved {len(deals)} deals")

    except Exception as e:
        db.rollback()
        logger.error("✗ DB save failed", exc_info=True)
        raise
    finally:
        db.close()


def run_all_scraping(max_products=None, max_pages=None):
    logger.info("▶ Running ALL scrapers")
    manager = ScraperManager(headless=settings.HEADLESS)
    deals = manager.run_all_scrapers(
        max_pages=max_pages,
        max_total_deals=max_products
    )
    if deals:
        save_deals_to_db(deals)


def run_specific_scraper(scraper_name: str, max_products=None, max_pages=None):
    logger.info(f"▶ Running scraper: {scraper_name}")
    manager = ScraperManager(headless=settings.HEADLESS)

    if scraper_name not in manager.get_available_scrapers():
        logger.error(f"Scraper '{scraper_name}' not found")
        return

    deals = manager.run_specific_scraper(
        scraper_name=scraper_name,
        max_pages=max_pages,
        max_total_deals=max_products
    )
    if deals:
        save_deals_to_db(deals)

# ------------------------------------------------------------------------------
# STARTUP (NO SCRAPING)
# ------------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("✓ App started (scraping disabled on startup)")

# ------------------------------------------------------------------------------
# ROOT
# ------------------------------------------------------------------------------
@app.get("/")
def root():
    manager = ScraperManager(headless=settings.HEADLESS)
    return {
        "status": "running",
        "version": "2.0.0",
        "available_scrapers": manager.get_available_scrapers()
    }

# ------------------------------------------------------------------------------
# SCRAPING ENDPOINTS
# ------------------------------------------------------------------------------
@app.post("/scrape/all")
def scrape_all(
    background_tasks: BackgroundTasks,
    max_pages: int | None = Query(None, ge=1),
    max_products: int | None = Query(None, ge=10)
):
    background_tasks.add_task(run_all_scraping, max_products, max_pages)
    return {"status": "started", "scope": "all scrapers"}


@app.post("/scrape/{scraper_name}/all")
def scrape_specific_all(
    scraper_name: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(
        run_specific_scraper,
        scraper_name,
        max_products=10000,
        max_pages=1000
    )
    return {"status": "started", "scraper": scraper_name, "mode": "full"}


@app.post("/scrape/{scraper_name}/limited")
def scrape_specific_limited(
    scraper_name: str,
    background_tasks: BackgroundTasks,
    max_pages: int = Query(5, ge=1),
    max_products: int = Query(200, ge=10)
):
    background_tasks.add_task(
        run_specific_scraper,
        scraper_name,
        max_products,
        max_pages
    )
    return {
        "status": "started",
        "scraper": scraper_name,
        "max_pages": max_pages,
        "max_products": max_products
    }

# ------------------------------------------------------------------------------
# DEALS API (Updated with scraper filtering and offer field)
# ------------------------------------------------------------------------------
@app.get("/deals")
def get_deals(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    source: Optional[str] = None,
    sources: Optional[List[str]] = Query(None, description="Filter by multiple scraper sources"),
    category: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = Query(False, description="Include inactive deals")
):
    """
    Get deals with filtering options.
    
    - **sources**: Filter by multiple scraper sources (comma-separated)
    - **source**: Filter by single scraper source (alternative to sources)
    - **include_inactive**: Set to True to include deals marked as inactive
    """
    q = db.query(Deal)
    
    if not include_inactive:
        q = q.filter(Deal.is_active == True)
    
    # Handle source filtering
    if sources:
        # Filter by multiple sources
        q = q.filter(Deal.source.in_(sources))
    elif source:
        # Filter by single source (backward compatibility)
        q = q.filter(Deal.source == source)
    
    if category:
        q = q.filter(Deal.category.ilike(f"%{category}%"))
    if search:
        q = q.filter(or_(
            Deal.title.ilike(f"%{search}%"),
            Deal.specs.ilike(f"%{search}%"),
            Deal.offer.ilike(f"%{search}%")  # Added offer to search
        ))

    total = q.count()
    deals = q.order_by(desc(Deal.scraped_at)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "filters": {
            "sources": sources,
            "category": category,
            "search": search,
            "include_inactive": include_inactive
        },
        "deals": [
            {
                "id": d.id,
                "title": d.title,
                "price": d.current_price,
                "original_price": d.original_price,
                "discount": d.discount_percentage,
                "source": d.source,
                "category": d.category,
                "image": d.image_url,
                "url": d.get_redirect_url(),
                "is_active": d.is_active,
                "scraped_at": d.scraped_at,
                "created_at": d.created_at,
                "updated_at": d.updated_at,
                "offer": d.offer,  # Added offer field
            }
            for d in deals
        ]
    }


# ------------------------------------------------------------------------------
# ENDPOINTS FOR SPECIFIC SCRAPERS
# ------------------------------------------------------------------------------
@app.get("/deals/sources")
def get_available_sources(db: Session = Depends(get_db)):
    """
    Get list of all available scraper sources in the database.
    """
    sources = db.query(Deal.source).distinct().all()
    return {
        "sources": [source[0] for source in sources],
        "total": len(sources)
    }


@app.get("/deals/from/{scraper_name}")
def get_deals_from_scraper(
    scraper_name: str,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = Query(False, description="Include inactive deals")
):
    """
    Get deals from a specific scraper.
    
    - **scraper_name**: Name of the scraper to filter by
    """
    q = db.query(Deal).filter(Deal.source == scraper_name)
    
    if not include_inactive:
        q = q.filter(Deal.is_active == True)
    
    if category:
        q = q.filter(Deal.category.ilike(f"%{category}%"))
    if search:
        q = q.filter(or_(
            Deal.title.ilike(f"%{search}%"),
            Deal.specs.ilike(f"%{search}%"),
            Deal.offer.ilike(f"%{search}%")  # Added offer to search
        ))

    total = q.count()
    deals = q.order_by(desc(Deal.scraped_at)).offset(skip).limit(limit).all()

    return {
        "source": scraper_name,
        "total": total,
        "skip": skip,
        "limit": limit,
        "filters": {
            "category": category,
            "search": search,
            "include_inactive": include_inactive
        },
        "deals": [
            {
                "id": d.id,
                "title": d.title,
                "price": d.current_price,
                "original_price": d.original_price,
                "discount": d.discount_percentage,
                "category": d.category,
                "image": d.image_url,
                "url": d.get_redirect_url(),
                "is_active": d.is_active,
                "scraped_at": d.scraped_at,
                "offer": d.offer,  # Added offer field
            }
            for d in deals
        ]
    }


@app.get("/deals/multiple-sources")
def get_deals_from_multiple_sources(
    sources: List[str] = Query(..., description="List of scraper sources to include"),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = Query(False, description="Include inactive deals")
):
    """
    Get deals from multiple specific scrapers.
    
    - **sources**: Comma-separated list of scraper sources
    """
    q = db.query(Deal).filter(Deal.source.in_(sources))
    
    if not include_inactive:
        q = q.filter(Deal.is_active == True)
    
    if category:
        q = q.filter(Deal.category.ilike(f"%{category}%"))
    if search:
        q = q.filter(or_(
            Deal.title.ilike(f"%{search}%"),
            Deal.specs.ilike(f"%{search}%"),
            Deal.offer.ilike(f"%{search}%")  # Added offer to search
        ))

    total = q.count()
    deals = q.order_by(desc(Deal.scraped_at)).offset(skip).limit(limit).all()
    
    # Count per source for statistics
    source_counts = {}
    for source in sources:
        count_query = db.query(Deal).filter(Deal.source == source)
        if not include_inactive:
            count_query = count_query.filter(Deal.is_active == True)
        source_counts[source] = count_query.count()

    return {
        "sources": sources,
        "total": total,
        "source_counts": source_counts,
        "skip": skip,
        "limit": limit,
        "filters": {
            "category": category,
            "search": search,
            "include_inactive": include_inactive
        },
        "deals": [
            {
                "id": d.id,
                "title": d.title,
                "price": d.current_price,
                "original_price": d.original_price,
                "discount": d.discount_percentage,
                "source": d.source,
                "category": d.category,
                "image": d.image_url,
                "url": d.get_redirect_url(),
                "is_active": d.is_active,
                "scraped_at": d.scraped_at,
                "offer": d.offer,  # Added offer field
            }
            for d in deals
        ]
    }


# ------------------------------------------------------------------------------
# SCRAPER STATISTICS ENDPOINT
# ------------------------------------------------------------------------------
@app.get("/scrapers/stats")
def get_scraper_statistics(db: Session = Depends(get_db)):
    """
    Get statistics for each scraper.
    """
    # Get all available sources
    all_sources = db.query(Deal.source).distinct().all()
    sources_list = [source[0] for source in all_sources]
    
    stats = []
    for source in sources_list:
        # Total deals for this source
        total_deals = db.query(Deal).filter(Deal.source == source).count()
        
        # Active deals
        active_deals = db.query(Deal).filter(
            Deal.source == source,
            Deal.is_active == True
        ).count()
        
        # Latest scrape time
        latest_scrape = db.query(Deal).filter(
            Deal.source == source
        ).order_by(desc(Deal.scraped_at)).first()
        
        # Category distribution
        categories_query = db.query(
            Deal.category,
            db.func.count(Deal.id).label('count')
        ).filter(
            Deal.source == source,
            Deal.is_active == True
        ).group_by(Deal.category).all()
        
        # Offer types distribution
        offers_query = db.query(
            Deal.offer,
            db.func.count(Deal.id).label('count')
        ).filter(
            Deal.source == source,
            Deal.is_active == True,
            Deal.offer.isnot(None),
            Deal.offer != ""
        ).group_by(Deal.offer).order_by(desc('count')).limit(10).all()
        
        stats.append({
            "source": source,
            "total_deals": total_deals,
            "active_deals": active_deals,
            "inactive_deals": total_deals - active_deals,
            "latest_scrape": latest_scrape.scraped_at if latest_scrape else None,
            "categories": [
                {"category": cat, "count": count}
                for cat, count in categories_query
                if cat  # Filter out None/empty categories
            ],
            "top_offers": [
                {"offer": offer, "count": count}
                for offer, count in offers_query
            ]
        })
    
    return {
        "scrapers": stats,
        "total_scrapers": len(stats)
    }

# ------------------------------------------------------------------------------
# NEW ENDPOINT: GET DEALS WITH OFFERS
# ------------------------------------------------------------------------------
@app.get("/deals/with-offers")
def get_deals_with_offers(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    source: Optional[str] = None,
    offer_type: Optional[str] = Query(None, description="Filter by specific offer type"),
):
    """
    Get deals that have promotional offers.
    """
    q = db.query(Deal).filter(
        Deal.is_active == True,
        Deal.offer.isnot(None),
        Deal.offer != ""
    )
    
    if source:
        q = q.filter(Deal.source == source)
    
    if offer_type:
        q = q.filter(Deal.offer.ilike(f"%{offer_type}%"))
    
    total = q.count()
    deals = q.order_by(desc(Deal.scraped_at)).offset(skip).limit(limit).all()
    
    # Get unique offer types for filtering
    offer_types = db.query(Deal.offer).filter(
        Deal.is_active == True,
        Deal.offer.isnot(None),
        Deal.offer != ""
    ).distinct().all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "available_offer_types": sorted(list(set([ot[0] for ot in offer_types if ot[0]]))),
        "deals": [
            {
                "id": d.id,
                "title": d.title,
                "price": d.current_price,
                "original_price": d.original_price,
                "discount": d.discount_percentage,
                "source": d.source,
                "category": d.category,
                "image": d.image_url,
                "url": d.get_redirect_url(),
                "is_active": d.is_active,
                "scraped_at": d.scraped_at,
                "offer": d.offer,
            }
            for d in deals
        ]
    }

# ------------------------------------------------------------------------------
# SCRAPERS LIST
# ------------------------------------------------------------------------------
@app.get("/scrapers")
def list_scrapers():
    manager = ScraperManager(headless=settings.HEADLESS)
    return {"scrapers": manager.get_available_scrapers()}

# ------------------------------------------------------------------------------
# SIMPLE DEALS ENDPOINT (Legacy - kept for backward compatibility)
# ------------------------------------------------------------------------------
@app.get("/deals/simple")
def get_deals_simple(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    source: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    q = db.query(Deal).filter(Deal.is_active == True)

    if source:
        q = q.filter(Deal.source == source)
    if category:
        q = q.filter(Deal.category.ilike(f"%{category}%"))
    if search:
        q = q.filter(or_(
            Deal.title.ilike(f"%{search}%"),
            Deal.specs.ilike(f"%{search}%"),
            Deal.offer.ilike(f"%{search}%")
        ))

    total = q.count()
    deals = q.order_by(desc(Deal.scraped_at)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "deals": [
            {
                "id": d.id,
                "title": d.title,
                "price": d.current_price,
                "discount": d.discount_percentage,
                "source": d.source,
                "image": d.image_url,
                "url": d.get_redirect_url(),
                "offer": d.offer,  # Added offer field
            }
            for d in deals
        ]
    }

# ------------------------------------------------------------------------------
# HEALTH
# ------------------------------------------------------------------------------
@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute("SELECT 1")
    return {"status": "healthy"}