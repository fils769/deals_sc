# masoutis_scraper.py - FIXED WITH CORRECT SELECTORS
import re
import time
import logging
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .base_scraper import BaseScraper
import random

logger = logging.getLogger(__name__)

class MasoutisScraper(BaseScraper):
    """Scraper for masoutis.gr website with infinite scroll"""
    
    def __init__(self, headless=True):
        super().__init__(headless=headless, scraper_name="MasoutisScraper")
        self.base_url = "https://www.masoutis.gr"
        self.deals_url = "https://www.masoutis.gr/categories/index/prosfores?item=0"
        self.scroll_pause_time = 2.0
        self.max_scroll_attempts = 30  # More for infinite scroll
        self.target_deals_count = 200
    
    def scrape_deals(self, max_pages=None, max_total_deals=None):
        """Scrape deals from masoutis.gr"""
        if not self.driver:
            self.setup_driver()
        
        # Set target
        target_deals = max_total_deals or self.target_deals_count
        logger.info(f"{self.scraper_name}: Starting to scrape deals")
        logger.info(f"{self.scraper_name}: Target deals: {target_deals}")
        
        all_deals = []
        
        try:
            # Navigate with retry
            if not self.navigate_with_retry(self.deals_url):
                logger.error(f"{self.scraper_name}: Failed to load page")
                return all_deals
            
            # Wait for page to load
            time.sleep(3)
            
            # Apply discount filter
            self._apply_discount_filter()
            
            # Wait after filter
            time.sleep(3)
            
            logger.info(f"{self.scraper_name}: Starting infinite scroll")
            
            scroll_count = 0
            last_deals_count = 0
            same_count_streak = 0
            
            while scroll_count < self.max_scroll_attempts and len(all_deals) < target_deals:
                scroll_count += 1
                
                # Scroll down
                self.gentle_scroll_infinite(pause_time=2.0)
                
                # Wait for content to load
                time.sleep(2 + random.uniform(0.5, 1))
                
                # Parse current page
                current_deals = self.parse_current_page()
                logger.info(f"{self.scraper_name}: Scroll {scroll_count}: Found {len(current_deals)} deals")
                
                # Check if we got new deals
                if len(current_deals) == last_deals_count:
                    same_count_streak += 1
                    if same_count_streak >= 3:
                        logger.info(f"{self.scraper_name}: No new deals for 3 scrolls, stopping")
                        break
                else:
                    same_count_streak = 0
                    last_deals_count = len(current_deals)
                
                # Add unique deals
                existing_ids = {d.get('product_id') for d in all_deals if d.get('product_id')}
                new_deals = []
                for deal in current_deals:
                    deal_id = deal.get('product_id')
                    if deal_id and deal_id not in existing_ids:
                        new_deals.append(deal)
                        existing_ids.add(deal_id)
                
                if new_deals:
                    all_deals.extend(new_deals)
                    logger.info(f"{self.scraper_name}: Added {len(new_deals)} new deals (total: {len(all_deals)})")
                
                # Check target
                if len(all_deals) >= target_deals:
                    logger.info(f"{self.scraper_name}: Reached target of {target_deals} deals")
                    break
            
            logger.info(f"✓ {self.scraper_name}: Completed - {len(all_deals)} deals collected")
            return all_deals[:target_deals] if max_total_deals else all_deals
            
        except Exception as e:
            logger.error(f"✗ {self.scraper_name}: Scraping failed: {e}", exc_info=True)
            return all_deals
        finally:
            self.close()
    
    def _apply_discount_filter(self):
        """Apply discount percentage filter"""
        try:
            # Wait a bit for page
            time.sleep(2)
            
            # Find the sort dropdown
            sort_select = None
            selectors = [
                "select.sort-select",
                "select.form-select",
                ".sortCont select",
                "select[class*='sort']"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        sort_select = elements[0]
                        logger.info(f"{self.scraper_name}: Found sort dropdown")
                        break
                except:
                    continue
            
            if sort_select:
                # Set to discount percentage (value "2: 2")
                self.driver.execute_script("""
                    arguments[0].value = '2: 2';
                    var event = new Event('change', { bubbles: true });
                    arguments[0].dispatchEvent(event);
                """, sort_select)
                
                logger.info(f"{self.scraper_name}: Applied discount percentage filter")
                time.sleep(3)  # Wait for page to update
            
        except Exception as e:
            logger.warning(f"{self.scraper_name}: Could not apply filter: {e}")
    
    def parse_current_page(self):
        """Parse deals from current page"""
        try:
            page_source = self.driver.page_source
            if len(page_source) < 10000:
                logger.warning(f"{self.scraper_name}: Page source too small")
                return []
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find product containers - CORRECT SELECTOR
            product_containers = soup.select('div.productList > div.product')
            
            # Alternative: if above doesn't work, try this
            if not product_containers:
                product_containers = soup.select('div.product')
            
            logger.info(f"{self.scraper_name}: Found {len(product_containers)} product containers")
            
            deals = []
            for idx, container in enumerate(product_containers):
                try:
                    deal_data = self.parse_product_container(container)
                    if deal_data:
                        deals.append(deal_data)
                except Exception as e:
                    logger.debug(f"{self.scraper_name}: Error parsing product {idx}: {e}")
                    continue
            
            return deals
            
        except Exception as e:
            logger.error(f"{self.scraper_name}: Parse error: {e}")
            return []
    
    def parse_product_container(self, container):
        """Parse individual product container"""
        try:
            # Extract discount percentage
            discount_elem = container.select_one('.pDscntPercent')
            discount_text = discount_elem.get_text(strip=True) if discount_elem else ""
            discount_percentage = self.extract_discount_percentage(discount_text)
            
            # Extract title
            title_elem = container.select_one('.productTitle')
            title = title_elem.get_text(strip=True) if title_elem else "No title"
            
            # Extract product ID from URL
            product_id = ""
            link_elem = container.select_one('a.cursor[href*="/categories/item/"]')
            if link_elem:
                href = link_elem.get('href', '')
                # Extract ID from: /categories/item/...?3947363=
                match = re.search(r'\?(\d+)=', href)
                if match:
                    product_id = match.group(1)
            
            # Extract prices
            original_price_elem = container.select_one('.pStartPrice')
            original_price_text = original_price_elem.get_text(strip=True) if original_price_elem else ""
            original_price = self.extract_price(original_price_text)
            
            current_price_elem = container.select_one('.pDscntPrice')
            current_price_text = current_price_elem.get_text(strip=True) if current_price_elem else ""
            current_price = self.extract_price(current_price_text)
            
            # Extract unit prices
            start_unit_elem = container.select_one('.startPriceKg')
            start_unit_text = start_unit_elem.get_text(strip=True) if start_unit_elem else ""
            
            current_unit_elem = container.select_one('.priceKg')
            current_unit_text = current_unit_elem.get_text(strip=True) if current_unit_elem else ""
            
            # Calculate discount if not explicitly provided
            if not discount_percentage and original_price and current_price:
                try:
                    discount_percentage = ((original_price - current_price) / original_price) * 100
                    discount_percentage = round(discount_percentage, 1)
                except (ValueError, ZeroDivisionError):
                    discount_percentage = None
            
            # Product URL
            product_url = ""
            if link_elem:
                href = link_elem.get('href', '')
                if href:
                    product_url = urljoin(self.base_url, href)
            
            # Image URL
            image_url = ""
            img_elem = container.select_one('img.productImage')
            if img_elem:
                src = img_elem.get('src', '')
                if src:
                    image_url = urljoin(self.base_url, src)
            
            # Check for special tags (vegan, bio, etc.)
            tags = []
            bio_icons = container.select('.bioIcons')
            for icon in bio_icons:
                title_attr = icon.get('title', '')
                if title_attr:
                    tags.append(title_attr)
            
            # Category - try to extract from URL or guess from title
            category = "Uncategorized"
            if link_elem:
                href = link_elem.get('href', '')
                # Extract from URL path: /categories/item/category-name?12345=
                match = re.search(r'/categories/item/([^/?]+)', href)
                if match:
                    category_part = match.group(1)
                    # Clean up category name
                    category = category_part.replace('-', ' ').title()
            
            # If no category from URL, guess from title
            if category == "Uncategorized" and title:
                title_lower = title.lower()
                if any(word in title_lower for word in ['γαλα', 'τυρί', 'βούτυρο', 'γιαούρτι']):
                    category = "Dairy"
                elif any(word in title_lower for word in ['κρέας', 'κοτόπουλο', 'μοσχάρι', 'χοιρινό']):
                    category = "Meat"
                elif any(word in title_lower for word in ['ψωμί', 'ζυμαρικά', 'ρύζι', 'αλεύρι']):
                    category = "Bakery/Pasta"
                elif any(word in title_lower for word in ['φρούτα', 'λαχανικά', 'μπανάνα', 'μήλο']):
                    category = "Produce"
                elif any(word in title_lower for word in ['ποτό', 'χυμό', 'νερό', 'κρασί']):
                    category = "Beverages"
            
            # Build specs
            specs_parts = []
            if current_unit_text:
                specs_parts.append(f"Unit: {current_unit_text}")
            if start_unit_text:
                specs_parts.append(f"Original unit: {start_unit_text}")
            if tags:
                specs_parts.append(f"Tags: {', '.join(tags)}")
            
            specs = " | ".join(specs_parts)
            
            # Create deal object
            return {
                'title': title[:500],
                'category': category[:200],
                'specs': specs[:500],
                'original_price': original_price,
                'current_price': current_price,
                'discount_percentage': discount_percentage,
                'rating': 0.0,
                'review_count': 0,
                'product_url': product_url,
                'image_url': image_url,
                'skuid': product_id,
                'product_id': product_id,
                'shop_count': "1",
                'is_active': True,
                'scraped_at': datetime.now(),
                'source': 'masoutis.gr',
                'offer': discount_text.strip() if discount_text else "",  # Discount badge as offer
            }
            
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Parse container error: {e}")
            return None