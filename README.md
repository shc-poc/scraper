# PadMapper Scraper Project

This project contains a Python-based web scraper for collecting apartment listings data from PadMapper, focusing on the Los Angeles area.

## Features

- Scrapes apartment listings in the Los Angeles area
- Collects detailed information including:
  - Pricing data
  - Building details
  - Amenities
  - Neighborhood information
  - Bedroom distributions
- Saves raw data in JSON format
- Provides detailed logging and statistics
- Includes debug screenshots for troubleshooting
- Supports test mode and listing limits

## Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- macOS, Linux, or Windows

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd padmapper_scraper
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Test Run
To test the scraper with a limit of 2 listings:
```bash
python web_scraper.py --test --limit 2
```

### Full Scrape
To run a complete scrape of all listings:
```bash
python web_scraper.py
```

### Options
- `--test`: Run in test mode (more verbose logging)
- `--limit N`: Limit the number of listings to scrape
- `--fallback`: Use fallback mode if standard mode fails

### Example Commands
```bash
# Test run with 5 listings
python web_scraper.py --test --limit 5

# Full run with fallback mode
python web_scraper.py --fallback

# Test run with debug output
python web_scraper.py --test --limit 1
```

## Output

### Data Files
- Raw data: `data/padmapper_data_YYYYMMDD_HHMMSS.json`
- Format: JSON with full listing details

### Logs
- Location: `logs/web_scraper.log`
- Contents:
  - Execution steps
  - Listing counts
  - Price statistics
  - Bedroom distribution
  - Neighborhood counts
  - Error messages (if any)

### Debug
- Screenshots: `logs/debug_screenshot.png`
- Updated on each run for troubleshooting

## Monitoring Progress

The scraper provides real-time feedback through:
1. Console output with current status
2. Detailed logs in `logs/web_scraper.log`
3. Statistics about found listings including:
   - Total number of listings
   - Price ranges
   - Bedroom distribution
   - Neighborhood coverage

## Troubleshooting

If you encounter issues:

1. Check the logs in `logs/web_scraper.log`
2. View the debug screenshot in `logs/debug_screenshot.png`
3. Try running with the `--fallback` option
4. Reduce the number of listings with `--limit`
5. Ensure Chrome is up to date
6. Check your internet connection

## Legal Considerations

This tool is intended for legal use only. Always respect:
- PadMapper's terms of service
- Rate limiting guidelines
- robots.txt directives

## License

[MIT License](LICENSE) 