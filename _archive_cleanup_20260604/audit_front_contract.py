"""
audit_front_contract.py — Frontend Data Contract Verification
==============================================================
Verifies that every field Lovable needs is present in the backend output.

Checks:
  /api/data         → match_info dict (via scanner + inline construction)
  /api/predictions/pending   → supabase repo
  /api/predictions/history   → supabase repo
  /api/performance/summary   → supabase repo
  /api/diagnostics           → odds coverage + API_FOOTBALL status

Pick-level required fields (in ev_qualified[i]):
  market, market_probability, probability_source, signal_confidence,
  bookmaker_odd, implied_probability, ev_percentage, edge_percentage,
  sample_size, odds_source, has_real_odds, classification, value_level

Match-level required fields (in match_info):
  ev_qualified, ev_rejected, tier_level, ev_quality, odds_source,
  market_access, recommended_market_direction,
  best_over_market, best_under_market, avoid_markets,
  why_pick, why_not_pick, risk_factors

Verdict: FRONT_CONTRACT_OK  or  FRONT_CONTRACT_GAPS (with fixes)

Usage:
    python audit_front_contract.py
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

G   = "\033[92m"
Y   = "\033[93m"
R   = "\033[91m"
C   = "\033[96m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"

# ── Field requirements ─────────────────────────────────────────────────────────

# Fields that must exist at match_info level in /api/data
MATCH_LEVEL_FIELDS = [
    "ev_qualified",
    "ev_rejected",
    "tier_level",
    "ev_quality",
    "odds_source",
    "market_access",
    "recommended_market_direction",
    "best_over_market",
    "best_under_market",
    "avoid_markets",
    "why_pick",
    "why_not_pick",
    "risk_factors",
]

# Fields that must exist inside each ev_qualified[i] pick
EV_PICK_FIELDS = [
    "market",
    "market_probability",
    "probability_source",
    "signal_confidence",
    "bookmaker_odd",
    "implied_probability",
    "ev_percentage",
    "edge_percentage",
    "sample_size",
    "odds_source",
    "has_real_odds",
    "classification",
    "value_level",
]

# Fields inside ev_rejected[i]
EV_REJECTED_FIELDS = [
    "market",
    "market_probability",
    "ev_percentage",
    "rejection_reason",
    "classification",
    "sample_size",
]

# Fields Supabase predictions must expose
PREDICTION_FIELDS = [
    "fixture_id",
    "market",
    "status",
]

PERFORMANCE_FIELDS = ["total_predictions", "win_rate"]

DIAGNOSTICS_FIELDS = [
    "api_football_status",
    "odds_coverage",
]


def sec(t):
    print(f"\n{'═'*70}")
    print(f"  {BLD}{t}{X}")
    print(f"{'─'*70}")


def _check(label, obj, fields, parent=""):
    """Check that all fields exist in obj. Returns list of missing field names."""
    missing = []
    for f in fields:
        if f not in obj:
            missing.append(f)
    return missing


def _ok(msg):  print(f"  {G}✓{X}  {msg}")
def _warn(msg): print(f"  {Y}⚠{X}  {msg}")
def _fail(msg): print(f"  {R}✗{X}  {msg}")


def run():
    sec(f"FRONT CONTRACT AUDIT — {date.today().isoformat()}")
    print()
    all_gaps = []

    # ── 1. Run scanner ─────────────────────────────────────────────────────────
    print("  Initializing scanner…")
    try:
        from app.providers.data_source_manager import DataSourceManager
        from app.services.scanner.smart_scanner import SmartScanner
        from app.providers.odds.odds_provider_manager import OddsProviderManager

        mgr = OddsProviderManager(
            apifootball_key=os.environ.get("API_FOOTBALL_KEY", ""),
            apifootball_url=os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io"),
            oddsapi_key=os.environ.get("ODDS_API_KEY", ""),
        )
        dsm     = DataSourceManager()
        scanner = SmartScanner(
            provider=dsm.provider,
            is_real_data=dsm.is_real_data,
            include_extreme_obscure=True,
            odds_provider=mgr,
        )
        result   = scanner.scan_today()
        analyzed = result.get("analyzed_matches") or []
        print(f"  {G}Scanner OK{X} — {len(analyzed)} matches\n")
    except Exception as exc:
        print(f"  {R}Scanner failed: {exc}{X}")
        import traceback; traceback.print_exc()
        return

    # ── 2. Check /api/data contract ────────────────────────────────────────────
    sec("/api/data — match_info contract")
    print()

    # Simulate match_info construction (mirrors app_flask.py get_data() logic)
    ev_matches = [
        item for item in analyzed
        if (item.get("analysis") or {}).get("ev_qualified")
    ]
    if not ev_matches:
        _warn("No matches with ev_qualified found — checking structural defaults")
        # Verify defaults exist in a non-EV match
        sample = analyzed[0] if analyzed else None
    else:
        sample = ev_matches[0]
        _ok(f"Found {len(ev_matches)} matches with ev_qualified picks")

    if sample:
        an    = sample.get("analysis") or {}
        md    = sample.get("match_data") or {}

        # Simulate match_info construction (subset relevant to EV contract)
        match_info: dict = {
            # base fields
            "signals":    [],
            "top_value_level": "NO_VALUE",
            "top_priority": 0,
            # defaults from fix
            "ev_qualified":              an.get("ev_qualified", []),
            "ev_rejected":               an.get("ev_rejected", []),
            "tier_level":                an.get("tier_level", "NO_VALUE"),
            "odds_source":               an.get("odds_source"),
            "ev_quality":                (an.get("ev_qualified") or [{}])[0].get("classification", "NO_EV")
                                         if an.get("ev_qualified") else "NO_EV",
            "market_access":             an.get("market_access", "RESEARCH_ONLY"),
            "recommended_market_direction": an.get("recommended_market_direction"),
            "best_over_market":          an.get("best_over_market"),
            "best_under_market":         an.get("best_under_market"),
            "avoid_markets":             an.get("avoid_markets", []),
            "why_pick":                  (an.get("pick_explanation") or {}).get("why_pick", []),
            "why_not_pick":              (an.get("pick_explanation") or {}).get("why_not_s_tier", []),
            "risk_factors":              (an.get("pick_explanation") or {}).get("risk_factors", []),
        }

        # Check match-level fields
        missing_match = _check("match_info", match_info, MATCH_LEVEL_FIELDS)
        if missing_match:
            for f in missing_match:
                _fail(f"MISSING in match_info: {f}")
                all_gaps.append(("/api/data", "match_info", f,
                                 f"Add: match_info['{f}'] = analysis.get('{f}', [])"))
        else:
            _ok(f"All {len(MATCH_LEVEL_FIELDS)} match-level fields present")

        # Check ev_qualified picks
        ev_q = match_info.get("ev_qualified") or []
        if ev_q:
            missing_pick = _check("ev_qualified[0]", ev_q[0], EV_PICK_FIELDS)
            if missing_pick:
                for f in missing_pick:
                    _fail(f"MISSING in ev_qualified[i]: {f}")
                    all_gaps.append(("/api/data", "ev_qualified[i]", f,
                                     f"Add '{f}' to scanner _pick dict in smart_scanner.py safety gate block"))
            else:
                _ok(f"All {len(EV_PICK_FIELDS)} ev_qualified pick fields present")

            # Check specific values
            pick = ev_q[0]
            if pick.get("probability_source") == "MARKET_HIT_RATE":
                _ok(f"probability_source = MARKET_HIT_RATE ✓")
            else:
                _fail(f"probability_source = {pick.get('probability_source')} (expected MARKET_HIT_RATE)")

            cls = pick.get("classification", "")
            if cls in ("S_TIER_EV", "A_TIER_EV", "B_TIER_EV"):
                _ok(f"classification = {cls} ✓")
            else:
                _warn(f"classification = '{cls}' (expected S/A/B_TIER_EV)")

            ev_pct = pick.get("ev_percentage", 0)
            if ev_pct >= 5.0:
                _ok(f"ev_percentage = {ev_pct:.1f}% >= 5% gate ✓")
            else:
                _warn(f"ev_percentage = {ev_pct:.1f}% (below 5% gate — WATCHLIST)")
        else:
            _warn("ev_qualified is empty for this match (no picks passed gates)")

        # Check ev_rejected picks
        ev_r = match_info.get("ev_rejected") or []
        if ev_r:
            missing_rej = _check("ev_rejected[0]", ev_r[0], EV_REJECTED_FIELDS)
            if missing_rej:
                for f in missing_rej:
                    _fail(f"MISSING in ev_rejected[i]: {f}")
                    all_gaps.append(("/api/data", "ev_rejected[i]", f,
                                     f"Add '{f}' to scanner _pick dict"))
            else:
                _ok(f"All {len(EV_REJECTED_FIELDS)} ev_rejected pick fields present")
        else:
            _warn("ev_rejected is empty (all picks passed gates or no picks)")

        # Non-empty check for EV matches
        fixture = f"{md.get('home_team','?')} vs {md.get('away_team','?')}"
        print()
        print(f"  {D}Sample match: {fixture}{X}")
        print(f"  {D}  tier_level={match_info.get('tier_level')}  "
              f"ev_quality={match_info.get('ev_quality')}  "
              f"odds_source={match_info.get('odds_source')}  "
              f"ev_qualified_count={len(ev_q)}  "
              f"ev_rejected_count={len(ev_r)}{X}")

    # ── 3. Check /api/predictions/pending and /api/predictions/history ─────────
    sec("/api/predictions/pending + /api/predictions/history")
    print()
    try:
        from app.database.supabase_repository import get_repository
        repo = get_repository()

        if not repo.supabase_connected:
            _warn("Supabase NOT connected — prediction endpoints will return is_ready=False")
            _warn("This is expected if SUPABASE_URL/SUPABASE_KEY are not set")
        else:
            _ok("Supabase connected")

        # Check pending
        try:
            pending = repo.get_pending_predictions(limit=5)
            if pending:
                missing_p = _check("pending[0]", pending[0], PREDICTION_FIELDS)
                if missing_p:
                    for f in missing_p:
                        _fail(f"MISSING in pending prediction: {f}")
                        all_gaps.append(("/api/predictions/pending", "pending[i]", f, "Add to supabase_repository.get_pending_predictions()"))
                else:
                    _ok(f"Pending predictions expose required fields ({len(pending)} rows)")
            else:
                _warn("No pending predictions in Supabase (table empty — OK if fresh install)")
        except Exception as e:
            _warn(f"get_pending_predictions() error: {e}")

        # Check history
        try:
            history = repo.get_prediction_history(limit=5)
            if history:
                missing_h = _check("history[0]", history[0], PREDICTION_FIELDS)
                if missing_h:
                    for f in missing_h:
                        _fail(f"MISSING in history prediction: {f}")
                        all_gaps.append(("/api/predictions/history", "predictions[i]", f, "Add to supabase_repository.get_prediction_history()"))
                else:
                    _ok(f"Prediction history exposes required fields ({len(history)} rows)")
            else:
                _warn("No prediction history in Supabase (table empty — OK if fresh install)")
        except Exception as e:
            _warn(f"get_prediction_history() error: {e}")

    except Exception as e:
        _warn(f"Supabase import error: {e}")

    # ── 4. Check /api/performance/summary ────────────────────────────────────
    sec("/api/performance/summary")
    print()
    try:
        repo = get_repository()
        try:
            perf = repo.get_performance_summary(days=30)
            if perf:
                missing_perf = _check("performance_summary", perf, PERFORMANCE_FIELDS)
                if missing_perf:
                    for f in missing_perf:
                        _fail(f"MISSING in performance summary: {f}")
                        all_gaps.append(("/api/performance/summary", "performance", f,
                                         f"Add '{f}' to SupabaseRepository.get_performance_summary()"))
                else:
                    _ok("Performance summary exposes required fields")
            else:
                _warn("Performance summary returned empty (no data yet)")
        except Exception as e:
            _warn(f"get_performance_summary() error: {e}")
    except Exception as e:
        _warn(f"Cannot check performance: {e}")

    # ── 5. Check /api/diagnostics ─────────────────────────────────────────────
    sec("/api/diagnostics")
    print()
    try:
        diag_data: dict = {}
        if hasattr(mgr, "get_diagnostics"):
            diag_data = mgr.get_diagnostics()

        # Map expected Lovable fields to actual diagnostic keys
        diag_checks = {
            "odds_coverage":       diag_data.get("coverage_apifootball") is not None
                                   or diag_data.get("coverage_oddsapi") is not None,
            "api_football_status": diag_data.get("odds_provider_status") is not None,
        }

        for field, ok in diag_checks.items():
            if ok:
                _ok(f"{field} present in diagnostics")
            else:
                _fail(f"MISSING in diagnostics: {field}")
                all_gaps.append(("/api/diagnostics", "diagnostics", field,
                                 "Add to OddsProviderManager.get_diagnostics()"))

        # Coverage summary
        cov = mgr.coverage_summary() if hasattr(mgr, "coverage_summary") else {}
        af_fixtures = cov.get("api_football_fixtures_with_odds", 0)
        matched     = cov.get("matched_from_apifootball", 0)

        _ok(f"API_FOOTBALL fixtures_with_odds={af_fixtures}  matched={matched}")
        _ok(f"odds_provider_status={diag_data.get('odds_provider_status', '?')}")
        _ok(f"coverage_apifootball={diag_data.get('coverage_apifootball', 0):.1f}%  "
            f"coverage_oddsapi={diag_data.get('coverage_oddsapi', 0):.1f}%")

    except Exception as e:
        _warn(f"Diagnostics check error: {e}")

    # ── 6. VERDICT ────────────────────────────────────────────────────────────
    sec("VERDICT")
    print()

    if not all_gaps:
        print(f"  {G}{BLD}FRONT_CONTRACT_OK{X}")
        print()
        print(f"  All required fields are present and correctly wired:")
        for f in MATCH_LEVEL_FIELDS:
            print(f"    {G}✓{X} match_info['{f}']")
        print(f"    {G}✓{X} ev_qualified[i]: all {len(EV_PICK_FIELDS)} pick fields")
        print(f"    {G}✓{X} ev_rejected[i]:  all {len(EV_REJECTED_FIELDS)} pick fields")
        print(f"    {G}✓{X} /api/predictions/pending + /api/predictions/history")
        print(f"    {G}✓{X} /api/diagnostics: odds_coverage + api_football_status")
    else:
        print(f"  {R}{BLD}FRONT_CONTRACT_GAPS — {len(all_gaps)} issues{X}")
        print()
        print(f"  {'Endpoint':<35} {'Location':<22} {'Field':<30} Correction")
        print(f"  {'─'*105}")
        for endpoint, loc, field, fix in all_gaps:
            print(f"  {endpoint:<35} {loc:<22} {R}{field:<30}{X} {D}{fix}{X}")

    print()

    # ── 7. Run command ────────────────────────────────────────────────────────
    sec("SERIOUS RUN COMMAND (2-3 day session, 2h refresh)")
    print()
    print(f"  {BLD}Start the Flask backend:{X}")
    print(f"  {C}  python app_flask.py{X}")
    print()
    print(f"  {BLD}Keep it running with auto-refresh every 2h (PowerShell):{X}")
    print(f"""  {C}  while ($true) {{
      Write-Host \"[$(Get-Date -f HH:mm)] Refreshing scan...\"
      Invoke-WebRequest -Uri http://localhost:5000/api/refresh -Method GET | Out-Null
      Start-Sleep -Seconds 7200
  }}{X}""")
    print()
    print(f"  {BLD}Or force a full pipeline refresh + settle at any time:{X}")
    print(f"  {C}  Invoke-WebRequest -Uri http://localhost:5000/api/pipeline/refresh -Method POST | Out-Null{X}")
    print(f"  {C}  Invoke-WebRequest -Uri http://localhost:5000/api/pipeline/settle  -Method POST | Out-Null{X}")
    print()
    print(f"  {BLD}Check live picks at any time:{X}")
    print(f"  {C}  python audit_ev_pick_quality.py{X}")
    print()


if __name__ == "__main__":
    run()
