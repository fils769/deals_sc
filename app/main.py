# from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
# from sqlalchemy.orm import Session
# from sqlalchemy import desc, or_
# from typing import List, Optional
# import logging
# import logging.handlers
# from datetime import datetime
# import os
# import sys
# import time

# from app.database import get_db, SessionLocal, engine
# from app.models import Base, Deal
# from app.scrapers.scraper_manager import ScraperManager
# from app.config import settings

# # Configure logging
# log_dir = "logs"
# if not os.path.exists(log_dir):
#     os.makedirs(log_dir)

# logger = logging.getLogger(__name__)
# logger.setLevel(settings.LOG_LEVEL)
# logger.propagate = False

# # Console handler
# console_handler = logging.StreamHandler(sys.stdout)
# console_handler.setLevel(settings.LOG_LEVEL)

# # File handler
# file_handler = logging.handlers.RotatingFileHandler(
#     os.path.join(log_dir, "app.log"),
#     maxBytes=10 * 1024 * 1024,
#     backupCount=5,
#     encoding='utf-8'
# )
# file_handler.setLevel(settings.LOG_LEVEL)

# # Formatter
# formatter = logging.Formatter(
#     '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
# console_handler.setFormatter(formatter)
# file_handler.setFormatter(formatter)

# # Add handlers
# logger.addHandler(console_handler)
# logger.addHandler(file_handler)

# logger.info("=" * 80)
# logger.info("Multi-Site Scraper Starting Up")
# logger.info(f"Database URL: {settings.DATABASE_URL}")
# logger.info(f"Log Level: {settings.LOG_LEVEL}")
# logger.info("=" * 80)

# # Create database tables
# try:
#     logger.info("Creating PostgreSQL database tables...")
#     Base.metadata.create_all(bind=engine)
#     logger.info("✓ Database tables created successfully")
# except Exception as e:
#     logger.error(f"✗ Failed to create database tables: {e}")
#     raise

# app = FastAPI(
#     title="Multi-Site Deals API",
#     version="2.0.0",
#     description="API for scraping and serving deals from multiple websites"
# )

# logger.info("✓ FastAPI app initialized successfully")

# def save_deals_to_db(deals_data: List[dict]):
#     """Save scraped deals to PostgreSQL database"""
#     logger.info(f"Saving {len(deals_data)} deals to database...")
#     db = SessionLocal()
#     try:
#         new_count = 0
#         updated_count = 0
        
#         for i, deal_data in enumerate(deals_data, 1):
#             # Use product_id AND source for unique identification
#             existing_deal = db.query(Deal).filter(
#                 Deal.product_id == deal_data.get('product_id'),
#                 Deal.source == deal_data.get('source')
#             ).first()
            
#             if existing_deal:
#                 # Update existing deal
#                 for key, value in deal_data.items():
#                     if hasattr(existing_deal, key) and key not in ['id', 'created_at']:
#                         setattr(existing_deal, key, value)
#                 existing_deal.updated_at = datetime.now()
#                 existing_deal.is_active = True
#                 updated_count += 1
#             else:
#                 # Create new deal
#                 new_deal = Deal(**deal_data)
#                 db.add(new_deal)
#                 new_count += 1
            
#             # Commit every 50 records to avoid large transactions
#             if i % 50 == 0:
#                 db.commit()
#                 logger.debug(f"Committed {i} deals...")
        
#         db.commit()
#         logger.info(f"✓ Database save completed: {new_count} new deals, {updated_count} updated deals")
        
#     except Exception as e:
#         logger.error(f"✗ Error saving to database: {e}", exc_info=True)
#         db.rollback()
#         raise
#     finally:
#         db.close()

# def run_all_scraping(max_products=None, max_pages=None):
#     """Run all scrapers in background"""
#     logger.info("=" * 80)
#     logger.info(f"MULTI-SITE SCRAPING JOB STARTED")
#     logger.info(f"Max pages per site: {'Unlimited' if not max_pages else max_pages}")
#     logger.info(f"Max products per site: {'Unlimited' if not max_products else max_products}")
#     logger.info("=" * 80)
    
#     try:
#         logger.info("Initializing ScraperManager...")
#         scraper_manager = ScraperManager(headless=settings.HEADLESS)
        
#         available_scrapers = scraper_manager.get_available_scrapers()
#         logger.info(f"Available scrapers: {available_scrapers}")
        
#         # Run all scrapers
#         deals = scraper_manager.run_all_scrapers(
#             max_pages=max_pages,
#             max_total_deals=max_products
#         )
        
#         logger.info(f"Total deals scraped from all sites: {len(deals)}")
        
#         if deals:
#             logger.info(f"Processing {len(deals)} deals...")
#             save_deals_to_db(deals)
#             logger.info("=" * 80)
#             logger.info(f"✓ MULTI-SITE SCRAPING COMPLETED SUCCESSFULLY - {len(deals)} deals processed")
#             logger.info("=" * 80)
#         else:
#             logger.warning("✗ No deals were scraped from any site")
                
#     except Exception as e:
#         logger.error("=" * 80)
#         logger.error(f"✗ SCRAPING JOB FAILED: {e}", exc_info=True)
#         logger.error("=" * 80)

# def run_specific_scraper(scraper_name: str, max_products=None, max_pages=None):
#     """Run a specific scraper"""
#     logger.info(f"Starting scraper: {scraper_name}")
    
#     try:
#         scraper_manager = ScraperManager(headless=settings.HEADLESS)
        
#         # Check if scraper exists
#         if scraper_name not in scraper_manager.get_available_scrapers():
#             logger.error(f"Scraper '{scraper_name}' not found")
#             return 0
        
#         deals = scraper_manager.run_specific_scraper(
#             scraper_name=scraper_name,
#             max_pages=max_pages,
#             max_total_deals=max_products
#         )
        
#         if deals:
#             save_deals_to_db(deals)
#             logger.info(f"✓ {scraper_name}: {len(deals)} deals processed")
#         else:
#             logger.warning(f"⚠ {scraper_name}: No deals scraped")
        
#         return len(deals)
        
#     except Exception as e:
#         logger.error(f"✗ {scraper_name}: Failed with error: {e}", exc_info=True)
#         return 0

# @app.on_event("startup")
# async def startup_event():
#     """Run scraping on application startup"""
#     logger.info("=" * 80)
#     logger.info("STARTUP EVENT: Triggering initial scraping...")
#     logger.info("=" * 80)
#     # Run all scrapers on startup with reasonable limits
#     run_all_scraping(max_products=500, max_pages=5)

# @app.get("/")
# def read_root():
#     """Root endpoint with API information"""
#     scraper_manager = ScraperManager(headless=settings.HEADLESS)
#     return {
#         "message": "Multi-Site Deals API",
#         "status": "active",
#         "version": "2.0.0",
#         "available_scrapers": scraper_manager.get_available_scrapers(),
#         "endpoints": {
#             "deals": "/deals",
#             "deals_by_source": "/deals/source/{source}",
#             "scrape_all": "/scrape/all (POST)",
#             "scrape_specific": "/scrape/{scraper_name} (POST)",
#             "scrapers_list": "/scrapers",
#             "categories": "/categories",
#             "health": "/health",
#             "stats": "/stats",
#             "sources": "/sources"
#         }
#     }

# @app.get("/health")
# def health_check(db: Session = Depends(get_db)):
#     """Health check endpoint"""
#     try:
#         logger.info("GET /health - Performing health check")
#         db.execute("SELECT 1")
#         deal_count = db.query(Deal).count()
#         scraper_manager = ScraperManager(headless=settings.HEADLESS)
#         logger.info("✓ Health check passed - database connected")
#         return {
#             "status": "healthy", 
#             "database": "connected",
#             "total_deals": deal_count,
#             "active_scrapers": len(scraper_manager.get_available_scrapers())
#         }
#     except Exception as e:
#         logger.error(f"✗ Health check failed: {e}")
#         return {"status": "unhealthy", "error": str(e)}, 500

# @app.post("/scrape/all")
# async def trigger_all_scrapers(
#     background_tasks: BackgroundTasks, 
#     max_pages: int = Query(None, ge=1, le=1000),
#     max_products: int = Query(None, ge=10, le=10000),
#     scrape_all: bool = Query(False)
# ):
#     """Manually trigger all scrapers"""
#     logger.info(f"POST /scrape/all - max_pages={max_pages}, max_products={max_products}, scrape_all={scrape_all}")
    
#     if scrape_all:
#         # Set high limits for "scrape all"
#         max_pages = 1000
#         max_products = 10000
#         message = "Scraping ALL pages from all sites started in background"
#     else:
#         message = "Scraping all sites started in background"
    
#     background_tasks.add_task(run_all_scraping, max_products, max_pages)
#     return {
#         "message": message,
#         "max_pages": max_pages if not scrape_all else "Unlimited",
#         "max_products": max_products if not scrape_all else "Unlimited",
#         "scrape_all": scrape_all,
#         "status": "processing",
#         "note": "Check logs for progress"
#     }

# @app.post("/scrape/{scraper_name}")
# async def trigger_specific_scraper(
#     scraper_name: str,
#     background_tasks: BackgroundTasks, 
#     max_pages: int = Query(None, ge=1, le=1000),
#     max_products: int = Query(None, ge=10, le=10000),
#     scrape_all: bool = Query(False)
# ):
#     """Manually trigger a specific scraper"""
#     logger.info(f"POST /scrape/{scraper_name} - scraper={scraper_name}")
    
#     scraper_manager = ScraperManager(headless=settings.HEADLESS)
#     if scraper_name not in scraper_manager.get_available_scrapers():
#         raise HTTPException(status_code=404, detail=f"Scraper '{scraper_name}' not found")
    
#     if scrape_all:
#         max_pages = 1000
#         max_products = 10000
    
#     background_tasks.add_task(run_specific_scraper, scraper_name, max_products, max_pages)
#     return {
#         "message": f"Scraper '{scraper_name}' started in background",
#         "scraper": scraper_name,
#         "max_pages": max_pages if not scrape_all else "Unlimited",
#         "max_products": max_products if not scrape_all else "Unlimited",
#         "scrape_all": scrape_all,
#         "status": "processing",
#         "note": "Check logs for progress"
#     }

# @app.get("/scrapers")
# def get_scrapers():
#     """Get list of available scrapers"""
#     scraper_manager = ScraperManager(headless=settings.HEADLESS)
#     return {
#         "scrapers": scraper_manager.get_available_scrapers(),
#         "count": len(scraper_manager.get_available_scrapers())
#     }

# @app.get("/deals", response_model=dict)
# def get_deals(
#     db: Session = Depends(get_db),
#     skip: int = Query(0, ge=0),
#     limit: int = Query(20, ge=1, le=100),
#     category: Optional[str] = None,
#     source: Optional[str] = None,
#     min_discount: Optional[float] = Query(None, ge=0, le=100),
#     max_price: Optional[float] = Query(None, ge=0),
#     min_rating: Optional[float] = Query(None, ge=0, le=5),
#     sort_by: str = Query("discount", regex="^(discount|price|newest|oldest)$"),
#     search: Optional[str] = None,
#     super_star_only: bool = Query(False)
# ):
#     """Get all deals with optional filtering and sorting"""
#     logger.info(f"GET /deals - skip={skip}, limit={limit}, source={source}, category={category}")
    
#     query = db.query(Deal).filter(Deal.is_active == True)
    
#     if source:
#         query = query.filter(Deal.source == source)
    
#     if category:
#         query = query.filter(Deal.category.ilike(f"%{category}%"))
    
#     if min_discount:
#         query = query.filter(Deal.discount_percentage >= min_discount)
    
#     if max_price:
#         query = query.filter(Deal.current_price <= max_price)
    
#     if min_rating:
#         query = query.filter(Deal.rating >= min_rating)
    
#     if search:
#         search_term = f"%{search}%"
#         query = query.filter(
#             or_(
#                 Deal.title.ilike(search_term),
#                 Deal.category.ilike(search_term),
#                 Deal.specs.ilike(search_term)
#             )
#         )
    
#     if super_star_only:
#         query = query.filter(Deal.discount_percentage.isnot(None))
    
#     if sort_by == "discount":
#         query = query.order_by(desc(Deal.discount_percentage))
#     elif sort_by == "price":
#         query = query.order_by(Deal.current_price)
#     elif sort_by == "newest":
#         query = query.order_by(desc(Deal.scraped_at))
#     elif sort_by == "oldest":
#         query = query.order_by(Deal.scraped_at)
    
#     total = query.count()
#     deals = query.offset(skip).limit(limit).all()
    
#     response = [
#         {
#             "id": deal.id,
#             "title": deal.title,
#             "category": deal.category,
#             "specs": deal.specs,
#             "original_price": deal.original_price,
#             "current_price": deal.current_price,
#             "discount_percentage": deal.discount_percentage,
#             "rating": deal.rating,
#             "review_count": deal.review_count,
#             "redirect_url": deal.get_redirect_url(),
#             "image_url": deal.image_url,
#             "shop_count": deal.shop_count,
#             "product_id": deal.product_id,
#             "source": deal.source,
#             "scraped_at": deal.scraped_at.isoformat() if deal.scraped_at else None,
#             "created_at": deal.created_at.isoformat() if deal.created_at else None
#         }
#         for deal in deals
#     ]
    
#     return {
#         "total": total,
#         "skip": skip,
#         "limit": limit,
#         "deals": response
#     }

# @app.get("/deals/source/{source}")
# def get_deals_by_source(
#     source: str,
#     db: Session = Depends(get_db),
#     skip: int = Query(0, ge=0),
#     limit: int = Query(20, ge=1, le=100)
# ):
#     """Get deals by specific source"""
#     logger.info(f"GET /deals/source/{source}")
    
#     query = db.query(Deal).filter(
#         Deal.is_active == True,
#         Deal.source == source
#     )
    
#     total = query.count()
#     deals = query.order_by(desc(Deal.scraped_at)).offset(skip).limit(limit).all()
    
#     response = [
#         {
#             "id": deal.id,
#             "title": deal.title,
#             "category": deal.category,
#             "specs": deal.specs,
#             "original_price": deal.original_price,
#             "current_price": deal.current_price,
#             "discount_percentage": deal.discount_percentage,
#             "rating": deal.rating,
#             "review_count": deal.review_count,
#             "redirect_url": deal.get_redirect_url(),
#             "image_url": deal.image_url,
#             "shop_count": deal.shop_count,
#             "product_id": deal.product_id,
#             "source": deal.source,
#             "scraped_at": deal.scraped_at.isoformat() if deal.scraped_at else None
#         }
#         for deal in deals
#     ]
    
#     return {
#         "source": source,
#         "total": total,
#         "skip": skip,
#         "limit": limit,
#         "deals": response
#     }

# @app.get("/stats")
# def get_stats(db: Session = Depends(get_db)):
#     """Get scraping statistics"""
#     logger.info("GET /stats - Getting statistics")
    
#     total_deals = db.query(Deal).count()
#     active_deals = db.query(Deal).filter(Deal.is_active == True).count()
    
#     # Get deals by source
#     sources_query = db.query(Deal.source, db.func.count(Deal.id).label('count')).group_by(Deal.source).all()
#     sources_stats = {source: count for source, count in sources_query}
    
#     # Get average discount
#     avg_discount = db.query(db.func.avg(Deal.discount_percentage)).filter(
#         Deal.discount_percentage.isnot(None)
#     ).scalar()
    
#     # Get newest scraped deal
#     newest = db.query(Deal).order_by(desc(Deal.scraped_at)).first()
    
#     # Get deals by category count
#     categories_count = db.query(Deal.category).distinct().count()
    
#     return {
#         "total_deals": total_deals,
#         "active_deals": active_deals,
#         "sources_stats": sources_stats,
#         "categories_count": categories_count,
#         "average_discount": round(float(avg_discount or 0), 2),
#         "last_scraped": newest.scraped_at.isoformat() if newest else None,
#         "newest_deal": {
#             "title": newest.title if newest else None,
#             "source": newest.source if newest else None
#         }
#     }

# @app.get("/sources")
# def get_sources(db: Session = Depends(get_db)):
#     """Get all available sources"""
#     logger.info("GET /sources - Getting sources")
    
#     sources = db.query(Deal.source).distinct().filter(Deal.source.isnot(None)).all()
    
#     return {
#         "sources": [source[0] for source in sources if source[0]],
#         "count": len([source for source in sources if source[0]])
#     }

# @app.get("/categories")
# def get_categories(db: Session = Depends(get_db)):
#     """Get all available categories"""
#     logger.info("GET /categories - Getting categories")
    
#     categories = db.query(Deal.category).distinct().filter(Deal.category.isnot(None)).all()
    
#     return {
#         "categories": [cat[0] for cat in categories if cat[0]],
#         "count": len([cat for cat in categories if cat[0]])
#     }

# @app.delete("/deals/{product_id}")
# def delete_deal(product_id: str, db: Session = Depends(get_db)):
#     """Delete or deactivate a deal"""
#     logger.info(f"DELETE /deals/{product_id} - Deleting deal")
    
#     deal = db.query(Deal).filter(Deal.product_id == product_id).first()
#     if not deal:
#         raise HTTPException(status_code=404, detail="Deal not found")
    
#     deal.is_active = False
#     db.commit()
    
#     return {"message": f"Deal {product_id} deactivated successfully"}

# @app.get("/deals/{product_id}")
# def get_deal_by_id(product_id: str, db: Session = Depends(get_db)):
#     """Get a specific deal by product ID"""
#     logger.info(f"GET /deals/{product_id} - Getting specific deal")
    
#     deal = db.query(Deal).filter(
#         Deal.product_id == product_id,
#         Deal.is_active == True
#     ).first()
    
#     if not deal:
#         raise HTTPException(status_code=404, detail="Deal not found")
    
#     return {
#         "id": deal.id,
#         "title": deal.title,
#         "category": deal.category,
#         "specs": deal.specs,
#         "original_price": deal.original_price,
#         "current_price": deal.current_price,
#         "discount_percentage": deal.discount_percentage,
#         "rating": deal.rating,
#         "review_count": deal.review_count,
#         "redirect_url": deal.get_redirect_url(),
#         "image_url": deal.image_url,
#         "shop_count": deal.shop_count,
#         "product_id": deal.product_id,
#         "source": deal.source,
#         "scraped_at": deal.scraped_at.isoformat() if deal.scraped_at else None,
#         "created_at": deal.created_at.isoformat() if deal.created_at else None
#     }

# logger.info("=" * 80)
# logger.info("Application startup complete - ready to accept requests")
# logger.info("=" * 80)

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
# SCRAPERS LIST
# ------------------------------------------------------------------------------
@app.get("/scrapers")
def list_scrapers():
    manager = ScraperManager(headless=settings.HEADLESS)
    return {"scrapers": manager.get_available_scrapers()}

# ------------------------------------------------------------------------------
# DEALS API
# ------------------------------------------------------------------------------
@app.get("/deals")
def get_deals(
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
            Deal.specs.ilike(f"%{search}%")
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
