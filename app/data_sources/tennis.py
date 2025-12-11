from typing import List, Dict, Any

def get_upcoming_matches() -> List[Dict[str, Any]]:
    return [
        {
            "match_id": "tennis_001",
            "player_a": "Carlos Alcaraz",
            "player_b": "Jannik Sinner",
            "tournament": "Australian Open",
            "surface": "Hard",
            "date": "2024-01-28",
        },
        {
            "match_id": "tennis_002",
            "player_a": "Novak Djokovic",
            "player_b": "Daniil Medvedev",
            "tournament": "Australian Open",
            "surface": "Hard",
            "date": "2024-01-28",
        },
    ]

def get_player_stats(player_name: str) -> Dict[str, Any]:
    mock_stats = {
        "Carlos Alcaraz": {"ranking": 2, "win_rate": 0.85, "hard_court_rate": 0.82},
        "Jannik Sinner": {"ranking": 4, "win_rate": 0.80, "hard_court_rate": 0.78},
        "Novak Djokovic": {"ranking": 1, "win_rate": 0.88, "hard_court_rate": 0.90},
        "Daniil Medvedev": {"ranking": 3, "win_rate": 0.78, "hard_court_rate": 0.82},
    }
    return mock_stats.get(player_name, {"ranking": 100, "win_rate": 0.5, "hard_court_rate": 0.5})

def get_model_probability(player_a: str, player_b: str) -> Dict[str, float]:
    stats_a = get_player_stats(player_a)
    stats_b = get_player_stats(player_b)
    
    prob_a = stats_a["win_rate"] / (stats_a["win_rate"] + stats_b["win_rate"])
    prob_b = 1 - prob_a
    
    return {player_a: round(prob_a, 3), player_b: round(prob_b, 3)}
