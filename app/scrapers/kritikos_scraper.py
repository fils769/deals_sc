import re
import time
import logging
import urllib.parse
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger("deals-api")

class KritikosScraper(BaseScraper):
    """Scraper for kritikos-sm.gr website (infinite scroll)"""
    
    def __init__(self, headless=True):
        super().__init__(headless=headless, scraper_name="KritikosScraper")
        self.base_url = "https://kritikos-sm.gr"
        self.deals_url = "https://kritikos-sm.gr/offers/"
    
    def scrape_deals(self, max_pages=None, max_total_deals=None):
        """Scrape deals from kritikos-sm.gr using infinite scroll"""
        if not self.driver:
            self.setup_driver()
        
        logger.info(f"🚀 {self.scraper_name}: Starting to scrape deals from infinite scroll page")
        logger.info(f"📌 URL: {self.deals_url}")
        
        try:
            # Navigate to the deals page
            logger.info(f"🌐 {self.scraper_name}: Loading initial page...")
            self.driver.get(self.deals_url)
            time.sleep(3 + random.uniform(1, 2))  # Initial load time
            
            # Wait for initial content
            wait = WebDriverWait(self.driver, 10)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ProductListItem_productItem__cKUyG"))
            )
            
            all_deals = []
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 20  # Safety limit
            consecutive_no_new_deals = 0
            max_consecutive_no_new = 3
            
            logger.info(f"📊 {self.scraper_name}: Starting infinite scroll collection")
            logger.info(f"⚙️ {self.scraper_name}: Max scroll attempts: {max_scroll_attempts}")
            
            while scroll_attempts < max_scroll_attempts:
                scroll_attempts += 1
                logger.info(f"🔄 {self.scraper_name}: Scroll attempt {scroll_attempts}/{max_scroll_attempts}")
                
                # Parse current page deals
                current_deals_count = len(all_deals)
                new_deals = self.parse_current_page()
                
                if new_deals:
                    # Filter out duplicates
                    new_deals_filtered = []
                    existing_urls = {deal['product_url'] for deal in all_deals}
                    
                    for deal in new_deals:
                        if deal['product_url'] not in existing_urls:
                            new_deals_filtered.append(deal)
                            existing_urls.add(deal['product_url'])
                    
                    if new_deals_filtered:
                        all_deals.extend(new_deals_filtered)
                        logger.info(f"✅ {self.scraper_name}: Added {len(new_deals_filtered)} new deals (total: {len(all_deals)})")
                        
                        # Log first new deal as sample
                        if len(new_deals_filtered) > 0:
                            sample_deal = new_deals_filtered[0]
                            logger.info(f"📋 {self.scraper_name}: Sample new deal added:")
                            logger.info(f"   Title: {sample_deal['title']}")
                            logger.info(f"   Product ID: {sample_deal['product_id']} (length: {len(sample_deal['product_id'])})")
                            logger.info(f"   SKUID: {sample_deal['skuid']} (length: {len(sample_deal['skuid'])})")
                            logger.info(f"   Current Price: {sample_deal['current_price']}€")
                            logger.info(f"   Original Price: {sample_deal['original_price']}€")
                            logger.info(f"   Discount: {sample_deal['discount_percentage']}%")
                            logger.info(f"   Offer: {sample_deal['offer']}")
                            logger.info(f"   Source: {sample_deal['source']}")
                        
                        consecutive_no_new_deals = 0
                    else:
                        consecutive_no_new_deals += 1
                        logger.info(f"ℹ️ {self.scraper_name}: No new unique deals found on this scroll (consecutive: {consecutive_no_new_deals})")
                else:
                    consecutive_no_new_deals += 1
                    logger.warning(f"⚠️ {self.scraper_name}: No deals parsed on this scroll (consecutive: {consecutive_no_new_deals})")
                
                # Check if we've reached max deals
                if max_total_deals and len(all_deals) >= max_total_deals:
                    logger.info(f"🎯 {self.scraper_name}: Reached max deals limit: {max_total_deals}")
                    all_deals = all_deals[:max_total_deals]
                    break
                
                # Check if we're not getting new content
                if consecutive_no_new_deals >= max_consecutive_no_new:
                    logger.info(f"🛑 {self.scraper_name}: No new deals for {max_consecutive_no_new} consecutive scrolls, stopping")
                    break
                
                # Scroll down
                logger.debug(f"{self.scraper_name}: Scrolling down...")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                time.sleep(2 + random.uniform(0.5, 1.5))
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    logger.info(f"📏 {self.scraper_name}: Page height unchanged, might be at the end")
                    # Try one more scroll with longer wait
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    if new_height == last_height:
                        logger.info(f"🏁 {self.scraper_name}: Reached end of content")
                        break
                
                last_height = new_height
                
                # Random delay between scrolls
                delay = random.uniform(0.5, 1.5)
                time.sleep(delay)
            
            # Final log with statistics
            logger.info(f"🎉 {self.scraper_name}: Scraping completed!")
            logger.info(f"📊 {self.scraper_name}: Total deals collected: {len(all_deals)}")
            logger.info(f"🔁 {self.scraper_name}: Total scroll attempts: {scroll_attempts}")
            
            if all_deals:
                logger.info(f"📋 {self.scraper_name}: First deal sample (full structure):")
                sample = all_deals[0]
                for key, value in sample.items():
                    if key != 'scraped_at':
                        logger.info(f"   {key}: {value}")
            
            return all_deals
            
        except Exception as e:
            logger.error(f"❌ {self.scraper_name}: Scraping failed: {e}", exc_info=True)
            return []
    
    def parse_current_page(self):
        """Parse deals from current page for kritikos-sm.gr"""
        page_source = self.driver.page_source
        
        if len(page_source) < 3000:
            logger.warning(f"{self.scraper_name}: Page source seems very small")
            return []
        
        soup = BeautifulSoup(page_source, 'html.parser')
        product_cards = soup.select('div.ProductListItem_productItem__cKUyG')
        
        if not product_cards:
            logger.debug(f"{self.scraper_name}: No product cards found in current view")
            return []
        
        logger.debug(f"{self.scraper_name}: Found {len(product_cards)} product cards in current view")
        
        deals = []
        for idx, card in enumerate(product_cards, 1):
            try:
                deal_data = self.parse_product_card(card)
                if deal_data:
                    deals.append(deal_data)
                    
                    if idx % 10 == 0:
                        logger.debug(f"{self.scraper_name}: Parsed {idx}/{len(product_cards)} deals from current view")
            except Exception as e:
                logger.error(f"{self.scraper_name}: Error parsing product {idx}: {e}")
                continue
        
        return deals

    def parse_product_card(self, card):
        """Parse individual product card for kritikos-sm.gr"""
        
        # Title - maps to 'title' column
        title_elem = card.select_one('p.ProductListItem_title__e6MEz')
        title = title_elem.get_text(strip=True) if title_elem else "No title"
        
        # Description/Subtitle - maps to 'specs' column
        desc_elem = card.select_one('p.ProductListItem_titleDesc__JzvBv')
        specs = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Current price - maps to 'current_price' column
        final_price_elem = card.select_one('p.ProductListItem_finalPrice__sEMjs')
        current_price = self.extract_price(final_price_elem.get_text()) if final_price_elem else None
        
        # Original price - maps to 'original_price' column
        original_price_elem = card.select_one('p.ProductListItem_beginPrice__vK_Dk')
        original_price = self.extract_price(original_price_elem.get_text()) if original_price_elem else None
        
        # Check for discount badges
        discount_badge = card.select_one('div.ProductListItem_badge__Z11mo')
        offer_badge = card.select_one('div.ProductListItem_badgeOffer__BW9pu')
        
        discount_percentage = None
        offer = None  # Maps to 'offer' column
        
        # If there's a money discount badge (e.g., "-2.25 €")
        if discount_badge:
            discount_text = discount_badge.get_text(strip=True)
            
            # Calculate percentage if we have both prices
            if original_price and current_price and original_price > 0:
                discount_percentage = round(((original_price - current_price) / original_price) * 100, 2)
            elif original_price and original_price > 0 and current_price:
                # If we have original price but no current price in badge
                discount_percentage = round(((original_price - current_price) / original_price) * 100, 2)
        
        # If there's an offer badge (e.g., "Offer 2+1")
        elif offer_badge:
            offer = offer_badge.get_text(strip=True)
            # For offers like "2+1", leave discount_percentage as None
        
        # Calculate discount percentage if we have both prices but no discount badge
        if not discount_percentage and original_price and current_price and original_price > current_price:
            discount_percentage = round(((original_price - current_price) / original_price) * 100, 2)
        
        # Product URL - maps to 'product_url' column
        link_elem = card.select_one('a.ProductListItem_productLink__BZo3P')
        product_url = link_elem.get('href', '') if link_elem else ""
        if product_url and not product_url.startswith('http'):
            product_url = f"{self.base_url}{product_url}"
        
        # Image URL - maps to 'image_url' column
        img_elem = card.select_one('img.ProductListItem_productImage__HbseK')
        image_url = img_elem.get('src', '') if img_elem else ''
        
        # Category - extract from URL or determine from content
        category = ""
        if product_url:
            if '/offers/' in product_url:
                category = "Offers"
            elif '/products/' in product_url:
                category = "Products"
            else:
                category = "General"
        
        # Generate clean product ID from URL - extract numeric ID if possible
        product_id = ""
        skuid = ""
        
        if product_url:
            # Try to extract numeric ID from URL (e.g., -4734 from ...-4734/)
            numeric_id_match = re.search(r'-(\d+)/?$', product_url)
            if numeric_id_match:
                product_id = numeric_id_match.group(1)
                skuid = product_id
            else:
                # Fallback: extract last part and clean it up
                parts = product_url.strip('/').split('/')
                if parts:
                    last_part = parts[-1]
                    # URL decode to get readable text
                    try:
                        decoded = urllib.parse.unquote(last_part)
                        # Extract alphanumeric characters only, max 100 chars
                        cleaned = re.sub(r'[^\w\s-]', '', decoded)[:95]
                        product_id = cleaned
                        skuid = cleaned[:100]
                    except:
                        # If decoding fails, use sanitized version
                        product_id = re.sub(r'[^\w\s-]', '', last_part)[:95]
                        skuid = product_id[:100]
        
        # If product_id is still too long or empty, create a hash
        if len(product_id) > 100 or not product_id:
            import hashlib
            hash_id = hashlib.md5(product_url.encode()).hexdigest()[:20]
            product_id = hash_id
            skuid = hash_id
        
        # Ensure lengths are within limits
        product_id = product_id[:100]
        skuid = skuid[:100]
        
        # Source is always 'kritikos-sm.gr'
        source = 'kritikos-sm.gr'
        
        # Default values for other columns
        rating = 0.0
        review_count = 0
        shop_count = "1"
        is_active = True
        
        return {
            'title': title[:500] if title else "No Title",
            'category': category[:200] if category else "Uncategorized",
            'specs': specs[:500],
            'original_price': original_price,
            'current_price': current_price,
            'discount_percentage': discount_percentage,
            'offer': offer[:200] if offer else None,  # Maps to 'offer' column
            'rating': rating,
            'review_count': review_count,
            'product_url': product_url,
            'image_url': image_url,
            'skuid': skuid,
            'product_id': product_id,
            'shop_count': shop_count,
            'is_active': is_active,
            'scraped_at': datetime.now(),
            'source': source  # Maps to 'source' column
        }
    
    def extract_price(self, text):
        """Extract price from text, handling euro symbols and commas"""
        if not text:
            return None
        
        try:
            # Remove euro symbols, spaces, and other non-numeric characters except dots and commas
            cleaned = re.sub(r'[^\d,\.]', '', str(text))
            # Replace comma with dot for decimal
            cleaned = cleaned.replace(',', '.')
            
            # Extract the first number found
            match = re.search(r'\d+\.?\d*', cleaned)
            if match:
                return float(match.group())
            return None
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Error extracting price from '{text}': {e}")
            return None