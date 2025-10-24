"""
Interactive Demo for Phase 4: Trading Scheduler

This script demonstrates the automated trading scheduler:
1. Shows current market status
2. Displays scheduled jobs
3. Allows manual triggering of jobs
4. Monitors scheduler in real-time

Usage:
    python examples/test_scheduler.py
"""

import time
import os
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.database.base import SessionLocal
from backend.database.init_db import init_database
from backend.services.scheduler import TradingScheduler
from backend.services.market_data import MarketDataService
from backend.config import settings
from backend.logger import get_logger

logger = get_logger(__name__)


def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)


def print_header(text):
    """Print a formatted header."""
    print_separator()
    print(f" {text}")
    print_separator()


def display_market_status(scheduler: TradingScheduler):
    """Display current market status."""
    print_header("MARKET STATUS")

    now = datetime.now(scheduler.cet)
    is_trading = scheduler.is_trading_day(now)
    is_open = scheduler.is_market_open(now)

    print(f"Current Time (CET):  {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Trading Day:         {'✓ YES' if is_trading else '✗ NO'}")
    print(f"Market Open:         {'✓ YES' if is_open else '✗ NO'}")

    if is_trading and not is_open:
        # Determine when market opens/closed
        if now.hour < 9:
            print(f"Status:              Market opens at 9:00 AM")
        else:
            print(f"Status:              Market closed at 5:30 PM")
    elif not is_trading:
        print(f"Status:              Non-trading day (weekend or holiday)")

    print()


def display_scheduled_jobs(scheduler: TradingScheduler):
    """Display all scheduled jobs."""
    print_header("SCHEDULED JOBS")

    status = scheduler.get_job_status()

    print(f"Scheduler Running:   {'✓ YES' if status['scheduler_running'] else '✗ NO'}")
    print()

    if status['jobs']:
        print(f"Total Jobs:          {len(status['jobs'])}")
        print()

        for job in status['jobs']:
            print(f"Job: {job['name']}")
            print(f"  ID:                {job['id']}")
            print(f"  Trigger:           {job['trigger']}")
            if job['next_run_time']:
                next_run = datetime.fromisoformat(job['next_run_time'])
                print(f"  Next Run:          {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            else:
                print(f"  Next Run:          Not scheduled")
            print()
    else:
        print("No jobs scheduled")
        print()


def manual_job_menu(scheduler: TradingScheduler):
    """Interactive menu for manually triggering jobs."""
    print_header("MANUAL JOB EXECUTION")

    jobs = scheduler.scheduler.get_jobs()
    if not jobs:
        print("No jobs available to trigger")
        return

    print("Available jobs:")
    for i, job in enumerate(jobs, 1):
        print(f"  {i}. {job.name} (ID: {job.id})")

    print(f"  0. Return to main menu")
    print()

    try:
        choice = input("Select job to trigger (0-{}): ".format(len(jobs)))
        choice = int(choice)

        if choice == 0:
            return
        elif 1 <= choice <= len(jobs):
            job = jobs[choice - 1]
            print(f"\nTriggering job: {job.name}...")
            print_separator("-")

            # Trigger the job
            scheduler.trigger_job_now(job.id)

            # Give it a moment to start
            time.sleep(2)

            print_separator("-")
            print(f"✓ Job '{job.name}' triggered successfully!")
            input("\nPress Enter to continue...")
        else:
            print("Invalid selection")
            input("\nPress Enter to continue...")

    except ValueError:
        print("Invalid input")
        input("\nPress Enter to continue...")
    except Exception as e:
        print(f"Error triggering job: {e}")
        input("\nPress Enter to continue...")


def monitor_mode(scheduler: TradingScheduler):
    """Real-time monitoring mode."""
    print_header("REAL-TIME MONITORING MODE")
    print("Press Ctrl+C to stop monitoring")
    print()

    try:
        while True:
            # Clear screen (works on Windows and Unix)
            os.system('cls' if os.name == 'nt' else 'clear')

            print_header("REAL-TIME MONITORING")
            display_market_status(scheduler)
            display_scheduled_jobs(scheduler)

            print(f"Last update: {datetime.now(scheduler.cet).strftime('%H:%M:%S')}")
            print("Refreshing every 30 seconds... (Ctrl+C to stop)")

            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")
        input("\nPress Enter to continue...")


def main():
    """Main demo function."""
    print_separator("=")
    print(" SENTIMENT ARENA - PHASE 4 SCHEDULER DEMO")
    print_separator("=")
    print()

    # Initialize database
    print("Initializing database...")
    init_database()
    print("✓ Database ready")
    print()

    # Create scheduler
    print("Creating scheduler...")
    market_data = MarketDataService()

    scheduler = TradingScheduler(
        market_data_service=market_data,
        openrouter_api_key=settings.OPENROUTER_API_KEY,
        alphavantage_api_key=settings.ALPHAVANTAGE_API_KEY,
        finnhub_api_key=settings.FINNHUB_API_KEY
    )
    print("✓ Scheduler created")
    print()

    # Start scheduler
    print("Starting scheduler...")
    scheduler.start()
    print("✓ Scheduler started")
    print()

    input("Press Enter to continue to main menu...")

    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')

            print_header("SCHEDULER DEMO - MAIN MENU")

            display_market_status(scheduler)

            print("Options:")
            print("  1. View scheduled jobs")
            print("  2. Manually trigger a job")
            print("  3. Real-time monitoring mode")
            print("  4. Check specific trading day")
            print("  5. Exit")
            print()

            choice = input("Select option (1-5): ").strip()

            if choice == "1":
                os.system('cls' if os.name == 'nt' else 'clear')
                display_scheduled_jobs(scheduler)
                input("\nPress Enter to continue...")

            elif choice == "2":
                os.system('cls' if os.name == 'nt' else 'clear')
                manual_job_menu(scheduler)

            elif choice == "3":
                monitor_mode(scheduler)

            elif choice == "4":
                os.system('cls' if os.name == 'nt' else 'clear')
                print_header("CHECK TRADING DAY")

                date_str = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()

                if date_str:
                    try:
                        from datetime import datetime
                        check_date = datetime.strptime(date_str, "%Y-%m-%d")
                        check_date = scheduler.cet.localize(check_date.replace(hour=10))
                    except ValueError:
                        print("Invalid date format")
                        input("\nPress Enter to continue...")
                        continue
                else:
                    check_date = datetime.now(scheduler.cet)

                is_trading = scheduler.is_trading_day(check_date)
                is_open_10am = scheduler.is_market_open(check_date.replace(hour=10, minute=0))

                print(f"\nDate: {check_date.strftime('%Y-%m-%d (%A)')}")
                print(f"Trading Day: {'✓ YES' if is_trading else '✗ NO (weekend or holiday)'}")
                print(f"Market Open (10:00 AM): {'✓ YES' if is_open_10am else '✗ NO'}")

                input("\nPress Enter to continue...")

            elif choice == "5":
                print("\nStopping scheduler...")
                break

            else:
                print("Invalid option")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    finally:
        # Stop scheduler
        scheduler.stop()
        print("✓ Scheduler stopped")
        print()
        print("Demo completed. Thank you!")
        print_separator("=")


if __name__ == "__main__":
    main()
