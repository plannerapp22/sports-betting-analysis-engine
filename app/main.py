from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import os

from app.services.analyzer import (
    get_all_value_bets, 
    get_value_bets_by_sport, 
    get_recommended_legs_for_week,
    get_weekly_summary
)
from app.services.multi_builder import build_suggested_multi
from app.config import SUPPORTED_SPORTS, SETTINGS
from app.data_sources.odds_api import get_cache_stats, clear_cache
from app.scheduled_fetch import fetch_and_store_all_odds, load_stored_data, is_fetch_day
from app.db import init_db
from app.models.probability import initialize_model

app = FastAPI(
    title="Sports Betting Analysis Engine",
    description="A backend service for analyzing sports betting value opportunities with ML-powered predictions, two-stage filtering, and data-backed rationales",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()
    initialize_model()
    print("Database initialized and ML model loaded")

@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "Sports Betting Analysis Engine",
        "version": "3.0.0",
        "supported_sports": SUPPORTED_SPORTS,
        "settings": {
            "min_odds_filter": SETTINGS["min_odds_filter"],
            "max_odds_filter": SETTINGS["max_odds_filter"],
        }
    }

@app.get("/value-bets")
async def get_value_bets(sport: Optional[str] = None, limit: Optional[int] = None):
    try:
        if sport:
            bets = get_value_bets_by_sport(sport)
        else:
            bets = get_all_value_bets()
        
        if limit:
            bets = bets[:limit]
        
        return {
            "success": True,
            "count": len(bets),
            "last_updated": datetime.utcnow().isoformat(),
            "value_bets": bets
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "value_bets": []
        }

@app.get("/recommended-legs")
async def get_recommended_legs(limit: Optional[int] = None):
    try:
        legs = get_recommended_legs_for_week(limit=limit)
        
        return {
            "success": True,
            "count": len(legs),
            "target_odds_range": f"{SETTINGS['min_odds_filter']:.2f} - {SETTINGS['max_odds_filter']:.2f}",
            "last_updated": datetime.utcnow().isoformat(),
            "recommended_legs": legs
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "recommended_legs": []
        }

@app.get("/weekly-summary")
async def get_weekly_summary_endpoint():
    try:
        summary = get_weekly_summary()
        summary["last_updated"] = datetime.utcnow().isoformat()
        return {
            "success": True,
            **summary
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/suggested-multi")
async def get_suggested_multi(target_odds: float = 2.0, max_legs: int = 4):
    try:
        multi = build_suggested_multi(target_odds=target_odds, max_legs=max_legs)
        return {
            "success": True,
            "suggested_multi": multi
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/sports")
async def get_sports():
    return {
        "success": True,
        "sports": SUPPORTED_SPORTS
    }

@app.get("/settings")
async def get_settings():
    return {
        "success": True,
        "settings": SETTINGS
    }

@app.get("/cache-stats")
async def cache_stats():
    stats = get_cache_stats()
    return {
        "success": True,
        "cache": stats,
        "ttl_minutes": stats["ttl_seconds"] / 60,
        "description": "Cache reduces API calls. Data refreshes every 10 minutes."
    }

@app.post("/clear-cache")
async def clear_cache_endpoint():
    clear_cache()
    return {
        "success": True,
        "message": "Cache cleared. Next request will fetch fresh data from API."
    }

@app.post("/fetch-odds")
async def fetch_odds_endpoint():
    try:
        data = fetch_and_store_all_odds()
        total_markets = sum(
            s.get("h2h_count", 0) + s.get("props_count", 0) 
            for s in data.get("sports", {}).values()
        )
        return {
            "success": True,
            "message": f"Fetched and stored {total_markets} markets",
            "fetch_time": data.get("fetch_time"),
            "sports": {k: {"h2h": v["h2h_count"], "props": v["props_count"]} 
                      for k, v in data.get("sports", {}).items()}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/stored-data-status")
async def stored_data_status():
    data = load_stored_data()
    if data:
        total_markets = sum(
            s.get("h2h_count", 0) + s.get("props_count", 0) 
            for s in data.get("sports", {}).values()
        )
        return {
            "success": True,
            "has_stored_data": True,
            "fetch_time": data.get("fetch_time"),
            "total_markets": total_markets,
            "is_fetch_day": is_fetch_day(),
            "fetch_days": "Monday and Thursday"
        }
    return {
        "success": True,
        "has_stored_data": False,
        "is_fetch_day": is_fetch_day(),
        "fetch_days": "Monday and Thursday",
        "message": "No stored data. Run POST /fetch-odds to fetch."
    }

ui_path = os.path.join(os.path.dirname(__file__), "ui")
app.mount("/static", StaticFiles(directory=ui_path), name="static")

@app.get("/ui")
async def serve_ui():
    return FileResponse(os.path.join(ui_path, "index.html"))

@app.get("/value-picks")
async def serve_value_picks():
    return FileResponse(os.path.join(ui_path, "value-picks.html"))

@app.get("/player-stats/{sport}/{player_name}")
async def get_player_stats_endpoint(sport: str, player_name: str, games: int = 10):
    try:
        if sport.lower() == "nba":
            from app.data_sources.nba import get_player_stats
            stats = get_player_stats(player_name, last_n_games=games)
        elif sport.lower() == "nfl":
            from app.data_sources.nfl import get_player_stats
            stats = get_player_stats(player_name, last_n_games=games)
        else:
            return {"success": False, "error": f"Unsupported sport: {sport}"}
        
        return {
            "success": True,
            "sport": sport,
            "player": player_name,
            "stats": stats
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/team-stats/{sport}/{team_name}")
async def get_team_stats_endpoint(sport: str, team_name: str):
    try:
        if sport.lower() == "nba":
            from app.data_sources.nba import get_team_stats
            stats = get_team_stats(team_name)
        elif sport.lower() == "nfl":
            from app.data_sources.nfl import get_team_stats
            stats = get_team_stats(team_name)
        else:
            return {"success": False, "error": f"Unsupported sport: {sport}"}
        
        return {
            "success": True,
            "sport": sport,
            "team": team_name,
            "stats": stats
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/stats-sources")
async def get_stats_sources():
    from app.data_sources.nba import check_stats_availability as nba_check
    from app.data_sources.nfl import check_stats_availability as nfl_check
    
    return {
        "success": True,
        "nba": nba_check(),
        "nfl": nfl_check(),
        "description": "Real-time stats from nba_api (NBA) and ESPN API (NFL)"
    }
