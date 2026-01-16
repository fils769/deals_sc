from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import List, Optional
import logging
import logging.handlers
from datetime import datetime, timedelta
import os
import sys
import time

from app.database import get_db, SessionLocal, engine
from app.models import Base, Deal
from app.scraper import MarketInScraper
from app.config import settings

# Configure logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logger = logging.getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)
logger.propagate = False

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(settings.LOG_LEVEL)

# File handler
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(log_dir, "app.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(settings.LOG_LEVEL)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.info("=" * 80)
logger.info("Market-In.gr Scraper Starting Up")
logger.info(f"Database URL: {settings.DATABASE_URL}")
logger.info(f"Log Level: {settings.LOG_LEVEL}")
logger.info("=" * 80)

# Create database tables
try:
    logger.info("Creating PostgreSQL database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✓ Database tables created successfully")
except Exception as e:
    logger.error(f"✗ Failed to create database tables: {e}")
    raise

app = FastAPI(
    title="Market-In.gr Deals API",
    version="1.0.0",
    description="API for scraping and serving Market-In.gr deals"
)

logger.info("✓ FastAPI app initialized successfully")

def save_deals_to_db(deals_data):
    """Save scraped deals to PostgreSQL database"""
    logger.info(f"Saving {len(deals_data)} deals to database...")
    db = SessionLocal()
    try:
        new_count = 0
        updated_count = 0
        
        for i, deal_data in enumerate(deals_data, 1):
            # Use product_id for identification
            existing_deal = db.query(Deal).filter(
                Deal.product_id == deal_data.get('product_id')
            ).first()
            
            if existing_deal:
                # Update existing deal
                for key, value in deal_data.items():
                    if hasattr(existing_deal, key) and key not in ['id', 'created_at']:
                        setattr(existing_deal, key, value)
                existing_deal.updated_at = datetime.now()
                existing_deal.is_active = True
                updated_count += 1
            else:
                # Create new deal
                new_deal = Deal(**deal_data)
                db.add(new_deal)
                new_count += 1
            
            # Commit every 50 records to avoid large transactions
            if i % 50 == 0:
                db.commit()
        
        db.commit()
        logger.info(f"✓ Database save completed: {new_count} new deals, {updated_count} updated deals")
        
    except Exception as e:
        logger.error(f"✗ Error saving to database: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

def run_scraping(max_products=None, max_pages=None):
    """Run scraping in background"""
    logger.info("=" * 80)
    logger.info(f"MARKET-IN.GR SCRAPING JOB STARTED")
    logger.info(f"Max pages: {'Unlimited' if not max_pages else max_pages}")
    logger.info(f"Max products: {'Unlimited' if not max_products else max_products}")
    logger.info("=" * 80)
    
    try:
        logger.info("Initializing Market-In scraper...")
        scraper = MarketInScraper(headless=settings.HEADLESS)
        
        try:
            logger.info("Scraper initialized, starting to scrape deals...")
            
            # Call the updated scrape_with_pagination method
            deals = scraper.scrape_with_pagination(
                max_pages=max_pages,
                max_total_deals=max_products
            )
            
            logger.info(f"Scraping completed, {len(deals) if deals else 0} deals scraped")
            
            if deals:
                logger.info(f"Processing {len(deals)} deals...")
                save_deals_to_db(deals)
                logger.info("=" * 80)
                logger.info(f"✓ SCRAPING JOB COMPLETED SUCCESSFULLY - {len(deals)} deals processed")
                logger.info("=" * 80)
            else:
                logger.warning("✗ No deals were scraped")
                
        finally:
            scraper.close()
                
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"✗ SCRAPING JOB FAILED: {e}", exc_info=True)
        logger.error("=" * 80)
@app.on_event("startup")
async def startup_event():
    """Run scraping on application startup"""
    logger.info("=" * 80)
    logger.info("STARTUP EVENT: Triggering initial scraping of all pages...")
    logger.info("=" * 80)
    # Scrape all pages on startup
    run_scraping(max_products=10000, max_pages=1000) 

@app.get("/")
def read_root():
    logger.info("GET / - Root endpoint accessed")
    return {
        "message": "Market-In.gr Deals API",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "deals": "/deals",
            "scrape": "/scrape (POST)",
            "categories": "/categories",
            "health": "/health",
            "stats": "/stats"
        }
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        logger.info("GET /health - Performing health check")
        db.execute("SELECT 1")
        deal_count = db.query(Deal).count()
        logger.info("✓ Health check passed - database connected")
        return {
            "status": "healthy", 
            "database": "connected",
            "deals_count": deal_count
        }
    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500

@app.get("/deals", response_model=dict)
def get_deals(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    min_discount: Optional[float] = Query(None, ge=0, le=100),
    max_price: Optional[float] = Query(None, ge=0),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    sort_by: str = Query("discount", regex="^(discount|price|newest|oldest)$"),
    search: Optional[str] = None,
    super_star_only: bool = Query(False)
):
    """Get all deals with optional filtering and sorting"""
    logger.info(f"GET /deals - skip={skip}, limit={limit}, category={category}")
    
    query = db.query(Deal).filter(Deal.is_active == True)
    
    if category:
        query = query.filter(Deal.category.ilike(f"%{category}%"))
    
    if min_discount:
        query = query.filter(Deal.discount_percentage >= min_discount)
    
    if max_price:
        query = query.filter(Deal.current_price <= max_price)
    
    if min_rating:
        query = query.filter(Deal.rating >= min_rating)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Deal.title.ilike(search_term),
                Deal.category.ilike(search_term),
                Deal.specs.ilike(search_term)
            )
        )
    
    if super_star_only:
        query = query.filter(Deal.discount_percentage.isnot(None))
    
    if sort_by == "discount":
        query = query.order_by(desc(Deal.discount_percentage))
    elif sort_by == "price":
        query = query.order_by(Deal.current_price)
    elif sort_by == "newest":
        query = query.order_by(desc(Deal.scraped_at))
    elif sort_by == "oldest":
        query = query.order_by(Deal.scraped_at)
    
    total = query.count()
    deals = query.offset(skip).limit(limit).all()
    
    response = [
        {
            "id": deal.id,
            "title": deal.title,
            "category": deal.category,
            "specs": deal.specs,
            "original_price": deal.original_price,
            "current_price": deal.current_price,
            "discount_percentage": deal.discount_percentage,
            "rating": deal.rating,
            "review_count": deal.review_count,
            "redirect_url": deal.get_redirect_url(),
            "image_url": deal.image_url,
            "shop_count": deal.shop_count,
            "product_id": deal.product_id,
            "scraped_at": deal.scraped_at.isoformat() if deal.scraped_at else None,
            "created_at": deal.created_at.isoformat() if deal.created_at else None
        }
        for deal in deals
    ]
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "deals": response
    }

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get scraping statistics"""
    logger.info("GET /stats - Getting statistics")
    
    total_deals = db.query(Deal).count()
    active_deals = db.query(Deal).filter(Deal.is_active == True).count()
    
    # Get deals by category
    categories = db.query(Deal.category).distinct().all()
    category_count = len([c for c in categories if c[0]])
    
    # Get average discount
    avg_discount = db.query(db.func.avg(Deal.discount_percentage)).filter(
        Deal.discount_percentage.isnot(None)
    ).scalar()
    
    # Get newest scraped deal
    newest = db.query(Deal).order_by(desc(Deal.scraped_at)).first()
    
    return {
        "total_deals": total_deals,
        "active_deals": active_deals,
        "categories_count": category_count,
        "average_discount": round(float(avg_discount or 0), 2),
        "last_scraped": newest.scraped_at.isoformat() if newest else None,
        "newest_deal": newest.title if newest else None
    }

@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """Get all available categories"""
    logger.info("GET /categories - Getting categories")
    
    categories = db.query(Deal.category).distinct().filter(Deal.category.isnot(None)).all()
    
    return {
        "categories": [cat[0] for cat in categories if cat[0]],
        "count": len([cat for cat in categories if cat[0]])
    }

@app.post("/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks, 
    max_pages: int = Query(None, ge=1, le=1000),
    max_products: int = Query(None, ge=10, le=10000),
    scrape_all: bool = Query(False)
):
    """Manually trigger scraping"""
    logger.info(f"POST /scrape - max_pages={max_pages}, max_products={max_products}, scrape_all={scrape_all}")
    
    if scrape_all:
        # Set very high limits for "scrape all"
        max_pages = 1000
        max_products = 10000
        message = "Scraping ALL pages started in background"
    else:
        message = "Scraping started in background"
    
    background_tasks.add_task(run_scraping, max_products, max_pages)
    return {
        "message": message,
        "max_pages": max_pages if not scrape_all else "Unlimited",
        "max_products": max_products if not scrape_all else "Unlimited",
        "scrape_all": scrape_all,
        "status": "processing",
        "note": "Check logs for progress"
    }

@app.delete("/deals/{product_id}")
def delete_deal(product_id: str, db: Session = Depends(get_db)):
    """Delete or deactivate a deal"""
    logger.info(f"DELETE /deals/{product_id} - Deleting deal")
    
    deal = db.query(Deal).filter(Deal.product_id == product_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    deal.is_active = False
    db.commit()
    
    return {"message": f"Deal {product_id} deactivated successfully"}

@app.get("/deals/{product_id}")
def get_deal_by_id(product_id: str, db: Session = Depends(get_db)):
    """Get a specific deal by product ID"""
    logger.info(f"GET /deals/{product_id} - Getting specific deal")
    
    deal = db.query(Deal).filter(
        Deal.product_id == product_id,
        Deal.is_active == True
    ).first()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {
        "id": deal.id,
        "title": deal.title,
        "category": deal.category,
        "specs": deal.specs,
        "original_price": deal.original_price,
        "current_price": deal.current_price,
        "discount_percentage": deal.discount_percentage,
        "rating": deal.rating,
        "review_count": deal.review_count,
        "redirect_url": deal.get_redirect_url(),
        "image_url": deal.image_url,
        "shop_count": deal.shop_count,
        "product_id": deal.product_id,
        "scraped_at": deal.scraped_at.isoformat() if deal.scraped_at else None,
        "created_at": deal.created_at.isoformat() if deal.created_at else None
    }

logger.info("=" * 80)
logger.info("Application startup complete - ready to accept requests")
logger.info("=" * 80)