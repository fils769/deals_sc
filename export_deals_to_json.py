import os
import json
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models import Deal, Base
from app.config import settings

# --- Setup SQLAlchemy ---
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# --- Output file ---
output_dir = "exports"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, f"deals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

def export_deals_to_json():
    session = SessionLocal()
    try:
        print("Fetching deals from database...")
        deals = session.query(Deal).filter(Deal.is_active == True).all()
        print(f"Found {len(deals)} active deals. Exporting to JSON...")

        deals_list = [
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
                "redirect_url": deal.get_redirect_url() if hasattr(deal, "get_redirect_url") else None,
                "image_url": deal.image_url,
                "shop_count": deal.shop_count,
                "product_id": deal.product_id,
                "scraped_at": deal.scraped_at.isoformat() if deal.scraped_at else None,
                "created_at": deal.created_at.isoformat() if deal.created_at else None
            }
            for deal in deals
        ]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(deals_list, f, ensure_ascii=False, indent=4)

        print(f"✓ Export completed successfully: {output_file}")

    except Exception as e:
        print(f"✗ Error exporting deals: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    export_deals_to_json()
