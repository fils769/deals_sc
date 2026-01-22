from sqlalchemy import text
from app.database import engine, Base
from app.models import Deal

def reset_deals_table():
    with engine.connect() as conn:
        print("⚠️ Dropping deals table with CASCADE...")
        conn.execute(text("DROP TABLE IF EXISTS deals CASCADE;"))
        conn.commit()

    print("✅ Recreating deals table...")
    Base.metadata.create_all(bind=engine, tables=[Deal.__table__])

    print("🎉 Deals table successfully reset.")

if __name__ == "__main__":
    reset_deals_table()
