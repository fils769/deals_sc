# sklavenitis_scraper.py
import re
import time
import json
import logging
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
import random

logger = logging.getLogger("deals-api")

class SklavenitisScraper(BaseScraper):
    """Scraper for sklavenitis.gr website"""
    
    def __init__(self, headless=True):
        super().__init__(headless=headless, scraper_name="SklavenitisScraper")
        self.base_url = "https://www.sklavenitis.gr"
        self.deals_url = "https://www.sklavenitis.gr/sylloges/prosfores/"
    
    def scrape_deals(self, max_pages=None, max_total_deals=None):
        """Scrape deals from sklavenitis.gr"""
        if not self.driver:
            self.setup_driver()
        
        logger.info(f"{self.scraper_name}: Starting to scrape deals")
        return self.scrape_with_pagination(max_pages, max_total_deals)
    
    def scrape_with_pagination(self, max_pages=None, max_total_deals=None):
        """Scrape deals with pagination"""
        logger.info(f"{self.scraper_name}: Starting pagination scraping")
        
        all_deals = []
        current_page = 1
        consecutive_empty_pages = 0
        
        try:
            while True:
                if max_pages and current_page > max_pages:
                    logger.info(f"✓ {self.scraper_name}: Reached max pages limit: {max_pages}")
                    break
                
                logger.info(f"{self.scraper_name}: Processing page {current_page}")
                
                # Navigate to the specific page
                url = self.deals_url if current_page == 1 else f"{self.deals_url}?pg={current_page}"
                logger.debug(f"{self.scraper_name}: Navigating to {url}")
                self.driver.get(url)
                
                # Random delay
                time.sleep(self.page_delay + random.uniform(0.5, 1.5))
                
                # Check page content
                page_source = self.driver.page_source
                if len(page_source) < 5000:
                    logger.warning(f"⚠ {self.scraper_name}: Page {current_page} source too small")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        break
                    current_page += 1
                    continue
                
                # Scroll to load all content
                self.scroll_page()
                time.sleep(0.5)
                
                # Parse current page
                page_deals = self.parse_current_page()
                
                if page_deals:
                    all_deals.extend(page_deals)
                    logger.info(f"✓ {self.scraper_name}: Page {current_page}: Added {len(page_deals)} deals (total: {len(all_deals)})")
                    
                    if max_total_deals and len(all_deals) >= max_total_deals:
                        logger.info(f"✓ {self.scraper_name}: Reached max deals: {max_total_deals}")
                        all_deals = all_deals[:max_total_deals]
                        break
                    
                    consecutive_empty_pages = 0
                else:
                    logger.warning(f"⚠ {self.scraper_name}: No deals found on page {current_page}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        logger.info(f"{self.scraper_name}: 2 consecutive empty pages, stopping")
                        break
                
                current_page += 1
                delay = self.page_delay + random.uniform(0.5, 2)
                time.sleep(delay)
            
            logger.info(f"✓ {self.scraper_name}: Scraping completed - {len(all_deals)} deals collected")
            return all_deals
            
        except Exception as e:
            logger.error(f"✗ {self.scraper_name}: Scraping failed: {e}", exc_info=True)
            return all_deals
        finally:
            self.close()
    
    def parse_current_page(self):
        """Parse deals from current page"""
        page_source = self.driver.page_source
        
        if len(page_source) < 10000:
            logger.warning(f"{self.scraper_name}: Page source too small")
            return []
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find all product cards
        product_cards = soup.select('div.product[data-plugin-product]')
        
        if not product_cards:
            product_cards = soup.select('div.product')
        
        logger.info(f"{self.scraper_name}: Found {len(product_cards)} product cards")
        
        deals = []
        for idx, card in enumerate(product_cards, 1):
            try:
                deal_data = self.parse_product_card(card)
                if deal_data:
                    deals.append(deal_data)
                    
                    if idx % 10 == 0:
                        logger.debug(f"{self.scraper_name}: Parsed {idx}/{len(product_cards)} deals")
            except Exception as e:
                logger.error(f"{self.scraper_name}: Error parsing product {idx}: {e}")
                continue
        
        return deals
    
    def parse_product_card(self, card):
        """Parse individual product card"""
        # Extract data from JSON attributes
        product_data = self._extract_from_json_attributes(card)
        
        # Extract from HTML elements
        html_data = self._extract_from_html(card)
        product_data.update(html_data)
        
        # Skip if missing essential data
        if not product_data.get('title') or not product_data.get('product_id'):
            return None
        
        # Clean data
        product_data = self._clean_product_data(product_data)
        
        # Calculate discount if possible
        discount = self._calculate_discount(
            product_data.get('original_price'),
            product_data.get('current_price')
        )
        
        # Build specs
        specs_parts = []
        if product_data.get('brand'):
            specs_parts.append(f"Brand: {product_data['brand']}")
        if product_data.get('unit'):
            specs_parts.append(f"Unit: {product_data['unit']}")
        
        specs = " | ".join(specs_parts)
        
        # Create final deal object matching Deal model
        return {
            'title': product_data.get('title', '')[:500],
            'category': product_data.get('category', 'Uncategorized')[:200],
            'specs': specs[:500],
            'original_price': product_data.get('original_price'),
            'current_price': product_data.get('current_price'),
            'discount_percentage': discount,
            'rating': 0.0,
            'review_count': 0,
            'product_url': product_data.get('product_url', ''),
            'image_url': product_data.get('image_url', ''),
            'skuid': product_data.get('sku', ''),
            'product_id': product_data.get('product_id', ''),
            'shop_count': "1",
            'is_active': True,
            'scraped_at': datetime.now(),
            'source': 'sklavenitis.gr',
        }
    
    def _extract_from_json_attributes(self, card):
        """Extract product data from JSON attributes"""
        data = {}
        
        try:
            # Extract from data-plugin-analyticsimpressions
            analytics_attr = card.get('data-plugin-analyticsimpressions', '')
            if analytics_attr:
                analytics_json = json.loads(analytics_attr)
                items = analytics_json.get('Call', {}).get('ecommerce', {}).get('items', [])
                if items:
                    item = items[0]
                    data.update({
                        'sku': item.get('item_id', ''),
                        'title': item.get('item_name', ''),
                        'brand': item.get('item_brand', ''),
                        'category': item.get('item_category', ''),
                        'current_price': item.get('price'),
                    })
            
            # Extract from data-plugin-product
            plugin_attr = card.get('data-plugin-product', '')
            if plugin_attr:
                plugin_json = json.loads(plugin_attr)
                data.update({
                    'unit': plugin_json.get('unitDisplay', ''),
                })
            
            # Extract from data-item
            item_attr = card.get('data-item', '')
            if item_attr:
                item_json = json.loads(item_attr)
                data.update({
                    'product_id': str(item_json.get('ProductID', '')),
                    'sku': data.get('sku') or item_json.get('ProductSKU', ''),
                })
            
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        
        return data
    
    def _extract_from_html(self, card):
        """Extract product data from HTML elements"""
        data = {}
        
        # Title
        title_elem = card.select_one('h4.product__title a')
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)
        
        # Price
        price_elem = card.select_one('div[data-price]')
        if price_elem:
            price = price_elem.get('data-price') or price_elem.get_text(strip=True)
            data['current_price'] = self.extract_price(price)
        
        # Original price
        old_price_elem = card.select_one('.price--old, .old-price, s')
        if old_price_elem:
            data['original_price'] = self.extract_price(old_price_elem.get_text(strip=True))
        
        # Product URL
        link_elem = card.select_one('a.absLink') or card.select_one('h4.product__title a')
        if link_elem:
            href = link_elem.get('href', '')
            if href and not href.startswith('http'):
                data['product_url'] = urljoin(self.base_url, href)
            elif href:
                data['product_url'] = href
        
        # Image URL
        img_elem = card.select_one('img')
        if img_elem:
            src = img_elem.get('src', '')
            if src and not src.startswith('http'):
                src = urljoin(self.base_url, src)
            data['image_url'] = src
        
        # Extract from class name (fallback for SKU)
        for cls in card.get('class', []):
            if cls.startswith('prGa_'):
                sku = cls.replace('prGa_', '')
                if not data.get('sku'):
                    data['sku'] = sku
                if not data.get('product_id'):
                    data['product_id'] = sku
                break
        
        return data
    
    def _clean_product_data(self, data):
        """Clean and normalize product data"""
        cleaned = {}
        
        # Title
        if data.get('title'):
            title = data['title'].strip()
            title = title.replace('&amp;', '&')
            cleaned['title'] = title
        
        # Prices
        for price_key in ['current_price', 'original_price']:
            price = data.get(price_key)
            if price is not None:
                if isinstance(price, str):
                    cleaned[price_key] = self.extract_price(price)
                else:
                    try:
                        cleaned[price_key] = float(price)
                    except (ValueError, TypeError):
                        cleaned[price_key] = None
            else:
                cleaned[price_key] = None
        
        # Category
        if data.get('category'):
            category = data['category'].strip()
            category = category.replace('&amp;', '&')
            cleaned['category'] = category
        
        # IDs
        cleaned['product_id'] = str(data.get('product_id', '')).strip()
        cleaned['sku'] = str(data.get('sku', cleaned['product_id'])).strip()
        
        # URLs
        for url_key in ['product_url', 'image_url']:
            url = data.get(url_key, '')
            if url and not url.startswith('http'):
                url = urljoin(self.base_url, url)
            cleaned[url_key] = url
        
        # Other fields
        for field in ['brand', 'unit']:
            if field in data:
                cleaned[field] = data[field]
        
        return cleaned
    
    def _calculate_discount(self, original_price, current_price):
        """Calculate discount percentage"""
        try:
            if original_price and current_price:
                original = float(original_price)
                current = float(current_price)
                if original > 0 and original > current:
                    discount = ((original - current) / original) * 100
                    return round(discount, 1)
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        return None
    
    def extract_price(self, price_text):
        """Extract price from Greek format text"""
        if not price_text:
            return None
        
        try:
            price_str = str(price_text)
            
            # Remove currency and text
            price_str = price_str.lower()
            price_str = re.sub(r'[^\d.,]', '', price_str)
            
            # Handle Greek decimal
            if ',' in price_str and '.' in price_str:
                price_str = price_str.replace('.', '').replace(',', '.')
            elif ',' in price_str:
                price_str = price_str.replace(',', '.')
            
            # Extract number
            match = re.search(r'(\d+\.?\d*)', price_str)
            if match:
                return float(match.group(1))
            
        except Exception:
            pass
        
        return None