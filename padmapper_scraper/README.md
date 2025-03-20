# PadMapper Web Scraper

A Python-based web scraper for extracting apartment listings from PadMapper.com. This scraper uses Selenium and BeautifulSoup to navigate through the website and extract detailed information about apartment listings.

## Features

- Extract listing URLs from search results pages
- Gather detailed information about each listing
- Save data in JSON format
- Configurable limits for testing or full scraping
- Built-in scheduler for regular data collection
- Anti-detection measures (rotating user agents, delays, etc.)

## Requirements

- Python 3.6+
- Chrome browser installed (for Selenium WebDriver)
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository or download the source code.
2. Navigate to the project directory.
3. Create a virtual environment (recommended):

```bash
python -m venv venv
```

4. Activate the virtual environment:

- On Windows:
```bash
venv\Scripts\activate
```

- On macOS/Linux:
```bash
source venv/bin/activate
```

5. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Using the run script

The easiest way to run the scraper is to use the provided shell script:

```bash
# Make the script executable if needed
chmod +x run.sh

# Run the script
./run.sh
```

This will present you with options to:
1. Run the full web scraper
2. Run the web scraper in test mode (limited sample)
3. Schedule daily runs
4. Exit

### Option 2: Running directly with Python

You can also run the scraper directly using Python:

```bash
# Full scraping
python web_scraper.py

# With a limit
python web_scraper.py --limit 50

# Test mode with a small sample
python web_scraper.py --test --limit 5
```

### Option 3: Scheduling automated runs

To schedule the scraper to run daily:

```bash
# Schedule to run at 3:00 AM
python schedule.py --time "03:00"

# Schedule and run immediately
python schedule.py --time "03:00" --run-now

# Schedule with a listing limit
python schedule.py --time "03:00" --limit 100
```

## Data Structure

The scraped data is saved as JSON in the `data` directory. Each listing contains the following information (when available):

- ID: Unique identifier for the listing
- URL: Link to the listing page
- Title: Title of the listing
- Price: Rental price
- Bedrooms: Number of bedrooms
- Bathrooms: Number of bathrooms
- Square feet: Square footage
- Address: Property address
- Description: Listing description
- Amenities: List of available amenities
- Pets policy: Information about pet policies
- Image count: Number of images in the listing
- Coordinates: Latitude and longitude (if available)
- Additional details: City, state, ZIP, available date, etc.

## Notes

- This scraper is for educational purposes only.
- Be respectful of the website's resources and avoid excessive scraping.
- The script includes random delays and user agent rotation to minimize impact.
- Consider adding proxies if you need to scrape a large number of listings. 