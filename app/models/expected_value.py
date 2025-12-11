from typing import Dict, Any, Optional
from app.models.probability import calculate_implied_probability, get_model_prediction
from app.config import SETTINGS

def calculate_ev(model_prob: float, decimal_odds: float) -> float:
    ev = (model_prob * decimal_odds) - 1
    return round(ev, 4)

def is_value_bet(model_prob: float, decimal_odds: float, min_ev: float = None) -> bool:
    if min_ev is None:
        min_ev = SETTINGS["min_ev_threshold"]
    ev = calculate_ev(model_prob, decimal_odds)
    return ev >= min_ev

def is_high_confidence(model_prob: float, min_confidence: float = None) -> bool:
    if min_confidence is None:
        min_confidence = SETTINGS["min_confidence_threshold"]
    return model_prob >= min_confidence

def analyze_selection(
    selection_name: str, 
    decimal_odds: float, 
    sport: str, 
    context: Optional[Dict] = None,
    min_ev_threshold: float = None,
    min_confidence_threshold: float = None
) -> Dict[str, Any]:
    if min_ev_threshold is None:
        min_ev_threshold = SETTINGS["min_ev_threshold"]
    if min_confidence_threshold is None:
        min_confidence_threshold = SETTINGS["min_confidence_threshold"]
    
    implied_prob = calculate_implied_probability(decimal_odds)
    
    if context is None:
        context = {}
    context["implied_prob"] = implied_prob
    
    model_prob = get_model_prediction(selection_name, sport, context)
    ev = calculate_ev(model_prob, decimal_odds)
    edge = model_prob - implied_prob
    
    if model_prob >= 0.85 and ev >= 0.05:
        confidence = "HIGH"
    elif model_prob >= 0.75 and ev >= 0.02:
        confidence = "MEDIUM"
    elif model_prob >= 0.65 and ev >= 0.01:
        confidence = "LOW"
    else:
        confidence = "NONE"
    
    if ev >= 0.10:
        value_rating = 5
    elif ev >= 0.06:
        value_rating = 4
    elif ev >= 0.04:
        value_rating = 3
    elif ev >= 0.02:
        value_rating = 2
    else:
        value_rating = 1
    
    is_value = ev >= min_ev_threshold
    is_confident = model_prob >= min_confidence_threshold
    qualifies = is_value and is_confident
    
    return {
        "selection": selection_name,
        "sport": sport,
        "decimal_odds": decimal_odds,
        "implied_probability": round(implied_prob * 100, 2),
        "model_probability": round(model_prob * 100, 2),
        "expected_value": round(ev * 100, 2),
        "edge": round(edge * 100, 2),
        "confidence": confidence,
        "value_rating": value_rating,
        "is_value_bet": is_value,
        "is_high_confidence": is_confident,
        "qualifies_as_recommended": qualifies,
    }

def analyze_market(market: Dict[str, Any]) -> Dict[str, Any]:
    selection_name = market.get("selection_name", "")
    decimal_odds = market.get("decimal_odds", 1.0)
    sport = market.get("sport", "")
    
    is_home = market.get("home_team", "") == selection_name
    is_favorite = decimal_odds < 2.0
    
    if decimal_odds <= 1.15:
        win_rate = 0.75
        recent_form = 0.75
    elif decimal_odds <= 1.25:
        win_rate = 0.68
        recent_form = 0.68
    elif decimal_odds <= 1.50:
        win_rate = 0.60
        recent_form = 0.60
    elif is_favorite:
        win_rate = 0.55
        recent_form = 0.55
    else:
        win_rate = 0.42
        recent_form = 0.42
    
    context = {
        "is_home": is_home,
        "is_favorite": is_favorite,
        "win_rate": win_rate,
        "recent_form": recent_form,
        "ranking_diff": -20 if decimal_odds < 1.5 else (-10 if is_favorite else 10),
    }
    
    analysis = analyze_selection(
        selection_name=selection_name,
        decimal_odds=decimal_odds,
        sport=sport,
        context=context
    )
    
    analysis["event"] = market.get("event", "")
    analysis["event_id"] = market.get("event_id", "")
    analysis["market_type"] = market.get("market_type", "moneyline")
    analysis["bookmaker"] = market.get("bookmaker", "")
    analysis["commence_time"] = market.get("commence_time", "")
    analysis["home_team"] = market.get("home_team", "")
    analysis["away_team"] = market.get("away_team", "")
    analysis["line"] = market.get("line")
    analysis["side"] = market.get("side")
    analysis["is_prop"] = market.get("is_prop", False)
    
    return analysis
