import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_scraping():
    """Debug function to test page loading"""
    logger.info("Starting debug scraping...")
    
    chrome_options = Options()
    # Run in non-headless mode for debugging
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Disable images
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        # Use local chromedriver
        service = Service("C:\\Windows\\chromedriver.EXE")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Test page 1
        logger.info("Testing page 1...")
        driver.get("https://www.skroutz.gr/deals")
        time.sleep(5)
        
        # Save screenshot
        driver.save_screenshot("page1.png")
        logger.info("Saved page1.png")
        
        # Get page info
        page1_source = driver.page_source
        soup1 = BeautifulSoup(page1_source, 'html.parser')
        deals1 = soup1.select('.cf.card[data-skuid]')
        logger.info(f"Page 1: Found {len(deals1)} deals")
        
        # Look for paginator
        paginator = soup1.select('.paginator')
        logger.info(f"Page 1: Has paginator: {len(paginator) > 0}")
        
        # Look for next button
        next_buttons = soup1.select('a.button.next[href*="page="]')
        logger.info(f"Page 1: Next buttons found: {len(next_buttons)}")
        
        if next_buttons:
            next_url = next_buttons[0].get('href')
            logger.info(f"Page 1: Next URL: {next_url}")
        
        # Test page 2
        logger.info("\nTesting page 2...")
        driver.get("https://www.skroutz.gr/deals?page=2")
        time.sleep(5)
        
        # Save screenshot
        driver.save_screenshot("page2.png")
        logger.info("Saved page2.png")
        
        # Get page info
        page2_source = driver.page_source
        soup2 = BeautifulSoup(page2_source, 'html.parser')
        deals2 = soup2.select('.cf.card[data-skuid]')
        logger.info(f"Page 2: Found {len(deals2)} deals")
        
        # Check if we got redirected
        current_url = driver.current_url
        logger.info(f"Current URL after page 2: {current_url}")
        
        # Check page title
        page_title = driver.title
        logger.info(f"Page title: {page_title}")
        
        # Save page source for debugging
        with open("page2_source.html", "w", encoding="utf-8") as f:
            f.write(page2_source)
        logger.info("Saved page2_source.html")
        
        driver.quit()
        
        return {
            "page1_deals": len(deals1),
            "page2_deals": len(deals2),
            "page2_url": current_url,
            "success": len(deals2) > 0
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    result = debug_scraping()
    print(f"\nResult: {result}")