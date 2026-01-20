# masoutis_scraper.py - UPDATED WITH BETTER ERROR HANDLING
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
        self.max_scroll_attempts = 30
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
            
            # Log final sample
            if all_deals:
                logger.info(f"📊 {self.scraper_name}: Sample of saved deals:")
                for i, deal in enumerate(all_deals[:3]):
                    logger.info(f"  Deal {i+1}: {deal.get('title', 'N/A')[:50]}...")
                    logger.info(f"    Current Price: {deal.get('current_price', 'N/A')}")
                    logger.info(f"    Original Price: {deal.get('original_price', 'N/A')}")
                    logger.info(f"    Discount: {deal.get('discount_percentage', 'N/A')}")
            
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
            time.sleep(2)
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
                self.driver.execute_script("""
                    arguments[0].value = '2: 2';
                    var event = new Event('change', { bubbles: true });
                    arguments[0].dispatchEvent(event);
                """, sort_select)
                logger.info(f"{self.scraper_name}: Applied discount percentage filter")
                time.sleep(3)
            
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
            product_containers = soup.select('div.product')
            
            logger.info(f"{self.scraper_name}: Found {len(product_containers)} product containers")
            
            deals = []
            successful_parses = 0
            failed_parses = 0
            
            for idx, container in enumerate(product_containers):
                try:
                    deal_data = self.parse_product_container(container)
                    if deal_data:
                        # Check if prices were actually extracted
                        if deal_data.get('current_price') is None or deal_data.get('original_price') is None:
                            logger.warning(f"{self.scraper_name}: Product {idx} has null prices: {deal_data.get('title', 'Unknown')}")
                            failed_parses += 1
                        else:
                            deals.append(deal_data)
                            successful_parses += 1
                        
                        # Log first few deals for debugging
                        if idx < 3:
                            self._log_sample_deal(deal_data, idx)
                except Exception as e:
                    logger.debug(f"{self.scraper_name}: Error parsing product {idx}: {e}")
                    failed_parses += 1
                    continue
            
            logger.info(f"{self.scraper_name}: Parsed {successful_parses} successful, {failed_parses} failed")
            return deals
            
        except Exception as e:
            logger.error(f"{self.scraper_name}: Parse error: {e}")
            return []
    
    def _log_sample_deal(self, deal_data, idx):
        """Log sample deal information for debugging"""
        logger.info(f"📝 {self.scraper_name}: Sample deal {idx}:")
        logger.info(f"  Title: {deal_data.get('title', 'N/A')}")
        logger.info(f"  Current Price: {deal_data.get('current_price', 'N/A')}")
        logger.info(f"  Original Price: {deal_data.get('original_price', 'N/A')}")
        logger.info(f"  Discount: {deal_data.get('discount_percentage', 'N/A')}%")
        logger.info(f"  Offer: {deal_data.get('offer', 'N/A')}")
        logger.info(f"  Product ID: {deal_data.get('product_id', 'N/A')}")
    
    def parse_product_container(self, container):
        """Parse individual product container with improved price extraction"""
        try:
            # Extract discount percentage
            discount_elem = container.select_one('.pDscntPercent')
            discount_text = discount_elem.get_text(strip=True) if discount_elem else ""
            
            # Check for special offer tags like "μόνo"
            offer_text = discount_text
            if not discount_text:
                # Look for other offer tags
                offer_tags = container.select('[class*="tag"], [class*="badge"], [class*="offer"]')
                for tag in offer_tags:
                    tag_text = tag.get_text(strip=True)
                    if tag_text:
                        offer_text = tag_text
                        break
            
            discount_percentage = self.extract_discount_percentage(discount_text)
            
            # Extract title
            title_elem = container.select_one('.productTitle')
            title = title_elem.get_text(strip=True) if title_elem else "No title"
            
            # Extract product ID from URL
            product_id = ""
            link_selectors = [
                'a.cursor[href*="/categories/item/"]',
                'a[href*="/categories/item/"]',
                '.catImgCont[href*="/categories/item/"]'
            ]
            
            link_elem = None
            for selector in link_selectors:
                link_elem = container.select_one(selector)
                if link_elem:
                    break
            
            if link_elem:
                href = link_elem.get('href', '')
                match = re.search(r'\?(\d+)=', href)
                if match:
                    product_id = match.group(1)
            
            # IMPORTANT: Find price elements using multiple strategies
            original_price = None
            current_price = None
            
            # Strategy 1: Look for standard price elements
            original_price_elem = container.select_one('.pStartPrice')
            current_price_elem = container.select_one('.pDscntPrice')
            
            if original_price_elem:
                original_price_text = original_price_elem.get_text(strip=True)
                original_price = self.extract_price(original_price_text)
            
            if current_price_elem:
                current_price_text = current_price_elem.get_text(strip=True)
                current_price = self.extract_price(current_price_text)
            
            # Strategy 2: If not found, look for price wrapper
            if not original_price or not current_price:
                price_wrapper = container.select_one('.disPrices-wrapper')
                if price_wrapper:
                    # Get all divs inside price wrapper
                    price_divs = price_wrapper.select('div')
                    prices_found = []
                    for div in price_divs:
                        text = div.get_text(strip=True)
                        price = self.extract_price(text)
                        if price:
                            prices_found.append(price)
                    
                    # If we found 2 prices, assume first is original, second is current
                    if len(prices_found) >= 2:
                        if not original_price:
                            original_price = prices_found[0]
                        if not current_price:
                            current_price = prices_found[1]
                    elif len(prices_found) == 1:
                        # Only one price found - this might be the current price
                        if not current_price:
                            current_price = prices_found[0]
            
            # Strategy 3: Look for any price-like text in the container
            if not original_price or not current_price:
                all_text = container.get_text()
                # Look for price patterns
                price_patterns = [
                    r'(\d+[\.,]\d+)\s*€',  # 3.52€ or 3,52€
                    r'€\s*(\d+[\.,]\d+)',  # €3.52 or €3,52
                ]
                
                prices = []
                for pattern in price_patterns:
                    matches = re.findall(pattern, all_text)
                    for match in matches:
                        price = self.extract_price(match)
                        if price and price not in prices:
                            prices.append(price)
                
                # Sort and take the highest as original, lowest as current (for discounts)
                if len(prices) >= 2:
                    prices.sort(reverse=True)
                    if not original_price:
                        original_price = prices[0]
                    if not current_price:
                        current_price = prices[-1]
                elif len(prices) == 1:
                    if not current_price:
                        current_price = prices[0]
            
            # Calculate discount if we have prices but no discount percentage
            if not discount_percentage and original_price and current_price and original_price > 0:
                try:
                    discount_percentage = ((original_price - current_price) / original_price) * 100
                    discount_percentage = round(discount_percentage, 1)
                except:
                    discount_percentage = None
            
            # If we have discount but missing original price, calculate it
            if discount_percentage and current_price and not original_price:
                try:
                    original_price = round(current_price / (1 - discount_percentage/100), 2)
                except:
                    pass
            
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
            
            # Category
            category = "Uncategorized"
            if link_elem:
                href = link_elem.get('href', '')
                match = re.search(r'/categories/item/([^/?]+)', href)
                if match:
                    category_part = match.group(1)
                    category = category_part.replace('-', ' ').title()
            
            # Build specs
            specs_parts = []
            # Look for weight/size in title
            weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:gr|g|kg|ml|l|γρ|κιλό)', title, re.IGNORECASE)
            if weight_match:
                specs_parts.append(f"Size: {weight_match.group(0)}")
            
            specs = " | ".join(specs_parts) if specs_parts else ""
            
            # Create deal object - ensure all fields are properly set
            deal = {
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
                'offer': offer_text.strip() if offer_text else "",
            }
            
            # Log if prices are null for debugging
            if original_price is None or current_price is None:
                logger.warning(f"{self.scraper_name}: Null prices in deal - Title: {title}, ID: {product_id}")
            
            return deal
            
        except Exception as e:
            logger.error(f"{self.scraper_name}: Parse container error: {e}")
            return None
    
    def extract_price(self, price_text):
        """Extract price from text like '3.52€' or '2,34€'"""
        if not price_text:
            return None
        
        try:
            # Remove euro symbol and any text
            price_clean = price_text.lower()
            
            # Remove everything except numbers, dot, and comma
            price_clean = re.sub(r'[^\d,\.]', '', price_clean)
            
            if not price_clean:
                return None
            
            # Handle Greek format with comma as decimal
            if ',' in price_clean:
                # If both comma and dot exist, dot is thousand separator
                if '.' in price_clean:
                    # Count dots - if more than one, they're thousand separators
                    if price_clean.count('.') > 1:
                        # Format like 1.234,56
                        parts = price_clean.split(',')
                        if len(parts) == 2:
                            integer_part = parts[0].replace('.', '')
                            decimal_part = parts[1]
                            price_clean = f"{integer_part}.{decimal_part}"
                    else:
                        # Single dot before comma: 3.52,34? This shouldn't happen
                        # Just replace comma with dot
                        price_clean = price_clean.replace(',', '.')
                else:
                    # Simple comma decimal: 3,52
                    price_clean = price_clean.replace(',', '.')
            
            # Parse the number
            match = re.search(r'(\d+\.?\d*)', price_clean)
            if match:
                return float(match.group(1))
            
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Error extracting price from '{price_text}': {e}")
        
        return None
    
    def extract_discount_percentage(self, discount_text):
        """Extract discount percentage from text like '-40%' or '40%'"""
        if not discount_text:
            return None
        
        try:
            # Clean the text
            discount_clean = discount_text.strip()
            
            # Remove any non-numeric characters except dot and percent
            discount_clean = re.sub(r'[^\d\.%\-]', '', discount_clean)
            
            # Extract the number (may include negative sign)
            match = re.search(r'[-]?(\d+(?:\.\d+)?)', discount_clean)
            if match:
                # Get the number (ignore negative sign)
                num_match = re.search(r'(\d+(?:\.\d+)?)', match.group(0))
                if num_match:
                    return float(num_match.group(1))
            
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Error extracting discount from '{discount_text}': {e}")
        
        return None