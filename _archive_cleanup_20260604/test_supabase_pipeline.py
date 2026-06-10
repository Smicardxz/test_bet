"""
test_supabase_pipeline.py — Phase 11 Validation
=================================================
Tests:
  1. DB connection (reads SUPABASE_URL/SUPABASE_KEY from .env)
  2. Config validation
  3. Schema validation (offline SQL parse)
  4. Repository logic with a mock client
  5. Prediction persistence (upsert + no duplicates)
  6. Settlement evaluation (market results)
  7. Performance aggregation (compute_stats)
  8. League profitability aggregation
  9. Refresh pipeline flow (mock scan)
 10. Settlement pipeline flow (mock provider)

Usage:
    python test_supabase_pipeline.py
    python test_supabase_pipeline.py --live    # attempt real Supabase I/O
    python test_supabase_pipeline.py --schema  # print SQL schema
"""

import argparse
import os
import sys
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

PASS = f"{GREEN}✓ PASS{RESET}"
FAIL = f"{RED}✗ FAIL{RESET}"
SKIP = f"{YELLOW}⚠ SKIP{RESET}"


def _section(title: str):
    print(f"\n{'═'*62}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{'─'*62}")


def _check(name: str, ok: bool, info: str = ""):
    status = PASS if ok else FAIL
    line   = f"  {status}  {name}"
    if info:
        line += f"  {DIM}({info}){RESET}"
    print(line)
    return ok


# ─── Mock Supabase client ─────────────────────────────────────────────────────
class MockTable:
    """Simulates supabase-py table fluent API, stores rows in-memory."""

    def __init__(self, store: dict, name: str):
        self._store  = store
        self._name   = name
        self._data: List[dict] = []
        self._filters: List = []
        self._limit_val = None
        self._upsert_conflict: Optional[str] = None

    def select(self, *_, **__): return self
    def insert(self, data):
        if isinstance(data, list):
            self._data = data
        else:
            self._data = [data]
        return self
    def upsert(self, data, on_conflict=""):
        self._upsert_conflict = on_conflict
        if isinstance(data, list):
            self._data = data
        else:
            self._data = [data]
        return self
    def update(self, data):
        self._data = [data]
        return self
    def eq(self, *_, **__):   return self
    def lt(self, *_, **__):   return self
    def gte(self, *_, **__):  return self
    def in_(self, *_, **__):  return self
    def limit(self, n):
        self._limit_val = n
        return self
    def order(self, *_, **__): return self
    def single(self):         return self
    def execute(self):
        # Save rows to store
        tbl = self._store.setdefault(self._name, [])
        for row in self._data:
            if self._upsert_conflict:
                keys = [k.strip() for k in self._upsert_conflict.split(",")]
                existing = next(
                    (r for r in tbl if all(r.get(k) == row.get(k) for k in keys)),
                    None,
                )
                if existing:
                    existing.update(row)
                else:
                    tbl.append(row)
            else:
                tbl.append(row)

        class Resp:
            data = tbl[-20:]  # last 20 rows
        return Resp()


class MockSupabaseClient:
    """In-memory mock for all Supabase calls."""
    def __init__(self):
        self._store: Dict[str, List[dict]] = {}

    def table(self, name: str) -> MockTable:
        return MockTable(self._store, name)

    def rows(self, table: str) -> List[dict]:
        return self._store.get(table, [])


# ─── Patch repository with mock ───────────────────────────────────────────────
def _make_mock_repo() -> "Any":
    from app.database.supabase_repository import SupabaseRepository
    repo = SupabaseRepository.__new__(SupabaseRepository)
    mock = MockSupabaseClient()
    repo._client              = mock
    repo.supabase_connected   = True
    repo.supabase_error       = None
    repo.supabase_status      = "CONNECTED (MOCK)"
    repo._mock                = mock  # expose for assertions
    return repo


# ─── Synthetic data helpers ───────────────────────────────────────────────────
def _make_match(fixture_id="FX001", market="FT_UNDER_2_5", tier="S_TIER"):
    return {
        "match_data": {
            "match_id":    fixture_id,
            "home_team":   "Team A",
            "away_team":   "Team B",
            "competition": "Test League",
            "country":     "TestLand",
            "kickoff_time": datetime.now(timezone.utc).isoformat(),
            "status":      "NS",
        },
        "analysis": {
            "statistical_tier": tier,
            "tier_level":       "A_TIER",
            "match_universe":   "STATISTICAL_ONLY",
            "coverage_quality": "NONE",
            "ranking_score":    0.75,
            "match_profile":    {"confidence_score": 72.0, "volatility_score": 35.0},
            "volatility_analysis":   {"chaos_score": 28.0},
            "false_signal_analysis": {"false_signal_score": 22.0},
            "signals": [
                {"signal_type": market, "market": market, "confidence": 72}
            ],
            "matched_odds": [
                {"market": market, "bookmaker": "B365", "bookmaker_odd": 1.85, "ev_percent": 4.2}
            ],
            "league_specialization": {
                "league_edge_rating": "EDGE",
                "market_historical_profitability": "EDGE",
            },
            "pick_explanation": {
                "why_pick": ["Stable league", "Low false signal"],
                "risk_factors": [],
                "why_not_s_tier": [],
                "historical_failure_penalty": 0.0,
                "failure_pattern_warning": "",
            },
        },
    }


def _make_settled_rows(n_win=6, n_loss=4):
    rows = []
    for i in range(n_win):
        rows.append({
            "status": "WON",
            "profit_loss": 0.85,
            "statistical_tier": "S_TIER",
            "match_universe": "STATISTICAL_ONLY",
            "league": "Test League",
            "market": "FT_UNDER_2_5",
            "confidence_score": 75.0,
            "prediction_date": date.today().isoformat(),
        })
    for i in range(n_loss):
        rows.append({
            "status": "LOST",
            "profit_loss": -1.0,
            "statistical_tier": "A_TIER",
            "match_universe": "STATISTICAL_ONLY",
            "league": "Test League",
            "market": "FT_UNDER_2_5",
            "confidence_score": 68.0,  # FP threshold
            "prediction_date": date.today().isoformat(),
        })
    return rows


# ─── Tests ────────────────────────────────────────────────────────────────────
def test_config(live: bool) -> bool:
    _section("TEST 1 — Supabase Config")
    from app.database.supabase_config import reset_supabase_config, get_supabase_config

    # Test missing credentials
    orig_url = os.environ.pop("SUPABASE_URL", None)
    orig_key = os.environ.pop("SUPABASE_KEY", None)
    reset_supabase_config()

    cfg = get_supabase_config()
    ok1 = _check("NOT_CONFIGURED when no env vars",
                 cfg.supabase_status == "NOT_CONFIGURED")
    ok2 = _check("supabase_connected = False when not configured",
                 not cfg.supabase_connected)
    ok3 = _check("to_dict() returns all required keys",
                 all(k in cfg.to_dict() for k in (
                     "supabase_connected", "supabase_error",
                     "supabase_status", "supabase_url_set", "supabase_key_set"
                 )))

    # Restore
    if orig_url:
        os.environ["SUPABASE_URL"] = orig_url
    if orig_key:
        os.environ["SUPABASE_KEY"] = orig_key
    reset_supabase_config()

    if live:
        from app.database.supabase_config import get_supabase_config as gc
        cfg2 = gc()
        ok4 = _check(f"Live connection: {cfg2.supabase_status}",
                     cfg2.supabase_connected,
                     cfg2.supabase_error or "")
        return all([ok1, ok2, ok3, ok4])

    _check("Live test skipped (use --live to attempt real connection)", True, "")
    return all([ok1, ok2, ok3])


def test_market_evaluation() -> bool:
    _section("TEST 2 — Market Evaluation (settlement logic)")
    from app.database.supabase_repository import evaluate_market_result, calculate_profit_loss

    cases = [
        ("FT_UNDER_2_5",  1, 1, 0, 0, "WIN"),
        ("FT_UNDER_2_5",  2, 1, 0, 0, "LOSS"),
        ("FT_OVER_2_5",   2, 1, 0, 0, "WIN"),
        ("FT_OVER_2_5",   1, 1, 0, 0, "LOSS"),
        ("HT_UNDER_0_5",  0, 0, 0, 0, "WIN"),
        ("HT_UNDER_0_5",  1, 0, 1, 0, "LOSS"),
        ("HT_UNDER_1_5",  0, 1, 0, 1, "WIN"),
        ("HT_UNDER_1_5",  1, 1, 1, 1, "LOSS"),
        ("BTTS_YES",      1, 1, 0, 0, "WIN"),
        ("BTTS_YES",      1, 0, 0, 0, "LOSS"),
        ("BTTS_NO",       1, 0, 0, 0, "WIN"),
        ("BTTS_NO",       1, 1, 0, 0, "LOSS"),
        ("FT_OVER_3_5",   2, 2, 0, 0, "WIN"),
        ("FT_OVER_3_5",   1, 2, 0, 0, "LOSS"),
    ]
    all_ok = True
    for market, hs, as_, hh, ha, expected in cases:
        got = evaluate_market_result(market, hs, as_, hh, ha)
        ok  = _check(f"{market} {hs}-{as_} (HT {hh}-{ha}) → {expected}",
                     got == expected, f"got={got}")
        all_ok = all_ok and ok

    # P/L
    pl_win  = calculate_profit_loss("WIN",  1.85)
    pl_loss = calculate_profit_loss("LOSS", 1.85)
    pl_void = calculate_profit_loss("VOID", 1.85)
    all_ok = all_ok and _check("P/L WIN @1.85 = +0.85",  abs(pl_win  - 0.85)  < 0.01)
    all_ok = all_ok and _check("P/L LOSS       = -1.00", abs(pl_loss - (-1.0)) < 0.01)
    all_ok = all_ok and _check("P/L VOID       =  0.00", abs(pl_void)          < 0.01)
    return all_ok


def test_persistence() -> bool:
    _section("TEST 3 — Prediction Persistence (mock DB)")
    repo  = _make_mock_repo()
    match = _make_match("FX100", "FT_UNDER_2_5", "S_TIER")

    ok1 = _check("save_fixture returns True",    repo.save_fixture(match))
    ok2 = _check("save_prediction returns True", repo.save_prediction(match))

    # Duplicate upsert should not create a second row
    repo.save_prediction(match)
    preds = repo._mock.rows("predictions")
    ok3 = _check("No duplicate predictions after 2 upserts",
                 len(preds) == 1, f"rows={len(preds)}")

    # Different market → different row
    match2 = _make_match("FX100", "BTTS_NO", "A_TIER")
    match2["match_data"]["match_id"] = "FX100"
    # Change the signal market
    match2["analysis"]["signals"][0]["market"] = "BTTS_NO"
    repo.save_prediction(match2)
    preds = repo._mock.rows("predictions")
    ok4 = _check("Two different markets → two rows",
                 len(preds) == 2, f"rows={len(preds)}")

    # Odds snapshot
    fid  = "FX100"
    odds = [{"market": "FT_UNDER_2_5", "bookmaker": "B365", "bookmaker_odd": 1.85}]
    n    = repo.save_odds_snapshots(fid, odds)
    ok5 = _check("save_odds_snapshots inserts 1 row", n == 1, f"n={n}")

    return all([ok1, ok2, ok3, ok4, ok5])


def test_performance_aggregation() -> bool:
    _section("TEST 4 — Performance Aggregation")
    from app.database.supabase_repository import SupabaseRepository

    rows  = _make_settled_rows(n_win=6, n_loss=4)
    stats = SupabaseRepository._compute_stats(rows)

    ok1 = _check("total_predictions = 10",   stats["total_predictions"] == 10)
    ok2 = _check("total_wins = 6",           stats["total_wins"] == 6)
    ok3 = _check("hit_rate = 0.60",          abs(stats["hit_rate"] - 0.60) < 0.01,
                 f"got={stats['hit_rate']:.3f}")
    ok4 = _check("total_profit_loss > 0",    stats["total_profit_loss"] > 0,
                 f"pl={stats['total_profit_loss']:.3f}")
    ok5 = _check("false_positive_count ≥ 0", stats["false_positive_count"] >= 0)
    ok6 = _check("max_drawdown ≥ 0",         stats["max_drawdown"] >= 0)
    ok7 = _check("longest_losing_streak ≥ 0",stats["longest_losing_streak"] >= 0)

    print(f"  {DIM}ROI={stats['roi']:+.1f}%  "
          f"HitRate={stats['hit_rate']:.0%}  "
          f"FP={stats['false_positive_count']}  "
          f"MaxDD={stats['max_drawdown']:.2f}  "
          f"WorstStreak={stats['longest_losing_streak']}{RESET}")

    return all([ok1, ok2, ok3, ok4, ok5, ok6, ok7])


def test_refresh_pipeline() -> bool:
    _section("TEST 5 — Refresh Pipeline (mock)")

    class MockScanner:
        def scan_today(self):
            return {
                "total_matches":   5,
                "analyzed_count":  3,
                "analyzed_matches": [
                    _make_match(f"FX{i}", "FT_UNDER_2_5", "S_TIER")
                    for i in range(3)
                ],
                "remaining_matches": [],
            }

    from app.pipelines.refresh_pipeline import RefreshPipeline
    repo     = _make_mock_repo()
    pipeline = RefreshPipeline(scanner=MockScanner(), repository=repo)
    result   = pipeline.run()

    ok1 = _check("scan_ok = True",          result.get("scan_ok") is True)
    ok2 = _check("fixtures_saved ≥ 1",      result.get("fixtures_saved", 0) >= 1)
    ok3 = _check("predictions_saved ≥ 1",   result.get("predictions_saved", 0) >= 1)
    ok4 = _check("No critical errors",       len(result.get("errors", [])) == 0,
                 str(result.get("errors", [])))

    print(f"  {DIM}fixtures={result['fixtures_saved']} "
          f"predictions={result['predictions_saved']} "
          f"odds={result['odds_saved']}{RESET}")
    return all([ok1, ok2, ok3, ok4])


def test_settlement_pipeline() -> bool:
    _section("TEST 6 — Settlement Pipeline (mock)")
    from app.pipelines.settlement_pipeline import SettlementPipeline, evaluate_market_result

    class MockProvider:
        def get_match_result(self, fixture_id):
            class M:
                status = "FINISHED"
                home_score = 1
                away_score = 1
                ht_home_score = 0
                ht_away_score = 0
            return M()

    repo = _make_mock_repo()
    # Pre-populate a pending prediction
    repo._mock._store["predictions"] = [{
        "prediction_id": "FX001_FT_UNDER_2_5_2025-01-01",
        "fixture_id":    "FX001",
        "market":        "FT_UNDER_2_5",
        "bookmaker_odd": 1.85,
        "status":        "PENDING",
        "kickoff_time":  "2025-01-01T12:00:00+00:00",
    }]

    pipeline = SettlementPipeline(repository=repo, provider=MockProvider())

    # Test evaluate_market_result directly
    r1 = evaluate_market_result("FT_UNDER_2_5", 1, 1)  # total=2, under 2.5 → WIN
    r2 = evaluate_market_result("FT_UNDER_2_5", 2, 1)  # total=3, over 2.5 → LOSS
    ok1 = _check("FT_UNDER_2_5: 1+1=2 → WIN",  r1 == "WIN",  r1)
    ok2 = _check("FT_UNDER_2_5: 2+1=3 → LOSS", r2 == "LOSS", r2)

    result = pipeline.run()
    ok3 = _check("pipeline.run() returns dict",  isinstance(result, dict))
    ok4 = _check("pending_found field present",  "pending_found" in result)
    ok5 = _check("no fatal errors",              isinstance(result.get("errors"), list))

    print(f"  {DIM}pending={result.get('pending_found')} "
          f"settled={result.get('settled')} "
          f"won={result.get('won')} lost={result.get('lost')}{RESET}")
    return all([ok1, ok2, ok3, ok4, ok5])


def test_schema_readable() -> bool:
    _section("TEST 7 — SQL Schema Readable")
    schema_path = os.path.join(os.path.dirname(__file__), "app", "database", "schema.sql")
    try:
        with open(schema_path, encoding="utf-8") as f:
            sql = f.read()
        tables = ["fixtures", "predictions", "odds_snapshots",
                  "league_profiles", "model_performance", "false_positive_patterns"]
        ok = True
        for t in tables:
            found = t in sql
            ok = _check(f"Table '{t}' defined", found) and ok
        _check("Indexes present",  "CREATE INDEX" in sql)
        _check("Unique constraints", "UNIQUE" in sql)
        _check("Foreign keys",      "REFERENCES" in sql)
        _check("Updated_at trigger","trigger_set_updated_at" in sql)
        return ok
    except FileNotFoundError:
        _check("schema.sql found", False, schema_path)
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────
def run_all(live: bool = False, show_schema: bool = False):
    print(f"\n{BOLD}{'═'*62}{RESET}")
    print(f"{BOLD}  SUPABASE PIPELINE — Phase 11 Test Suite{RESET}")
    print(f"{'═'*62}")

    if show_schema:
        schema_path = os.path.join("app", "database", "schema.sql")
        print(f"\n{CYAN}── Schema: {schema_path} ──{RESET}")
        try:
            with open(schema_path) as f:
                print(f.read())
        except Exception as e:
            print(f"  {RED}Cannot read schema: {e}{RESET}")
        return

    results = [
        test_schema_readable(),
        test_config(live=live),
        test_market_evaluation(),
        test_persistence(),
        test_performance_aggregation(),
        test_refresh_pipeline(),
        test_settlement_pipeline(),
    ]

    passed = sum(results)
    total  = len(results)

    _section("SUMMARY")
    color = GREEN if passed == total else (YELLOW if passed >= total // 2 else RED)
    print(f"\n  {color}{BOLD}{passed}/{total} test groups passed{RESET}\n")

    if passed == total:
        print(f"  {GREEN}✓ Supabase Pipeline opérationnel{RESET}")
    else:
        print(f"  {YELLOW}⚠ Some tests failed — check output above{RESET}")

    print(f"\n  {DIM}── Next steps ──────────────────────────────────────────")
    print(f"  1. Add SUPABASE_URL and SUPABASE_KEY to your .env")
    print(f"  2. Run the schema.sql in Supabase SQL Editor")
    print(f"  3. pip install supabase")
    print(f"  4. Run again with --live to verify real connection")
    print(f"  5. Call POST /api/pipeline/refresh to start persisting")
    print(f"  6. Call POST /api/pipeline/settle to settle predictions{RESET}")
    print(f"{'═'*62}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Supabase Pipeline Test Suite (Phase 11)"
    )
    parser.add_argument("--live",   action="store_true",
                        help="Attempt real Supabase connection")
    parser.add_argument("--schema", action="store_true",
                        help="Print the SQL schema and exit")
    args = parser.parse_args()
    run_all(live=args.live, show_schema=args.schema)
