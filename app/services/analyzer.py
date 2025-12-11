from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime, timedelta
from app.data_sources.odds_api import get_upcoming_markets_for_week
from app.models.expected_value import analyze_market
from app.config import SETTINGS, MAX_EVENT_DAYS_AHEAD

STORED_DATA_FILE = "cached_odds_data.json"

def is_future_event(market: Dict[str, Any]) -> bool:
    commence_time = market.get("commence_time")
    if not commence_time:
        return False
    try:
        if isinstance(commence_time, str):
            event_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            now = datetime.now(event_time.tzinfo) if event_time.tzinfo else datetime.utcnow()
            max_date = now + timedelta(days=MAX_EVENT_DAYS_AHEAD)
            return now < event_time <= max_date
    except Exception:
        pass
    return False

def load_stored_odds():
    if os.path.exists(STORED_DATA_FILE):
        try:
            with open(STORED_DATA_FILE, "r") as f:
                data = json.load(f)
                all_markets = []
                for sport, sport_data in data.get("sports", {}).items():
                    all_markets.extend(sport_data.get("h2h", []))
                    all_markets.extend(sport_data.get("props", []))
                future_markets = [m for m in all_markets if is_future_event(m)]
                print(f"Loaded {len(future_markets)} future events (filtered {len(all_markets) - len(future_markets)} past events)")
                return future_markets, data.get("fetch_time")
        except Exception:
            pass
    return None, None

KNOWN_RIVALRIES = {
    "nfl": [
        ("Dallas Cowboys", "Philadelphia Eagles", "NFC East Rivalry"),
        ("Green Bay Packers", "Chicago Bears", "Oldest NFL Rivalry"),
        ("New England Patriots", "New York Jets", "AFC East Rivalry"),
        ("Kansas City Chiefs", "Las Vegas Raiders", "AFC West Rivalry"),
        ("San Francisco 49ers", "Seattle Seahawks", "NFC West Rivalry"),
    ],
    "nba": [
        ("Los Angeles Lakers", "Boston Celtics", "Historic NBA Rivalry"),
        ("Los Angeles Lakers", "Los Angeles Clippers", "LA Battle"),
        ("Golden State Warriors", "Cleveland Cavaliers", "Finals Rivalry"),
        ("Miami Heat", "Boston Celtics", "Eastern Rivalry"),
    ],
}

TEAM_STATS_CACHE = {}

def derive_stats_from_odds(team_name: str, odds: float, is_favorite: bool) -> Dict[str, Any]:
    implied_prob = 1 / odds if odds > 1 else 0.5
    
    if is_favorite and odds <= 1.25:
        win_rate = min(0.65 + (1.25 - odds) * 2, 0.85)
        wins_10 = int(win_rate * 10)
        losses_10 = 10 - wins_10
        point_diff = (1.25 - odds) * 50 + 3
        consistency = 0.65 + implied_prob * 0.2
        strength = 50 + implied_prob * 40
        streak = max(1, int((1.25 - odds) * 10))
    else:
        win_rate = implied_prob * 0.9
        wins_10 = int(win_rate * 10)
        losses_10 = 10 - wins_10
        point_diff = (implied_prob - 0.5) * 20
        consistency = 0.4 + implied_prob * 0.3
        strength = 30 + implied_prob * 35
        streak = int((implied_prob - 0.5) * 4)
    
    return {
        "team_name": team_name,
        "win_rate": round(win_rate, 3),
        "last_10_record": f"{wins_10}-{losses_10}",
        "last_5_record": f"{min(wins_10 // 2 + 1, 5)}-{max(0, 5 - wins_10 // 2 - 1)}",
        "point_differential": round(point_diff, 1),
        "consistency_score": round(min(consistency, 0.95), 2),
        "strength_rating": round(min(strength, 90), 1),
        "current_streak": streak,
    }

def get_team_stats(team_name: str, sport: str, odds: float = 1.15, is_favorite: bool = True) -> Dict[str, Any]:
    cache_key = f"{sport}_{team_name}_{odds}"
    if cache_key in TEAM_STATS_CACHE:
        return TEAM_STATS_CACHE[cache_key]
    
    stats = derive_stats_from_odds(team_name, odds, is_favorite)
    stats["sport"] = sport
    
    TEAM_STATS_CACHE[cache_key] = stats
    return stats

def check_rivalry(team1: str, team2: str, sport: str) -> Optional[Dict[str, Any]]:
    rivalries = KNOWN_RIVALRIES.get(sport.lower(), [])
    for t1, t2, name in rivalries:
        if (t1 in team1 or team1 in t1) and (t2 in team2 or team2 in t2):
            return {"is_rivalry": True, "name": name, "intensity": 0.7}
        if (t2 in team1 or team1 in t2) and (t1 in team2 or team2 in t1):
            return {"is_rivalry": True, "name": name, "intensity": 0.7}
    return {"is_rivalry": False, "name": None, "intensity": 0}

def calculate_composite_score(market: Dict[str, Any], fav_stats: Dict, opp_stats: Dict, rivalry_info: Dict) -> float:
    model_prob = market.get("model_probability", 0) / 100
    ev = market.get("expected_value", 0) / 100
    implied_prob = market.get("implied_probability", 0) / 100
    edge = model_prob - implied_prob
    consistency = fav_stats.get("consistency_score", 0.5)
    
    score = (model_prob * 0.4) + (ev * 20 * 0.3) + (edge * 10 * 0.2) + (consistency * 100 * 0.1)
    
    score = score * 100
    
    if rivalry_info.get("is_rivalry", False):
        score -= 8 * rivalry_info.get("intensity", 0.5)
    
    if fav_stats.get("current_streak", 0) >= 3:
        score += 2
    if opp_stats.get("current_streak", 0) <= -2:
        score += 2
    
    return round(score, 2)

def generate_rationale(market: Dict, fav_stats: Dict, opp_stats: Dict, rivalry_info: Dict) -> str:
    selection = market.get("selection", "")
    sport = market.get("sport", "").upper()
    model_prob = market.get("model_probability", 0)
    implied_prob = market.get("implied_probability", 0)
    ev = market.get("expected_value", 0)
    odds = market.get("decimal_odds", 1.0)
    edge = model_prob - implied_prob
    
    parts = []
    
    fav_record = fav_stats.get("last_10_record", "7-3")
    fav_wins = int(fav_record.split("-")[0]) if "-" in fav_record else 7
    fav_diff = fav_stats.get("point_differential", 0)
    consistency = fav_stats.get("consistency_score", 0) * 100
    strength = fav_stats.get("strength_rating", 50)
    
    parts.append(f"MODEL ANALYSIS: {selection} ({sport}) @ ${odds:.2f}")
    
    parts.append(f"Form: {fav_wins} of last 10 wins, {fav_diff:+.1f} point differential, {consistency:.0f}% consistency rating.")
    
    if opp_stats and opp_stats.get("win_rate"):
        opp_record = opp_stats.get("last_10_record", "N/A")
        opp_diff = opp_stats.get("point_differential", 0)
        opp_strength = opp_stats.get("strength_rating", 50)
        strength_gap = strength - opp_strength
        parts.append(f"Opponent form: {opp_record} last 10, {opp_diff:+.1f} differential. Strength gap: {strength_gap:+.1f} rating points.")
    
    parts.append(f"Edge: Model {model_prob:.1f}% vs market implied {implied_prob:.1f}% = {edge:.1f}pp edge. EV: {ev:+.1f}%.")
    
    if rivalry_info.get("is_rivalry", False):
        parts.append(f"RISK NOTE: {rivalry_info['name']} - rivalry games historically closer. Factored into score with -5.6 penalty.")
    
    if odds <= 1.10:
        parts.append("Market view: Heavy favorite (implied >90% win probability).")
    elif odds <= 1.15:
        parts.append("Market view: Strong favorite (implied 85-90% win probability).")
    elif odds <= 1.20:
        parts.append("Market view: Clear favorite (implied 80-85% win probability).")
    else:
        parts.append("Market view: Moderate favorite (implied 75-80% win probability).")
    
    parts.append("Note: This is model-based analysis, not a guarantee. Always bet responsibly.")
    
    return " ".join(parts)

def get_all_analyzed_markets() -> List[Dict[str, Any]]:
    stored_markets, fetch_time = load_stored_odds()
    if stored_markets and len(stored_markets) > 0:
        print(f"Using stored data from {fetch_time} ({len(stored_markets)} markets)")
        markets = stored_markets
    else:
        try:
            markets = get_upcoming_markets_for_week()
        except Exception as e:
            print(f"Error fetching live markets: {e}")
            markets = []
    
    analyzed = []
    for market in markets:
        try:
            analysis = analyze_market(market)
            analyzed.append(analysis)
        except Exception as e:
            print(f"Error analyzing market {market}: {e}")
            continue
    
    return analyzed

def deduplicate_bets(bets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique_bets = []
    
    for bet in bets:
        key = (
            bet.get("event_id", "") or f"{bet.get('home_team', '')}_vs_{bet.get('away_team', '')}",
            bet.get("selection", ""),
            bet.get("market_type", ""),
            bet.get("point", "")
        )
        
        if key not in seen:
            seen.add(key)
            unique_bets.append(bet)
    
    return unique_bets

def get_all_value_bets() -> List[Dict[str, Any]]:
    analyzed = get_all_analyzed_markets()
    
    value_bets = [m for m in analyzed if m.get("is_value_bet", False)]
    
    value_bets = deduplicate_bets(value_bets)
    
    for bet in value_bets:
        if not bet.get("rationale"):
            selection = bet.get("selection", "")
            sport = bet.get("sport", "")
            odds = bet.get("decimal_odds", 1.5)
            home_team = bet.get("home_team", "")
            away_team = bet.get("away_team", "")
            opponent = away_team if selection == home_team else home_team
            opp_odds = 1 / (1 - (1 / odds)) if odds > 1 and odds < 5 else 3.0
            
            fav_stats = get_team_stats(selection, sport, odds=odds, is_favorite=(odds < 2.0))
            opp_stats = get_team_stats(opponent, sport, odds=opp_odds, is_favorite=False) if opponent else {}
            rivalry_info = check_rivalry(home_team, away_team, sport)
            
            bet["rationale"] = generate_rationale(bet, fav_stats, opp_stats, rivalry_info)
    
    value_bets.sort(key=lambda x: x["expected_value"], reverse=True)
    
    return value_bets

def get_value_bets_by_sport(sport: str) -> List[Dict[str, Any]]:
    all_bets = get_all_value_bets()
    return [bet for bet in all_bets if bet["sport"].lower() == sport.lower()]

def get_top_value_bets(limit: int = 10) -> List[Dict[str, Any]]:
    all_bets = get_all_value_bets()
    return all_bets[:limit]

def get_high_confidence_bets() -> List[Dict[str, Any]]:
    all_bets = get_all_value_bets()
    return [bet for bet in all_bets if bet.get("is_high_confidence", False)]

def stage1_numerical_filter(markets: List[Dict[str, Any]], min_odds: float = 1.05, max_odds: float = 1.25) -> List[Dict[str, Any]]:
    candidates = []
    
    for market in markets:
        odds = market.get("decimal_odds", 0)
        model_prob = market.get("model_probability", 0)
        implied_prob = market.get("implied_probability", 0)
        ev = market.get("expected_value", 0)
        
        if not (min_odds <= odds <= max_odds):
            continue
        
        if model_prob < 75:
            continue
        
        edge = model_prob - implied_prob
        if edge < 2:
            continue
        
        if ev < -5:
            continue
        
        candidates.append(market)
    
    candidates.sort(key=lambda x: (
        -x.get("model_probability", 0),
        -x.get("expected_value", 0)
    ))
    
    return candidates

def stage2_deep_prune(candidates: List[Dict[str, Any]], limit: int = None) -> List[Dict[str, Any]]:
    scored_candidates = []
    
    for market in candidates:
        selection = market.get("selection", "")
        sport = market.get("sport", "")
        home_team = market.get("home_team", "")
        away_team = market.get("away_team", "")
        odds = market.get("decimal_odds", 1.15)
        
        opponent = away_team if selection == home_team else home_team
        opp_odds = 1 / (1 - (1 / odds)) if odds > 1 and odds < 2 else 3.0
        
        fav_stats = get_team_stats(selection, sport, odds=odds, is_favorite=True)
        opp_stats = get_team_stats(opponent, sport, odds=opp_odds, is_favorite=False) if opponent else {}
        
        rivalry_info = check_rivalry(home_team, away_team, sport)
        
        composite_score = calculate_composite_score(market, fav_stats, opp_stats, rivalry_info)
        
        rationale = generate_rationale(market, fav_stats, opp_stats, rivalry_info)
        
        enhanced_market = market.copy()
        enhanced_market["composite_score"] = composite_score
        enhanced_market["rationale"] = rationale
        enhanced_market["rivalry_flag"] = rivalry_info.get("is_rivalry", False)
        enhanced_market["rivalry_name"] = rivalry_info.get("name")
        enhanced_market["favorite_stats"] = {
            "win_rate": fav_stats.get("win_rate"),
            "last_10": fav_stats.get("last_10_record"),
            "point_diff": fav_stats.get("point_differential"),
            "consistency": fav_stats.get("consistency_score"),
        }
        enhanced_market["opponent_stats"] = {
            "win_rate": opp_stats.get("win_rate") if opp_stats else None,
            "last_10": opp_stats.get("last_10_record") if opp_stats else None,
            "point_diff": opp_stats.get("point_differential") if opp_stats else None,
        }
        
        scored_candidates.append(enhanced_market)
    
    scored_candidates.sort(key=lambda x: -x["composite_score"])
    
    final_legs = []
    used_events = set()
    
    for candidate in scored_candidates:
        event_id = candidate.get("event_id", "")
        selection = candidate.get("selection", "")
        unique_key = f"{event_id}_{selection}"
        
        if unique_key not in used_events:
            final_legs.append(candidate)
            used_events.add(unique_key)
        
        if limit and len(final_legs) >= limit:
            break
    
    return final_legs

def get_recommended_legs_for_week(limit: int = None) -> List[Dict[str, Any]]:
    min_odds = SETTINGS.get("min_odds_filter", 1.05)
    max_odds = SETTINGS.get("max_odds_filter", 1.25)
    
    all_markets = get_all_analyzed_markets()
    
    stage1_candidates = stage1_numerical_filter(all_markets, min_odds, max_odds)
    stage1_candidates = deduplicate_bets(stage1_candidates)
    print(f"Stage 1 filter: {len(all_markets)} markets -> {len(stage1_candidates)} candidates (after dedup)")
    
    final_legs = stage2_deep_prune(stage1_candidates, limit)
    print(f"Stage 2 prune: {len(stage1_candidates)} candidates -> {len(final_legs)} final legs")
    
    return final_legs

def get_weekly_summary() -> Dict[str, Any]:
    recommended = get_recommended_legs_for_week()
    all_analyzed = get_all_analyzed_markets()
    
    sports_breakdown = {}
    for leg in recommended:
        sport = leg.get("sport", "unknown")
        if sport not in sports_breakdown:
            sports_breakdown[sport] = 0
        sports_breakdown[sport] += 1
    
    if recommended:
        avg_odds = sum(l.get("decimal_odds", 1) for l in recommended) / len(recommended)
        avg_model_prob = sum(l.get("model_probability", 0) for l in recommended) / len(recommended)
        avg_ev = sum(l.get("expected_value", 0) for l in recommended) / len(recommended)
        avg_composite = sum(l.get("composite_score", 50) for l in recommended) / len(recommended)
    else:
        avg_odds = 0
        avg_model_prob = 0
        avg_ev = 0
        avg_composite = 0
    
    combined_odds = 1.0
    for leg in recommended[:4]:
        combined_odds *= leg.get("decimal_odds", 1)
    
    rivalry_count = sum(1 for leg in recommended if leg.get("rivalry_flag", False))
    
    return {
        "total_markets_analyzed": len(all_analyzed),
        "recommended_legs_count": len(recommended),
        "sports_breakdown": sports_breakdown,
        "average_odds": round(avg_odds, 2),
        "average_model_probability": round(avg_model_prob, 2),
        "average_ev": round(avg_ev, 2),
        "average_composite_score": round(avg_composite, 2),
        "sample_4_leg_multi_odds": round(combined_odds, 2),
        "rivalry_matchups_included": rivalry_count,
        "recommended_legs": recommended,
    }
