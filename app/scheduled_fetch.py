import os
import json
from datetime import datetime
from app.data_sources.odds_api import get_upcoming_odds, get_player_props, clear_cache
from app.config import SUPPORTED_SPORTS

DATA_FILE = "cached_odds_data.json"

def is_fetch_day():
    today = datetime.now().weekday()
    return today in [0, 3]  # Monday=0, Thursday=3

def fetch_and_store_all_odds():
    print(f"Scheduled fetch started at {datetime.now().isoformat()}")
    
    clear_cache()
    
    all_data = {
        "fetch_time": datetime.now().isoformat(),
        "sports": {}
    }
    
    for sport in SUPPORTED_SPORTS:
        print(f"Fetching {sport}...")
        
        h2h_markets = get_upcoming_odds(sport)
        props_markets = get_player_props(sport)
        
        all_data["sports"][sport] = {
            "h2h": h2h_markets,
            "props": props_markets,
            "h2h_count": len(h2h_markets),
            "props_count": len(props_markets)
        }
        
        print(f"  {sport}: {len(h2h_markets)} h2h, {len(props_markets)} props")
    
    with open(DATA_FILE, "w") as f:
        json.dump(all_data, f, indent=2)
    
    print(f"Data saved to {DATA_FILE}")
    print(f"Scheduled fetch completed at {datetime.now().isoformat()}")
    
    return all_data

def load_stored_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return None

def get_stored_odds_for_sport(sport: str):
    data = load_stored_data()
    if data and sport.lower() in data.get("sports", {}):
        sport_data = data["sports"][sport.lower()]
        return sport_data.get("h2h", []) + sport_data.get("props", [])
    return []

if __name__ == "__main__":
    if is_fetch_day():
        fetch_and_store_all_odds()
    else:
        print(f"Today is not a fetch day (Mon/Thu). Current day: {datetime.now().strftime('%A')}")
        print("Run with --force to fetch anyway")
        import sys
        if "--force" in sys.argv:
            fetch_and_store_all_odds()
