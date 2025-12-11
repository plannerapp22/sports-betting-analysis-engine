from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
import json

try:
    from nba_api.stats.endpoints import playergamelog, leagueleaders, teamgamelog, commonteamroster
    from nba_api.stats.static import players, teams
    from nba_api.live.nba.endpoints import scoreboard
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False
    print("nba_api not available - NBA stats will use fallback")

_stats_cache: Dict[str, Any] = {}
_cache_ttl = 3600

def _get_current_season() -> str:
    now = datetime.now()
    if now.month >= 10:
        return f"{now.year}-{str(now.year + 1)[2:]}"
    else:
        return f"{now.year - 1}-{str(now.year)[2:]}"

def _safe_api_call(func, *args, **kwargs):
    try:
        time.sleep(0.6)
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 10
        return func(*args, **kwargs)
    except Exception as e:
        print(f"NBA API call failed: {e}")
        return None

def get_player_id(player_name: str) -> Optional[int]:
    if not NBA_API_AVAILABLE:
        return None
    
    cache_key = f"player_id_{player_name.lower()}"
    if cache_key in _stats_cache:
        return _stats_cache[cache_key]
    
    try:
        all_players = players.get_players()
        name_lower = player_name.lower()
        
        for p in all_players:
            if p['full_name'].lower() == name_lower:
                _stats_cache[cache_key] = p['id']
                return p['id']
        
        for p in all_players:
            if name_lower in p['full_name'].lower():
                _stats_cache[cache_key] = p['id']
                return p['id']
        
        name_parts = name_lower.split()
        if len(name_parts) >= 2:
            for p in all_players:
                player_parts = p['full_name'].lower().split()
                if len(player_parts) >= 2:
                    if name_parts[-1] == player_parts[-1]:
                        _stats_cache[cache_key] = p['id']
                        return p['id']
    except Exception as e:
        print(f"Error finding player {player_name}: {e}")
    
    return None

def get_team_id(team_name: str) -> Optional[int]:
    if not NBA_API_AVAILABLE:
        return None
    
    cache_key = f"team_id_{team_name.lower()}"
    if cache_key in _stats_cache:
        return _stats_cache[cache_key]
    
    try:
        all_teams = teams.get_teams()
        name_lower = team_name.lower()
        
        for t in all_teams:
            if t['full_name'].lower() == name_lower:
                _stats_cache[cache_key] = t['id']
                return t['id']
        
        for t in all_teams:
            if t['nickname'].lower() in name_lower or name_lower in t['full_name'].lower():
                _stats_cache[cache_key] = t['id']
                return t['id']
    except Exception as e:
        print(f"Error finding team {team_name}: {e}")
    
    return None

def get_player_season_stats(player_name: str, last_n_games: int = 10) -> Dict[str, Any]:
    cache_key = f"player_stats_{player_name.lower()}_{last_n_games}"
    now = datetime.now()
    
    if cache_key in _stats_cache:
        cached = _stats_cache[cache_key]
        if (now - cached['timestamp']).seconds < _cache_ttl:
            return cached['data']
    
    if not NBA_API_AVAILABLE:
        return {"error": "NBA API not available", "source": "none"}
    
    player_id = get_player_id(player_name)
    if not player_id:
        return {"error": f"Player not found: {player_name}", "source": "none"}
    
    try:
        season = _get_current_season()
        gamelog = _safe_api_call(
            playergamelog.PlayerGameLog,
            player_id=player_id,
            season=season
        )
        
        if not gamelog:
            return {"error": "Failed to fetch game log", "source": "none"}
        
        df = gamelog.get_data_frames()[0]
        
        if df.empty:
            return {"error": "No games this season", "source": "none"}
        
        recent_games = df.head(last_n_games)
        
        stats = {
            "player_name": player_name,
            "player_id": player_id,
            "games_played": len(recent_games),
            "season": season,
            "source": "nba_api",
            "last_updated": now.isoformat(),
            "averages": {
                "points": round(recent_games['PTS'].mean(), 1) if 'PTS' in recent_games else 0,
                "rebounds": round(recent_games['REB'].mean(), 1) if 'REB' in recent_games else 0,
                "assists": round(recent_games['AST'].mean(), 1) if 'AST' in recent_games else 0,
                "threes": round(recent_games['FG3M'].mean(), 1) if 'FG3M' in recent_games else 0,
                "steals": round(recent_games['STL'].mean(), 1) if 'STL' in recent_games else 0,
                "blocks": round(recent_games['BLK'].mean(), 1) if 'BLK' in recent_games else 0,
                "minutes": round(recent_games['MIN'].mean(), 1) if 'MIN' in recent_games else 0,
            },
            "recent_games": []
        }
        
        for _, game in recent_games.iterrows():
            stats["recent_games"].append({
                "date": str(game.get('GAME_DATE', '')),
                "matchup": str(game.get('MATCHUP', '')),
                "points": int(game.get('PTS', 0)),
                "rebounds": int(game.get('REB', 0)),
                "assists": int(game.get('AST', 0)),
                "threes": int(game.get('FG3M', 0)),
                "minutes": str(game.get('MIN', '0')),
            })
        
        hit_rates = {}
        for stat_key, col in [('points', 'PTS'), ('rebounds', 'REB'), ('assists', 'AST'), ('threes', 'FG3M')]:
            if col in recent_games.columns:
                values = recent_games[col].tolist()
                avg = stats['averages'][stat_key]
                thresholds = _get_stat_thresholds(stat_key, avg)
                hit_rates[stat_key] = {}
                for threshold in thresholds:
                    hits = sum(1 for v in values if v >= threshold)
                    hit_rates[stat_key][threshold] = round(hits / len(values), 3) if values else 0
        
        stats['hit_rates'] = hit_rates
        
        _stats_cache[cache_key] = {'data': stats, 'timestamp': now}
        return stats
        
    except Exception as e:
        print(f"Error fetching player stats for {player_name}: {e}")
        return {"error": str(e), "source": "none"}

def _get_stat_thresholds(stat_type: str, avg: float) -> List[float]:
    if stat_type == 'points':
        base = [10, 15, 20, 25, 30, 35, 40]
    elif stat_type == 'rebounds':
        base = [5, 8, 10, 12, 15]
    elif stat_type == 'assists':
        base = [4, 6, 8, 10, 12]
    elif stat_type == 'threes':
        base = [2, 3, 4, 5, 6]
    else:
        base = [5, 10, 15]
    
    return [t for t in base if t <= avg * 1.5]

def get_team_stats_real(team_name: str, last_n_games: int = 10) -> Dict[str, Any]:
    cache_key = f"team_stats_{team_name.lower()}_{last_n_games}"
    now = datetime.now()
    
    if cache_key in _stats_cache:
        cached = _stats_cache[cache_key]
        if (now - cached['timestamp']).seconds < _cache_ttl:
            return cached['data']
    
    if not NBA_API_AVAILABLE:
        return {"error": "NBA API not available", "source": "none"}
    
    team_id = get_team_id(team_name)
    if not team_id:
        return {"error": f"Team not found: {team_name}", "source": "none"}
    
    try:
        season = _get_current_season()
        gamelog = _safe_api_call(
            teamgamelog.TeamGameLog,
            team_id=team_id,
            season=season
        )
        
        if not gamelog:
            return {"error": "Failed to fetch team game log", "source": "none"}
        
        df = gamelog.get_data_frames()[0]
        
        if df.empty:
            return {"error": "No games this season", "source": "none"}
        
        recent = df.head(last_n_games)
        wins = len(recent[recent['WL'] == 'W'])
        
        stats = {
            "team_name": team_name,
            "team_id": team_id,
            "season": season,
            "source": "nba_api",
            "last_updated": now.isoformat(),
            "games_played": len(recent),
            "wins": wins,
            "losses": len(recent) - wins,
            "win_rate": round(wins / len(recent), 3) if recent.size > 0 else 0.5,
            "ppg": round(recent['PTS'].mean(), 1) if 'PTS' in recent else 0,
            "opponent_ppg": round(recent['PTS'].mean() - recent['PLUS_MINUS'].mean(), 1) if 'PLUS_MINUS' in recent else 0,
            "avg_plus_minus": round(recent['PLUS_MINUS'].mean(), 1) if 'PLUS_MINUS' in recent else 0,
            "last_10_record": f"{wins}-{len(recent) - wins}",
        }
        
        _stats_cache[cache_key] = {'data': stats, 'timestamp': now}
        return stats
        
    except Exception as e:
        print(f"Error fetching team stats for {team_name}: {e}")
        return {"error": str(e), "source": "none"}

def get_player_prop_probability(player_name: str, prop_type: str, line: float) -> Dict[str, Any]:
    stats = get_player_season_stats(player_name, last_n_games=15)
    
    if stats.get("error"):
        return {
            "player": player_name,
            "prop_type": prop_type,
            "line": line,
            "over_probability": 0.5,
            "confidence": "none",
            "source": "no_data",
            "error": stats.get("error")
        }
    
    prop_mapping = {
        'points': 'points',
        'rebounds': 'rebounds',
        'assists': 'assists',
        'threes': 'threes',
        '3pm': 'threes',
        'steals': 'steals',
        'blocks': 'blocks',
    }
    
    stat_key = prop_mapping.get(prop_type.lower())
    if not stat_key or stat_key not in stats.get('averages', {}):
        return {
            "player": player_name,
            "prop_type": prop_type,
            "line": line,
            "over_probability": 0.5,
            "confidence": "none",
            "source": "unknown_prop"
        }
    
    avg = stats['averages'][stat_key]
    
    if 'hit_rates' in stats and stat_key in stats['hit_rates']:
        hit_rates = stats['hit_rates'][stat_key]
        closest_threshold = min(hit_rates.keys(), key=lambda x: abs(x - line), default=None)
        if closest_threshold is not None:
            over_prob = hit_rates[closest_threshold]
            if closest_threshold < line:
                adjustment = (line - closest_threshold) / avg * 0.1 if avg > 0 else 0
                over_prob = max(0.1, over_prob - adjustment)
            elif closest_threshold > line:
                adjustment = (closest_threshold - line) / avg * 0.1 if avg > 0 else 0
                over_prob = min(0.9, over_prob + adjustment)
        else:
            over_prob = 0.5 + (avg - line) / (avg + 1) * 0.3
    else:
        over_prob = 0.5 + (avg - line) / (avg + 1) * 0.3
    
    over_prob = max(0.1, min(0.9, over_prob))
    
    games_played = stats.get('games_played', 0)
    if games_played >= 10:
        confidence = "high"
    elif games_played >= 5:
        confidence = "medium"
    else:
        confidence = "low"
    
    return {
        "player": player_name,
        "prop_type": prop_type,
        "line": line,
        "season_avg": avg,
        "over_probability": round(over_prob, 3),
        "under_probability": round(1 - over_prob, 3),
        "confidence": confidence,
        "games_analyzed": games_played,
        "source": "nba_api",
        "recent_values": [g.get(stat_key.replace('threes', 'threes'), g.get('points', 0)) for g in stats.get('recent_games', [])[:5]]
    }

def clear_stats_cache():
    global _stats_cache
    _stats_cache = {}
    return {"status": "cleared"}
