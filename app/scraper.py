import time
import logging
import re
import sys
import os
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from shutil import which

from app.config import settings

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MarketInScraper:
    def __init__(self, headless=True):
        self.base_url = settings.BASE_URL
        self.deals_url = settings.DEALS_URL
        self.headless = headless
        self.driver = None
        self.scroll_pause_time = 1
        self.max_scroll_attempts = 10
        self.max_pages = settings.MAX_PAGES
        self.deals_per_page = settings.DEALS_PER_PAGE
        self.page_delay = settings.PAGE_DELAY_SECONDS
        logger.info(f"MarketInScraper initialized - headless={headless}, max_pages={self.max_pages}")
    
    def setup_driver(self):
        """Setup Chrome driver with anti-bot measures"""
        logger.info("Setting up Chrome driver...")
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            logger.info("Chrome running in headless mode")
        
        # Essential arguments
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Realistic browser fingerprint
        chrome_options.add_argument(f"user-agent={random.choice(settings.USER_AGENTS)}")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        # Disable features that might trigger bot detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Enable JavaScript and cookies
        prefs = {
            "profile.default_content_setting_values.cookies": 1,
            "profile.default_content_setting_values.javascript": 1,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            local = os.environ.get('CHROMEDRIVER_PATH') or which('chromedriver')
            if local:
                service = Service(local)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info(f"✓ Using local ChromeDriver at: {local}")
            else:
                service = Service()
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("✓ Using Selenium's ChromeDriver manager")
            
            # Stealth modifications
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✓ Chrome driver initialized with stealth mode")
            
        except Exception as e:
            logger.error(f"✗ Failed to create Chrome driver: {e}", exc_info=True)
            raise
    
    def scrape_deals(self, max_products=200):
        """Main scraping function"""
        if not self.driver:
            self.setup_driver()
        
        logger.info(f"Scraping {max_products} products from market-in.gr")
        
        # Calculate pages needed
        pages_needed = max(max_products // self.deals_per_page, 1)
        
        return self.scrape_with_pagination(
            max_pages=min(pages_needed, self.max_pages),
            max_total_deals=max_products
        )
    
    def scrape_with_pagination(self, max_pages=None, max_total_deals=None):
        """Scrape deals with pagination until no more pages"""
        if not self.driver:
            self.setup_driver()
        
        logger.info("=" * 80)
        logger.info(f"STARTING PAGINATION SCRAPING - market-in.gr")
        logger.info(f"Max pages to scrape: {max_pages if max_pages else 'Unlimited'}")
        logger.info(f"Max total deals: {max_total_deals}")
        logger.info("=" * 80)
        
        all_deals = []
        current_page = 1
        consecutive_empty_pages = 0
        
        try:
            while True:
                # Check max pages limit
                if max_pages and current_page > max_pages:
                    logger.info(f"✓ Reached max pages limit: {max_pages}")
                    break
                
                logger.info(f"\n{'='*60}")
                logger.info(f"PROCESSING PAGE {current_page}")
                logger.info(f"{'='*60}")
                
                # Navigate to the specific page
                if current_page == 1:
                    url = self.deals_url
                else:
                    url = f"{self.deals_url}?pageno={current_page}"
                
                logger.info(f"Loading URL: {url}")
                self.driver.get(url)
                
                # Wait for page to load with randomized delay
                time.sleep(2 + random.uniform(1, 2))
                
                # Check if page exists and has content
                page_source = self.driver.page_source
                
                # Check for 404 or empty page
                if "404" in self.driver.title.lower() or len(page_source) < 10000:
                    logger.warning(f"⚠ Page {current_page} appears to be empty or doesn't exist")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        logger.info(f"✓ No more pages found after {consecutive_empty_pages} consecutive empty pages")
                        break
                    current_page += 1
                    continue
                
                # Reset consecutive empty pages counter
                consecutive_empty_pages = 0
                
                # Get current URL and title
                current_url = self.driver.current_url
                page_title = self.driver.title
                logger.info(f"Current URL: {current_url}")
                logger.info(f"Page title: {page_title}")
                
                # Scroll to load content
                self.scroll_page()
                
                # Parse the page
                page_deals = self.parse_current_page()
                
                if page_deals:
                    # Check if we're getting duplicate content (stuck on same page)
                    if all_deals and len(page_deals) > 0:
                        # Compare first deal title with last page's first deal title
                        current_first_title = page_deals[0]['title'][:50]
                        last_first_title = all_deals[-len(page_deals)]['title'][:50] if len(all_deals) >= len(page_deals) else ""
                        
                        if current_first_title == last_first_title:
                            logger.warning(f"⚠ Page {current_page} appears to have duplicate content")
                            logger.info("✓ Likely reached the last page")
                            break
                    
                    # Log some sample deals
                    sample_titles = [deal['title'][:30] for deal in page_deals[:3]]
                    logger.info(f"Sample deals from page {current_page}: {sample_titles}")
                    
                    all_deals.extend(page_deals)
                    logger.info(f"✓ Page {current_page}: Added {len(page_deals)} deals (total: {len(all_deals)})")
                    
                    # Check max deals limit
                    if max_total_deals and len(all_deals) >= max_total_deals:
                        logger.info(f"✓ Reached max deals: {max_total_deals}")
                        all_deals = all_deals[:max_total_deals]
                        break
                else:
                    logger.warning(f"⚠ No deals found on page {current_page}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        logger.info(f"✓ No more content after {consecutive_empty_pages} consecutive empty pages")
                        break
                
                # Try to find next page button or check pagination
                try:
                    soup = BeautifulSoup(page_source, 'html.parser')
                    pagination = soup.select_one('.pagination')
                    
                    if pagination:
                        # Look for current page indicator
                        current_page_elem = pagination.select_one('.current-page')
                        if current_page_elem:
                            logger.info(f"Found current page indicator in pagination")
                        
                        # Check if there's a next page link
                        next_links = pagination.select('a[href*="pageno="]')
                        next_page_numbers = []
                        for link in next_links:
                            href = link.get('href', '')
                            match = re.search(r'pageno=(\d+)', href)
                            if match:
                                next_page_numbers.append(int(match.group(1)))
                        
                        # Find max page number
                        if next_page_numbers:
                            max_page_found = max(next_page_numbers)
                            logger.info(f"Pagination shows pages up to: {max_page_found}")
                            
                            if current_page >= max_page_found:
                                logger.info(f"✓ Reached last page according to pagination")
                                break
                    
                    # Alternative: check for disabled next button
                    disabled_next = soup.select_one('.pagination .disabled')
                    if disabled_next and "next" in str(disabled_next).lower():
                        logger.info(f"✓ Next button is disabled, likely last page")
                        break
                        
                except Exception as e:
                    logger.debug(f"Error checking pagination: {e}")
                
                current_page += 1
                
                # Random delay between pages to look more human
                delay = self.page_delay + random.uniform(1, 2)
                logger.info(f"Waiting {delay:.1f} seconds before next page...")
                time.sleep(delay)
            
            logger.info("=" * 80)
            logger.info(f"✓ SCRAPING COMPLETED")
            logger.info(f"Total pages scraped: {current_page - 1}")
            logger.info(f"Total deals collected: {len(all_deals)}")
            logger.info("=" * 80)
            
            return all_deals
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"✗ SCRAPING FAILED on page {current_page}")
            logger.error(f"Error: {e}", exc_info=True)
            logger.error(f"Total deals collected: {len(all_deals)}")
            logger.error("=" * 80)
            return all_deals
    def has_next_page(self, soup):
        """Check if there's a next page available"""
        try:
            # Check pagination component
            pagination = soup.select_one('.pagination')
            if not pagination:
                return True  # Assume there might be more pages
            
            # Check for next page links
            next_links = pagination.select('a[href*="pageno="]')
            if not next_links:
                return False
            
            # Get current page number from URL or element
            current_page_elem = pagination.select_one('.current-page')
            if current_page_elem:
                current_text = current_page_elem.get_text(strip=True)
                try:
                    current_page_num = int(current_text)
                except:
                    current_page_num = 1
            else:
                # Try to extract from URL
                current_url = self.driver.current_url
                match = re.search(r'pageno=(\d+)', current_url)
                current_page_num = int(match.group(1)) if match else 1
            
            # Find all page numbers in pagination
            page_numbers = []
            for link in pagination.select('a'):
                text = link.get_text(strip=True)
                if text.isdigit():
                    page_numbers.append(int(text))
                else:
                    # Try to extract from href
                    href = link.get('href', '')
                    match = re.search(r'pageno=(\d+)', href)
                    if match:
                        page_numbers.append(int(match.group(1)))
            
            if page_numbers:
                max_page = max(page_numbers)
                return current_page_num < max_page
            
            return True  # Default to continue
            
        except Exception as e:
            logger.debug(f"Error checking next page: {e}")
            return True  # On error, assume there might be more pages
        
    def scroll_page(self):
        """Scroll page to load content"""
        logger.info("Scrolling page...")
        
        # Scroll down multiple times
        for i in range(3):
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_position = scroll_height * (i + 1) / 4
            self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
            time.sleep(0.5 + random.uniform(0, 0.5))
        
        # Final scroll to bottom
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
    
    def parse_current_page(self):
        """Parse deals from current page for market-in.gr"""
        # Get page source
        page_source = self.driver.page_source
        
        # Check if page has content
        if len(page_source) < 5000:
            logger.warning("Page source seems very small, might be an error page")
            return []
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find all product cards - market-in.gr structure
        product_cards = soup.select('div.product-col')
        logger.info(f"Found {len(product_cards)} product cards on page")
        
        if not product_cards:
            # Try alternative selectors
            product_cards = soup.select('.product-item')
            logger.info(f"Found {len(product_cards)} product cards with alternative selector")
        
        deals = []
        for idx, card in enumerate(product_cards, 1):
            try:
                deal_data = self.parse_product_card(card)
                if deal_data:
                    deals.append(deal_data)
                    
                    # Log progress every 5 deals
                    if idx % 5 == 0:
                        logger.debug(f"  Parsed {idx}/{len(product_cards)} deals")
            except Exception as e:
                logger.error(f"Error parsing product {idx}: {e}")
                continue
        
        return deals
    
    def parse_product_card(self, card):
        """Parse individual product card for market-in.gr"""
        # Extract product ID from add-to-cart button
        add_to_cart_btn = card.select_one('a.add-to-cart-btn')
        product_id = add_to_cart_btn.get('data-id', '') if add_to_cart_btn else ""
        
        # Title
        title_elem = card.select_one('a.product-ttl')
        title = title_elem.get_text(strip=True) if title_elem else "No title"
        
        # Brand (we'll include it in specs or title)
        brand_elem = card.select_one('a.product-brand')
        brand = brand_elem.get_text(strip=True) if brand_elem else ""
        
        # Category - from URL or we can extract from breadcrumbs
        category_elem = card.select_one('a.product-ttl')
        category = ""
        if category_elem:
            href = category_elem.get('href', '')
            # Extract category from URL path
            if '/el-gr/' in href:
                parts = href.split('/')
                if len(parts) > 4:
                    category = parts[3].replace('-', ' ').title()
        
        # Discount badge
        discount_elem = card.select_one('.disc-value')
        discount_percentage = None
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True)
            discount_percentage = self.extract_discount_percentage(discount_text)
        
        # Prices
        original_price = None
        current_price = None
        
        old_price_elem = card.select_one('.old-price')
        if old_price_elem:
            original_price = self.extract_price(old_price_elem.get_text())
        
        new_price_elem = card.select_one('.new-price')
        if new_price_elem:
            current_price = self.extract_price(new_price_elem.get_text())
        
        # If no old price but we have discount, calculate original price
        if not original_price and current_price and discount_percentage:
            original_price = round(current_price / (1 - discount_percentage/100), 2)
        
        # Product URL
        link_elem = card.select_one('a.product-thumb')
        if link_elem:
            product_url = link_elem.get('href', '')
        else:
            title_link = card.select_one('a.product-ttl')
            product_url = title_link.get('href', '') if title_link else ""
        
        # Image URL
        img_elem = card.select_one('img')
        image_url = img_elem.get('src', '') if img_elem else ''
        if image_url and not image_url.startswith('http'):
            image_url = f"{self.base_url}{image_url}"
        
        # Unit price (per kg/liter) - include in specs
        kg_price_elem = card.select_one('.kg-price-weight span')
        unit_price_text = ""
        if kg_price_elem:
            # Get the bold text which usually contains unit price
            bold_elem = kg_price_elem.select_one('span[style*="font-weight:bold"]')
            if bold_elem:
                unit_price_text = bold_elem.get_text(strip=True)
        
        # Extract weight/volume from title or other elements
        weight_match = re.search(r'(\d+[\.,]?\d*)\s*(?:gr|γρ|g|kg|κιλό|ml|λίτρο|l)', title, re.IGNORECASE)
        weight = weight_match.group(1) if weight_match else ""
        
        # Create specs string with brand and other info
        specs_parts = []
        if brand:
            specs_parts.append(f"Brand: {brand}")
        if weight:
            specs_parts.append(f"Weight: {weight}")
        if unit_price_text:
            specs_parts.append(f"Unit Price: {unit_price_text}")
        
        specs = " | ".join(specs_parts) if specs_parts else ""
        
        return {
            'title': title[:500],
            'category': category[:200] if category else "Uncategorized",
            'specs': specs[:500],
            'original_price': original_price,
            'current_price': current_price,
            'discount_percentage': discount_percentage,
            'rating': 0.0,  # market-in.gr doesn't seem to have ratings
            'review_count': 0,
            'product_url': product_url,
            'image_url': image_url,
            'skuid': product_id,
            'product_id': product_id,
            'shop_count': "1",  # Single shop (market-in.gr)
            'is_active': True,
            'scraped_at': datetime.now()
        }
    def extract_price(self, price_text):
        """Extract numeric price from text for market-in.gr format"""
        if not price_text:
            return None
        
        try:
            # Handle Greek format: "5,89 €" -> 5.89
            price_text = str(price_text).replace('€', '').replace(' ', '').strip()
            price_text = price_text.replace(',', '.')
            matches = re.findall(r'\d+\.?\d*', price_text)
            return float(matches[0]) if matches else None
        except Exception as e:
            logger.debug(f"Error extracting price: {e}")
            return None
    
    def extract_discount_percentage(self, discount_text):
        """Extract discount percentage from badge text"""
        if not discount_text:
            return None
        
        try:
            discount_text = str(discount_text).replace('-', '').replace('%', '').strip()
            return float(discount_text) if discount_text else None
        except Exception as e:
            logger.debug(f"Error extracting discount: {e}")
            return None
    
    def close(self):
        """Close the driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✓ Chrome driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Chrome driver: {e}")