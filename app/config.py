import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class Settings:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/deals")
    
    # Selenium
    CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "chromedriver")
    HEADLESS = os.getenv("HEADLESS", "True").lower() == "true"
    
    # General Scraping Settings
    PAGE_DELAY_SECONDS = int(os.getenv("PAGE_DELAY_SECONDS", "3"))
    DEFAULT_MAX_PRODUCTS = int(os.getenv("DEFAULT_MAX_PRODUCTS", "200"))
    DEFAULT_MAX_PAGES = int(os.getenv("DEFAULT_MAX_PAGES", "10"))
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "logs/scraper.log"
    
    # Request settings
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    # Website-specific settings
    WEBSITES = {
        "market-in.gr": {
            "base_url": "https://www.market-in.gr",
            "deals_url": "https://www.market-in.gr/el-gr/ALL/1-1/",
            "enabled": os.getenv("MARKETIN_ENABLED", "True").lower() == "true",
            "max_pages": int(os.getenv("MARKETIN_MAX_PAGES", "50")),
            "deals_per_page": 24,
            "timeout": int(os.getenv("MARKETIN_TIMEOUT", "30")),
            "category": "supermarket",
        },
        # SKLAVENITIS FULL CONFIG
        "sklavenitis": {
            "base_url": "https://www.sklavenitis.gr",
            "deals_url": "https://www.sklavenitis.gr/sylloges/prosfores/",
            "enabled": os.getenv("SKLAVENITIS_ENABLED", "True").lower() == "true",
            "max_pages": int(os.getenv("SKLAVENITIS_MAX_PAGES", "50")),
            "deals_per_page": 96,
            "timeout": int(os.getenv("SKLAVENITIS_TIMEOUT", "30")),
            "category": "supermarket",
            "postal_codes": {
                "Αττική": [
                    "10431", "10432", "10433", "10434", "10435", "10436", "10437", "10438", "10439", "10440",
                    "10441", "10442", "10443", "10444", "10445", "10446", "10447", "10551", "10552", "10553",
                    "10554", "10555", "10556", "10557", "10558", "10559", "10560", "10561", "10562", "10563",
                    "10564", "10671", "10672", "10673", "10674", "10675", "10676", "10677", "10678", "10679",
                    "10680", "10681", "10682", "10683", "11141", "11142", "11143", "11144", "11145", "11146",
                    "11147", "11251", "11252", "11253", "11254", "11255", "11256", "11257", "11361", "11362",
                    "11363", "11364", "11471", "11472", "11473", "11474", "11475", "11476", "11521", "11522",
                    "11523", "11524", "11525", "11526", "11527", "11528", "11631", "11632", "11633", "11634",
                    "11635", "11636", "11741", "11742", "11743", "11744", "11745", "11851", "11852", "11853",
                    "11854", "11855", "12131", "12132", "12133", "12134", "12135", "12136", "12137", "12241",
                    "12242", "12243", "12244", "12351", "12461", "12462", "12561", "13121", "13122", "13123",
                    "13231", "13232", "13341", "13342", "13343", "13344", "13345", "13351", "13451", "13561",
                    "13562", "13671", "13672", "13673", "13674", "13675", "13677", "13678", "13679", "14121",
                    "14122", "14123", "14231", "14232", "14233", "14234", "14235", "14341", "14342", "14343",
                    "14451", "14452", "14561", "14562", "14563", "14564", "14569", "14574", "14578", "14671",
                    "15121", "15122", "15123", "15124", "15125", "15126", "15127", "15231", "15232", "15233",
                    "15234", "15235", "15236", "15237", "15238", "15239", "15341", "15342", "15343", "15344",
                    "15451", "15452", "15561", "15562", "15669", "15771", "15772", "15773", "16121", "16122",
                    "16231", "16232", "16233", "16341", "16342", "16343", "16344", "16345", "16346", "16451",
                    "16452", "16561", "16562", "16671", "16672", "16673", "16674", "16675", "16777", "17121",
                    "17122", "17123", "17124", "17234", "17235", "17236", "17237", "17341", "17342", "17343",
                    "17455", "17456", "17561", "17562", "17563", "17564", "17671", "17672", "17673", "17674",
                    "17675", "17676", "17755", "17778", "18120", "18121", "18122", "18233", "18344", "18345",
                    "18346", "18450", "18451", "18452", "18453", "18454", "18531", "18532", "18533", "18534",
                    "18535", "18536", "18537", "18538", "18539", "18540", "18541", "18542", "18543", "18544",
                    "18545", "18546", "18547", "18551", "18648", "18755", "18756", "18757", "18758", "18863",
                    "19003", "19005", "19007", "19009", "19011", "19014", "19015", "19016", "19023"
                ],
                "Θεσσαλονίκη": [
                    "54248", "54249", "54250", "54351", "54352", "54453", "54454", "54500", "54621", "54622",
                    "54623", "54624", "54625", "54626", "54627", "54628", "54629", "54630", "54631", "54632",
                    "54633", "54634", "54635", "54636", "54638", "54639", "54640", "54641", "54642", "54643",
                    "54644", "54645", "54646", "54655", "55131", "55132", "55133", "55134", "55135", "55236",
                    "55337", "55438", "55534", "55535", "55536", "56121", "56122", "56123", "56224", "56225",
                    "56238", "56343", "56429", "56430", "56431", "56437", "56532", "56533", "56625", "56626",
                    "56727", "56728", "57001", "57003", "57004", "57006", "57007", "57008", "57009", "57010",
                    "57011", "57013", "57018", "57019", "57022", "57200", "57300", "57400", "57500", "63080"
                ],
                "Πάτρα": [
                    "26221", "26222", "26223", "26224", "26225", "26226", "26331", "26332", "26333", "26334",
                    "26335", "26441", "26442", "26443", "26500", "26504"
                ],
                "Λάρισα": [
                    "40100", "40400", "41221", "41222", "41223", "41334", "41335", "41336", "41447", "41500"
                ],
                "Ιωάννινα": [
                    "45221", "45222", "45332", "45333", "45444", "45445", "45500"
                ]
            }
        },
        "ab.gr": {
            "base_url": "https://www.ab.gr",
            "deals_url": "https://www.ab.gr/search/promotions",
            "enabled": os.getenv("AB_ENABLED", "True").lower() == "true",
            "max_pages": int(os.getenv("AB_MAX_PAGES", "20")),
            "deals_per_page": 24,
            "timeout": int(os.getenv("AB_TIMEOUT", "30")),
            "category": "supermarket",
        },"masoutis.gr": {
            "base_url": "https://www.masoutis.gr",
            "deals_url": "https://www.masoutis.gr/categories/index/prosfores?item=0&sort=2",
            "enabled": os.getenv("MASOUTIS_ENABLED", "True").lower() == "true",
            "max_pages": 1,  # Infinite scroll, not paginated
            "deals_per_page": 50,  # Estimated per scroll
            "timeout": int(os.getenv("MASOUTIS_TIMEOUT", "60")),  # Longer for scrolling
            "category": "supermarket",
        },
        'kritikos-sm.gr': {
            'enabled': True,
            'max_pages': 1,  # For infinite scroll, pages don't apply
            'delay': 2,
            'timeout': 30,
            'retries': 3
        }
       
    }
    
    # Scraper settings
    SCRAPER_CONFIG = {
        "default_timeout": 30,
        "implicit_wait": 10,
        "page_load_timeout": 30,
        "retry_attempts": 3,
        "retry_delay": 5,
        "scroll_attempts": 3,
        "random_delay_min": 1,
        "random_delay_max": 3,
        "proxy_enabled": os.getenv("PROXY_ENABLED", "False").lower() == "true",
        "proxy_list": os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else [],
    }
    
    # Database cleanup settings
    CLEANUP_CONFIG = {
        "inactive_days": int(os.getenv("INACTIVE_DAYS", "30")),
        "auto_cleanup": os.getenv("AUTO_CLEANUP", "True").lower() == "true",
        "cleanup_interval_hours": int(os.getenv("CLEANUP_INTERVAL_HOURS", "24")),
    }
    
    # Performance settings
    PERFORMANCE = {
        "max_concurrent_scrapers": int(os.getenv("MAX_CONCURRENT_SCRAPERS", "2")),
        "scraper_cooldown": int(os.getenv("SCRAPER_COOLDOWN", "5")),
        "db_pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
        "db_max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "40")),
    }
    
    # Email notifications (optional)
    EMAIL_CONFIG = {
        "enabled": os.getenv("EMAIL_ENABLED", "False").lower() == "true",
        "smtp_server": os.getenv("SMTP_SERVER", ""),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "email_from": os.getenv("EMAIL_FROM", ""),
        "email_to": os.getenv("EMAIL_TO", ""),
        "email_username": os.getenv("EMAIL_USERNAME", ""),
        "email_password": os.getenv("EMAIL_PASSWORD", ""),
    }
    
    def get_website_config(self, website_name: str) -> Dict[str, Any]:
        """Get configuration for a specific website"""
        return self.WEBSITES.get(website_name, {})
    
    def get_enabled_websites(self) -> list:
        """Get list of enabled websites"""
        return [name for name, config in self.WEBSITES.items() 
                if config.get("enabled", True)]
    
    def get_scraper_names(self) -> list:
        """Get list of scraper names from website configs"""
        return list(self.WEBSITES.keys())

settings = Settings()