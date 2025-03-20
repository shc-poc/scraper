#!/bin/bash
# Simple script to run the PadMapper web scraper

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3."
    exit 1
fi

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install each requirement separately for better error handling
echo "Installing/updating requirements..."
pip install -r requirements.txt || {
    echo "Error with batch installation, trying individual packages..."
    
    # Read requirements file and install packages one by one
    while read -r package; do
        if [ ! -z "$package" ]; then
            echo "Installing $package..."
            pip install "$package" || echo "Warning: Failed to install $package"
        fi
    done < requirements.txt
}

# Print usage information
echo ""
echo "PadMapper Web Scraper"
echo "---------------------"
echo ""
echo "Available options:"
echo "  1. Run web scraper (Selenium-based)"
echo "  2. Run web scraper with fallback method (requests-based)"
echo "  3. Run web scraper in test mode (limited sample)"
echo "  4. Schedule daily runs"
echo "  5. View logs"
echo "  6. Exit"
echo ""

# Ask user what to do
read -p "Select an option (1-6): " option

case $option in
    1)
        echo "Running web scraper (Selenium-based)..."
        # Ask for an optional limit
        read -p "Enter a limit for listings (leave empty for no limit): " limit
        if [ -z "$limit" ]; then
            python web_scraper.py
        else
            python web_scraper.py --limit "$limit"
        fi
        ;;
    2)
        echo "Running web scraper with fallback method (requests-based)..."
        # Ask for an optional limit
        read -p "Enter a limit for listings (leave empty for no limit): " limit
        if [ -z "$limit" ]; then
            python web_scraper.py --fallback
        else
            python web_scraper.py --fallback --limit "$limit"
        fi
        ;;
    3)
        echo "Running web scraper in test mode..."
        read -p "Enter a limit for test listings (default: 5): " limit
        if [ -z "$limit" ]; then
            limit=5
        fi
        read -p "Use fallback method (requests instead of Selenium)? (y/n, default: n): " use_fallback
        if [[ "$use_fallback" == "y" || "$use_fallback" == "Y" ]]; then
            python web_scraper.py --test --limit "$limit" --fallback
        else
            python web_scraper.py --test --limit "$limit"
        fi
        ;;
    4)
        echo "Setting up scheduled runs..."
        read -p "Time to run daily (HH:MM, default: 03:00): " run_time
        if [ -z "$run_time" ]; then
            run_time="03:00"
        fi
        
        read -p "Would you like to run the scraper now? (y/n, default: n): " run_now
        if [[ "$run_now" == "y" || "$run_now" == "Y" ]]; then
            run_now_arg="--run-now"
        else
            run_now_arg=""
        fi
        
        read -p "Enter a limit for listings (leave empty for no limit): " limit
        if [ -z "$limit" ]; then
            limit_arg=""
        else
            limit_arg="--limit $limit"
        fi
        
        read -p "Use fallback method (requests instead of Selenium)? (y/n, default: n): " use_fallback
        if [[ "$use_fallback" == "y" || "$use_fallback" == "Y" ]]; then
            fallback_arg="--fallback"
        else
            fallback_arg=""
        fi
        
        echo "Scheduling web scraper to run daily at $run_time"
        python schedule.py --time "$run_time" $run_now_arg $limit_arg $fallback_arg
        ;;
    5)
        echo "Viewing logs..."
        echo ""
        echo "Available logs:"
        echo "  1. Web scraper log"
        echo "  2. Scheduler log" 
        echo "  3. Back to main menu"
        echo ""
        read -p "Select a log to view (1-3): " log_option
        
        case $log_option in
            1)
                if [ -f "logs/web_scraper.log" ]; then
                    less "logs/web_scraper.log"
                else
                    echo "Web scraper log not found."
                fi
                ;;
            2)
                if [ -f "logs/scheduler.log" ]; then
                    less "logs/scheduler.log"
                else
                    echo "Scheduler log not found."
                fi
                ;;
            *)
                echo "Returning to main menu..."
                ;;
        esac
        ;;
    6)
        echo "Exiting..."
        deactivate
        exit 0
        ;;
    *)
        echo "Invalid option. Exiting."
        deactivate
        exit 1
        ;;
esac

# Deactivate virtual environment
deactivate 