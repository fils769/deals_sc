# ab_scraper.py
import re
import time
import logging
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from .base_scraper import BaseScraper
import random

logger = logging.getLogger("deals-api")

class ABScraper(BaseScraper):
    """Scraper for ab.gr website"""
    
    def __init__(self, headless=True):
        super().__init__(headless=headless, scraper_name="ABScraper")
        self.base_url = "https://www.ab.gr"
        self.deals_url = "https://www.ab.gr/search/promotions"
        self.total_products = 0
        self.products_per_page = 24  # Typical for e-commerce sites
        self.start_time = None
        
    def scrape_deals(self, max_pages=None, max_total_deals=None):
        """Scrape deals from ab.gr"""
        self.start_time = datetime.now()
        if not self.driver:
            self.setup_driver()
        
        logger.info(f"{self.scraper_name}: Starting to scrape deals")
        logger.info(f"{self.scraper_name}: Max pages: {max_pages if max_pages else 'No limit'}")
        logger.info(f"{self.scraper_name}: Max total deals: {max_total_deals if max_total_deals else 'No limit'}")
        return self.scrape_with_pagination(max_pages, max_total_deals)
    
    def scrape_with_pagination(self, max_pages=None, max_total_deals=None):
        """Scrape deals with pagination"""
        logger.info(f"{self.scraper_name}: Starting pagination scraping")
        
        all_deals = []
        current_page = 1
        consecutive_empty_pages = 0
        MAX_CONSECUTIVE_EMPTY = 2
        MAX_SAFETY_PAGES = 50
        
        try:
            while True:
                # Safety checks
                if current_page > MAX_SAFETY_PAGES:
                    logger.warning(f"⚠ {self.scraper_name}: Hit safety limit of {MAX_SAFETY_PAGES} pages")
                    break
                    
                if max_pages and current_page > max_pages:
                    logger.info(f"✓ {self.scraper_name}: Reached max pages limit: {max_pages}")
                    break
                
                # Log progress
                elapsed_time = datetime.now() - self.start_time
                logger.info(f"📄 {self.scraper_name}: Processing page {current_page} | "
                           f"Total deals so far: {len(all_deals)} | "
                           f"Elapsed: {elapsed_time.seconds // 60}m {elapsed_time.seconds % 60}s")
                
                # Navigate to the specific page
                url = self.deals_url if current_page == 1 else f"{self.deals_url}?pageNumber={current_page}"
                logger.debug(f"{self.scraper_name}: Navigating to {url}")
                
                try:
                    logger.debug(f"{self.scraper_name}: Loading page {current_page}...")
                    self.driver.get(url)
                    # Wait for page to load
                    WebDriverWait(self.driver, 20).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )
                    
                    # Wait for products to load
                    logger.debug(f"{self.scraper_name}: Waiting for content to load...")
                    time.sleep(2 + random.uniform(1, 2))
                    
                    # Scroll to trigger lazy loading
                    logger.debug(f"{self.scraper_name}: Scrolling to load all content...")
                    self._scroll_for_content()
                    
                    logger.info(f"✅ {self.scraper_name}: Page {current_page} loaded successfully")
                    
                except TimeoutException as e:
                    logger.error(f"⚠ {self.scraper_name}: Timeout loading page {current_page}: {e}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= MAX_CONSECUTIVE_EMPTY:
                        break
                    current_page += 1
                    continue
                except Exception as e:
                    logger.error(f"⚠ {self.scraper_name}: Failed to load page {current_page}: {e}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= MAX_CONSECUTIVE_EMPTY:
                        break
                    current_page += 1
                    continue
                
                # Get page source
                page_source = self.driver.page_source
                
                # Check if page is valid
                if self._is_end_of_pages(page_source, current_page):
                    logger.info(f"✓ {self.scraper_name}: Reached end of pages at page {current_page}")
                    break
                
                if len(page_source) < 5000:
                    logger.warning(f"⚠ {self.scraper_name}: Page {current_page} source too small")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= MAX_CONSECUTIVE_EMPTY:
                        break
                    current_page += 1
                    continue
                
                # Extract pagination info on first page
                if current_page == 1:
                    self._extract_pagination_info(page_source)
                    # Log estimated progress after first page
                    if self.total_products > 0:
                        estimated_pages = (self.total_products + self.products_per_page - 1) // self.products_per_page
                        logger.info(f"📊 {self.scraper_name}: Estimated total: {self.total_products} products "
                                  f"across {estimated_pages} pages")
                
                # Parse current page
                logger.debug(f"{self.scraper_name}: Parsing page {current_page} content...")
                page_deals = self.parse_current_page()
                
                if page_deals:
                    all_deals.extend(page_deals)
                    logger.info(f"✅ {self.scraper_name}: Page {current_page}: Added {len(page_deals)} deals "
                              f"(Total: {len(all_deals)}/{self.total_products if self.total_products > 0 else '?'})")
                    
                    # Calculate progress percentage if we have total products
                    if self.total_products > 0:
                        progress = (len(all_deals) / self.total_products) * 100
                        logger.info(f"📈 {self.scraper_name}: Progress: {progress:.1f}% complete")
                    
                    # Reset consecutive empty counter
                    consecutive_empty_pages = 0
                    
                    if max_total_deals and len(all_deals) >= max_total_deals:
                        logger.info(f"✓ {self.scraper_name}: Reached max deals limit: {max_total_deals}")
                        all_deals = all_deals[:max_total_deals]
                        break
                    
                    # Check if we've scraped all products
                    if self.total_products > 0 and len(all_deals) >= self.total_products:
                        logger.info(f"✓ {self.scraper_name}: Scraped all {self.total_products} products")
                        break
                        
                else:
                    logger.warning(f"⚠ {self.scraper_name}: No deals found on page {current_page}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= MAX_CONSECUTIVE_EMPTY:
                        logger.info(f"{self.scraper_name}: {MAX_CONSECUTIVE_EMPTY} consecutive empty pages, stopping")
                        break
                
                # Calculate if we should continue based on total products
                if self.total_products > 0:
                    estimated_pages = (self.total_products + self.products_per_page - 1) // self.products_per_page
                    if current_page >= estimated_pages:
                        logger.info(f"✓ {self.scraper_name}: Reached estimated last page ({estimated_pages})")
                        break
                
                # Page delay before next page
                current_page += 1
                if current_page <= (max_pages if max_pages else estimated_pages if self.total_products > 0 else MAX_SAFETY_PAGES):
                    delay = self.page_delay + random.uniform(1, 3)
                    logger.debug(f"{self.scraper_name}: Waiting {delay:.1f} seconds before next page...")
                    time.sleep(delay)
            
            total_time = datetime.now() - self.start_time
            logger.info(f"✅ {self.scraper_name}: Scraping completed - {len(all_deals)} deals collected in "
                       f"{total_time.seconds // 60}m {total_time.seconds % 60}s")
            logger.info(f"📊 {self.scraper_name}: Average speed: "
                       f"{len(all_deals)/(total_time.seconds/60):.1f} deals per minute")
            return all_deals
            
        except Exception as e:
            logger.error(f"✗ {self.scraper_name}: Scraping failed: {e}", exc_info=True)
            return all_deals
        finally:
            self.close()
    
    def _scroll_for_content(self):
        """Scroll to trigger lazy loading of products"""
        try:
            # Scroll multiple times to load all content
            for i in range(3):
                scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_position = scroll_height * (i + 1) / 4
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                logger.debug(f"{self.scraper_name}: Scrolling to position {scroll_position:.0f}...")
                time.sleep(0.5 + random.uniform(0, 0.5))
            
            # Final scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Scroll back up a bit to ensure all elements are visible
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
            time.sleep(0.5)
            
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Scroll error: {e}")
    
    def _is_end_of_pages(self, page_source, current_page):
        """Check if we've reached the end of pagination"""
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Check 1: Look for no products message
        no_products_keywords = ['δεν βρέθηκαν προϊόντα', 'no products found', 'κανένα αποτέλεσμα']
        page_text = soup.get_text().lower()
        if any(keyword in page_text for keyword in no_products_keywords):
            logger.info(f"{self.scraper_name}: Found 'no products' message on page {current_page}")
            return True
        
        # Check 2: Check if there are no product blocks
        product_blocks = soup.select('[data-testid="product-block"]')
        if not product_blocks:
            logger.info(f"{self.scraper_name}: No product blocks found on page {current_page}")
            return True
        
        # Check 3: Look for pagination indicators
        pagination_elements = soup.select('[data-testid*="pagination"], .pagination, .page-numbers')
        if pagination_elements:
            for element in pagination_elements:
                text = element.get_text()
                if 'σελίδα' in text.lower() and 'από' in text.lower():
                    # Extract page numbers if available
                    match = re.search(r'(\d+)\s*από\s*(\d+)', text)
                    if match:
                        current, total = match.groups()
                        logger.info(f"{self.scraper_name}: Pagination shows {current} of {total} pages")
                        if int(current) > int(total):
                            logger.info(f"{self.scraper_name}: Current page {current} exceeds total {total}")
                            return True
        
        return False
    
    def _extract_pagination_info(self, page_source):
        """Extract pagination information from the first page"""
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Try to find total products count
        # Look for text like "X προϊόντα" or "X αντικείμενα"
        page_text = soup.get_text()
        patterns = [
            r'(\d+(?:\.?\d+)?)\s+προϊόντα',
            r'(\d+(?:\.?\d+)?)\s+αντικείμενα',
            r'(\d+(?:\.?\d+)?)\s+results',
            r'(\d+(?:\.?\d+)?)\s+items'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                self.total_products = int(match.group(1).replace('.', ''))
                logger.info(f"{self.scraper_name}: Found {self.total_products} total products")
                break
        
        # Calculate products per page from first page
        product_blocks = soup.select('[data-testid="product-block"]')
        if product_blocks:
            self.products_per_page = len(product_blocks)
            logger.info(f"{self.scraper_name}: Estimated {self.products_per_page} products per page")
        
        # Estimate total pages
        if self.total_products > 0 and self.products_per_page > 0:
            estimated_pages = (self.total_products + self.products_per_page - 1) // self.products_per_page
            logger.info(f"{self.scraper_name}: Estimated total pages: {estimated_pages}")
    
    def parse_current_page(self):
        """Parse deals from current page"""
        page_source = self.driver.page_source
        
        if len(page_source) < 10000:
            logger.warning(f"{self.scraper_name}: Page source too small")
            return []
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find all product blocks
        product_blocks = soup.select('[data-testid="product-block"]')
        
        logger.info(f"{self.scraper_name}: Found {len(product_blocks)} product blocks on page")
        
        deals = []
        for idx, block in enumerate(product_blocks, 1):
            try:
                deal_data = self.parse_product_block(block)
                if deal_data:
                    deals.append(deal_data)
                    
                    # Log progress every 5 products
                    if idx % 5 == 0 or idx == len(product_blocks):
                        logger.debug(f"{self.scraper_name}: Parsed {idx}/{len(product_blocks)} products "
                                   f"({(idx/len(product_blocks)*100):.0f}%)")
            except Exception as e:
                logger.error(f"{self.scraper_name}: Error parsing product {idx}: {e}")
                continue
        
        return deals
    
    def parse_product_block(self, block):
        """Parse individual product block for ab.gr"""
        from datetime import datetime
        
        # Extract product ID
        product_id_elem = block.select_one('[data-testid="product-id"]')
        product_id = product_id_elem.get_text(strip=True) if product_id_elem else ""
        
        # Extract SKU/position
        position_elem = block.select_one('[data-testid="search-position"]')
        skuid = position_elem.get_text(strip=True) if position_elem else product_id
        
        # Brand and Name
        brand_elem = block.select_one('[data-testid="product-brand"]')
        brand = brand_elem.get_text(strip=True) if brand_elem else ""
        
        name_elem = block.select_one('[data-testid="product-name"]')
        name = name_elem.get_text(strip=True) if name_elem else ""
        
        # Combine for title
        title = f"{brand} {name}".strip()
        
        # Category - try to extract from URL or structure
        category = "Uncategorized"
        link_elem = block.select_one('[data-testid="product-block-name-link"]')
        if link_elem:
            href = link_elem.get('href', '')
            if '/el/eshop/' in href:
                parts = href.split('/')
                if len(parts) > 4:
                    # Try to extract category from URL path
                    category_part = parts[3] if parts[3] else parts[2]
                    category = category_part.replace('-', ' ').title()
        
        # Weight/size
        weight_elem = block.select_one('[data-testid="product-block-supplementary-price"]')
        weight = weight_elem.get_text(strip=True) if weight_elem else ""
        
        # Price per unit
        price_per_unit_elem = block.select_one('[data-testid="product-block-price-per-unit"]')
        price_per_unit = price_per_unit_elem.get_text(strip=True) if price_per_unit_elem else ""
        
        # Total price
        total_price_elem = block.select_one('[data-testid="product-block-price"]')
        total_price_text = total_price_elem.get_text(strip=True) if total_price_elem else ""
        
        # Extract numeric price
        current_price = self.extract_price(total_price_text)
        
        # PROMOTION/OFFER - This is the key new field
        promotion_elem = block.select_one('[data-testid="tag-promo"]')
        offer = promotion_elem.get_text(strip=True) if promotion_elem else ""
        
        # Try to calculate discount from offer text
        discount_percentage = None
        if offer:
            # Look for percentage in offer text (e.g., "Με 20% έκπτωση")
            match = re.search(r'(\d+)%', offer)
            if match:
                discount_percentage = float(match.group(1))
            # Or look for discount amount
            elif 'έκπτωση' in offer.lower() or 'discount' in offer.lower():
                # Try to extract any number
                numbers = re.findall(r'\d+', offer)
                if numbers:
                    discount_percentage = float(numbers[0])
        
        # Original price calculation if we have discount
        original_price = None
        if discount_percentage and current_price:
            original_price = round(current_price / (1 - discount_percentage/100), 2)
        
        # Product URL
        link_elem = block.select_one('[data-testid="product-block-name-link"]') or \
                   block.select_one('[data-testid="product-block-image-link"]')
        product_url = ""
        if link_elem:
            href = link_elem.get('href', '')
            if href:
                if not href.startswith('http'):
                    product_url = urljoin(self.base_url, href)
                else:
                    product_url = href
        
        # Image URL
        img_elem = block.select_one('[data-testid="product-block-image"]')
        image_url = ""
        if img_elem:
            src = img_elem.get('src', '')
            if src:
                if not src.startswith('http'):
                    image_url = urljoin(self.base_url, src)
                else:
                    image_url = src
        
        # Build specs
        specs_parts = []
        if weight:
            specs_parts.append(f"Weight: {weight}")
        if price_per_unit:
            specs_parts.append(f"Unit price: {price_per_unit}")
        if brand:
            specs_parts.append(f"Brand: {brand}")
        
        specs = " | ".join(specs_parts)
        
        # Create final deal object
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
            'skuid': skuid,
            'product_id': product_id,
            'shop_count': "1",
            'is_active': True,
            'scraped_at': datetime.now(),
            'source': 'ab.gr',
            'offer': offer[:200] if offer else "",  # NEW FIELD: Promotional offer text
        }
    
    def extract_price(self, price_text):
        """Extract price from Greek format text"""
        if not price_text:
            return None
        
        try:
            price_str = str(price_text)
            
            # Remove currency symbols and text
            price_str = price_str.lower()
            price_str = re.sub(r'[^\d.,]', '', price_str)
            
            # Handle Greek decimal (comma as decimal separator)
            if ',' in price_str and '.' in price_str:
                # If both present, assume comma is decimal and dot is thousand separator
                price_str = price_str.replace('.', '').replace(',', '.')
            elif ',' in price_str:
                # Comma is decimal separator
                price_str = price_str.replace(',', '.')
            
            # Extract number
            match = re.search(r'(\d+\.?\d*)', price_str)
            if match:
                return float(match.group(1))
            
        except Exception:
            pass
        
        return None
    
    def extract_discount_percentage(self, discount_text):
        """Extract discount percentage from badge text"""
        if not discount_text:
            return None
        
        try:
            # Handle Greek percentage format
            discount_str = str(discount_text)
            
            # Remove non-numeric characters except dot and comma
            discount_str = re.sub(r'[^\d.,%]', '', discount_str)
            
            # Look for percentage sign
            if '%' in discount_str:
                # Extract number before %
                match = re.search(r'(\d+[.,]?\d*)%', discount_str)
                if match:
                    num_str = match.group(1).replace(',', '.')
                    return float(num_str)
            else:
                # Try to extract any number
                match = re.search(r'(\d+[.,]?\d*)', discount_str)
                if match:
                    num_str = match.group(1).replace(',', '.')
                    return float(num_str)
                    
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Error extracting discount: {e}")
        
        return None