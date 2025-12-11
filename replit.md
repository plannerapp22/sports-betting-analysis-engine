# Sports Betting Analysis Engine

## Overview
A Python FastAPI backend service for analyzing sports betting value opportunities across UFC, NBA, NFL, and NRL. The system uses ML-powered Expected Value (EV) calculations with two-stage filtering to identify up to 20 high-confidence betting legs with odds between 1.05-1.25 for safe multi-leg parlays. Each recommendation includes a data-backed rationale explaining the pick based purely on probability analysis. Uses ONLY real live data from The Odds API with scheduled Monday/Thursday fetches.

## Data Sources (All Real - No Mock Data)
- **Odds Data**: The Odds API (Australian bookmakers for h2h, US bookmakers for player props)
- **NBA Stats**: nba_api Python package (official NBA.com data)
- **NFL Stats**: ESPN API (unofficial, free, no auth required)
- **Cross-validation**: Multiple sources verify stats accuracy

## How to Use Recommendations
The system identifies value betting opportunities using odds data from multiple bookmakers. 
Users should place these bets on their preferred Australian betting app:
- **Sportsbet** - Largest AU bookmaker, extensive player props
- **TAB** - Strong racing integration
- **Ladbrokes** - Best tools and live tracking
- **Neds** - High user satisfaction
- **Pointsbet** - Strong NBA/NFL props
- **Betr** - New entrant with competitive odds

All major Australian apps offer the same player prop markets identified by the system.

## Project Structure
```
/app
    __init__.py
    main.py              # FastAPI entry point
    config.py            # Settings and configuration
    utils.py             # Shared helper functions
    db.py                # SQLite database configuration
    models_db.py         # SQLAlchemy ORM models
    scheduled_fetch.py   # Scheduled data fetching logic

/app/data_sources
    __init__.py
    nba.py               # NBA game data (uses nba_stats.py)
    nfl.py               # NFL game data (uses nfl_stats.py)
    odds_api.py          # The Odds API integration
    nba_stats.py         # Real NBA stats from nba_api
    nfl_stats.py         # Real NFL stats from ESPN API

/app/models
    __init__.py
    probability.py       # ML probability model (Random Forest)
    expected_value.py    # EV calculation and bet analysis

/app/services
    __init__.py
    analyzer.py          # Two-stage filtering with composite scoring
    multi_builder.py     # Parlay builder targeting ~$2 odds

/app/ui
    index.html           # Main web interface (recommended legs)
    value-picks.html     # Separate value picks page
    script.js            # Frontend JavaScript
    styles.css           # Styling

/model_artifacts
    default_model.pkl    # Trained ML model

cached_odds_data.json    # Stored odds data from scheduled fetches
fetch_scheduled.py       # Standalone fetch script for cron
```

## API Endpoints
- `GET /` - Health check (version 3.0.0)
- `GET /recommended-legs` - Get up to 20 high-confidence legs with rationales
- `GET /weekly-summary` - Get weekly analysis summary
- `GET /value-bets` - Get all value bets (?sport=nba&limit=100)
- `GET /suggested-multi` - Get suggested parlay (?target_odds=2.0&max_legs=4)
- `GET /sports` - List supported sports (ufc, nba, nfl, nrl)
- `GET /settings` - View current configuration
- `GET /cache-stats` - View cache statistics
- `POST /clear-cache` - Manually clear cached data
- `POST /fetch-odds` - Trigger immediate data fetch
- `GET /stored-data-status` - Check when data was last fetched
- `GET /ui` - Main web interface
- `GET /value-picks` - Value picks page
- `GET /stats-sources` - View connected stats APIs status
- `GET /player-stats/{sport}/{player_name}` - Get real player statistics
- `GET /team-stats/{sport}/{team_name}` - Get real team statistics

## Stats API Endpoints

### Player Stats
```
GET /player-stats/nfl/Patrick%20Mahomes
GET /player-stats/nba/LeBron%20James?games=10
```
Returns real season stats, averages, and totals from ESPN (NFL) or NBA.com (NBA).

### Team Stats
```
GET /team-stats/nfl/Kansas%20City%20Chiefs
GET /team-stats/nba/Boston%20Celtics
```
Returns real win rates, PPG, defensive ratings from official sources.

## Supported Sports
- **NBA** - Basketball with extensive player props and alternates (real stats from nba_api)
- **NFL** - Football with comprehensive player props and alternates (real stats from ESPN API)

## Allowed Market Types by Sport

### NFL Markets (16 markets)
| Market Type | Description |
|-------------|-------------|
| `moneyline` | Game winner (head-to-head) |
| `spread` | Point spread betting |
| `totals` | Over/under total points |
| `player_pass_tds_over_under` | QB passing touchdowns |
| `player_pass_yards_over_under` | QB passing yards |
| `player_pass_completions_over_under` | QB pass completions |
| `player_pass_attempts_over_under` | QB pass attempts |
| `player_rush_yards_over_under` | Player rushing yards |
| `player_rush_attempts_over_under` | Player rush attempts |
| `player_receiving_yards_over_under` | Player receiving yards |
| `player_receptions_over_under` | Player total receptions |
| `player_anytime_touchdown` | Player to score anytime |
| `player_first_touchdown` | First touchdown scorer |
| `alternate_player_pass_yards` | Alternate passing yards lines (250+, 300+, etc.) |
| `alternate_player_rush_yards` | Alternate rushing yards lines (75+, 100+, etc.) |
| `alternate_player_receiving_yards` | Alternate receiving yards lines (50+, 75+, etc.) |

### NBA Markets (13 markets)
| Market Type | Description |
|-------------|-------------|
| `moneyline` | Game winner (head-to-head) |
| `player_points_over_under` | Player total points |
| `player_assists_over_under` | Player total assists |
| `player_rebounds_over_under` | Player total rebounds |
| `player_threes_over_under` | Player three-pointers made |
| `player_blocks_over_under` | Player total blocks |
| `player_steals_over_under` | Player total steals |
| `player_pra_over_under` | Points + Rebounds + Assists combo |
| `player_double_double` | Player to get a double-double |
| `alternate_player_points` | Alternate points lines (25+, 30+, 35+, etc.) |
| `alternate_player_rebounds` | Alternate rebounds lines (10+, 12+, etc.) |
| `alternate_player_assists` | Alternate assists lines (8+, 10+, etc.) |
| `alternate_player_threes` | Alternate threes lines (4+, 5+, etc.) |

## Alternate Lines Explained
Alternate lines offer different thresholds than the standard line:
- **Standard**: Patrick Mahomes Over/Under 275.5 passing yards
- **Alternate**: Patrick Mahomes 300+ passing yards (higher odds, lower probability)

These are useful for finding value when statistics suggest a player will significantly exceed expectations.

## Two-Stage Filtering Process

### Stage 1: Numerical Filter (All markets -> ~60 candidates)
- Odds between 1.05 and 1.25
- Model probability >= 75%
- Edge (model prob - implied prob) >= 2 percentage points
- EV >= -5%

### Stage 2: Deep Prune (60 candidates -> up to 20 final legs)
- Composite score calculation
- Rivalry/upset risk penalties
- Consistency bonuses
- Rank by score, select top 20

## Key Formulas
- **Implied Probability**: `1 / decimal_odds`
- **Expected Value**: `(model_prob * decimal_odds) - 1`
- **Edge**: `model_probability - implied_probability`
- **Composite Score**: `(model_prob * 0.4) + (ev * 20 * 0.3) + (edge * 10 * 0.2) + (consistency * 100 * 0.1)`

## Event Filtering
- Only includes confirmed, scheduled matchups
- Automatically excludes events that have already occurred
- Only shows events within 7 days from current time
- Excludes TBA/TBD matchups

## Australian Bookmakers Supported
- Sportsbet, TAB, Neds, Ladbrokes, Betfair, Unibet, Pointsbet, Betr

## Environment Variables
- `THE_ODDS_API_KEY` - API key for The Odds API (required for live data)
- `BETTING_DB_URL` - Database URL (defaults to SQLite)

## Running the Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

## Scheduled Fetching
The system fetches fresh odds data only on Mondays and Thursdays to minimize API usage:
- **Script**: `python fetch_scheduled.py`
- **Schedule**: Mondays and Thursdays at 6:00 AM UTC
- **Cron expression**: `0 6 * * 1,4`
- **API usage**: ~4 requests per fetch, ~32/month total

### Manual Fetch
- `POST /fetch-odds` - Trigger immediate fetch
- `GET /stored-data-status` - Check when data was last fetched

## Deployment Notes
- **Main API**: Uses autoscale deployment (stateless)
- **Scheduled Task**: Runs `python fetch_scheduled.py` on Mon/Thu
- Requires `THE_ODDS_API_KEY` secret for production
- Free tier: 500 requests/month (system uses ~32)

## Current State
- Real odds from Australian bookmakers via The Odds API
- Real NFL stats from ESPN API (no auth required)
- Real NBA stats from nba_api (official NBA.com data)
- NO mock/hardcoded data - all stats are live
- Two-stage filtering with composite scoring
- Data-backed rationales for each recommended leg (pure probability analysis)
- Scheduled Mon/Thu fetches to optimize API usage
- Card-based UI with expandable rationales
- Separate value picks page with filtering
- Supports alternate player prop lines for NFL/NBA
- Automatic past event filtering

## Recent Changes (Dec 11, 2025)
- Integrated real NFL stats via ESPN API (free, no auth)
- Integrated real NBA stats via nba_api package
- Removed ALL mock/hardcoded data from codebase
- Added /player-stats and /team-stats endpoints
- Added /stats-sources endpoint to verify data sources
- Increased recommended legs cap from 12 to 20
- Removed Tennis as a supported sport
- Added separate Value Picks page (/value-picks)
- Added automatic filtering of past events

## Stats Data Available

### NFL Player Stats (from ESPN)
- Passing: yards, TDs, completions, attempts, rating
- Rushing: yards, attempts, TDs
- Receiving: yards, receptions, TDs

### NBA Player Stats (from nba_api)
- Points, rebounds, assists
- Threes made, steals, blocks
- Game logs and hit rates

### Team Stats
- Win rate, PPG, defensive rating
- Recent form (last 10 games)
