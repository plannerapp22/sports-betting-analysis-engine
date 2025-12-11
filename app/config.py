import os

API_KEYS = {
    "odds_api": os.getenv("THE_ODDS_API_KEY", "") or os.getenv("ODDS_API_KEY", ""),
}

SETTINGS = {
    "min_ev_threshold": 0.02,
    "min_confidence_threshold": 0.70,
    "target_multi_odds": 2.0,
    "max_legs_in_multi": 4,
    "min_odds_filter": 1.05,
    "max_odds_filter": 1.25,
    "recommended_legs_count": 20,
    "stage1_min_model_prob": 75,
    "stage1_min_edge": 2,
    "stage1_candidate_limit": 60,
    "stage2_rivalry_penalty": 8,
    "stage2_consistency_bonus": 4,
}

SUPPORTED_SPORTS = ["nba", "nfl"]

ODDS_API_SPORTS = {
    "nba": "basketball_nba",
    "nfl": "americanfootball_nfl",
}

ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
ODDS_API_REGIONS = "au"
ODDS_API_MARKETS = "h2h"

ODDS_API_PROPS_MARKETS = {
    "nba": "player_points,player_rebounds,player_assists,player_points_rebounds_assists,player_threes,player_blocks,player_steals,player_double_double",
    "nfl": "player_pass_tds,player_pass_yds,player_rush_yds,player_reception_yds,player_receptions,player_anytime_td,player_pass_completions,player_pass_attempts,player_rush_attempts,player_first_td",
}

MARKET_TYPE_MAPPING = {
    "h2h": "moneyline",
    "h2h_lay": "moneyline_lay",
    "spreads": "spread",
    "totals": "totals",
    "player_points": "player_points_over_under",
    "player_rebounds": "player_rebounds_over_under",
    "player_assists": "player_assists_over_under",
    "player_points_rebounds_assists": "player_pra_over_under",
    "player_threes": "player_threes_over_under",
    "player_blocks": "player_blocks_over_under",
    "player_steals": "player_steals_over_under",
    "player_double_double": "player_double_double",
    "player_pass_tds": "player_pass_tds_over_under",
    "player_pass_yds": "player_pass_yards_over_under",
    "player_rush_yds": "player_rush_yards_over_under",
    "player_reception_yds": "player_receiving_yards_over_under",
    "player_receptions": "player_receptions_over_under",
    "player_anytime_td": "player_anytime_touchdown",
    "player_pass_completions": "player_pass_completions_over_under",
    "player_pass_attempts": "player_pass_attempts_over_under",
    "player_rush_attempts": "player_rush_attempts_over_under",
    "player_first_td": "player_first_touchdown",
    "alternate_player_points": "alternate_player_points",
    "alternate_player_rebounds": "alternate_player_rebounds",
    "alternate_player_assists": "alternate_player_assists",
    "alternate_player_threes": "alternate_player_threes",
    "alternate_player_pass_yds": "alternate_player_pass_yards",
    "alternate_player_rush_yds": "alternate_player_rush_yards",
    "alternate_player_reception_yds": "alternate_player_receiving_yards",
}

ALLOWED_MARKET_TYPES = {
    "NBA": [
        "moneyline",
        "player_points_over_under",
        "player_assists_over_under",
        "player_rebounds_over_under",
        "player_threes_over_under",
        "player_blocks_over_under",
        "player_steals_over_under",
        "player_pra_over_under",
        "player_double_double",
        "alternate_player_points",
        "alternate_player_rebounds",
        "alternate_player_assists",
        "alternate_player_threes",
    ],
    "NFL": [
        "moneyline",
        "spread",
        "totals",
        "player_pass_tds_over_under",
        "player_pass_yards_over_under",
        "player_rush_yards_over_under",
        "player_receiving_yards_over_under",
        "player_receptions_over_under",
        "player_anytime_touchdown",
        "player_pass_completions_over_under",
        "player_pass_attempts_over_under",
        "player_rush_attempts_over_under",
        "player_first_touchdown",
        "alternate_player_pass_yards",
        "alternate_player_rush_yards",
        "alternate_player_receiving_yards",
    ],
}

CONFIRMED_EVENT_STATUSES = ["scheduled", "pre_match", "open"]
MAX_EVENT_DAYS_AHEAD = 7
EXCLUDE_TBA_STRINGS = ["TBA", "To be announced", "tba", "to be announced", "TBD", "To be determined"]

MODEL_ARTIFACTS_PATH = "model_artifacts"
