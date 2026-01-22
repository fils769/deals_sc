import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.database import Base
from app.models import Deal

DATABASE_URL='postgresql://neondb_owner:npg_FMUDfKHpj98r@ep-sparkling-thunder-a4uyz8aa-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=True,
)

JSON_PATH = "./exports/deals.json"


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_deals():
    data = load_json(JSON_PATH)

    if not isinstance(data, list):
        raise ValueError("deals.json must contain a list of objects")

    deals = []
    for item in data:
        deals.append(
            Deal(
                title=item.get("title"),
                category=item.get("category"),
                specs=item.get("specs"),
                original_price=item.get("original_price"),
                current_price=item.get("current_price"),
                discount_percentage=item.get("discount_percentage"),
                rating=item.get("rating", 0.0),
                review_count=item.get("review_count", 0),
                product_url=item.get("product_url"),
                image_url=item.get("image_url"),
                skuid=item.get("skuid"),
                product_id=item.get("product_id"),
                shop_count=item.get("shop_count"),
                source=item.get("source", "market-in.gr"),
                scraped_at=item.get("scraped_at") and datetime.fromisoformat(item["scraped_at"]),
                is_active=item.get("is_active", True),
                offer=item.get("offer"),
            )
        )

    with Session(engine) as session:
        session.bulk_save_objects(deals)
        session.commit()

    print(f"✅ Seeded {len(deals)} deals successfully")


if __name__ == "__main__":
    seed_deals()
