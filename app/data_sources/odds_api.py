from typing import List, Dict, Any, Optional
import requests
from datetime import datetime, timedelta, timezone
import os
import time

from app.config import (
    API_KEYS, 
    ODDS_API_BASE_URL, 
    ODDS_API_SPORTS, 
    ODDS_API_REGIONS,
    ODDS_API_MARKETS,
    ODDS_API_PROPS_MARKETS,
    MARKET_TYPE_MAPPING,
    ALLOWED_MARKET_TYPES,
    MAX_EVENT_DAYS_AHEAD,
    EXCLUDE_TBA_STRINGS,
    CONFIRMED_EVENT_STATUSES,
    SUPPORTED_SPORTS
)

CACHE_TTL_SECONDS = 600
_odds_cache: Dict[str, Dict[str, Any]] = {}
_last_api_remaining: Optional[int] = None

def get_api_key() -> str:
    return API_KEYS.get("odds_api", "") or os.getenv("ODDS_API_KEY", "")

def _get_cached(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    if cache_key in _odds_cache:
        entry = _odds_cache[cache_key]
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            print(f"Cache HIT for {cache_key} (age: {int(time.time() - entry['timestamp'])}s)")
            return entry["data"]
        else:
            del _odds_cache[cache_key]
    return None

def _set_cached(cache_key: str, data: List[Dict[str, Any]]) -> None:
    _odds_cache[cache_key] = {
        "timestamp": time.time(),
        "data": data
    }
    print(f"Cached {len(data)} items for {cache_key}")

def get_cache_stats() -> Dict[str, Any]:
    now = time.time()
    valid_entries = sum(1 for v in _odds_cache.values() if now - v["timestamp"] < CACHE_TTL_SECONDS)
    return {
        "total_entries": len(_odds_cache),
        "valid_entries": valid_entries,
        "ttl_seconds": CACHE_TTL_SECONDS,
        "last_api_remaining": _last_api_remaining,
    }

def clear_cache() -> None:
    global _odds_cache
    _odds_cache = {}
    print("Cache cleared")

def is_confirmed_event(event: Dict[str, Any], max_days_ahead: int = None) -> bool:
    if max_days_ahead is None:
        max_days_ahead = MAX_EVENT_DAYS_AHEAD
    
    event_status = event.get("status", event.get("event_status", "")).lower()
    if event_status and event_status not in [s.lower() for s in CONFIRMED_EVENT_STATUSES]:
        return False
    
    commence_time = event.get("commence_time", "")
    if not commence_time:
        return False
    
    try:
        if isinstance(commence_time, str):
            event_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        else:
            event_time = commence_time
        
        now = datetime.now(timezone.utc)
        max_date = now + timedelta(days=max_days_ahead)
        
        if event_time < now or event_time > max_date:
            return False
    except Exception as e:
        print(f"Error parsing event time: {e}")
        return False
    
    home_team = event.get("home_team", "").lower()
    away_team = event.get("away_team", "").lower()
    
    for keyword in EXCLUDE_TBA_STRINGS:
        if keyword.lower() in home_team or keyword.lower() in away_team:
            return False
    
    if not home_team or not away_team:
        return False
    
    if home_team == away_team:
        return False
    
    return True

def get_available_sports() -> List[Dict[str, Any]]:
    api_key = get_api_key()
    if not api_key:
        return []
    
    try:
        response = requests.get(
            f"{ODDS_API_BASE_URL}/sports",
            params={"apiKey": api_key}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error fetching sports: {e}")
        return []

def get_upcoming_odds(sport: str, regions: str = None, markets: str = None, include_props: bool = False) -> List[Dict[str, Any]]:
    global _last_api_remaining
    
    cache_key = f"odds_{sport.lower()}_{include_props}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    api_key = get_api_key()
    if not api_key:
        print(f"ERROR: No API key set. Set THE_ODDS_API_KEY environment variable.")
        return []
    
    sport_key = ODDS_API_SPORTS.get(sport.lower())
    if not sport_key:
        print(f"ERROR: Unknown sport '{sport}'. Supported: {list(ODDS_API_SPORTS.keys())}")
        return []
    
    all_markets = []
    
    try:
        response = requests.get(
            f"{ODDS_API_BASE_URL}/sports/{sport_key}/odds",
            params={
                "apiKey": api_key,
                "regions": regions or ODDS_API_REGIONS,
                "markets": markets or ODDS_API_MARKETS,
                "oddsFormat": "decimal"
            }
        )
        
        if response.status_code == 200:
            remaining = response.headers.get("x-requests-remaining", "unknown")
            print(f"Odds API requests remaining: {remaining}")
            try:
                _last_api_remaining = int(remaining)
            except:
                pass
            
            events = response.json()
            confirmed_events = [e for e in events if is_confirmed_event(e)]
            print(f"{sport.upper()}: {len(events)} total events, {len(confirmed_events)} confirmed within {MAX_EVENT_DAYS_AHEAD} days")
            
            all_markets.extend(parse_odds_response(confirmed_events, sport))
        else:
            print(f"Odds API error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error fetching odds for {sport}: {e}")
        return []
    
    if include_props and sport.lower() in ODDS_API_PROPS_MARKETS:
        props_markets = get_player_props(sport)
        all_markets.extend(props_markets)
    
    _set_cached(cache_key, all_markets)
    return all_markets

def get_player_props(sport: str, regions: str = None) -> List[Dict[str, Any]]:
    global _last_api_remaining
    
    cache_key = f"props_{sport.lower()}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    api_key = get_api_key()
    if not api_key:
        return []
    
    sport_key = ODDS_API_SPORTS.get(sport.lower())
    if not sport_key:
        return []
    
    props_market_string = ODDS_API_PROPS_MARKETS.get(sport.lower(), "")
    if not props_market_string:
        return []
    
    props_region = "us"
    
    all_props = []
    
    try:
        response = requests.get(
            f"{ODDS_API_BASE_URL}/sports/{sport_key}/events",
            params={"apiKey": api_key}
        )
        
        if response.status_code != 200:
            print(f"Error fetching events for props: {response.status_code}")
            return []
        
        events = response.json()
        confirmed_events = [e for e in events if is_confirmed_event(e)]
        
        remaining = response.headers.get("x-requests-remaining", "unknown")
        print(f"Fetching player props for {len(confirmed_events[:5])} {sport.upper()} events...")
        
        for event in confirmed_events[:5]:
            event_id = event.get("id", "")
            if not event_id:
                continue
            
            try:
                props_response = requests.get(
                    f"{ODDS_API_BASE_URL}/sports/{sport_key}/events/{event_id}/odds",
                    params={
                        "apiKey": api_key,
                        "regions": props_region,
                        "markets": props_market_string,
                        "oddsFormat": "decimal"
                    }
                )
                
                if props_response.status_code == 200:
                    remaining = props_response.headers.get("x-requests-remaining", "unknown")
                    print(f"Odds API requests remaining: {remaining}")
                    
                    props_data = props_response.json()
                    parsed_props = parse_props_response(props_data, sport, event)
                    all_props.extend(parsed_props)
            except Exception as e:
                print(f"Error fetching props for event {event_id}: {e}")
                continue
                
    except Exception as e:
        print(f"Error fetching player props for {sport}: {e}")
    
    if all_props:
        _set_cached(cache_key, all_props)
    return all_props

def parse_props_response(data: Dict, sport: str, event_info: Dict) -> List[Dict[str, Any]]:
    markets = []
    sport_upper = sport.upper()
    allowed_types = ALLOWED_MARKET_TYPES.get(sport_upper, [])
    
    event_id = data.get("id", event_info.get("id", ""))
    home_team = data.get("home_team", event_info.get("home_team", ""))
    away_team = data.get("away_team", event_info.get("away_team", ""))
    commence_time = data.get("commence_time", event_info.get("commence_time", ""))
    
    for bookmaker in data.get("bookmakers", []):
        bookmaker_name = bookmaker.get("key", "")
        
        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            mapped_market_type = MARKET_TYPE_MAPPING.get(market_key, market_key)
            
            if allowed_types and mapped_market_type not in allowed_types:
                continue
            
            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description", "")
                side = outcome.get("name", "").lower()
                point = outcome.get("point")
                decimal_odds = outcome.get("price", 0)
                
                if decimal_odds > 0:
                    if point is not None and side in ["over", "under"]:
                        prop_type = market_key.replace("player_", "").replace("fighter_", "")
                        selection_name = f"{player_name} {side} {point} {prop_type}"
                    elif player_name:
                        selection_name = f"{player_name} {side}" if side else player_name
                    else:
                        selection_name = side
                    
                    markets.append({
                        "event_id": event_id,
                        "sport": sport_upper,
                        "event": f"{home_team} vs {away_team}",
                        "home_team": home_team,
                        "away_team": away_team,
                        "commence_time": commence_time,
                        "market_type": mapped_market_type,
                        "selection_name": selection_name,
                        "line": point,
                        "side": side if side in ["over", "under"] else None,
                        "decimal_odds": decimal_odds,
                        "bookmaker": bookmaker_name,
                        "is_prop": True,
                        "prop_player": player_name,
                    })
    
    return markets

def parse_odds_response(data: List[Dict], sport: str) -> List[Dict[str, Any]]:
    markets = []
    sport_upper = sport.upper()
    allowed_types = ALLOWED_MARKET_TYPES.get(sport_upper, [])
    
    for event in data:
        event_id = event.get("id", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        commence_time = event.get("commence_time", "")
        
        for bookmaker in event.get("bookmakers", []):
            bookmaker_name = bookmaker.get("key", "")
            
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                mapped_market_type = MARKET_TYPE_MAPPING.get(market_key, market_key)
                
                if allowed_types and mapped_market_type not in allowed_types:
                    continue
                
                for outcome in market.get("outcomes", []):
                    selection_name = outcome.get("name", "")
                    decimal_odds = outcome.get("price", 0)
                    point = outcome.get("point")
                    
                    if decimal_odds > 0:
                        markets.append({
                            "event_id": event_id,
                            "sport": sport_upper,
                            "event": f"{home_team} vs {away_team}",
                            "home_team": home_team,
                            "away_team": away_team,
                            "commence_time": commence_time,
                            "market_type": mapped_market_type,
                            "selection_name": selection_name,
                            "line": point,
                            "side": None,
                            "decimal_odds": decimal_odds,
                            "bookmaker": bookmaker_name,
                            "is_prop": False,
                        })
    
    return markets

def get_confirmed_upcoming_events_for_week(max_days_ahead: int = None) -> List[Dict[str, Any]]:
    if max_days_ahead is None:
        max_days_ahead = MAX_EVENT_DAYS_AHEAD
    
    all_events = []
    api_key = get_api_key()
    
    if not api_key:
        print(f"ERROR: No API key set. Set THE_ODDS_API_KEY environment variable.")
        return []
    
    for sport in SUPPORTED_SPORTS:
        sport_key = ODDS_API_SPORTS.get(sport.lower())
        if not sport_key:
            continue
        
        try:
            response = requests.get(
                f"{ODDS_API_BASE_URL}/sports/{sport_key}/events",
                params={"apiKey": api_key}
            )
            
            if response.status_code == 200:
                events = response.json()
                confirmed = [e for e in events if is_confirmed_event(e, max_days_ahead)]
                
                for event in confirmed:
                    event["sport"] = sport
                
                all_events.extend(confirmed)
                print(f"{sport.upper()}: {len(confirmed)} confirmed events in next {max_days_ahead} days")
        except Exception as e:
            print(f"Error fetching events for {sport}: {e}")
            continue
    
    return all_events

def get_upcoming_markets_for_week(include_props: bool = True) -> List[Dict[str, Any]]:
    all_markets = []
    
    for sport in SUPPORTED_SPORTS:
        try:
            should_include_props = include_props and sport.lower() in ODDS_API_PROPS_MARKETS
            sport_markets = get_upcoming_odds(sport, include_props=should_include_props)
            all_markets.extend(sport_markets)
        except Exception as e:
            print(f"Error fetching {sport} markets: {e}")
            continue
    
    return all_markets

def get_best_odds_per_selection(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best_odds = {}
    
    for market in markets:
        key = f"{market['event_id']}_{market['selection_name']}"
        
        if key not in best_odds or market['decimal_odds'] > best_odds[key]['decimal_odds']:
            best_odds[key] = market
    
    return list(best_odds.values())

def get_odds_for_sport(sport: str) -> List[Dict[str, Any]]:
    return get_upcoming_odds(sport, include_props=sport.lower() in ODDS_API_PROPS_MARKETS)
