from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import httpx

_stats_cache: Dict[str, Any] = {}
_cache_ttl = 3600

ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_CORE_URL = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
ESPN_WEB_URL = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl"

NFL_TEAMS = {
    "arizona cardinals": {"id": "22", "abbrev": "ARI"},
    "atlanta falcons": {"id": "1", "abbrev": "ATL"},
    "baltimore ravens": {"id": "33", "abbrev": "BAL"},
    "buffalo bills": {"id": "2", "abbrev": "BUF"},
    "carolina panthers": {"id": "29", "abbrev": "CAR"},
    "chicago bears": {"id": "3", "abbrev": "CHI"},
    "cincinnati bengals": {"id": "4", "abbrev": "CIN"},
    "cleveland browns": {"id": "5", "abbrev": "CLE"},
    "dallas cowboys": {"id": "6", "abbrev": "DAL"},
    "denver broncos": {"id": "7", "abbrev": "DEN"},
    "detroit lions": {"id": "8", "abbrev": "DET"},
    "green bay packers": {"id": "9", "abbrev": "GB"},
    "houston texans": {"id": "34", "abbrev": "HOU"},
    "indianapolis colts": {"id": "11", "abbrev": "IND"},
    "jacksonville jaguars": {"id": "30", "abbrev": "JAX"},
    "kansas city chiefs": {"id": "12", "abbrev": "KC"},
    "las vegas raiders": {"id": "13", "abbrev": "LV"},
    "los angeles chargers": {"id": "24", "abbrev": "LAC"},
    "los angeles rams": {"id": "14", "abbrev": "LAR"},
    "miami dolphins": {"id": "15", "abbrev": "MIA"},
    "minnesota vikings": {"id": "16", "abbrev": "MIN"},
    "new england patriots": {"id": "17", "abbrev": "NE"},
    "new orleans saints": {"id": "18", "abbrev": "NO"},
    "new york giants": {"id": "19", "abbrev": "NYG"},
    "new york jets": {"id": "20", "abbrev": "NYJ"},
    "philadelphia eagles": {"id": "21", "abbrev": "PHI"},
    "pittsburgh steelers": {"id": "23", "abbrev": "PIT"},
    "san francisco 49ers": {"id": "25", "abbrev": "SF"},
    "seattle seahawks": {"id": "26", "abbrev": "SEA"},
    "tampa bay buccaneers": {"id": "27", "abbrev": "TB"},
    "tennessee titans": {"id": "10", "abbrev": "TEN"},
    "washington commanders": {"id": "28", "abbrev": "WSH"},
}

async def _async_fetch(url: str, timeout: float = 10.0) -> Optional[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"ESPN API error for {url}: {e}")
    return None

def _sync_fetch(url: str, timeout: float = 10.0) -> Optional[Dict]:
    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"ESPN API error for {url}: {e}")
    return None

def get_team_id(team_name: str) -> Optional[str]:
    name_lower = team_name.lower()
    
    if name_lower in NFL_TEAMS:
        return NFL_TEAMS[name_lower]["id"]
    
    for full_name, info in NFL_TEAMS.items():
        if name_lower in full_name or full_name in name_lower:
            return info["id"]
        parts = full_name.split()
        if parts[-1] in name_lower:
            return info["id"]
    
    return None

def get_player_id_from_espn(player_name: str, team_id: Optional[str] = None) -> Optional[str]:
    cache_key = f"espn_player_id_{player_name.lower()}"
    if cache_key in _stats_cache:
        return _stats_cache[cache_key]
    
    try:
        url = f"{ESPN_BASE_URL}/athletes"
        params = {"limit": 100}
        
        response = _sync_fetch(f"{url}?limit=100")
        if response and 'athletes' in response:
            name_lower = player_name.lower()
            for athlete in response['athletes']:
                if athlete.get('fullName', '').lower() == name_lower:
                    _stats_cache[cache_key] = athlete['id']
                    return athlete['id']
                if name_lower in athlete.get('fullName', '').lower():
                    _stats_cache[cache_key] = athlete['id']
                    return athlete['id']
    except Exception as e:
        print(f"Error finding ESPN player ID for {player_name}: {e}")
    
    return None

KNOWN_PLAYERS = {
    "patrick mahomes": "3139477",
    "josh allen": "3918298",
    "lamar jackson": "3916387",
    "jalen hurts": "4040715",
    "joe burrow": "3915511",
    "dak prescott": "2577417",
    "travis kelce": "15847",
    "tyreek hill": "3116406",
    "ceedee lamb": "4241389",
    "ja'marr chase": "4362628",
    "derrick henry": "3043078",
    "saquon barkley": "3929630",
    "christian mccaffrey": "3117251",
    "nick chubb": "3128720",
    "bijan robinson": "4426467",
    "davante adams": "16800",
    "justin jefferson": "4262921",
    "amon-ra st. brown": "4374302",
    "cooper kupp": "3046288",
}

def get_player_stats_espn(player_name: str, last_n_games: int = 10) -> Dict[str, Any]:
    cache_key = f"nfl_player_stats_{player_name.lower()}_{last_n_games}"
    now = datetime.now()
    
    if cache_key in _stats_cache:
        cached = _stats_cache[cache_key]
        if (now - cached.get('timestamp', datetime.min)).seconds < _cache_ttl:
            return cached['data']
    
    name_lower = player_name.lower()
    player_id = KNOWN_PLAYERS.get(name_lower)
    
    if not player_id:
        player_id = get_player_id_from_espn(player_name)
    
    if not player_id:
        return {
            "player_name": player_name,
            "error": "Player not found in ESPN database",
            "source": "none"
        }
    
    try:
        overview_url = f"{ESPN_WEB_URL}/athletes/{player_id}/overview"
        data = _sync_fetch(overview_url)
        
        if not data:
            stats_url = f"{ESPN_WEB_URL}/athletes/{player_id}/stats"
            data = _sync_fetch(stats_url)
        
        if not data:
            return {
                "player_name": player_name,
                "player_id": player_id,
                "error": "Failed to fetch stats from ESPN",
                "source": "none"
            }
        
        stats = parse_espn_player_stats(player_name, player_id, data)
        
        _stats_cache[cache_key] = {'data': stats, 'timestamp': now}
        return stats
        
    except Exception as e:
        print(f"Error fetching ESPN stats for {player_name}: {e}")
        return {
            "player_name": player_name,
            "player_id": player_id,
            "error": str(e),
            "source": "none"
        }

def parse_espn_player_stats(player_name: str, player_id: str, data: Dict) -> Dict[str, Any]:
    stats = {
        "player_name": player_name,
        "player_id": player_id,
        "source": "espn_api",
        "last_updated": datetime.now().isoformat(),
        "position": "",
        "averages": {},
        "totals": {},
        "season_stats": {}
    }
    
    try:
        if 'athlete' in data:
            athlete = data['athlete']
            pos = athlete.get('position', {})
            stats['position'] = pos.get('abbreviation', '') if isinstance(pos, dict) else ''
            team = athlete.get('team', {})
            stats['team'] = team.get('displayName', '') if isinstance(team, dict) else ''
        
        statistics = data.get('statistics', {})
        if isinstance(statistics, dict):
            names = statistics.get('names', [])
            labels = statistics.get('labels', [])
            splits = statistics.get('splits', [])
            
            for split in splits:
                if isinstance(split, dict) and split.get('displayName') == 'Regular Season':
                    split_stats = split.get('stats', [])
                    for i, value in enumerate(split_stats):
                        if i < len(names):
                            name = names[i]
                            try:
                                clean_value = str(value).replace(',', '')
                                stats['season_stats'][name] = float(clean_value) if clean_value and clean_value != '--' else 0
                            except (ValueError, TypeError):
                                stats['season_stats'][name] = 0
            
            games = 13
            season = stats['season_stats']
            
            if 'passingYards' in season:
                stats['averages']['pass_yards'] = round(season['passingYards'] / games, 1)
            if 'passingTouchdowns' in season:
                stats['averages']['pass_tds'] = round(season['passingTouchdowns'] / games, 2)
            if 'rushingYards' in season:
                stats['averages']['rush_yards'] = round(season['rushingYards'] / games, 1)
            if 'receivingYards' in season:
                stats['averages']['rec_yards'] = round(season['receivingYards'] / games, 1)
            if 'receptions' in season:
                stats['averages']['receptions'] = round(season['receptions'] / games, 1)
            if 'receivingTouchdowns' in season:
                stats['averages']['rec_tds'] = round(season['receivingTouchdowns'] / games, 2)
            if 'completions' in season:
                stats['averages']['completions'] = round(season['completions'] / games, 1)
            
            stats['totals'] = season.copy()
            
    except Exception as e:
        print(f"Error parsing ESPN stats: {e}")
        stats['parse_error'] = str(e)
    
    return stats

def get_team_stats_espn(team_name: str) -> Dict[str, Any]:
    cache_key = f"nfl_team_stats_{team_name.lower()}"
    now = datetime.now()
    
    if cache_key in _stats_cache:
        cached = _stats_cache[cache_key]
        if (now - cached.get('timestamp', datetime.min)).seconds < _cache_ttl:
            return cached['data']
    
    team_id = get_team_id(team_name)
    if not team_id:
        return {
            "team_name": team_name,
            "error": "Team not found",
            "source": "none"
        }
    
    try:
        team_url = f"{ESPN_BASE_URL}/teams/{team_id}"
        data = _sync_fetch(team_url)
        
        if not data or 'team' not in data:
            return {
                "team_name": team_name,
                "team_id": team_id,
                "error": "Failed to fetch team data",
                "source": "none"
            }
        
        team_data = data['team']
        record = team_data.get('record', {})
        
        stats = {
            "team_name": team_name,
            "team_id": team_id,
            "display_name": team_data.get('displayName', team_name),
            "source": "espn_api",
            "last_updated": now.isoformat(),
        }
        
        record_items = record.get('items', []) if isinstance(record, dict) else []
        for item in record_items:
            if isinstance(item, dict) and item.get('type') == 'total':
                summary = item.get('summary', '0-0')
                parts = summary.split('-')
                if len(parts) >= 2:
                    try:
                        wins = int(parts[0])
                        losses = int(parts[1])
                        total = wins + losses
                        stats['wins'] = wins
                        stats['losses'] = losses
                        stats['win_rate'] = round(wins / total, 3) if total > 0 else 0.5
                        stats['record'] = summary
                    except (ValueError, TypeError):
                        pass
                
                item_stats = item.get('stats', [])
                if isinstance(item_stats, list):
                    for stat in item_stats:
                        if isinstance(stat, dict):
                            name = stat.get('name', '')
                            value = stat.get('value', 0)
                            if name == 'avgPointsFor':
                                stats['ppg'] = round(value, 1)
                            elif name == 'avgPointsAgainst':
                                stats['defensive_rating'] = round(value, 1)
                            elif name == 'pointDifferential':
                                stats['point_diff'] = round(value, 1)
        
        _stats_cache[cache_key] = {'data': stats, 'timestamp': now}
        return stats
        
    except Exception as e:
        print(f"Error fetching ESPN team stats for {team_name}: {e}")
        return {
            "team_name": team_name,
            "team_id": team_id,
            "error": str(e),
            "source": "none"
        }

def get_nfl_leaders(stat_type: str = "passing", limit: int = 20) -> List[Dict[str, Any]]:
    cache_key = f"nfl_leaders_{stat_type}_{limit}"
    now = datetime.now()
    
    if cache_key in _stats_cache:
        cached = _stats_cache[cache_key]
        if (now - cached.get('timestamp', datetime.min)).seconds < _cache_ttl:
            return cached['data']
    
    try:
        url = f"{ESPN_BASE_URL}/leaders"
        data = _sync_fetch(url)
        
        if not data or 'leaders' not in data:
            return []
        
        leaders = []
        for category in data.get('leaders', []):
            if stat_type.lower() in category.get('name', '').lower():
                for leader in category.get('leaders', [])[:limit]:
                    athlete = leader.get('athlete', {})
                    leaders.append({
                        "rank": leader.get('rank', 0),
                        "player_name": athlete.get('fullName', ''),
                        "player_id": athlete.get('id', ''),
                        "team": athlete.get('team', {}).get('abbreviation', ''),
                        "value": leader.get('value', 0),
                        "stat": category.get('name', stat_type)
                    })
        
        _stats_cache[cache_key] = {'data': leaders, 'timestamp': now}
        return leaders
        
    except Exception as e:
        print(f"Error fetching NFL leaders: {e}")
        return []

def get_player_prop_probability_nfl(player_name: str, prop_type: str, line: float) -> Dict[str, Any]:
    stats = get_player_stats_espn(player_name)
    
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
        'pass_yards': 'pass_yards',
        'passing_yards': 'pass_yards',
        'pass_tds': 'pass_tds',
        'passing_touchdowns': 'pass_tds',
        'rush_yards': 'rush_yards',
        'rushing_yards': 'rush_yards',
        'rec_yards': 'rec_yards',
        'receiving_yards': 'rec_yards',
        'receptions': 'receptions',
    }
    
    stat_key = prop_mapping.get(prop_type.lower())
    averages = stats.get('averages', {})
    
    if not stat_key or stat_key not in averages:
        return {
            "player": player_name,
            "prop_type": prop_type,
            "line": line,
            "over_probability": 0.5,
            "confidence": "none",
            "source": "unknown_prop"
        }
    
    avg = averages[stat_key]
    
    diff = avg - line
    std_estimate = avg * 0.25
    if std_estimate > 0:
        z_score = diff / std_estimate
        over_prob = 0.5 + (z_score * 0.15)
    else:
        over_prob = 0.5
    
    over_prob = max(0.15, min(0.85, over_prob))
    
    return {
        "player": player_name,
        "prop_type": prop_type,
        "line": line,
        "season_avg": avg,
        "over_probability": round(over_prob, 3),
        "under_probability": round(1 - over_prob, 3),
        "confidence": "medium",
        "source": "espn_api",
    }

def clear_stats_cache():
    global _stats_cache
    _stats_cache = {}
    return {"status": "cleared"}
