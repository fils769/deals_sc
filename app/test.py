from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time

def test_website_for_bot_protection(url, driver, wait_time=15):
    """
    Tests a website for signs of bot protection.
    Returns a dictionary with results.
    """
    result = {
        'url': url,
        'accessible': False,
        'title': None,
        'cloudflare_detected': False,
        'blocked_by_403': False,
        'error': None,
        'page_source_sample': None
    }

    try:
        print(f"[*] Accessing: {url}")
        driver.get(url)

        # Wait for page title to load
        WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, "title")))
        time.sleep(2)  # Additional wait for stability

        current_title = driver.title
        result['title'] = current_title
        print(f"    Title: {current_title}")

        # Check 1: Cloudflare "Just a moment..." page
        cloudflare_indicators = ["Just a moment", "Checking your browser", "Please wait", "DDoS protection"]
        if any(indicator in current_title for indicator in cloudflare_indicators):
            result['cloudflare_detected'] = True
            result['accessible'] = False
            print(f"    ⚠️  CLOUDFLARE/DDOS PROTECTION DETECTED!")

        # Check 2: Look for blocked page indicators in content
        page_source = driver.page_source.lower()
        blocked_indicators = [
            "access denied", "forbidden", "403", "blocked", 
            "bot detected", "unauthorized access", "security challenge"
        ]
        
        if any(indicator in page_source for indicator in blocked_indicators):
            result['accessible'] = False
            print(f"    ⚠️  Page appears to be blocked/restricted")

        # Check 3: Try to find actual content (e.g., body text)
        # If page has very little visible text, it might be blocked
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
            if len(body_text) < 50:  # Very little text
                result['accessible'] = False
                print(f"    ⚠️  Very little content. Possible blocking.")
            else:
                result['accessible'] = True
                print(f"    ✅ Page appears accessible.")
                result['page_source_sample'] = driver.page_source[:500]  # Sample for verification
        except:
            result['accessible'] = False
            print(f"    ⚠️  No main content found.")

    except TimeoutException:
        result['error'] = f"Timeout: Page didn't load in {wait_time} seconds."
        print(f"    ❌ {result['error']}")
    except Exception as e:
        result['error'] = str(e)
        print(f"    ❌ Error: {e}")

    return result

# List of websites to test
websites_to_test = [
    # "https://www.sklavenitis.gr",
    # "https://www.ab.gr", 
    # "https://www.lidl-hellas.gr",
    # "https://www.mymarket.gr",
    # "https://www.masoutis.gr",
    # "https://galaxias.shop/",
    # "https://www.market-in.gr",
    # "https://www.kritikos-sm.gr",
    "https://www.visitgreece.gr/events/",
    "https://allofgreeceone.culture.gov.gr/",
    "https://pigolampides.gr/",
    "https://www.more.com/",
    "https://events.kalamata.gr/",
    "https://www.olakala.gr/"
]

def run_bot_detection_test():
    """Runs the bot detection test for all websites."""
    print("=" * 60)
    print("🚀 STARTING ANTI-BOT SYSTEM DETECTION TEST")
    print("=" * 60)

    # Setup Selenium WebDriver (Chrome)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in background (remove for visual debugging)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Add more convincing User-Agent
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)  # Make sure you have chromedriver installed
    
    results = []
    
    try:
        for website in websites_to_test:
            result = test_website_for_bot_protection(website, driver)
            results.append(result)
            print("-" * 40)
            
            # Small delay between requests to avoid rate limiting
            time.sleep(3)
            
    finally:
        driver.quit()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    blocked_sites = []
    accessible_sites = []
    cloudflare_sites = []
    
    for result in results:
        if result.get('cloudflare_detected'):
            cloudflare_sites.append(result['url'])
        elif not result.get('accessible', False):
            blocked_sites.append(result['url'])
        else:
            accessible_sites.append(result['url'])
    
    print(f"\n✅ ACCESSIBLE SITES ({len(accessible_sites)}):")
    for site in accessible_sites:
        print(f"  - {site}")
    
    print(f"\n⚠️  CLOUDFLARE/BOT PROTECTION DETECTED ({len(cloudflare_sites)}):")
    for site in cloudflare_sites:
        print(f"  - {site}")
    
    print(f"\n❌ BLOCKED/INACCESSIBLE ({len(blocked_sites)}):")
    for site in blocked_sites:
        print(f"  - {site}")
    
    return results

if __name__ == "__main__":
    # Run the test
    all_results = run_bot_detection_test()
    
    # Save detailed results to file
    with open("bot_detection_results.txt", "w", encoding="utf-8") as f:
        f.write("BOT DETECTION TEST RESULTS\n")
        f.write("=" * 50 + "\n\n")
        for result in all_results:
            f.write(f"URL: {result['url']}\n")
            f.write(f"Title: {result['title']}\n")
            f.write(f"Accessible: {result['accessible']}\n")
            f.write(f"Cloudflare Detected: {result['cloudflare_detected']}\n")
            f.write(f"Error: {result['error'] or 'None'}\n")
            if result['page_source_sample']:
                f.write(f"Page Sample: {result['page_source_sample'][:200]}...\n")
            f.write("-" * 40 + "\n")
    
    print(f"\n📁 Detailed results saved to: bot_detection_results.txt")