# import logging
# import time
# import random
# from abc import ABC, abstractmethod
# from datetime import datetime
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service

# logger = logging.getLogger("deals-api")

# class BaseScraper(ABC):
#     """Base class for all scrapers"""
    
#     def __init__(self, headless=True, scraper_name="BaseScraper"):
#         self.headless = headless
#         self.scraper_name = scraper_name
#         self.driver = None
#         self.page_delay = 3  # seconds between pages
#         self.max_scroll_attempts = 10
#         self.scroll_pause_time = 1
        
#         logger.info(f"{self.scraper_name} initialized - headless={headless}")
    
#     def setup_driver(self):
#         """Setup Chrome driver with anti-bot measures"""
#         logger.info(f"{self.scraper_name}: Setting up Chrome driver...")
#         chrome_options = Options()
        
#         if self.headless:
#             chrome_options.add_argument("--headless")
#             chrome_options.add_argument("--disable-gpu")
        
#         # Essential arguments
#         chrome_options.add_argument("--no-sandbox")
#         chrome_options.add_argument("--disable-dev-shm-usage")
        
#         # Anti-detection
#         chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
#         chrome_options.add_experimental_option('useAutomationExtension', False)
        
#         # Realistic browser fingerprint
#         chrome_options.add_argument(f"user-agent={random.choice(self.get_user_agents())}")
#         chrome_options.add_argument("--window-size=1920,1080")
#         chrome_options.add_argument("--start-maximized")
        
#         # Disable features that might trigger bot detection
#         chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
#         # Enable JavaScript and cookies
#         prefs = {
#             "profile.default_content_setting_values.cookies": 1,
#             "profile.default_content_setting_values.javascript": 1,
#             "profile.default_content_setting_values.notifications": 2,
#         }
#         chrome_options.add_experimental_option("prefs", prefs)
        
#         try:
#             from shutil import which
#             from app.config import settings
            
#             local = which('chromedriver') or settings.CHROMEDRIVER_PATH
#             service = Service(local) if local else Service()
#             self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
#             # Stealth modifications
#             self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
#             logger.info(f"✓ {self.scraper_name}: Chrome driver initialized")
            
#         except Exception as e:
#             logger.error(f"✗ {self.scraper_name}: Failed to create Chrome driver: {e}", exc_info=True)
#             raise
    
#     def get_user_agents(self):
#         """Get list of user agents"""
#         return [
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
#             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
#         ]
    
#     @abstractmethod
#     def scrape_deals(self, max_pages=None, max_total_deals=None):
#         """Main scraping method to be implemented by each scraper"""
#         pass
    
#     @abstractmethod
#     def parse_current_page(self):
#         """Parse deals from current page"""
#         pass
    
#     def scroll_page(self):
#         """Scroll page to load content"""
#         logger.info(f"{self.scraper_name}: Scrolling page...")
        
#         for i in range(3):
#             scroll_height = self.driver.execute_script("return document.body.scrollHeight")
#             scroll_position = scroll_height * (i + 1) / 4
#             self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
#             time.sleep(0.5 + random.uniform(0, 0.5))
        
#         self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#         time.sleep(1)
    
#     def extract_price(self, price_text):
#         """Extract numeric price from text"""
#         if not price_text:
#             return None
        
#         try:
#             import re
#             price_text = str(price_text).replace('€', '').replace('$', '').replace('£', '').replace(' ', '').strip()
#             price_text = price_text.replace(',', '.')
#             matches = re.findall(r'\d+\.?\d*', price_text)
#             return float(matches[0]) if matches else None
#         except Exception as e:
#             logger.debug(f"{self.scraper_name}: Error extracting price: {e}")
#             return None
    
#     def extract_discount_percentage(self, discount_text):
#         """Extract discount percentage from badge text"""
#         if not discount_text:
#             return None
        
#         try:
#             discount_text = str(discount_text).replace('-', '').replace('%', '').replace('off', '').strip()
#             return float(discount_text) if discount_text else None
#         except Exception as e:
#             logger.debug(f"{self.scraper_name}: Error extracting discount: {e}")
#             return None
    
#     def close(self):
#         """Close the driver"""
#         if self.driver:
#             try:
#                 self.driver.quit()
#                 logger.info(f"✓ {self.scraper_name}: Chrome driver closed")
#             except Exception as e:
#                 logger.error(f"{self.scraper_name}: Error closing Chrome driver: {e}")


import logging
import time
import random
from abc import ABC, abstractmethod
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import re

logger = logging.getLogger("deals-api")

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, headless=True, scraper_name="BaseScraper"):
        self.headless = headless
        self.scraper_name = scraper_name
        self.driver = None
        self.page_delay = 3  # seconds between pages
        self.max_scroll_attempts = 10
        self.scroll_pause_time = 1
        self.page_load_timeout = 45  # Increased timeout for slow sites
        self.retry_count = 0
        self.max_retries = 3
        
        logger.info(f"{self.scraper_name} initialized - headless={headless}")
    
    def setup_driver(self):
        """Setup Chrome driver with enhanced anti-bot measures"""
        logger.info(f"{self.scraper_name}: Setting up Chrome driver...")
        chrome_options = Options()
        
        # USE NEW HEADLESS MODE (less detectable)
        if self.headless:
            chrome_options.add_argument("--headless=new")  # Changed from --headless
            chrome_options.add_argument("--disable-gpu")
        
        # Essential arguments for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # CRITICAL ANTI-DETECTION MEASURES
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Performance optimizations for slow sites
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--mute-audio")
        
        # Memory and performance
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Security/accessibility tweaks
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        # Realistic browser fingerprint
        user_agent = random.choice(self.get_user_agents())
        chrome_options.add_argument(f"user-agent={user_agent}")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        # Enable JavaScript and cookies with better settings
        prefs = {
            "profile.default_content_setting_values.cookies": 1,
            "profile.default_content_setting_values.javascript": 1,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.images": 2,  # Allow images
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.popups": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.geolocation": 2,
            "download.default_directory": "/tmp",
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            from shutil import which
            from app.config import settings
            
            local = which('chromedriver') or settings.CHROMEDRIVER_PATH
            service = Service(
                executable_path=local if local else 'chromedriver',
                service_args=['--timeout=30000']  # 30 seconds for driver operations
            )
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts for better reliability
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.set_script_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Enhanced stealth modifications
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent,
                "userAgentMetadata": {
                    "brands": [
                        {"brand": "Chromium", "version": "121"},
                        {"brand": "Google Chrome", "version": "121"},
                        {"brand": "Not;A=Brand", "version": "99"}
                    ],
                    "fullVersion": "121.0.0.0",
                    "platform": "Windows",
                    "platformVersion": "10.0.0",
                    "architecture": "x86",
                    "model": "",
                    "mobile": False
                }
            })
            
            # Additional anti-detection scripts
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['el-GR', 'el', 'en-US', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });
            """)
            
            logger.info(f"✓ {self.scraper_name}: Chrome driver initialized with enhanced anti-bot measures")
            
        except Exception as e:
            logger.error(f"✗ {self.scraper_name}: Failed to create Chrome driver: {e}", exc_info=True)
            raise
    
    def get_user_agents(self):
        """Get expanded list of user agents"""
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Chrome on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        ]
    
    @abstractmethod
    def scrape_deals(self, max_pages=None, max_total_deals=None):
        """Main scraping method to be implemented by each scraper"""
        pass
    
    @abstractmethod
    def parse_current_page(self):
        """Parse deals from current page"""
        pass
    
    def navigate_with_retry(self, url, max_attempts=3):
        """Navigate to URL with retry logic for slow/unreliable sites"""
        for attempt in range(max_attempts):
            try:
                logger.info(f"{self.scraper_name}: Navigation attempt {attempt + 1}/{max_attempts} to {url}")
                
                # Clear cookies and cache between attempts
                if attempt > 0:
                    try:
                        self.driver.delete_all_cookies()
                        logger.debug(f"{self.scraper_name}: Cleared cookies")
                    except:
                        pass
                
                # Use JavaScript navigation to avoid detection
                if attempt > 0:
                    self.driver.execute_script(f"window.location.href = '{url}';")
                else:
                    self.driver.get(url)
                
                # Wait for page to load with flexible conditions
                wait_time = 3 + random.uniform(1, 3) + (attempt * 2)  # Exponential backoff
                time.sleep(wait_time)
                
                # Check if page loaded successfully
                page_source = self.driver.page_source
                if len(page_source) > 5000:  # Reasonable minimum page size
                    logger.info(f"✓ {self.scraper_name}: Page loaded successfully ({len(page_source)} chars)")
                    return True
                else:
                    logger.warning(f"{self.scraper_name}: Page source too small: {len(page_source)} chars")
                    
            except TimeoutException:
                logger.warning(f"{self.scraper_name}: Timeout on attempt {attempt + 1}")
                if attempt < max_attempts - 1:
                    backoff = 5 * (attempt + 1)
                    logger.info(f"{self.scraper_name}: Backing off for {backoff} seconds")
                    time.sleep(backoff)
            except Exception as e:
                logger.error(f"{self.scraper_name}: Navigation error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(3 * (attempt + 1))
        
        logger.error(f"{self.scraper_name}: Failed to load page after {max_attempts} attempts")
        return False
    
    def scroll_page(self):
        """Scroll page to load content with multiple strategies"""
        logger.info(f"{self.scraper_name}: Scrolling page...")
        
        # Multiple scroll strategies
        scroll_strategies = [
            # 1. Incremental scroll
            lambda: self._incremental_scroll(),
            # 2. Viewport scroll
            lambda: self._viewport_scroll(),
            # 3. Element-based scroll
            lambda: self._element_scroll(),
        ]
        
        for strategy in scroll_strategies:
            try:
                strategy()
                time.sleep(0.5 + random.uniform(0, 0.5))
            except Exception as e:
                logger.debug(f"{self.scraper_name}: Scroll strategy failed: {e}")
                continue
        
        # Final scroll to bottom
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        except:
            pass
    
    def _incremental_scroll(self):
        """Scroll in increments"""
        for i in range(3):
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_position = scroll_height * (i + 1) / 4
            self.driver.execute_script(f"window.scrollTo({{top: {scroll_position}, behavior: 'smooth'}});")
            time.sleep(0.5 + random.uniform(0, 0.5))
    
    def _viewport_scroll(self):
        """Scroll by viewport height"""
        viewport_height = self.driver.execute_script("return window.innerHeight")
        for i in range(2):
            self.driver.execute_script(f"window.scrollBy(0, {viewport_height});")
            time.sleep(0.3 + random.uniform(0, 0.3))
    
    def _element_scroll(self):
        """Scroll to specific elements"""
        try:
            # Try to find elements to scroll to
            elements = self.driver.find_elements("css selector", ".product, .item, [data-testid*='product']")
            if elements and len(elements) > 5:
                # Scroll to middle element
                mid_element = elements[len(elements) // 2]
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", mid_element)
        except:
            pass
    
    def gentle_scroll_infinite(self, pause_time=1.5):
        """Gentle scrolling for infinite scroll pages"""
        try:
            # Scroll in small increments
            for i in range(4):
                scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_position = scroll_height * (i + 1) / 5  # Smaller increments
                self.driver.execute_script(f"window.scrollTo({{top: {scroll_position}, behavior: 'smooth'}});")
                time.sleep(pause_time / 4 + random.uniform(0, 0.3))
            
            # Final gentle scroll
            self.driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")
            time.sleep(pause_time)
            
            # Scroll up a bit to trigger more loading
            self.driver.execute_script("window.scrollTo({top: document.body.scrollHeight * 0.7, behavior: 'smooth'});")
            time.sleep(0.5)
            
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Gentle scroll failed: {e}")
    
    def wait_for_element(self, selector, timeout=20):
        """Wait for element to be present"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(lambda d: d.find_element("css selector", selector))
        except TimeoutException:
            logger.warning(f"{self.scraper_name}: Timeout waiting for element: {selector}")
            return None
    
    def extract_price(self, price_text):
        """Extract numeric price from text with Greek format support"""
        if not price_text:
            return None
        
        try:
            import re
            # Handle Greek format (comma as decimal)
            price_str = str(price_text)
            
            # Remove currency symbols and text
            price_str = price_str.replace('€', '').replace('$', '').replace('£', '')
            price_str = price_str.replace(' ', '').strip()
            
            # Handle Greek decimal comma
            if ',' in price_str and '.' in price_str:
                # If both present, assume comma is decimal and dot is thousand separator
                price_str = price_str.replace('.', '').replace(',', '.')
            elif ',' in price_str:
                # Comma is decimal separator
                price_str = price_str.replace(',', '.')
            
            # Extract numeric value
            matches = re.findall(r'\d+\.?\d*', price_str)
            return float(matches[0]) if matches else None
            
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Error extracting price from '{price_text}': {e}")
            return None
    
    def extract_discount_percentage(self, discount_text):
        """Extract discount percentage from badge text with Greek support"""
        if not discount_text:
            return None
        
        try:
            # Handle Greek percentage format and negative signs
            discount_str = str(discount_text)
            
            # Remove common symbols
            discount_str = discount_str.replace('-', '').replace('%', '').replace('έκπτωση', '').replace('εκπτωση', '')
            discount_str = discount_str.strip()
            
            # Extract numeric value
            import re
            match = re.search(r'(\d+\.?\d*|\d+)', discount_str)
            if match:
                return float(match.group(1))
            
            return None
            
        except Exception as e:
            logger.debug(f"{self.scraper_name}: Error extracting discount: {e}")
            return None
    
    def extract_greek_price(self, price_text):
        """Specialized Greek price extractor"""
        if not price_text:
            return None
        
        try:
            price_str = str(price_text)
            
            # Remove everything except numbers, comma, and dot
            price_str = re.sub(r'[^\d,.]', '', price_str)
            
            # Handle Greek decimal (comma as decimal separator)
            if ',' in price_str and '.' in price_str:
                # If both present, remove dots (thousand separators) and convert comma to dot
                price_str = price_str.replace('.', '').replace(',', '.')
            elif ',' in price_str:
                # Comma is decimal separator
                price_str = price_str.replace(',', '.')
            
            # Extract number
            match = re.search(r'(\d+\.?\d*)', price_str)
            if match:
                return float(match.group(1))
            
        except:
            pass
        
        return None
    
    def close(self):
        """Close the driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"✓ {self.scraper_name}: Chrome driver closed")
            except Exception as e:
                logger.error(f"{self.scraper_name}: Error closing Chrome driver: {e}")