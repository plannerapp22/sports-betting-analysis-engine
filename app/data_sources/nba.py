from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

from app.config import MAX_EVENT_DAYS_AHEAD, EXCLUDE_TBA_STRINGS, CONFIRMED_EVENT_STATUSES
from app.data_sources.nba_stats import (
    get_player_season_stats,
    get_team_stats_real,
    get_player_prop_probability,
    NBA_API_AVAILABLE
)

def is_confirmed_game(home_team: str, away_team: str, game_date: str = None) -> bool:
    if not home_team or not away_team:
        return False
    
    home_lower = home_team.lower()
    away_lower = away_team.lower()
    
    for keyword in EXCLUDE_TBA_STRINGS:
        if keyword.lower() in home_lower or keyword.lower() in away_lower:
            return False
    
    if game_date:
        try:
            if isinstance(game_date, str):
                if "T" in game_date:
                    game_time = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
                else:
                    game_time = datetime.strptime(game_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                game_time = game_date
            
            now = datetime.now(timezone.utc)
            max_date = now + timedelta(days=MAX_EVENT_DAYS_AHEAD)
            
            if game_time < now or game_time > max_date:
                return False
        except Exception as e:
            print(f"Error parsing NBA game date: {e}")
            return False
    
    return True

def get_confirmed_upcoming_events_for_week(max_days_ahead: int = None) -> List[Dict[str, Any]]:
    return []

def get_upcoming_games() -> List[Dict[str, Any]]:
    return get_confirmed_upcoming_events_for_week()

def get_team_stats(team_name: str) -> Dict[str, Any]:
    real_stats = get_team_stats_real(team_name, last_n_games=10)
    
    if real_stats.get("error") or real_stats.get("source") == "none":
        return {
            "win_rate": 0.5,
            "ppg": 110.0,
            "defensive_rating": 115.0,
            "last_10": "5-5",
            "source": "fallback",
            "error": real_stats.get("error", "No data available")
        }
    
    return {
        "win_rate": real_stats.get("win_rate", 0.5),
        "ppg": real_stats.get("ppg", 110.0),
        "defensive_rating": real_stats.get("opponent_ppg", 115.0),
        "last_10": real_stats.get("last_10_record", "5-5"),
        "source": real_stats.get("source", "nba_api"),
        "games_analyzed": real_stats.get("games_played", 0)
    }

def get_player_props_analysis(player_name: str, prop_type: str, line: float) -> Dict[str, Any]:
    result = get_player_prop_probability(player_name, prop_type, line)
    return result

def get_player_stats(player_name: str, last_n_games: int = 10) -> Dict[str, Any]:
    return get_player_season_stats(player_name, last_n_games)

def get_model_probability(home_team: str, away_team: str) -> Dict[str, float]:
    home_stats = get_team_stats(home_team)
    away_stats = get_team_stats(away_team)
    
    home_win_rate = home_stats.get("win_rate", 0.5)
    away_win_rate = away_stats.get("win_rate", 0.5)
    
    home_advantage = 0.03
    prob_home = home_win_rate + home_advantage
    prob_away = away_win_rate
    
    total = prob_home + prob_away
    if total > 0:
        prob_home = prob_home / total
        prob_away = prob_away / total
    else:
        prob_home = 0.53
        prob_away = 0.47
    
    return {home_team: round(prob_home, 3), away_team: round(prob_away, 3)}

def check_stats_availability() -> Dict[str, Any]:
    return {
        "nba_api_available": NBA_API_AVAILABLE,
        "source": "nba_api" if NBA_API_AVAILABLE else "none"
    }
