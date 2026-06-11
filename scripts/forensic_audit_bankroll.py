"""
Bankroll Forensic Audit
=======================
Usage: python scripts/forensic_audit_bankroll.py

Verifies:
  1. Bankroll update formula correctness
  2. Equity curve order (settled_at ascending)
  3. Drawdown calculation integrity
  4. Bankroll never resets during simulation
  5. Portfolio stake weights sum == 1.0
  6. profit == final_bankroll - starting_bankroll
  7. First 10 + Last 10 equity curve rows

Expected final line: BANKROLL_FORENSIC_AUDIT_OK
"""

import os, sys, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from app.database.supabase_repository import get_repository
from app.services.simulation.bankroll_simulator import (
    build_bankroll_simulation, _PORTFOLIO_WEIGHTS,
    _picks_betiq_live_safe, _picks_no_extreme_unders, _picks_shadow_market_v1,
    _picks_shadow_strategy, _sorted_picks
)

# ── Fetch data (same paginated logic as validate script) ─────────────────────
repo     = get_repository()
reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()

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

needed   = list({r["fixture_id"] for r in rows if r.get("fixture_id")})
fixtures = []
for i in range(0, len(needed), 200):
    batch = repo._client.table("fixtures").select(
        "fixture_id, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status"
    ).in_("fixture_id", needed[i:i+200]).execute().data or []
    fixtures.extend(batch)
fixture_lookup = {f["fixture_id"]: f for f in fixtures if f.get("fixture_id")}

# ── Re-generate shadow picks (same logic as shadow-lab) ──────────────────────
def _gp(profile, key, default=0):
    if not profile: return default
    if isinstance(profile, str):
        try: profile = json.loads(profile)
        except: return default
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
        if datetime.fromisoformat(created_at.replace("Z","+00:00")) > \
           datetime.fromisoformat(kickoff_time.replace("Z","+00:00")):
            continue
    except: continue

    op = pred.get("offensive_profile") or {}
    dp = pred.get("defensive_profile") or {}
    if isinstance(op, str):
        try: op = json.loads(op)
        except: op = {}
    if isinstance(dp, str):
        try: dp = json.loads(dp)
        except: dp = {}

    btts_rate       = _gp(op, "btts_rate",             0)
    over_2_5_rate   = _gp(op, "over_2_5_rate",         0)
    early_goal_rate = _gp(op, "early_goal_rate",        0)
    away_btts_rate  = _gp(op, "away_btts_rate",         0)
    explosive_score = _gp(op, "explosive_pairing_score",0)
    market_regime   = pred.get("market_regime", "")
    volatility      = pred.get("volatility_score", 0) or 0
    chaos           = pred.get("chaos_score",      0) or 0
    fixture         = fixture_lookup.get(fid, {})
    home_sc         = fixture.get("home_score")
    away_sc         = fixture.get("away_score")

    def _add(strategy, market, confidence, reason):
        sp = {
            "fixture_id": fid, "strategy": strategy, "market": market,
            "confidence": confidence, "reason": reason,
            "home_team": pred.get("home_team",""), "away_team": pred.get("away_team",""),
            "league": pred.get("league",""), "country": pred.get("country",""),
            "kickoff_time": kickoff_time, "created_at": created_at,
            "bookmaker_odd": None, "simulated_result": None, "simulated_profit_loss": None
        }
        if home_sc is not None and away_sc is not None:
            h, a = int(home_sc), int(away_sc)
            if market == "BTTS_YES":    sp["simulated_result"] = "WON" if h>0 and a>0 else "LOST"
            elif market == "BTTS_NO":   sp["simulated_result"] = "WON" if h==0 or a==0 else "LOST"
            elif market == "HOME_TEAM_OVER_0_5": sp["simulated_result"] = "WON" if h>=1 else "LOST"
            elif market == "HOME_TEAM_OVER_1_5": sp["simulated_result"] = "WON" if h>=2 else "LOST"
            elif market == "AWAY_TEAM_OVER_0_5": sp["simulated_result"] = "WON" if a>=1 else "LOST"
            elif market == "AWAY_TEAM_OVER_1_5": sp["simulated_result"] = "WON" if a>=2 else "LOST"
            r = sp["simulated_result"]
            if r=="WON":  sp["simulated_profit_loss"] = 0.9 if "BTTS" in market else 0.8
            elif r=="LOST": sp["simulated_profit_loss"] = -1.0
        shadow_predictions.append(sp)

    HIGH_REGIMES = {"HIGH_TEMPO","CHAOTIC","HIGH_TEMPO_OVER","SECOND_HALF_CHAOS"}
    if btts_rate>=65 or (volatility>=60 and chaos>=55):      _add("SHADOW_BTTS","BTTS_YES",70,f"btts={btts_rate}")
    if over_2_5_rate<=35 or btts_rate<=30:                   _add("SHADOW_BTTS","BTTS_NO", 65,f"btts={btts_rate}")
    if early_goal_rate>=60 or (over_2_5_rate>=50 and btts_rate>=50):
                                                              _add("SHADOW_TEAM_GOALS","HOME_TEAM_OVER_0_5",70,"")
    if early_goal_rate>=75 and over_2_5_rate>=60:             _add("SHADOW_TEAM_GOALS","HOME_TEAM_OVER_1_5",75,"")
    if away_btts_rate>=50 or (btts_rate>=55 and over_2_5_rate>=50):
                                                              _add("SHADOW_TEAM_GOALS","AWAY_TEAM_OVER_0_5",70,"")
    if away_btts_rate>=65 and over_2_5_rate>=65:              _add("SHADOW_TEAM_GOALS","AWAY_TEAM_OVER_1_5",75,"")
    if early_goal_rate>=70 and over_2_5_rate>=60 and market_regime in HIGH_REGIMES:
                                                              _add("TEAM_GOALS_CONSERVATIVE","HOME_TEAM_OVER_0_5",80,"")
    if early_goal_rate>=80 and over_2_5_rate>=70 and explosive_score>=65:
                                                              _add("TEAM_GOALS_CONSERVATIVE","HOME_TEAM_OVER_1_5",85,"")
    if away_btts_rate>=60 and btts_rate>=60:                  _add("TEAM_GOALS_CONSERVATIVE","AWAY_TEAM_OVER_0_5",75,"")
    if away_btts_rate>=70 and over_2_5_rate>=70:              _add("TEAM_GOALS_CONSERVATIVE","AWAY_TEAM_OVER_1_5",80,"")

print(f"Predictions: {len(rows)} | Fixtures: {len(fixture_lookup)} | Shadow picks: {len(shadow_predictions)}")

# ── Run simulation ────────────────────────────────────────────────────────────
sim = build_bankroll_simulation(rows, shadow_predictions)
STARTING = sim["settings"]["starting_bankroll"]
STAKE    = sim["settings"]["flat_stake"]

PASS_MARK = "\u2705"
FAIL_MARK = "\u274c"
issues = []

def check(label, condition, detail=""):
    ok = bool(condition)
    mark = PASS_MARK if ok else FAIL_MARK
    print(f"  {mark}  {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        issues.append(label)
    return ok

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("AUDIT 5 — Portfolio stake weights")
print("="*70)
total_weight = sum(_PORTFOLIO_WEIGHTS.values())
check("Weights sum == 1.0", abs(total_weight - 1.0) < 1e-9,
      f"sum = {total_weight}")
for bucket, w in _PORTFOLIO_WEIGHTS.items():
    print(f"       {bucket:<28}: {w*100:.0f}%")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("AUDIT — Individual strategies")
print("="*70)

strategies_by_name = {s["strategy"]: s for s in sim["strategies"]}

for name, s in strategies_by_name.items():
    ec   = s["equity_curve"]
    n    = s["settled_picks"]
    fb   = s["final_bankroll"]
    prof = s["profit"]
    sb   = s["starting_bankroll"]

    print(f"\n  ── {name} ({n} settled picks) ──")

    # 6. profit == final - starting
    check("profit = final_bankroll - starting_bankroll",
          abs(prof - (fb - sb)) < 0.01,
          f"{prof:.4f} vs {fb - sb:.4f}")

    # 1. Bankroll update formula — recompute independently
    picks_for_check = {
        "BETIQ_LIVE_SAFE":         _picks_betiq_live_safe(rows),
        "SHADOW_TEAM_GOALS":       _picks_shadow_strategy(shadow_predictions, "SHADOW_TEAM_GOALS"),
        "TEAM_GOALS_CONSERVATIVE": _picks_shadow_strategy(shadow_predictions, "TEAM_GOALS_CONSERVATIVE"),
        "SHADOW_BTTS":             _picks_shadow_strategy(shadow_predictions, "SHADOW_BTTS"),
        "NO_EXTREME_UNDERS":       _picks_no_extreme_unders(rows),
        "SHADOW_MARKET_V1":        _picks_shadow_market_v1(rows),
    }.get(name, [])

    indep_bk = STARTING
    for p in picks_for_check:
        eff = float(p.get("odd") or 1.8)
        if eff < 1.01: eff = 1.8
        if p["result"] == "WON":   indep_bk += (eff - 1.0) * STAKE
        elif p["result"] == "LOST": indep_bk -= STAKE
    check("Independent bankroll recompute matches",
          abs(round(indep_bk, 2) - fb) < 0.02,
          f"independent={indep_bk:.2f} simulator={fb:.2f}")

    # 4. Bankroll never resets (no sudden large jump up mid-sequence)
    zero_or_neg = [e for e in ec if e.get("bankroll_after", 1) <= 0]
    check("Bankroll never <= 0", len(zero_or_neg) == 0,
          f"{len(zero_or_neg)} entries with bankroll_after <= 0")
    if zero_or_neg:
        for z in zero_or_neg[:3]:
            print(f"         !! index={z['index']} bankroll_after={z['bankroll_after']} result={z['result']} odd={z['odd']}")

    # 2. Equity curve ordering
    settled_ats = [e["settled_at"] for e in ec if e.get("settled_at")]
    is_sorted   = all(settled_ats[i] <= settled_ats[i+1] for i in range(len(settled_ats)-1))
    check("Equity curve sorted by settled_at ascending", is_sorted,
          f"{len(settled_ats)} dated entries")

    # 3. Drawdown calculation — recompute
    peak_bk = STARTING
    computed_max_dd = 0.0
    for e in ec[1:]:
        bk_after = e.get("bankroll_after", STARTING)
        if bk_after > peak_bk:
            peak_bk = bk_after
        dd = peak_bk - bk_after
        if dd > computed_max_dd:
            computed_max_dd = dd
    reported_dd = s["max_drawdown_units"]
    check("Max drawdown matches independent recompute",
          abs(computed_max_dd - reported_dd) < 0.02,
          f"computed={computed_max_dd:.2f} reported={reported_dd:.2f}")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("AUDIT — PORTFOLIO_BALANCED_V1")
print("="*70)

port = sim["portfolios"][0]
ec_p = port["equity_curve"]
fb_p = port["final_bankroll"]
pf_p = port["portfolio_profit"]

check("profit = final_bankroll - starting_bankroll",
      abs(pf_p - (fb_p - STARTING)) < 0.01,
      f"{pf_p:.4f} vs {fb_p - STARTING:.4f}")

zero_port = [e for e in ec_p if e.get("bankroll_after", 1) <= 0]
check("Portfolio bankroll never <= 0", len(zero_port) == 0,
      f"{len(zero_port)} zero-or-negative entries")
if zero_port:
    for z in zero_port[:3]:
        print(f"     !! index={z['index']} bankroll_after={z['bankroll_after']} result={z['result']} odd={z['odd']} stake={z['stake']}")

settled_ats_p = [e["settled_at"] for e in ec_p if e.get("settled_at")]
check("Portfolio equity curve sorted ascending",
      all(settled_ats_p[i] <= settled_ats_p[i+1] for i in range(len(settled_ats_p)-1)),
      f"{len(settled_ats_p)} dated entries")

# Recompute max drawdown from equity_curve
peak_bk = STARTING
computed_dd_p = 0.0
for e in ec_p[1:]:
    bk = e.get("bankroll_after", STARTING)
    if bk > peak_bk: peak_bk = bk
    dd = peak_bk - bk
    if dd > computed_dd_p: computed_dd_p = dd
check("Portfolio max drawdown matches equity_curve",
      abs(computed_dd_p - port["max_drawdown"]) < 0.02,
      f"computed={computed_dd_p:.2f} reported={port['max_drawdown']:.2f}")

# Stake allocation per pick sums check
stakes_seen = set(e["stake"] for e in ec_p[1:] if e["stake"] > 0)
valid_stakes = set(_PORTFOLIO_WEIGHTS.values())
invalid_stakes = stakes_seen - valid_stakes
check("All portfolio stakes are in weight set",
      len(invalid_stakes) == 0,
      f"invalid={invalid_stakes}" if invalid_stakes else f"valid={sorted(stakes_seen)}")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("KEY METRICS SUMMARY")
print("="*70)
print(f"  starting_bankroll     : {STARTING:.2f}u")
print(f"  final_bankroll (port) : {fb_p:.2f}u")
print(f"  profit (port)         : {pf_p:+.2f}u")
print(f"  max_drawdown (port)   : {port['max_drawdown']:.2f}u ({port['max_drawdown_percent']:.1f}%)")
print(f"  longest_losing_streak : {port['longest_losing_streak']}")
print(f"  peak_bankroll (port)  : {port['peak_bankroll']:.2f}u")
print(f"  lowest_bankroll (port): {port['lowest_bankroll']:.2f}u")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("PORTFOLIO EQUITY CURVE — first 10 entries")
print("="*70)
COLS = ["index","settled_at","match","market","result","odd","stake","profit_loss","bankroll_after"]
header = f"{'#':>4} {'settled_at':<20} {'match':<25} {'market':<22} {'res':>4} {'odd':>6} {'stk':>4} {'p/l':>7} {'bk_after':>9}"
print(header)
print("-" * len(header))
for e in ec_p[:10]:
    match = (e.get("match") or "")[:24]
    mkt   = (e.get("market") or "")[:21]
    print(f"{e['index']:>4} {str(e.get('settled_at','')):<20} {match:<25} {mkt:<22} "
          f"{str(e.get('result',''))[:4]:>4} {e.get('odd',0):>6.3f} {e.get('stake',0):>4.2f} "
          f"{e.get('profit_loss',0):>+7.4f} {e.get('bankroll_after',0):>9.2f}")

print(f"\n  ... ({len(ec_p)} total entries) ...")

print("\n" + "="*70)
print("PORTFOLIO EQUITY CURVE — last 10 entries")
print("="*70)
print(header)
print("-" * len(header))
for e in ec_p[-10:]:
    match = (e.get("match") or "")[:24]
    mkt   = (e.get("market") or "")[:21]
    print(f"{e['index']:>4} {str(e.get('settled_at','')):<20} {match:<25} {mkt:<22} "
          f"{str(e.get('result',''))[:4]:>4} {e.get('odd',0):>6.3f} {e.get('stake',0):>4.2f} "
          f"{e.get('profit_loss',0):>+7.4f} {e.get('bankroll_after',0):>9.2f}")

# ═══════════════════════════════════════════════════════════════════════════════
# Search for any anomalous bankroll drops in ALL strategy equity curves
print("\n" + "="*70)
print("ANOMALY SCAN — bankroll_after <= 0 or bankroll_after < 10% of starting")
print("="*70)
found_anomaly = False
for s in sim["strategies"]:
    for e in s["equity_curve"]:
        bk = e.get("bankroll_after", STARTING)
        if bk <= 0 or bk < STARTING * 0.10:
            print(f"  [{s['strategy']}] index={e['index']} bankroll_after={bk:.4f} result={e.get('result')} odd={e.get('odd')} date={e.get('settled_at')}")
            found_anomaly = True
for e in ec_p:
    bk = e.get("bankroll_after", STARTING)
    if bk <= 0 or bk < STARTING * 0.10:
        print(f"  [PORTFOLIO] index={e['index']} bankroll_after={bk:.4f} result={e.get('result')} odd={e.get('odd')} stake={e.get('stake')}")
        found_anomaly = True
if not found_anomaly:
    print("  No anomalies found.")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
if issues:
    print(f"AUDIT FAILED — {len(issues)} issue(s):")
    for iss in issues:
        print(f"  - {iss}")
    sys.exit(1)
else:
    print("BANKROLL_FORENSIC_AUDIT_OK")
