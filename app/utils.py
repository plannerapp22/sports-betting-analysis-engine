from typing import List, Dict, Any
from datetime import datetime

def format_decimal_odds(odds: float) -> str:
    return f"${odds:.2f}"

def calculate_combined_odds(legs: List[Dict[str, Any]]) -> float:
    if not legs:
        return 1.0
    combined = 1.0
    for leg in legs:
        combined *= leg.get("decimal_odds", 1.0)
    return round(combined, 2)

def get_current_timestamp() -> str:
    return datetime.now().isoformat()

def validate_odds(odds: float) -> bool:
    return odds >= 1.0

def calculate_payout(stake: float, decimal_odds: float) -> float:
    return round(stake * decimal_odds, 2)

def format_percentage(value: float) -> str:
    return f"{value * 100:.1f}%"
