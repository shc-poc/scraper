"""
Simple test script to verify that the web scraper works
and all dependencies are properly installed.
"""
import os
import sys

# Print Python version and location
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Try importing required modules
print("\nTesting imports:")
try:
    import requests
    print("✓ requests")
except ImportError:
    print("✗ requests - Not installed")

try:
    from bs4 import BeautifulSoup
    print("✓ BeautifulSoup")
except ImportError:
    print("✗ BeautifulSoup - Not installed")

try:
    import lxml
    print("✓ lxml")
except ImportError:
    print("✗ lxml - Not installed")

try:
    from selenium import webdriver
    print("✓ selenium")
except ImportError:
    print("✗ selenium - Not installed")

try:
    from webdriver_manager.chrome import ChromeDriverManager
    print("✓ webdriver-manager")
except ImportError:
    print("✗ webdriver-manager - Not installed")

try:
    import schedule
    print("✓ schedule")
except ImportError:
    print("✗ schedule - Not installed")

# Check if directories exist
print("\nChecking directories:")
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_dir, "data")
logs_dir = os.path.join(current_dir, "logs")

print(f"Current directory: {current_dir}")
print(f"Data directory exists: {os.path.exists(data_dir)}")
print(f"Logs directory exists: {os.path.exists(logs_dir)}")

# Create directories if they don't exist
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
    print(f"Created data directory: {data_dir}")

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
    print(f"Created logs directory: {logs_dir}")

print("\nTest completed. If all modules are installed and directories exist, you're ready to run the web scraper.")

# Try initializing a Chrome driver (without opening a browser)
print("\nTesting Chrome WebDriver initialization:")
try:
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    
    print("Installing Chrome WebDriver...")
    driver = webdriver.Chrome(service=service, options=options)
    print("✓ Chrome WebDriver successfully initialized")
    driver.quit()
except Exception as e:
    print(f"✗ Chrome WebDriver initialization failed: {e}")

if __name__ == "__main__":
    print("\nIf all tests have passed, you can run the web scraper using:")
    print("./run.sh")
    print("or")
    print("python web_scraper.py --test --limit 2") 