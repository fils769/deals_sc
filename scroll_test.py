import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("debug")

def debug_page_load():
    """Debug script to see what's actually loading"""
    
    # Simple Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Add user agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        url = "https://kritikos-sm.gr/offers/"
        logger.info(f"🌐 Loading: {url}")
        
        driver.get(url)
        time.sleep(10)  # Wait 10 seconds
        
        # Get page info
        title = driver.title
        current_url = driver.current_url
        page_source = driver.page_source
        
        logger.info(f"📄 Title: {title}")
        logger.info(f"🔗 Current URL: {current_url}")
        logger.info(f"📊 Page source size: {len(page_source):,} characters")
        
        # Save page source to file
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        logger.info("💾 Saved page source to debug_page.html")
        
        # Try to find elements
        logger.info("\n🔍 Looking for elements:")
        
        # Check for common selectors
        selectors = [
            'div.ProductListItem_productItem__cKUyG',
            'div.ProductMenu_listHeader__Crgmj',
            'body',
            'html'
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements('css selector', selector)
                logger.info(f"  {selector}: {len(elements)} found")
            except:
                logger.info(f"  {selector}: ERROR")
        
        # Check if JavaScript is running
        logger.info("\n🧪 Testing JavaScript:")
        try:
            js_result = driver.execute_script("return typeof jQuery;")
            logger.info(f"  jQuery: {js_result}")
        except:
            logger.info("  jQuery: Not found or error")
        
        # Check for errors in console
        logger.info("\n⚠️ Checking for console errors...")
        
        # Keep browser open
        logger.info("\n👀 Browser will stay open for 60 seconds...")
        logger.info("Check if you can see the page content manually")
        time.sleep(60)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        logger.info("✅ Browser closed")

if __name__ == "__main__":
    debug_page_load()