#!/usr/bin/env python
"""
Scheduler for running the PadMapper web scraper daily.

This script sets up a scheduled job to run the web scraper
once per day at a specified time.
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime

import schedule

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=os.path.join(LOGS_DIR, "scheduler.log"),
    filemode="a"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)
logger = logging.getLogger("web_scheduler")

def run_scraper_job(limit=None, use_fallback=False):
    """
    Run the web scraper as a scheduled job.
    
    Args:
        limit: Maximum number of listings to scrape
        use_fallback: Whether to use the fallback method (requests instead of Selenium)
    """
    logger.info("Running scheduled web scraper job")
    
    try:
        # Get the absolute path to the web_scraper.py script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_script = os.path.join(script_dir, "web_scraper.py")
        
        # Build command with options
        command = f"{sys.executable} {scraper_script}"
        
        if limit is not None:
            command += f" --limit {limit}"
            
        if use_fallback:
            command += " --fallback"
        
        logger.info(f"Executing: {command}")
        
        exit_code = os.system(command)
        if exit_code != 0:
            logger.error(f"Scraper job failed with exit code {exit_code}")
        else:
            logger.info("Scraper job completed successfully")
            
    except Exception as e:
        logger.exception(f"Error running scheduled job: {e}")

def main():
    """Main entry point for the scheduler."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Scheduler for PadMapper Web Scraper")
    parser.add_argument(
        "--time", 
        type=str, 
        default="03:00",
        help="Time to run the scraper daily (24-hour format, default: 03:00)"
    )
    parser.add_argument(
        "--run-now", 
        action="store_true", 
        help="Run the scraper immediately before starting the scheduler"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=None,
        help="Limit the number of listings to scrape"
    )
    parser.add_argument(
        "--fallback", 
        action="store_true", 
        help="Use fallback method (requests instead of Selenium)"
    )
    args = parser.parse_args()
    
    # Create a closure to pass arguments to the job function
    def job():
        run_scraper_job(limit=args.limit, use_fallback=args.fallback)
    
    # Schedule the job
    schedule.every().day.at(args.time).do(job)
    
    # Log scheduling details
    method = "fallback (requests)" if args.fallback else "primary (Selenium)"
    limit_info = f" with limit of {args.limit}" if args.limit else " with no limit"
    logger.info(f"Scheduled web scraper to run daily at {args.time} using {method} method{limit_info}")
    
    # Run immediately if requested
    if args.run_now:
        logger.info("Running web scraper immediately")
        job()
    
    # Calculate time until next run
    next_run = schedule.next_run()
    if next_run:
        time_until_next = next_run - datetime.now()
        hours, remainder = divmod(time_until_next.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        logger.info(f"Next run in {hours}h {minutes}m {seconds}s")
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.exception(f"Error in scheduler loop: {e}")
            # Wait before retrying
            time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    main() 