import logging
import time
from typing import List, Dict, Any, Optional
from .marketin_scraper import MarketInScraper
from .ab_scraper import ABScraper
from .kritikos_scraper import KritikosScraper
# from .skroutz_scraper import SkroutzScraper
# from .bestprice_scraper import BestPriceScraper
# from .eshop_scraper import EshopScraper
# from .kotsovolos_scraper import KotsovolosScraper
# from .plaisio_scraper import PlaisioScraper
from .masoutis_scraper import MasoutisScraper
from .sklavenitis_scraper import SklavenitisScraper
from app.config import settings

logger = logging.getLogger("deals-api")

class ScraperManager:
    """Manages all scrapers with configuration support"""
    
    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else settings.HEADLESS
        self.scrapers = self._initialize_scrapers()
        self.enabled_scrapers = self._get_enabled_scrapers()
        logger.info(f"ScraperManager initialized with {len(self.enabled_scrapers)} enabled scrapers")
        logger.info(f"Available scrapers: {list(self.scrapers.keys())}")  # Debug line
    
    def _initialize_scrapers(self) -> Dict[str, Any]:
        """Initialize all scrapers"""
        scrapers = {}
        
        # Dynamically create scrapers based on config
        scraper_classes = {
            'market-in.gr': MarketInScraper,
            'sklavenitis': SklavenitisScraper, 
             'ab.gr': ABScraper,
             'masoutis.gr': MasoutisScraper,
              'kritikos-sm.gr': KritikosScraper,
        }
        
        logger.info(f"Initializing scrapers from config: {list(settings.WEBSITES.keys())}")
        
        for website_name, scraper_class in scraper_classes.items():
            logger.info(f"Processing website: {website_name}")
            
            if website_name in settings.WEBSITES:
                try:
                    scraper = scraper_class(headless=self.headless)
                    scrapers[website_name] = scraper
                    logger.info(f"✅ Successfully initialized scraper for {website_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize scraper for {website_name}: {e}", exc_info=True)
            else:
                logger.warning(f"⚠ Website {website_name} not found in settings.WEBSITES")
        
        return scrapers
    
    def _get_enabled_scrapers(self) -> Dict[str, Any]:
        """Get only enabled scrapers based on config"""
        enabled_scrapers = {}
        enabled_websites = settings.get_enabled_websites()
        
        for website_name in enabled_websites:
            if website_name in self.scrapers:
                enabled_scrapers[website_name] = self.scrapers[website_name]
        
        return enabled_scrapers
    
    def run_all_scrapers(
        self, 
        max_pages: Optional[int] = None,
        max_total_deals: Optional[int] = None,
        specific_scrapers: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Run all enabled scrapers sequentially with progress & per-scraper stats"""

        all_deals: List[Dict[str, Any]] = []
        scraper_stats: Dict[str, int] = {}

        # Determine which scrapers to run
        scrapers_to_run = self.enabled_scrapers
        if specific_scrapers:
            scrapers_to_run = {
                name: scraper
                for name, scraper in self.enabled_scrapers.items()
                if name in specific_scrapers
            }

        total_scrapers = len(scrapers_to_run)

        logger.info(f"🧩 Total scrapers to run: {total_scrapers}")
        logger.info(f"📌 Scrapers: {list(scrapers_to_run.keys())}")

        for index, (scraper_name, scraper) in enumerate(scrapers_to_run.items(), start=1):
            logger.info(
                f"🚀 [{index}/{total_scrapers}] Starting scraper: {scraper_name}"
            )

            try:
                website_config = settings.get_website_config(scraper_name)

                scraper_max_pages = (
                    max_pages
                    or website_config.get("max_pages", settings.DEFAULT_MAX_PAGES)
                )
                scraper_max_deals = max_total_deals or settings.DEFAULT_MAX_PRODUCTS

                logger.info(
                    f"   Limits → pages={scraper_max_pages}, deals={scraper_max_deals}"
                )

                # Run scraper
                deals = scraper.scrape_deals(
                    max_pages=scraper_max_pages,
                    max_total_deals=scraper_max_deals,
                )

                deal_count = len(deals) if deals else 0
                scraper_stats[scraper_name] = deal_count

                if deal_count > 0:
                    all_deals.extend(deals)
                    logger.info(
                        f"✅ [{index}/{total_scrapers}] {scraper_name} finished: {deal_count} deals scraped"
                    )
                else:
                    logger.warning(
                        f"⚠ [{index}/{total_scrapers}] {scraper_name} finished: no deals found"
                    )

            except Exception as e:
                scraper_stats[scraper_name] = 0
                logger.error(
                    f"❌ [{index}/{total_scrapers}] {scraper_name} failed: {e}",
                    exc_info=True,
                )

            finally:
                # Always cleanup
                try:
                    scraper.close()
                except Exception:
                    logger.debug(f"{scraper_name}: driver already closed")

            # Cooldown (skip after last scraper)
            if index < total_scrapers:
                cooldown = settings.PERFORMANCE["scraper_cooldown"]
                logger.info(f"⏳ Cooling down for {cooldown}s before next scraper...")
                time.sleep(cooldown)

        # Final summary
        logger.info("📊 Scraping summary per scraper:")
        for name, count in scraper_stats.items():
            logger.info(f"   • {name}: {count} deals")

        logger.info(f"🏁 Total deals scraped (all scrapers): {len(all_deals)}")

        return all_deals

    
    def run_specific_scraper(
        self, 
        scraper_name: str, 
        max_pages: Optional[int] = None,
        max_total_deals: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Run a specific scraper"""
        if scraper_name not in self.enabled_scrapers:
            raise ValueError(f"Scraper '{scraper_name}' not found or disabled")
        
        scraper = self.enabled_scrapers[scraper_name]
        website_config = settings.get_website_config(scraper_name)
        
        # Get website-specific limits or use provided ones
        scraper_max_pages = max_pages or website_config.get('max_pages', settings.DEFAULT_MAX_PAGES)
        scraper_max_deals = max_total_deals or settings.DEFAULT_MAX_PRODUCTS
        
        try:
            deals = scraper.scrape_deals(
                max_pages=scraper_max_pages,
                max_total_deals=scraper_max_deals
            )
            scraper.close()
            return deals
        except Exception as e:
            logger.error(f"❌ {scraper_name}: Failed with error: {e}", exc_info=True)
            scraper.close()
            return []
    
    def get_available_scrapers(self) -> List[str]:
        """Get list of available scrapers"""
        return list(self.scrapers.keys())
    
    def get_enabled_scrapers_list(self) -> List[str]:
        """Get list of enabled scrapers"""
        return list(self.enabled_scrapers.keys())
    
    def get_scraper_config(self, scraper_name: str) -> Dict[str, Any]:
        """Get configuration for a specific scraper"""
        if scraper_name in settings.WEBSITES:
            return settings.WEBSITES[scraper_name]
        return {}
    
    def enable_scraper(self, scraper_name: str):
        """Enable a specific scraper"""
        if scraper_name in self.scrapers:
            if scraper_name not in self.enabled_scrapers:
                self.enabled_scrapers[scraper_name] = self.scrapers[scraper_name]
                logger.info(f"Enabled scraper: {scraper_name}")
    
    def disable_scraper(self, scraper_name: str):
        """Disable a specific scraper"""
        if scraper_name in self.enabled_scrapers:
            del self.enabled_scrapers[scraper_name]
            logger.info(f"Disabled scraper: {scraper_name}")
    
    def close_all(self):
        """Close all scraper drivers"""
        for scraper_name, scraper in self.scrapers.items():
            try:
                scraper.close()
                logger.debug(f"Closed {scraper_name} driver")
            except Exception as e:
                logger.error(f"Error closing {scraper_name}: {e}")