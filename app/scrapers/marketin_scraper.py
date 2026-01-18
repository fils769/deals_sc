import re
import time
import logging
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from app.config import settings
import random

logger = logging.getLogger("deals-api")

class MarketInScraper(BaseScraper):
    """Scraper for market-in.gr website"""
    
    def __init__(self, headless=True):
        super().__init__(headless=headless, scraper_name="MarketInScraper")
        self.base_url = "https://www.market-in.gr"
        self.deals_url = "https://www.market-in.gr/el-gr/ALL/1-1/"
    
    def scrape_deals(self, max_pages=None, max_total_deals=None):
        """Scrape deals from market-in.gr"""
        if not self.driver:
            self.setup_driver()
        
        logger.info(f"{self.scraper_name}: Starting to scrape deals")
        return self.scrape_with_pagination(max_pages, max_total_deals)
    
    def scrape_with_pagination(self, max_pages=None, max_total_deals=None):
        """Scrape deals with pagination"""
        logger.info(f"{self.scraper_name}: Starting pagination scraping")
        
        all_deals = []
        current_page = 1
        max_consecutive_failures = 3  # Changed from 2 to be more tolerant
        
        try:
            while True:
                if max_pages and current_page > max_pages:
                    logger.info(f"✓ {self.scraper_name}: Reached max pages limit: {max_pages}")
                    break
                
                logger.info(f"{self.scraper_name}: Processing page {current_page}")
                
                # Navigate to the specific page
                if current_page == 1:
                    url = self.deals_url
                else:
                    url = f"{self.deals_url}?pageno={current_page}"
                
                self.driver.get(url)
                time.sleep(2 + random.uniform(1, 2))
                
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # ENHANCED: Multiple checks for valid product page
                page_is_valid = self._validate_page_content(soup, page_source)
                
                if not page_is_valid:
                    logger.warning(f"⚠ {self.scraper_name}: Page {current_page} appears invalid or is empty")
                    max_consecutive_failures -= 1
                    if max_consecutive_failures <= 0:
                        logger.info(f"✓ {self.scraper_name}: Too many invalid pages, stopping")
                        break
                    current_page += 1
                    continue
                
                # Reset failure counter on successful page
                max_consecutive_failures = 3
                
                self.scroll_page()
                time.sleep(0.5)  # Small delay after scrolling
                
                page_deals = self.parse_current_page()
                
                if page_deals:
                    all_deals.extend(page_deals)
                    logger.info(f"✓ {self.scraper_name}: Page {current_page}: Added {len(page_deals)} deals (total: {len(all_deals)})")
                    
                    if max_total_deals and len(all_deals) >= max_total_deals:
                        logger.info(f"✓ {self.scraper_name}: Reached max deals: {max_total_deals}")
                        all_deals = all_deals[:max_total_deals]
                        break
                else:
                    # If parse_current_page returns empty but page seemed valid
                    logger.warning(f"⚠ {self.scraper_name}: No deals parsed from page {current_page}")
                    max_consecutive_failures -= 1
                    if max_consecutive_failures <= 0:
                        logger.info(f"✓ {self.scraper_name}: Too many pages with no parsable deals, stopping")
                        break
                
                # Check for pagination limits
                if self._has_reached_page_limit(soup, current_page):
                    logger.info(f"✓ {self.scraper_name}: Reached natural page limit")
                    break
                
                current_page += 1
                delay = self.page_delay + random.uniform(1, 2)
                time.sleep(delay)
            
            logger.info(f"✓ {self.scraper_name}: Scraping completed - {len(all_deals)} deals collected")
            return all_deals
            
        except Exception as e:
            logger.error(f"✗ {self.scraper_name}: Scraping failed: {e}", exc_info=True)
            return all_deals

    def _validate_page_content(self, soup, page_source):
        """Validate if the page contains actual product content"""
        
        # Check 1: Page source minimum size
        if len(page_source) < 15000:  # Increased from 10000
            logger.debug(f"{self.scraper_name}: Page source too small")
            return False
        
        # Check 2: Look for product count indicator (from URL content: "Βρέθηκαν 306 προϊόντα")
        product_count_text = soup.find(text=lambda t: 'προϊόντα' in str(t) or 'προϊόν' in str(t))
        if product_count_text and '0 προϊόν' in str(product_count_text):
            logger.debug(f"{self.scraper_name}: Page shows 0 products")
            return False
        
        # Check 3: Look for actual product containers
        product_cards = soup.select('div.product-col, .product-item, .product-card')
        if not product_cards:
            logger.debug(f"{self.scraper_name}: No product cards found")
            return False
        
        # Check 4: Look for pagination elements that might indicate we're past the last page
        pagination_text = soup.get_text()
        if 'σελίδα' in pagination_text.lower() and 'από' in pagination_text.lower():
            # Try to extract current/total pages if available
            import re
            page_match = re.search(r'σελίδα\s*(\d+)\s*από\s*(\d+)', pagination_text, re.IGNORECASE)
            if page_match:
                current, total = page_match.groups()
                if int(current) > int(total):
                    logger.debug(f"{self.scraper_name}: Current page {current} exceeds total {total}")
                    return False
        
        # Check 5: Look for "no results" messages
        no_results_keywords = ['δεν βρέθηκαν', 'no results', 'κανένα αποτέλεσμα']
        page_text_lower = soup.get_text().lower()
        if any(keyword in page_text_lower for keyword in no_results_keywords):
            logger.debug(f"{self.scraper_name}: 'No results' message found")
            return False
        
        return True

    def _has_reached_page_limit(self, soup, current_page):
        """Check if we've reached the natural limit of pagination"""

        # Look for product count to estimate pages
        # From URL: "Βρέθηκαν 306 προϊόντα" = 306 products found
        product_count_text = soup.find(text=lambda t: 'Βρέθηκαν' in str(t) and 'προϊόντα' in str(t))
        if product_count_text:
            import re  # Move import inside the if block
            match = re.search(r'Βρέθηκαν\s+(\d+)\s+προϊόντα', str(product_count_text))
            if match:
                total_products = int(match.group(1))
                estimated_pages = (total_products + 23) // 24  # Assuming ~24 products per page
                
                if current_page > estimated_pages:
                    logger.info(f"{self.scraper_name}: Current page {current_page} exceeds estimated pages {estimated_pages}")
                    return True

        # Look for pagination controls that might be disabled
        next_button = soup.select_one('a.next, .pagination-next, [rel="next"]')
        if next_button and ('disabled' in str(next_button.get('class', '')) or 'disabled' in str(next_button)):
            logger.debug(f"{self.scraper_name}: Next button is disabled")
            return True

        return False
        
    def parse_current_page(self):
        """Parse deals from current page for market-in.gr"""
        page_source = self.driver.page_source
        
        if len(page_source) < 5000:
            logger.warning(f"{self.scraper_name}: Page source seems very small")
            return []
        
        soup = BeautifulSoup(page_source, 'html.parser')
        product_cards = soup.select('div.product-col')
        
        if not product_cards:
            product_cards = soup.select('.product-item')
        
        logger.info(f"{self.scraper_name}: Found {len(product_cards)} product cards")
        
        deals = []
        for idx, card in enumerate(product_cards, 1):
            try:
                deal_data = self.parse_product_card(card)
                if deal_data:
                    deals.append(deal_data)
                    
                    if idx % 5 == 0:
                        logger.debug(f"{self.scraper_name}: Parsed {idx}/{len(product_cards)} deals")
            except Exception as e:
                logger.error(f"{self.scraper_name}: Error parsing product {idx}: {e}")
                continue
        
        return deals

    def parse_product_card(self, card):
        """Parse individual product card for market-in.gr"""
        from datetime import datetime
        
        # Extract product ID
        add_to_cart_btn = card.select_one('a.add-to-cart-btn')
        product_id = add_to_cart_btn.get('data-id', '') if add_to_cart_btn else ""
        
        # Title
        title_elem = card.select_one('a.product-ttl')
        title = title_elem.get_text(strip=True) if title_elem else "No title"
        
        # Category
        category = ""
        if title_elem:
            href = title_elem.get('href', '')
            if '/el-gr/' in href:
                parts = href.split('/')
                if len(parts) > 4:
                    category = parts[3].replace('-', ' ').title()
        
        # Discount
        discount_elem = card.select_one('.disc-value')
        discount_percentage = None
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True)
            discount_percentage = self.extract_discount_percentage(discount_text)
        
        # Prices
        old_price_elem = card.select_one('.old-price')
        original_price = self.extract_price(old_price_elem.get_text()) if old_price_elem else None
        
        new_price_elem = card.select_one('.new-price')
        current_price = self.extract_price(new_price_elem.get_text()) if new_price_elem else None
        
        # Calculate original price if not available
        if not original_price and current_price and discount_percentage:
            original_price = round(current_price / (1 - discount_percentage/100), 2)
        
        # Product URL
        link_elem = card.select_one('a.product-thumb') or card.select_one('a.product-ttl')
        product_url = link_elem.get('href', '') if link_elem else ""
        
        # Image URL
        img_elem = card.select_one('img')
        image_url = img_elem.get('src', '') if img_elem else ''
        if image_url and not image_url.startswith('http'):
            image_url = f"{self.base_url}{image_url}"
        
        # Brand
        brand_elem = card.select_one('a.product-brand')
        brand = brand_elem.get_text(strip=True) if brand_elem else ""
        
        # Create specs
        specs_parts = []
        if brand:
            specs_parts.append(f"Brand: {brand}")
        
        specs = " | ".join(specs_parts) if specs_parts else ""
        
        return {
            'title': title[:500],
            'category': category[:200] if category else "Uncategorized",
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
            'source': 'market-in.gr'  # Add source identifier
        }