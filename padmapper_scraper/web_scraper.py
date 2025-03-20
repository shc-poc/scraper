"""
PadMapper Web Scraper

This module scrapes PadMapper's website directly using Selenium and BeautifulSoup.
It's designed to work with the web interface rather than the API.
"""
import json
import os
import time
import random
import logging
from datetime import datetime
import re

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Create data directory inside padmapper_scraper folder
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "@data")
os.makedirs(DATA_DIR, exist_ok=True)

# Set up enhanced logging with both file and console output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "web_scraper.log"), mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("web_scraper")

# Constants
BASE_URL = "https://www.padmapper.com/apartments/los-angeles-ca"
PAGE_LOAD_TIMEOUT = 120
SCRIPT_TIMEOUT = 120
IMPLICIT_WAIT = 30
LISTING_SELECTOR = ".ListingCardstyles__LinkContainer-h2iq0y-1, a[href*='/apartments/']"
SCROLL_PAUSE_TIME = 2

def get_random_user_agent():
    """Get a random user agent string that looks more like a real browser"""
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
    ]
    return random.choice(user_agents)

def setup_driver():
    """Set up Chrome driver with anti-detection measures"""
    chrome_options = Options()
    
    # Add common Chrome arguments
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument(f'user-agent={get_random_user_agent()}')
    
    # Add experimental options
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Create the driver service
    service = Service(ChromeDriverManager().install())
    
    # Create and return the driver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Execute CDP commands to prevent detection
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": get_random_user_agent()
    })
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def safe_extract(container, selector, attribute=None):
    """Safely extract an element or attribute from a BeautifulSoup container"""
    try:
        element = container.select_one(selector)
        if not element:
            return None
            
        if attribute:
            return element.get(attribute)
        else:
            return element.text.strip()
    except Exception:
        return None

def extract_listing_urls(limit=None):
    """
    Extract listing URLs from PadMapper search results
    
    Args:
        limit: Maximum number of listings to extract
        
    Returns:
        List of listing URLs
    """
    logger.info("Setting up Chrome driver")
    driver = setup_driver()
    
    try:
        logger.info(f"Navigating to {BASE_URL}")
        
        # Add random delay before accessing the site
        time.sleep(random.uniform(2, 5))
        
        # Multiple attempts in case of timeout
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                driver.get(BASE_URL)
                
                # Longer wait time (45 seconds instead of 20)
                logger.info(f"Waiting for page to load (attempt {attempt+1}/{max_attempts})...")
                WebDriverWait(driver, 45).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, LISTING_SELECTOR))
                )
                logger.info("Page loaded successfully, starting to scrape listing URLs")
                break
            except TimeoutException:
                if attempt < max_attempts - 1:
                    logger.warning(f"Timed out waiting for page to load on attempt {attempt+1}, retrying...")
                    # Clear cookies and cache
                    driver.delete_all_cookies()
                    time.sleep(random.uniform(5, 10))  # Longer delay between attempts
                else:
                    logger.error("Timed out waiting for page to load after multiple attempts")
                    # Try with a different selector as fallback
                    try:
                        logger.info("Trying alternative selector...")
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/apartments/']"))
                        )
                        logger.info("Found alternative elements, continuing with scraping")
                    except TimeoutException:
                        logger.error("Failed to find any listing elements")
                        return []
        
        # Try to get the page source to check if we're being blocked
        page_source = driver.page_source
        if "captcha" in page_source.lower() or "cloudflare" in page_source.lower():
            logger.error("Detected CAPTCHA or Cloudflare protection. Manual intervention might be required.")
            return []
        
        # Take a screenshot to debug
        screenshot_path = os.path.join(LOGS_DIR, "debug_screenshot.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"Saved debug screenshot to {screenshot_path}")
        
        # Keep track of seen URLs to avoid duplicates
        listing_urls = set()
        
        # Scroll down to load more results
        previous_height = driver.execute_script("return document.body.scrollHeight")
        
        # Keep scrolling until we have enough listings or no more results
        scroll_attempts = 0
        max_scroll_attempts = 10  # Limit to prevent infinite loop
        
        while (limit is None or len(listing_urls) < limit) and scroll_attempts < max_scroll_attempts:
            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for page to load
            time.sleep(SCROLL_PAUSE_TIME + random.uniform(1, 2))  # Randomized wait
            
            # Get all listing links
            soup = BeautifulSoup(driver.page_source, "lxml")
            
            # Try multiple selectors to find listing links
            links = soup.select(LISTING_SELECTOR)
            if not links:
                links = soup.select("a[href*='/apartments/']")
            
            # Extract hrefs and add to set
            for link in links:
                href = link.get("href")
                if href and href.startswith("/apartments/"):
                    full_url = f"https://www.padmapper.com{href}"
                    listing_urls.add(full_url)
            
            # Log progress
            logger.info(f"Found {len(listing_urls)} listing URLs so far")
            
            # Check if we've reached the end of the page
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == previous_height:
                scroll_attempts += 1
                logger.info(f"No new content loaded, attempt {scroll_attempts}/{max_scroll_attempts}")
                
                if scroll_attempts >= max_scroll_attempts:
                    logger.info("Reached maximum scroll attempts, stopping")
                    break
            else:
                # Reset attempts if the page grew
                scroll_attempts = 0
                previous_height = new_height
            
            # Add a small random delay to avoid detection
            time.sleep(random.uniform(1, 3))
            
            # Check if we have enough listings
            if limit and len(listing_urls) >= limit:
                logger.info(f"Reached the limit of {limit} listings")
                break
        
        total_urls = len(listing_urls)
        if total_urls > 0:
            logger.info(f"Found a total of {total_urls} unique listing URLs")
        else:
            logger.warning("No listing URLs found. The website might be blocking scraping attempts.")
            
            # Try to save the page source for debugging
            debug_html_path = os.path.join(LOGS_DIR, "debug_page.html")
            with open(debug_html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.info(f"Saved debug HTML to {debug_html_path}")
        
        # Convert set to list for easier processing
        result = list(listing_urls)
        
        # If limit is specified, ensure we don't exceed it
        if limit:
            result = result[:limit]
            
        return result
        
    except Exception as e:
        logger.error(f"Error extracting listing URLs: {e}")
        return []
        
    finally:
        driver.quit()
        logger.info("Chrome driver closed")

def extract_listing_details(url, driver=None):
    """Extract details from a listing page"""
    should_close_driver = False
    max_retries = 3
    retry_delay = 5
    
    try:
        if not driver:
            driver = setup_driver()
            should_close_driver = True
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Extracting details from {url} (attempt {attempt + 1}/{max_retries})")
                
                # Add random delay between requests
                time.sleep(random.uniform(2, 4))
                
                driver.get(url)
                
                # Wait for content to load with exponential backoff
                wait_time = (attempt + 1) * retry_delay
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
                
                # Check for CAPTCHA/protection
                if is_protected_page(driver):
                    if attempt < max_retries - 1:
                        logger.warning(f"Protection detected, retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception("Protection page detected after max retries")
                
                # Extract the data
                html = driver.page_source
                soup = BeautifulSoup(html, 'lxml')
                
                # Save the HTML for debugging
                debug_path = os.path.join(LOGS_DIR, f"listing_debug_{int(time.time())}.html")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(html)
                
                # Pass the HTML content to parse_listing_details
                return parse_listing_details(html)
                
            except TimeoutException:
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
                    
    except Exception as e:
        logger.error(f"Error extracting listing details: {e}")
        return None
        
    finally:
        if should_close_driver and driver:
            driver.quit()

def is_protected_page(driver):
    """Check if we've hit a CAPTCHA or protection page"""
    try:
        # Check common protection indicators
        protection_indicators = [
            "//h1[contains(text(), 'Please verify you are a human')]",
            "//title[contains(text(), 'Security Check')]",
            "//div[contains(@class, 'cf-browser-verification')]",
            "//div[contains(@id, 'challenge-running')]"
        ]
        
        for indicator in protection_indicators:
            if len(driver.find_elements(By.XPATH, indicator)) > 0:
                return True
                
        # Check for Cloudflare specifically
        if "cf-" in driver.page_source or "cloudflare" in driver.page_source.lower():
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error checking for protection: {e}")
        return True  # Assume protected if we can't check

def extract_listing_details_fallback(url):
    """
    Extract details from a single listing page using requests instead of Selenium
    
    Args:
        url: URL of the listing page
        
    Returns:
        Dictionary containing listing details or None if failed
    """
    logger.info(f"Extracting details from {url} (fallback method)")
    
    # Extract listing ID from URL
    try:
        listing_id = url.split('/')[-1]
    except Exception:
        listing_id = f"unknown_{int(time.time())}"
        
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "TE": "Trailers",
        "DNT": "1"
    }
    
    try:
        # Add a random delay before visiting the page
        time.sleep(random.uniform(1, 3))
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse the page
        soup = BeautifulSoup(response.text, "lxml")
        
        # Save debug HTML
        debug_html_path = os.path.join(LOGS_DIR, f"detail_page_{listing_id}.html")
        with open(debug_html_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info(f"Saved detail page HTML to {debug_html_path}")
        
        # Extract basic information
        title_elem = soup.select_one("h1")
        title = title_elem.text.strip() if title_elem else "Unknown"
        
        # Extract price
        price_elem = soup.select_one("[data-testid='listing-price']")
        if not price_elem:
            price_elem = soup.select_one(".ListingPrice")
        price_text = price_elem.text.strip() if price_elem else ""
        price = re.search(r'\$[\d,]+', price_text)
        price = price.group(0).replace('$', '').replace(',', '') if price else None
        
        # Extract beds and baths
        beds_elem = soup.select_one("[data-testid='listing-bedroom']")
        if not beds_elem:
            beds_elem = soup.select_one(".ListingBedrooms")
        beds_text = beds_elem.text.strip() if beds_elem else ""
        beds = re.search(r'(\d+)', beds_text)
        beds = beds.group(1) if beds else None
        
        baths_elem = soup.select_one("[data-testid='listing-bathroom']")
        if not baths_elem:
            baths_elem = soup.select_one(".ListingBathrooms")
        baths_text = baths_elem.text.strip() if baths_elem else ""
        baths = re.search(r'(\d+)', baths_text)
        baths = baths.group(1) if baths else None
        
        # Extract square footage
        sqft_elem = soup.select_one("[data-testid='listing-specification-2']")
        if not sqft_elem:
            sqft_elem = soup.select_one(".ListingSquareFeet")
        sqft_text = sqft_elem.text.strip() if sqft_elem else ""
        sqft = re.search(r'(\d+)', sqft_text)
        sqft = sqft.group(1) if sqft else None
        
        # Extract address
        address_elem = soup.select_one("[data-testid='listing-address']")
        if not address_elem:
            address_elem = soup.select_one(".ListingAddress")
        address = address_elem.text.strip() if address_elem else "Unknown"
        
        # Extract description
        description_elem = soup.select_one("[data-testid='listing-description']")
        if not description_elem:
            description_elem = soup.select_one(".ListingDescription")
        description = description_elem.text.strip() if description_elem else ""
        
        # Extract amenities
        amenities_list = []
        amenities_elems = soup.select("[data-testid='listing-amenity-item']")
        if not amenities_elems:
            amenities_elems = soup.select(".ListingAmenity")
        for amenity in amenities_elems:
            amenities_list.append(amenity.text.strip())
        
        # Count images by looking for image elements
        image_elems = soup.select("img[src*='padmapper']")
        image_count = len(image_elems)
        
        # Build the listing object
        listing = {
            "id": listing_id,
            "url": url,
            "title": title,
            "price": price,
            "bedrooms": beds,
            "bathrooms": baths,
            "square_feet": sqft,
            "address": address,
            "description": description,
            "amenities": amenities_list,
            "image_count": image_count,
            "last_scraped": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Try to extract more details like latitude/longitude from page scripts
        try:
            scripts = soup.select("script")
            for script in scripts:
                script_text = script.string
                if script_text and "window.__PRELOADED_STATE__" in script_text:
                    # Extract JSON data from script
                    json_match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', script_text, re.DOTALL)
                    if json_match:
                        json_data = json_match.group(1)
                        # Try to clean up the JSON
                        try:
                            data = json.loads(json_data)
                            if "listing" in data and "lat" in data["listing"]:
                                listing["latitude"] = data["listing"]["lat"]
                                listing["longitude"] = data["listing"]["lng"]
                                
                                # Extract more details if available
                                if "available_date" in data["listing"]:
                                    listing["available_date"] = data["listing"]["available_date"]
                                if "city" in data["listing"]:
                                    listing["city"] = data["listing"]["city"]
                                if "state" in data["listing"]:
                                    listing["state"] = data["listing"]["state"]
                                if "zip" in data["listing"]:
                                    listing["zip"] = data["listing"]["zip"]
                        except Exception as e:
                            logger.warning(f"Failed to parse JSON data from script: {e}")
        except Exception as e:
            logger.warning(f"Failed to extract additional details from scripts: {e}")
            
        logger.info(f"Successfully extracted details for listing {listing_id} using fallback method")
        return listing
        
    except Exception as e:
        logger.error(f"Error extracting details for listing {url} (fallback method): {e}")
        return None

def save_json(data, filename):
    """Save data to a JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file: {e}")
        return False

def get_listing_urls_fallback(limit=None):
    """Extract listing URLs using requests and BeautifulSoup (fallback method)"""
    logger.info("Using fallback method to get listing URLs")
    
    # Set up session with proper headers
    session = requests.Session()
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'DNT': '1'
    }
    
    try:
        # Add a longer initial delay
        time.sleep(random.uniform(3, 5))
        
        logger.info(f"Attempting to fetch {BASE_URL}")
        response = session.get(BASE_URL, headers=headers, timeout=30)
        
        if 'cf-ray' in response.headers:
            logger.warning("Cloudflare detected, might need to adjust approach")
            
        if response.status_code != 200:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return []
            
        # Save debug HTML
        debug_html_path = os.path.join(LOGS_DIR, "fallback_debug_page.html")
        with open(debug_html_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Look for listing URLs
        listing_urls = []
        
        # Try multiple selectors
        selectors = [
            "a[href*='/apartments/']",
            ".ListingCardstyles__LinkContainer-h2iq0y-1",
            "a[href*='/buildings/']"
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and ('/apartments/' in href or '/buildings/' in href):
                    full_url = f"https://www.padmapper.com{href}" if href.startswith('/') else href
                    listing_urls.append(full_url)
        
        # Remove duplicates
        listing_urls = list(set(listing_urls))
        
        # Apply limit if specified
        if limit:
            listing_urls = listing_urls[:limit]
            
        logger.info(f"Found {len(listing_urls)} listing URLs")
        return listing_urls
        
    except Exception as e:
        logger.error(f"Error getting listing URLs: {e}")
        return []

def log_stats(data):
    """Log statistics about the scraped data"""
    try:
        # Get the buildings data from the correct path
        buildings = data.get("bundle", {}).get("buildings", {})
        logger.info(f"Found {len(buildings)} unique buildings")

        # Initialize counters
        total_listings = 0
        prices = []
        bedroom_counts = {}
        neighborhoods = set()
        amenities_count = {}

        # Process each building
        for building_id, building in buildings.items():
            if isinstance(building, dict):
                # Count listings in this building
                floorplan_count = building.get("floorplan_count", 0)
                total_listings += floorplan_count

                # Get price range if available
                min_price = building.get("min_price")
                if min_price and isinstance(min_price, (int, float)):
                    prices.append(min_price)
                max_price = building.get("max_price")
                if max_price and isinstance(max_price, (int, float)):
                    prices.append(max_price)

                # Get neighborhood
                neighborhood = building.get("neighborhood")
                if neighborhood:
                    neighborhoods.add(neighborhood)

                # Get amenities
                amenities = building.get("amenities", [])
                for amenity in amenities:
                    amenities_count[amenity] = amenities_count.get(amenity, 0) + 1

                # Get bedroom counts
                min_beds = building.get("min_beds")
                max_beds = building.get("max_beds")
                if min_beds is not None:
                    bedroom_counts[min_beds] = bedroom_counts.get(min_beds, 0) + 1
                if max_beds is not None and max_beds != min_beds:
                    bedroom_counts[max_beds] = bedroom_counts.get(max_beds, 0) + 1

        # Log the statistics
        logger.info(f"Found {total_listings} total listings across {len(buildings)} buildings")

        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            logger.info(f"Price range: ${min_price:,.2f} - ${max_price:,.2f}")
            logger.info(f"Average price: ${avg_price:,.2f}")

        # Log bedroom distribution
        if bedroom_counts:
            logger.info("Bedroom distribution:")
            for beds, count in sorted(bedroom_counts.items()):
                logger.info(f"  {beds} bedroom(s): {count} listings")

        # Log neighborhood count
        if neighborhoods:
            logger.info(f"Found listings in {len(neighborhoods)} neighborhoods:")
            for hood in sorted(neighborhoods):
                logger.info(f"  - {hood}")

        # Log top amenities
        if amenities_count:
            logger.info("\nTop amenities:")
            sorted_amenities = sorted(amenities_count.items(), key=lambda x: x[1], reverse=True)[:10]
            for amenity, count in sorted_amenities:
                logger.info(f"  - {amenity}: {count} buildings")

    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}")
        logger.error("Data structure received:", json.dumps(data, indent=2)[:500] + "...")

def extract_preloaded_state(driver):
    """Extract the preloaded state data from the page"""
    try:
        logger.info("Waiting for preloaded state to be available...")
        script = """
        return window.__PRELOADED_STATE__;
        """
        state = driver.execute_script(script)
        if state:
            logger.info("Successfully extracted preloaded state")
            return state
        else:
            logger.error("Preloaded state not found in page")
            return None
    except Exception as e:
        logger.error(f"Error extracting preloaded state: {str(e)}")
        return None

def extract_search_results(limit=None):
    """Extract search results from PadMapper"""
    logger.info(f"Starting extraction{' (test mode)' if limit else ''}")
    
    try:
        driver = setup_driver()
        logger.info(f"Navigating to {BASE_URL}")
        driver.get(BASE_URL)
        
        # Take screenshot for debugging
        driver.save_screenshot(os.path.join(LOGS_DIR, "debug_screenshot.png"))
        logger.info("Saved debug screenshot")
        
        # Extract data
        data = extract_preloaded_state(driver)
        if not data:
            logger.error("Failed to extract data")
            return None
            
        # Save raw data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"padmapper_data_{timestamp}.json"
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved raw data to {filename}")
        
        # Log statistics
        log_stats(data)
        
        return data
        
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        return None
    finally:
        try:
            driver.quit()
            logger.info("Closed browser")
        except:
            pass

def fetch_building_html(building_id):
    """
    Fetch the HTML content for a specific building using its ID.
    
    Args:
        building_id: The building ID to fetch details for
        
    Returns:
        Tuple of (success, html_content)
        where success is a boolean indicating if the fetch was successful
        and html_content is the raw HTML string or None if failed
    """
    logger.info(f"Fetching HTML content for building {building_id}")
    
    # Construct the building URL
    building_url = f"https://www.padmapper.com/buildings/p{building_id}"
    
    # Set up headers to mimic a browser
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "TE": "Trailers",
        "DNT": "1"
    }
    
    try:
        # Add random delay
        time.sleep(random.uniform(1, 3))
        
        # Make the request
        response = requests.get(building_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Save debug HTML
        debug_html_path = os.path.join(LOGS_DIR, f"building_{building_id}.html")
        with open(debug_html_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info(f"Saved building HTML to {debug_html_path}")
        
        return True, response.text
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch building {building_id}: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error fetching building {building_id}: {e}")
        return False, None

def extract_listing_details_with_html(url, html_content=None):
    """
    Extract details from a listing page, optionally using provided HTML content
    
    Args:
        url: URL of the listing page
        html_content: Optional pre-fetched HTML content
        
    Returns:
        Dictionary containing listing details
    """
    logger.info(f"Extracting details from {url}")
    
    # Extract listing ID from URL
    try:
        listing_id = url.split('/')[-1]
    except Exception:
        listing_id = f"unknown_{int(time.time())}"
    
    # If no HTML content provided, fetch it using Selenium
    if not html_content:
        driver = setup_driver()
        try:
            # Add random delay
            time.sleep(random.uniform(1, 3))
            driver.get(url)
            
            # Wait for main content
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ListingPage__ListingDetailsContainer-sc-13if55j-0"))
                )
            except TimeoutException:
                logger.error(f"Timed out waiting for listing page to load: {url}")
                return None
                
            html_content = driver.page_source
        finally:
            driver.quit()
    
    # Parse the HTML content
    soup = BeautifulSoup(html_content, "lxml")
    
    # Extract listing details as before...
    # [Previous extraction code remains the same]
    
    # Build and return the listing object
    listing = {
        "id": listing_id,
        "url": url,
        "html_content": html_content,  # Store the raw HTML
        # [Rest of the listing details remain the same]
    }
    
    return listing

def parse_listing_details(html_content):
    """Parse listing details from HTML content."""
    try:
        # Parse HTML content into BeautifulSoup object
        soup = BeautifulSoup(html_content, 'lxml')
        
        listing = {
            'id': None,
            'url': None,
            'title': None,
            'price': None,
            'bedrooms': None,
            'bathrooms': None,
            'square_feet': None,
            'address': None,
            'description': None,
            'amenities': [],
            'image_count': 0,
            'last_scraped': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'available_units': [],
            'floorplans': []
        }

        # Extract data from window.__PRELOADED_STATE__
        scripts = soup.find_all('script')
        preloaded_state = None
        for script in scripts:
            if script.string and 'window.__PRELOADED_STATE__' in script.string:
                try:
                    # Extract the JSON object
                    json_str = script.string.split('window.__PRELOADED_STATE__ = ')[1].split(';')[0]
                    preloaded_state = json.loads(json_str)
                    logger.info("Successfully extracted preloaded state")
                    break
                except Exception as e:
                    logger.warning(f"Failed to parse preloaded state: {e}")
                    continue

        if preloaded_state:
            # Extract listing data from preloaded state
            listables = preloaded_state.get('listables', {})
            current_listing = None
            
            # Find the first listing in listables
            if 'listables' in listables and len(listables['listables']) > 0:
                current_listing = listables['listables'][0]
                logger.info("Found current listing in preloaded state")

            if current_listing:
                listing['id'] = str(current_listing.get('listing_id'))
                listing['url'] = current_listing.get('padmapper_url')
                listing['title'] = current_listing.get('title')
                listing['address'] = current_listing.get('address')
                listing['price'] = str(current_listing.get('max_price'))
                listing['bedrooms'] = str(current_listing.get('max_bedrooms'))
                listing['bathrooms'] = str(current_listing.get('max_bathrooms'))
                listing['square_feet'] = str(current_listing.get('max_square_feet'))
                listing['description'] = current_listing.get('short_description')
                listing['amenities'] = current_listing.get('amenity_tags', [])
                listing['image_count'] = len(current_listing.get('image_ids', []))

                # Extract floorplan data
                if 'floorplan_count' in current_listing:
                    floorplans_data = current_listing.get('floorplans', [])
                    logger.info(f"Found {len(floorplans_data)} floorplans")
                    for fp in floorplans_data:
                        floorplan = {
                            'id': str(fp.get('id')),
                            'name': fp.get('name'),
                            'bedrooms': fp.get('bedrooms'),
                            'bathrooms': fp.get('bathrooms'),
                            'min_square_feet': fp.get('min_square_feet'),
                            'max_square_feet': fp.get('max_square_feet'),
                            'min_price': fp.get('min_price'),
                            'max_price': fp.get('max_price'),
                            'available_units_count': fp.get('available_units_count', 0)
                        }
                        listing['floorplans'].append(floorplan)

                # Extract available units data
                units_data = current_listing.get('units', [])
                logger.info(f"Found {len(units_data)} units")
                for unit in units_data:
                    if unit.get('is_available', False):
                        unit_data = {
                            'floorplan_id': str(unit.get('floorplan_id')),
                            'title': unit.get('title'),
                            'bedrooms': unit.get('bedrooms'),
                            'bathrooms': unit.get('bathrooms'),
                            'square_feet': unit.get('square_feet'),
                            'price': unit.get('price'),
                            'available_date': unit.get('available_date'),
                            'is_available': True,
                            'features': unit.get('features', []),
                            'unit_amenities': unit.get('unit_amenities', []),
                            'lease_terms': {
                                'min_lease_days': unit.get('min_lease_days'),
                                'max_lease_days': unit.get('max_lease_days')
                            }
                        }
                        listing['available_units'].append(unit_data)
                        logger.info(f"Added available unit: {unit_data['title']}")

        # Fallback to HTML parsing if needed
        if not listing['title']:
            title_elem = soup.find('h1', {'class': 'listing-title'}) or soup.find('title')
            if title_elem:
                listing['title'] = title_elem.text.strip()

        if not listing['address']:
            address_elem = soup.find('div', {'class': 'listing-address'})
            if address_elem:
                listing['address'] = address_elem.text.strip()

        if not listing['amenities']:
            amenities_container = soup.find('div', {'class': 'amenities-section'})
            if amenities_container:
                amenities = amenities_container.find_all('div', {'class': 'amenity-item'})
                listing['amenities'] = [amenity.text.strip() for amenity in amenities]

        # Clean up any None values or empty lists
        listing = {k: v for k, v in listing.items() if v is not None and v != [] and v != ''}
        
        logger.info(f"Successfully parsed listing with {len(listing['available_units'])} available units and {len(listing['floorplans'])} floorplans")
        return listing
    except Exception as e:
        logger.error(f"Error parsing listing details: {str(e)}")
        return None

def test_parse_building(url):
    """Test function to parse a specific building URL"""
    logger.info(f"Testing parser with URL: {url}")
    
    try:
        # Set up session with proper headers
        session = requests.Session()
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Fetch the page
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Save debug HTML
        debug_path = os.path.join(LOGS_DIR, f"building_debug_{int(time.time())}.html")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(response.text)
            
        # Parse the details
        result = parse_listing_details(soup)
        
        # Save parsed JSON
        if result:
            json_path = os.path.join(DATA_DIR, f"building_parsed_{int(time.time())}.json")
            with open(json_path, "w") as f:
                json.dump(result, f, indent=2)
            logger.info(f"Saved parsed JSON to {json_path}")
            
        return result
        
    except Exception as e:
        logger.error(f"Error testing parser: {e}")
        return None

def main(limit=None, test_mode=False, use_fallback=False):
    """Main entry point for the scraper"""
    logger.info("Starting PadMapper scraper")
    
    # Create output directory for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(DATA_DIR, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    
    try:
        # Get listing URLs
        if use_fallback:
            listing_urls = get_listing_urls_fallback(limit=limit)
        else:
            listing_urls = extract_listing_urls(limit=limit)
            
        if not listing_urls:
            logger.error("No listing URLs found")
            return False
            
        logger.info(f"Found {len(listing_urls)} listings to process")
        
        # Process each listing
        results = []
        for url in listing_urls:
            try:
                # Extract building ID from URL
                building_id = None
                if "/buildings/p" in url:
                    building_id = url.split("/buildings/p")[1].split("/")[0]
                
                # If we have a building ID, try to fetch HTML directly
                html_content = None
                if building_id:
                    success, html_content = fetch_building_html(building_id)
                    if not success:
                        logger.warning(f"Failed to fetch HTML for building {building_id}, falling back to Selenium")
                
                # Extract listing details
                listing = extract_listing_details_with_html(url, html_content)
                if listing:
                    results.append(listing)
                    
                    # Save individual listing result
                    listing_file = os.path.join(run_dir, f"listing_{listing['id']}.json")
                    with open(listing_file, "w") as f:
                        json.dump(listing, f, indent=2)
                    
                # Add random delay between listings
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.error(f"Error processing listing {url}: {e}")
                continue
        
        # Save all results
        if results:
            output_file = os.path.join(DATA_DIR, f"padmapper_data_{timestamp}.json")
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved {len(results)} listings to {output_file}")
            
            # Save processed results
            processed_file = os.path.join(DATA_DIR, f"processed_results_{timestamp}.json")
            with open(processed_file, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved processed results to {processed_file}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PadMapper Web Scraper")
    parser.add_argument("--test", action="store_true", help="Run in test mode with fewer listings")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of listings to scrape")
    parser.add_argument("--fallback", action="store_true", help="Use fallback method (requests instead of Selenium)")
    parser.add_argument("--url", type=str, help="Test a specific URL")
    
    args = parser.parse_args()
    
    try:
        if args.url:
            test_parse_building(args.url)
        else:
            main(limit=args.limit, test_mode=args.test, use_fallback=args.fallback)
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Exiting...")
    except Exception as e:
        logger.exception(f"Error during scraping: {e}")
        print(f"\nAn error occurred: {e}")