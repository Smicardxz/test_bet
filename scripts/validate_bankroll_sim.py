"""
Phase 4 — Bankroll Simulation Validation
==========================================
Usage:  python scripts/validate_bankroll_sim.py

Fetches live Supabase data, runs the bankroll simulator, and prints a
formatted comparison table.

Expected final line: BANKROLL_PORTFOLIO_SIMULATION_OK
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.database.supabase_repository import get_repository
from app.services.simulation.bankroll_simulator import build_bankroll_simulation

# ─── Fetch data (same logic as shadow-lab endpoint) ──────────────────────────

repo     = get_repository()
reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()

# Paginated predictions
_PRED_COLS = (
    "id, market, status, selection_mode, bookmaker_odd, ev_percentage, "
    "created_at, prediction_date, home_team, away_team, league, fixture_id, "
    "offensive_profile, defensive_profile, market_generation_stats, "
    "recommended_market_direction, best_over_market, best_under_market, "
    "market_regime, confidence_score, volatility_score, chaos_score, "
    "event_context, country, kickoff_time"
)

if reset_at:
    _fc = "created_at" if "T" in reset_at else "prediction_date"
    _fv = reset_at
else:
    from datetime import date, timedelta
    _fc = "prediction_date"
    _fv = (date.today() - timedelta(days=30)).isoformat()

rows, _page, _sz = [], 0, 1000
while True:
    batch = repo._client.table("predictions").select(_PRED_COLS).gte(
        _fc, _fv
    ).range(_page * _sz, (_page + 1) * _sz - 1).execute().data or []
    rows.extend(batch)
    if len(batch) < _sz:
        break
    _page += 1

print(f"Predictions loaded: {len(rows)}")

# Targeted fixture fetch
needed  = list({r["fixture_id"] for r in rows if r.get("fixture_id")})
fixtures = []
for i in range(0, len(needed), 200):
    batch = repo._client.table("fixtures").select(
        "fixture_id, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status"
    ).in_("fixture_id", needed[i:i+200]).execute().data or []
    fixtures.extend(batch)

fixture_lookup = {f["fixture_id"]: f for f in fixtures if f.get("fixture_id")}
print(f"Fixtures loaded: {len(fixture_lookup)} (with scores: {sum(1 for f in fixture_lookup.values() if f.get('home_score') is not None)})")

# ─── Reconstruct shadow_predictions (minimal version for validation) ─────────
import json

def _gp(profile, key, default=0):
    if not profile:
        return default
    if isinstance(profile, str):
        try:
            profile = json.loads(profile)
        except Exception:
            return default
    return profile.get(key, default) or default

from datetime import datetime, timezone

shadow_predictions = []
for pred in rows:
    fid          = pred.get("fixture_id", "")
    kickoff_time = pred.get("kickoff_time", pred.get("prediction_date", ""))
    created_at   = pred.get("created_at", "")
    if not kickoff_time or not created_at:
        continue
    try:
        if datetime.fromisoformat(created_at.replace("Z", "+00:00")) > \
           datetime.fromisoformat(kickoff_time.replace("Z", "+00:00")):
            continue
    except Exception:
        continue

    op   = pred.get("offensive_profile") or {}
    dp   = pred.get("defensive_profile") or {}
    if isinstance(op, str):
        try: op = json.loads(op)
        except: op = {}
    if isinstance(dp, str):
        try: dp = json.loads(dp)
        except: dp = {}

    btts_rate       = _gp(op, "btts_rate", 0)
    over_2_5_rate   = _gp(op, "over_2_5_rate", 0)
    early_goal_rate = _gp(op, "early_goal_rate", 0)
    away_btts_rate  = _gp(op, "away_btts_rate", 0)
    explosive_score = _gp(op, "explosive_pairing_score", 0)
    market_regime   = pred.get("market_regime", "")
    volatility      = pred.get("volatility_score", 0) or 0
    chaos           = pred.get("chaos_score", 0) or 0

    fixture = fixture_lookup.get(fid, {})
    home_sc = fixture.get("home_score")
    away_sc = fixture.get("away_score")

    def _add(strategy, market, confidence, reason):
        sp = {
            "fixture_id": fid, "strategy": strategy, "market": market,
            "confidence": confidence, "reason": reason,
            "home_team": pred.get("home_team", ""), "away_team": pred.get("away_team", ""),
            "league": pred.get("league", ""), "country": pred.get("country", ""),
            "kickoff_time": kickoff_time, "created_at": created_at,
            "bookmaker_odd": None, "simulated_result": None, "simulated_profit_loss": None
        }
        if home_sc is not None and away_sc is not None:
            home_sc_i, away_sc_i = int(home_sc), int(away_sc)
            if market == "BTTS_YES":
                sp["simulated_result"] = "WON" if home_sc_i > 0 and away_sc_i > 0 else "LOST"
            elif market == "BTTS_NO":
                sp["simulated_result"] = "WON" if home_sc_i == 0 or away_sc_i == 0 else "LOST"
            elif market == "HOME_TEAM_OVER_0_5":
                sp["simulated_result"] = "WON" if home_sc_i >= 1 else "LOST"
            elif market == "HOME_TEAM_OVER_1_5":
                sp["simulated_result"] = "WON" if home_sc_i >= 2 else "LOST"
            elif market == "AWAY_TEAM_OVER_0_5":
                sp["simulated_result"] = "WON" if away_sc_i >= 1 else "LOST"
            elif market == "AWAY_TEAM_OVER_1_5":
                sp["simulated_result"] = "WON" if away_sc_i >= 2 else "LOST"
            r = sp["simulated_result"]
            if r == "WON":
                sp["simulated_profit_loss"] = 0.9 if "BTTS" in market else 0.8
            elif r == "LOST":
                sp["simulated_profit_loss"] = -1.0
        shadow_predictions.append(sp)

    # SHADOW_BTTS
    if btts_rate >= 65 or (volatility >= 60 and chaos >= 55):
        _add("SHADOW_BTTS", "BTTS_YES", 70, f"BTTS rate {btts_rate}%")
    if over_2_5_rate <= 35 or (btts_rate <= 30):
        _add("SHADOW_BTTS", "BTTS_NO",  65, f"Low BTTS {btts_rate}%")

    # SHADOW_TEAM_GOALS
    if early_goal_rate >= 60 or (over_2_5_rate >= 50 and btts_rate >= 50):
        _add("SHADOW_TEAM_GOALS", "HOME_TEAM_OVER_0_5", 70, f"Early {early_goal_rate}%")
    if early_goal_rate >= 75 and over_2_5_rate >= 60:
        _add("SHADOW_TEAM_GOALS", "HOME_TEAM_OVER_1_5", 75, f"Early {early_goal_rate}%")
    if away_btts_rate >= 50 or (btts_rate >= 55 and over_2_5_rate >= 50):
        _add("SHADOW_TEAM_GOALS", "AWAY_TEAM_OVER_0_5", 70, f"Away BTTS {away_btts_rate}%")
    if away_btts_rate >= 65 and over_2_5_rate >= 65:
        _add("SHADOW_TEAM_GOALS", "AWAY_TEAM_OVER_1_5", 75, f"Away BTTS {away_btts_rate}%")

    # TEAM_GOALS_CONSERVATIVE
    HIGH_REGIMES = {"HIGH_TEMPO", "CHAOTIC", "HIGH_TEMPO_OVER", "SECOND_HALF_CHAOS"}
    if early_goal_rate >= 70 and over_2_5_rate >= 60 and market_regime in HIGH_REGIMES:
        _add("TEAM_GOALS_CONSERVATIVE", "HOME_TEAM_OVER_0_5", 80, f"Conservative {market_regime}")
    if early_goal_rate >= 80 and over_2_5_rate >= 70 and explosive_score >= 65:
        _add("TEAM_GOALS_CONSERVATIVE", "HOME_TEAM_OVER_1_5", 85, f"Explosive {explosive_score}%")
    if away_btts_rate >= 60 and btts_rate >= 60:
        _add("TEAM_GOALS_CONSERVATIVE", "AWAY_TEAM_OVER_0_5", 75, f"Away BTTS {away_btts_rate}%")
    if away_btts_rate >= 70 and over_2_5_rate >= 70:
        _add("TEAM_GOALS_CONSERVATIVE", "AWAY_TEAM_OVER_1_5", 80, f"Away BTTS {away_btts_rate}%")

print(f"Shadow picks generated: {len(shadow_predictions)}")

# ─── Run simulation ──────────────────────────────────────────────────────────

sim = build_bankroll_simulation(rows, shadow_predictions)

# ─── Validation table ────────────────────────────────────────────────────────

REQUIRED_STRATEGIES = {
    "BETIQ_LIVE_SAFE", "SHADOW_TEAM_GOALS", "TEAM_GOALS_CONSERVATIVE",
    "SHADOW_BTTS", "NO_EXTREME_UNDERS", "SHADOW_MARKET_V1",
}

strategies_by_name = {s["strategy"]: s for s in sim["strategies"]}

print()
print("=" * 100)
print(f"{'Strategy':<28} {'Final BK':>9} {'Profit':>8} {'ROI':>7} {'Max DD':>8} {'Peak BK':>8} {'Low BK':>8} {'LLS':>4} {'Vol':>7} {'Picks':>6}")
print("-" * 100)

all_ok = True
for name in sorted(REQUIRED_STRATEGIES):
    m = strategies_by_name.get(name)
    if not m:
        print(f"{name:<28}  MISSING — FAIL")
        all_ok = False
        continue

    # Validate required fields are present
    required_fields = [
        "strategy", "starting_bankroll", "final_bankroll", "profit", "roi",
        "settled_picks", "wins", "losses", "hit_rate", "avg_odd",
        "max_drawdown_units", "max_drawdown_percent", "peak_bankroll",
        "lowest_bankroll", "longest_win_streak", "longest_losing_streak",
        "profit_factor", "volatility_score", "equity_curve",
    ]
    missing_fields = [f for f in required_fields if f not in m]
    if missing_fields:
        print(f"{name:<28}  MISSING FIELDS: {missing_fields}")
        all_ok = False
        continue

    # Validate equity_curve item format
    if m["equity_curve"] and len(m["equity_curve"]) > 1:
        ec_item = m["equity_curve"][1]
        ec_required = ["index", "settled_at", "fixture_id", "match", "market",
                       "result", "odd", "stake", "profit_loss", "bankroll_after"]
        missing_ec = [f for f in ec_required if f not in ec_item]
        if missing_ec:
            print(f"{name:<28}  EQUITY_CURVE missing fields: {missing_ec}")
            all_ok = False
            continue

    print(
        f"{name:<28} "
        f"{m['final_bankroll']:>8.2f}u "
        f"{m['profit']:>+7.2f}u "
        f"{m['roi']:>6.1f}% "
        f"{m['max_drawdown_units']:>6.2f}u "
        f"{m['peak_bankroll']:>7.2f}u "
        f"{m['lowest_bankroll']:>7.2f}u "
        f"{m['longest_losing_streak']:>4} "
        f"{m['volatility_score']:>7.4f} "
        f"{m['settled_picks']:>6}"
    )

print("=" * 100)

# ── Comparison summary ────────────────────────────────────────────────────────
print()
print("Comparison summary:")
print("-" * 50)
cmp = sim.get("comparison", {})
for key, val in cmp.items():
    if val:
        print(f"  {key:<26}: {val['strategy']} ({val['value']})")
    else:
        print(f"  {key:<26}: N/A")

# ── Portfolio ─────────────────────────────────────────────────────────────────
print()
print("Portfolio PORTFOLIO_BALANCED_V1:")
print("-" * 50)
for p in sim["portfolios"]:
    print(f"  Total bets      : {p['portfolio_total_bets']}")
    print(f"  Wins / Losses   : {p['portfolio_wins']} / {p['portfolio_losses']}")
    print(f"  Profit          : {p['portfolio_profit']:+.2f}u")
    print(f"  ROI             : {p['portfolio_roi']:+.2f}%")
    print(f"  Final bankroll  : {p['final_bankroll']:.2f}u")
    print(f"  Peak bankroll   : {p['peak_bankroll']:.2f}u")
    print(f"  Lowest bankroll : {p['lowest_bankroll']:.2f}u")
    print(f"  Max drawdown    : {p['max_drawdown']:.2f}u  ({p['max_drawdown_percent']:.1f}%)")
    print(f"  Longest L-streak: {p['longest_losing_streak']}")
    print(f"  Profit factor   : {p['profit_factor']:.3f}")
    print(f"  Volatility      : {p['volatility_score']:.4f}")
    print()

print()
if all_ok:
    print("BANKROLL_SIMULATION_OK")
else:
    print("VALIDATION FAILED — see errors above")
    sys.exit(1)
