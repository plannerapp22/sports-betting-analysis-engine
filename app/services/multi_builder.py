from typing import List, Dict, Any
from app.services.analyzer import get_all_value_bets, get_high_confidence_bets
from app.config import SETTINGS

def calculate_multi_odds(legs: List[Dict[str, Any]]) -> float:
    if not legs:
        return 1.0
    combined = 1.0
    for leg in legs:
        combined *= leg["decimal_odds"]
    return round(combined, 2)

def build_suggested_multi(target_odds: float = None, max_legs: int = None) -> Dict[str, Any]:
    if target_odds is None:
        target_odds = SETTINGS["target_multi_odds"]
    if max_legs is None:
        max_legs = SETTINGS["max_legs_in_multi"]
    
    value_bets = get_all_value_bets()
    
    if not value_bets:
        return {
            "legs": [],
            "combined_odds": 1.0,
            "combined_probability": 0.0,
            "num_legs": 0,
            "target_odds": target_odds,
            "potential_return": 0.0,
        }
    
    min_legs = 2
    selected_legs = []
    current_odds = 1.0
    used_events = set()
    
    min_target = target_odds * 0.85
    max_target = target_odds * 1.5
    
    low_odds_bets = [b for b in value_bets if b["decimal_odds"] <= 1.6]
    other_bets = [b for b in value_bets if b["decimal_odds"] > 1.6]
    
    sorted_bets = low_odds_bets + other_bets
    
    for bet in sorted_bets:
        if len(selected_legs) >= max_legs:
            break
            
        if bet["event"] in used_events:
            continue
        
        potential_odds = current_odds * bet["decimal_odds"]
        
        if potential_odds <= max_target:
            selected_legs.append(bet)
            current_odds = potential_odds
            used_events.add(bet["event"])
            
            if len(selected_legs) >= min_legs and current_odds >= min_target:
                break
    
    if len(selected_legs) < min_legs and len(selected_legs) < max_legs:
        for bet in value_bets:
            if bet["event"] in used_events:
                continue
            
            selected_legs.append(bet)
            current_odds *= bet["decimal_odds"]
            used_events.add(bet["event"])
            
            if len(selected_legs) >= min_legs or len(selected_legs) >= max_legs:
                break
    
    combined_probability = 1.0
    for leg in selected_legs:
        combined_probability *= (leg["model_probability"] / 100)
    
    return {
        "legs": selected_legs,
        "combined_odds": calculate_multi_odds(selected_legs),
        "combined_probability": round(combined_probability * 100, 2),
        "num_legs": len(selected_legs),
        "target_odds": target_odds,
        "potential_return": round(10 * calculate_multi_odds(selected_legs), 2),
    }

def build_multiple_multis(count: int = 3, target_odds: float = None) -> List[Dict[str, Any]]:
    if target_odds is None:
        target_odds = SETTINGS["target_multi_odds"]
    
    value_bets = get_all_value_bets()
    multis = []
    
    main_multi = build_suggested_multi(target_odds)
    if main_multi["legs"]:
        multis.append(main_multi)
    
    return multis
