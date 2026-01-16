import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/deals")
    
    # Selenium
    CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "chromedriver")
    HEADLESS = os.getenv("HEADLESS", "True").lower() == "true"
    
    # Scraping - Updated for market-in.gr
    BASE_URL = "https://www.market-in.gr"
    DEALS_URL = "https://www.market-in.gr/el-gr/ALL/1-1/"
    
    # Pagination settings
    MAX_PAGES = int(os.getenv("MAX_PAGES", "10"))
    DEALS_PER_PAGE = int(os.getenv("DEALS_PER_PAGE", "20"))
    PAGE_DELAY_SECONDS = int(os.getenv("PAGE_DELAY_SECONDS", "3"))
    DEFAULT_MAX_PRODUCTS = int(os.getenv("DEFAULT_MAX_PRODUCTS", "200"))
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "logs/marketin_scraper.log"
    
    # Request settings
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]

settings = Settings()