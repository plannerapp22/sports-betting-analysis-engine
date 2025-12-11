#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from app.scheduled_fetch import fetch_and_store_all_odds, is_fetch_day
from datetime import datetime

if __name__ == "__main__":
    print(f"Scheduled fetch triggered at {datetime.now().isoformat()}")
    print(f"Today: {datetime.now().strftime('%A')}")
    print(f"Is fetch day (Mon/Thu): {is_fetch_day()}")
    
    if is_fetch_day() or "--force" in sys.argv:
        result = fetch_and_store_all_odds()
        print(f"Fetch completed successfully")
        print(f"Total markets: {sum(s.get('h2h_count', 0) + s.get('props_count', 0) for s in result.get('sports', {}).values())}")
    else:
        print("Not a fetch day. Use --force to fetch anyway.")
