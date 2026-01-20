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
            r'(\d+(?:\.?\d+?))\s+results',
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
                    
                    # Log sample deal info for debugging (first deal only)
                    if idx == 1:
                        self._log_sample_deal(deal_data)
                    
                    # Log progress every 5 products
                    if idx % 5 == 0 or idx == len(product_blocks):
                        logger.debug(f"{self.scraper_name}: Parsed {idx}/{len(product_blocks)} products "
                                   f"({(idx/len(product_blocks)*100):.0f}%)")
            except Exception as e:
                logger.error(f"{self.scraper_name}: Error parsing product {idx}: {e}", exc_info=True)
                continue
        
        return deals
    
    def _log_sample_deal(self, deal_data):
        """Log sample deal information for debugging"""
        logger.info(f"📝 {self.scraper_name}: Sample deal:")
        logger.info(f"  Title: {deal_data.get('title', 'N/A')}")
        logger.info(f"  Current Price: €{deal_data.get('current_price', 'N/A')}")
        logger.info(f"  Original Price: €{deal_data.get('original_price', 'N/A')}")
        logger.info(f"  Discount: {deal_data.get('discount_percentage', 'N/A')}%")
        logger.info(f"  Offer: {deal_data.get('offer', 'N/A')}")
        logger.info(f"  Product URL: {deal_data.get('product_url', 'N/A')}")
    
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
        
        # PROMOTION/OFFER - This is the key new field
        promotion_elem = block.select_one('[data-testid="tag-promo"]')
        offer = promotion_elem.get_text(strip=True) if promotion_elem else ""
        
        # Extract prices with the new format handling
        current_price = self._extract_current_price(block)
        original_price = self._extract_original_price(block)
        
        # Calculate discount if we have both prices
        discount_percentage = None
        if current_price and original_price and original_price > 0:
            discount_percentage = round(((original_price - current_price) / original_price) * 100, 1)
        
        # If discount not calculated from prices, try to extract from offer text
        if not discount_percentage and offer:
            match = re.search(r'(\d+)%', offer)
            if match:
                discount_percentage = float(match.group(1))
        
        # Product URL
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
    
    def _extract_current_price(self, block):
        """Extract current price from product block"""
        # Look for the main price element - NEW price
        price_elem = block.select_one('[data-testid="product-block-price"]')
        if not price_elem:
            return None
        
        # Log the HTML structure for debugging
        price_html = str(price_elem)[:200]
        logger.debug(f"{self.scraper_name}: Price element HTML: {price_html}")
        
        # Method 1: Extract from aria-label (most reliable)
        aria_label = price_elem.get('aria-label', '')
        logger.debug(f"{self.scraper_name}: Price aria-label: {aria_label}")
        
        if aria_label:
            # Try Greek format: "Νέα τιμή: 2 ευρώ και 94 λεπτά"
            if 'Νέα τιμή' in aria_label or 'New price' in aria_label:
                # Extract euros and cents
                euros_match = re.search(r'(\d+)\s+ευρώ|\s+(\d+)\s+euro', aria_label, re.IGNORECASE)
                cents_match = re.search(r'(\d+)\s+λεπτά|\s+(\d+)\s+cents', aria_label, re.IGNORECASE)
                
                if euros_match:
                    euros = float(euros_match.group(1) if euros_match.group(1) else euros_match.group(2))
                    if cents_match:
                        cents = float(cents_match.group(1) if cents_match.group(1) else cents_match.group(2)) / 100
                    else:
                        cents = 0
                    return round(euros + cents, 2)
            
            # Try any price pattern
            patterns = [
                r'(\d+)\s*ευρώ.*?(\d+)\s*λεπτά',  # Greek
                r'(\d+)\s*euro.*?(\d+)\s*cents',  # English
                r'€?\s*(\d+)[,\.](\d+)',  # €3,68 or €2.94
                r'(\d+)\^(\d+)',  # 2^94 format
            ]
            
            for pattern in patterns:
                match = re.search(pattern, aria_label, re.IGNORECASE)
                if match:
                    try:
                        if pattern in [r'€?\s*(\d+)[,\.](\d+)', r'(\d+)\^(\d+)']:
                            # For formats like €3,68 or 2^94
                            euros = float(match.group(1))
                            cents = float(match.group(2)) / 100
                            return round(euros + cents, 2)
                        else:
                            # For "X euros and Y cents" format
                            euros = float(match.group(1))
                            cents = float(match.group(2)) / 100
                            return round(euros + cents, 2)
                    except:
                        continue
        
        # Method 2: Extract from visible text structure
        # Look for the price parts in the specific structure
        try:
            # Find euro symbol element
            euro_elem = price_elem.select_one('.sc-dqia0p-7')
            if euro_elem:
                # Find euros number element
                euros_elem = price_elem.select_one('.sc-dqia0p-8, .hSCnvJ')
                # Find cents superscript element
                cents_elem = price_elem.select_one('.sc-dqia0p-9, .ibBxTt, sup')
                
                if euros_elem and cents_elem:
                    euros = float(euros_elem.get_text(strip=True))
                    cents = float(cents_elem.get_text(strip=True)) / 100
                    return round(euros + cents, 2)
        except:
            pass
        
        # Method 3: Extract all text and parse
        text = price_elem.get_text(strip=True)
        logger.debug(f"{self.scraper_name}: Price text: {text}")
        if text:
            return self._parse_price_text(text)
        
        return None
    
    def _extract_original_price(self, block):
        """Extract original price from product block"""
        # Look for old price element
        old_price_elem = block.select_one('[data-testid="product-block-old-price"]')
        if not old_price_elem:
            return None
        
        # Log the HTML structure for debugging
        old_price_html = str(old_price_elem)[:200]
        logger.debug(f"{self.scraper_name}: Old price element HTML: {old_price_html}")
        
        # Method 1: Extract from aria-label
        aria_label = old_price_elem.get('aria-label', '')
        logger.debug(f"{self.scraper_name}: Old price aria-label: {aria_label}")
        
        if aria_label:
            # Try Greek format: "Παλιά τιμή: 3 ευρώ και 68 λεπτά"
            if 'Παλιά τιμή' in aria_label or 'Old price' in aria_label:
                euros_match = re.search(r'(\d+)\s+ευρώ|\s+(\d+)\s+euro', aria_label, re.IGNORECASE)
                cents_match = re.search(r'(\d+)\s+λεπτά|\s+(\d+)\s+cents', aria_label, re.IGNORECASE)
                
                if euros_match:
                    euros = float(euros_match.group(1) if euros_match.group(1) else euros_match.group(2))
                    if cents_match:
                        cents = float(cents_match.group(1) if cents_match.group(1) else cents_match.group(2)) / 100
                    else:
                        cents = 0
                    return round(euros + cents, 2)
        
        # Method 2: Extract from visible text
        text = old_price_elem.get_text(strip=True)
        logger.debug(f"{self.scraper_name}: Old price text: {text}")
        if text:
            price = self._parse_price_text(text)
            if price:
                return price
        
        # Method 3: Look for span elements with class ETpLg (from your example)
        span_elements = old_price_elem.select('.sc-dqia0p-20, .ETpLg, span')
        for span in span_elements:
            text = span.get_text(strip=True)
            if text and ('€' in text or 'ευρώ' in text.lower()):
                price = self._parse_price_text(text)
                if price:
                    return price
        
        return None
    
    def _parse_price_text(self, price_text):
        """Parse price text like €3,68 or €2.94 or 2^94"""
        if not price_text:
            return None
        
        logger.debug(f"{self.scraper_name}: Parsing price text: '{price_text}'")
        
        try:
            # Clean the text
            text = price_text.strip()
            
            # Remove currency symbols and extra text
            text = re.sub(r'[^\d\^,\.]', '', text)
            
            # Handle 2^94 format
            if '^' in text:
                parts = text.split('^')
                if len(parts) == 2:
                    euros = float(parts[0])
                    cents = float(parts[1]) / 100
                    return round(euros + cents, 2)
            
            # Handle Greek format with comma as decimal: 3,68
            if ',' in text:
                # Remove dots as thousand separators if they exist
                if '.' in text:
                    # If format is like 1.234,56 (thousands separator)
                    parts = text.split(',')
                    if len(parts) == 2:
                        integer_part = parts[0].replace('.', '')
                        decimal_part = parts[1]
                        return float(f"{integer_part}.{decimal_part}")
                else:
                    # Simple comma as decimal: 3,68
                    text = text.replace(',', '.')
            
            # Parse the number
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                num = float(match.group(1))
                # If number is less than 100 and has no decimal, it might be in cents format
                if num < 100 and '.' not in match.group(1):
                    # Check if this looks like it should be in euros.cents format
                    if len(match.group(1)) > 2:
                        # Format like 294 -> 2.94
                        euros = int(match.group(1)[:-2])
                        cents = int(match.group(1)[-2:])
                        return round(euros + (cents / 100), 2)
                return num
            
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Error parsing price text '{price_text}': {e}")
        
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