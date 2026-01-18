from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Index
from sqlalchemy.sql import func
from app.database import Base

class Deal(Base):
    __tablename__ = "deals"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    category = Column(String(200))
    specs = Column(String(500))
    original_price = Column(Float)
    current_price = Column(Float)
    discount_percentage = Column(Float)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    product_url = Column(Text, nullable=False)
    image_url = Column(Text)
    skuid = Column(String(100))
    product_id = Column(String(100), index=True)
    shop_count = Column(String(100))
    source = Column(String(100), default="market-in.gr")  # Add source field
    scraped_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    offer = Column(String(200), nullable=True) 
    
    # Create indexes for better query performance
    __table_args__ = (
        Index('idx_product_id_source', 'product_id', 'source'),
        Index('idx_discount', 'discount_percentage'),
        Index('idx_current_price', 'current_price'),
        Index('idx_scraped_at', 'scraped_at'),
        Index('idx_source', 'source'),
    )
    
    def get_redirect_url(self):
        """Generate the full redirect URL for the deal"""
        if self.product_id and '?' not in self.product_url:
            return f"{self.product_url}?product_id={self.product_id}"
        return self.product_url