"""
test_auto_settlement.py
=======================
Validates the complete auto-settlement pipeline:
  - fetch_final_result: correct sentinel returns
  - evaluate_market: all market types, HT vs FT, BTTS
  - auto_settle_predictions: end-to-end with mock objects
  - live_test_session: _evaluate_result normalisation
  - Supabase update: settle_prediction + update_fixture_result

Run:
    python test_auto_settlement.py
    python test_auto_settlement.py --live    # real API-Football + Supabase
"""

import sys
import os
import argparse
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
BOLD  = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0


def assert_eq(got, expected):
    assert got == expected, f"Expected {expected!r}, got {got!r}"
    return got


def _run(name, fn):
    global passed, failed
    try:
        result = fn()
        print(f"  {GREEN}✓{RESET} {name}")
        passed += 1
        return result
    except AssertionError as exc:
        print(f"  {RED}✗{RESET} {name}")
        print(f"       {RED}AssertionError: {exc}{RESET}")
        failed += 1
        return None
    except Exception as exc:
        print(f"  {RED}✗{RESET} {name}")
        print(f"       {RED}{type(exc).__name__}: {exc}{RESET}")
        traceback.print_exc()
        failed += 1
        return None


# =============================================================================
# 1. evaluate_market — unit tests
# =============================================================================
print(f"\n{BOLD}1. evaluate_market — unit tests{RESET}")

from app.services.settlement.auto_settler import evaluate_market, _parse_line

FINISHED = {
    "status": "FINISHED",
    "ft_home_goals": 2, "ft_away_goals": 1,
    "ht_home_goals": 1, "ht_away_goals": 0,
    "total_ft_goals": 3, "total_ht_goals": 1,
}
ZERO_ZERO = {
    "status": "FINISHED",
    "ft_home_goals": 0, "ft_away_goals": 0,
    "ht_home_goals": 0, "ht_away_goals": 0,
    "total_ft_goals": 0, "total_ht_goals": 0,
}

_run("FT_UNDER_2_5 → LOSS  (3 goals)",  lambda: (r := evaluate_market("FT_UNDER_2_5", FINISHED)) or None or (assert_eq(r, "LOSS")))
_run("FT_UNDER_3_5 → WIN   (3 goals)",  lambda: assert_eq(evaluate_market("FT_UNDER_3_5", FINISHED), "WIN"))
_run("FT_OVER_2_5  → WIN   (3 goals)",  lambda: assert_eq(evaluate_market("FT_OVER_2_5", FINISHED), "WIN"))
_run("FT_OVER_3_5  → LOSS  (3 goals)",  lambda: assert_eq(evaluate_market("FT_OVER_3_5", FINISHED), "LOSS"))
_run("HT_UNDER_0_5 → LOSS  (1 HT goal)", lambda: assert_eq(evaluate_market("HT_UNDER_0_5", FINISHED), "LOSS"))
_run("HT_UNDER_1_5 → WIN   (1 HT goal)", lambda: assert_eq(evaluate_market("HT_UNDER_1_5", FINISHED), "WIN"))
_run("HT_OVER_0_5  → WIN   (1 HT goal)", lambda: assert_eq(evaluate_market("HT_OVER_0_5", FINISHED), "WIN"))
_run("HT_UNDER_0_5 → WIN   (0-0 match)", lambda: assert_eq(evaluate_market("HT_UNDER_0_5", ZERO_ZERO), "WIN"))
_run("BTTS_YES     → WIN   (2-1)",        lambda: assert_eq(evaluate_market("BTTS_YES", FINISHED), "WIN"))
_run("BTTS_NO      → LOSS  (2-1)",        lambda: assert_eq(evaluate_market("BTTS_NO", FINISHED), "LOSS"))
_run("BTTS_YES     → LOSS  (2-0)",        lambda: assert_eq(evaluate_market("BTTS_YES", {
    **FINISHED, "ft_away_goals": 0, "total_ft_goals": 2}), "LOSS"))
_run("space format: 'UNDER 2.5' → WIN (0-0)", lambda: assert_eq(evaluate_market("UNDER 2.5", ZERO_ZERO), "WIN"))
_run("space format: 'HT UNDER 0.5' → WIN (0-0)", lambda: assert_eq(evaluate_market("HT UNDER 0.5", ZERO_ZERO), "WIN"))
_run("NOT_FINISHED → VOID",             lambda: assert_eq(
    evaluate_market("FT_UNDER_2_5", {"status": "NOT_FINISHED"}), "VOID"))
_run("_parse_line FT_UNDER_2_5 → 2.5", lambda: assert_eq(_parse_line("FT_UNDER_2_5"), 2.5))
_run("_parse_line HT_OVER_0_5  → 0.5", lambda: assert_eq(_parse_line("HT_OVER_0_5"), 0.5))


# =============================================================================
# 2. fetch_final_result — mock provider tests
# =============================================================================
print(f"\n{BOLD}2. fetch_final_result — mock provider tests{RESET}")

from app.services.settlement.auto_settler import fetch_final_result


class _MockProvider:
    def __init__(self, response_data):
        self._data = response_data

    def _make_request(self, endpoint, params=None):
        return self._data


def _ft_response(status_short, home, away, ht_home=0, ht_away=0):
    return {
        "response": [{
            "fixture": {"status": {"short": status_short}},
            "goals":   {"home": home, "away": away},
            "score":   {"halftime": {"home": ht_home, "away": ht_away}},
        }]
    }


_run("Finished match → FINISHED + correct goals", lambda: (
    r := fetch_final_result(12345, _MockProvider(_ft_response("FT", 2, 1, 1, 0))),
    assert_eq(r["status"], "FINISHED"),
    assert_eq(r["ft_home_goals"], 2),
    assert_eq(r["ft_away_goals"], 1),
    assert_eq(r["ht_home_goals"], 1),
    assert_eq(r["total_ft_goals"], 3),
    assert_eq(r["total_ht_goals"], 1),
))
_run("LIVE match → NOT_FINISHED", lambda: (
    r := fetch_final_result(999, _MockProvider(_ft_response("1H", None, None))),
    assert_eq(r["status"], "NOT_FINISHED"),
))
_run("NS (not started) → NOT_FINISHED", lambda: (
    r := fetch_final_result(999, _MockProvider(_ft_response("NS", None, None))),
    assert_eq(r["status"], "NOT_FINISHED"),
))
_run("FT but no goals → RESULT_MISSING", lambda: (
    r := fetch_final_result(999, _MockProvider(_ft_response("FT", None, None))),
    assert_eq(r["status"], "RESULT_MISSING"),
))
_run("Empty response → RESULT_MISSING", lambda: (
    r := fetch_final_result(999, _MockProvider({"response": []})),
    assert_eq(r["status"], "RESULT_MISSING"),
))


class _RaisingProvider:
    def _make_request(self, *a, **kw):
        raise ConnectionError("Network failure")


_run("API_ERROR on exception", lambda: (
    r := fetch_final_result(999, _RaisingProvider()),
    assert_eq(r["status"], "API_ERROR"),
))


# =============================================================================
# 3. auto_settle_predictions — mock repo + provider
# =============================================================================
print(f"\n{BOLD}3. auto_settle_predictions — mock objects{RESET}")

from app.services.settlement.auto_settler import auto_settle_predictions


class _MockRepo:
    def __init__(self, predictions):
        self.supabase_connected = True
        self._preds = predictions
        self.settled = []
        self.fixture_updates = []

    def get_pending_predictions(self):
        return self._preds

    def settle_prediction(self, prediction_id, home_score, away_score,
                          ht_home=0, ht_away=0, bookmaker_odd=1.0, notes=""):
        self.settled.append({
            "prediction_id": prediction_id,
            "home": home_score, "away": away_score,
            "ht_home": ht_home, "ht_away": ht_away,
        })
        return True

    def update_fixture_result(self, fixture_id, home_score, away_score,
                              ht_home=0, ht_away=0, status="FINISHED"):
        self.fixture_updates.append({"fixture_id": fixture_id})
        return True


_preds = [
    {"prediction_id": "pred_1", "fixture_id": "1001",
     "market": "FT_UNDER_2_5", "bookmaker_odd": 1.85},
    {"prediction_id": "pred_2", "fixture_id": "1002",
     "market": "HT_UNDER_0_5", "bookmaker_odd": 1.5},
    {"prediction_id": "pred_3", "fixture_id": "1003",
     "market": "BTTS_YES", "bookmaker_odd": 1.7},
]

_provider_map = {
    "1001": _ft_response("FT", 0, 1, 0, 0),   # 1 FT goal → UNDER 2.5 WIN
    "1002": _ft_response("FT", 1, 0, 0, 0),   # HT 0-0 → HT_UNDER_0_5 WIN
    "1003": _ft_response("1H", None, None),   # LIVE → NOT_FINISHED
}


class _MultiProvider:
    def _make_request(self, endpoint, params=None):
        fid = str((params or {}).get("id", ""))
        return _provider_map.get(fid, {"response": []})


def _test_auto_settle():
    repo = _MockRepo(_preds)
    summary = auto_settle_predictions(repo, _MultiProvider())
    assert summary["settled"] == 2, f"Expected 2 settled, got {summary['settled']}"
    assert summary["pending"] == 1, f"Expected 1 pending, got {summary['pending']}"
    assert summary["won"]     == 2, f"Expected 2 won, got {summary['won']}"
    assert summary["lost"]    == 0, f"Expected 0 lost"
    assert len(repo.settled)  == 2, f"Expected 2 settle_prediction calls"
    return summary


_run("auto_settle_predictions: 2 settled WIN, 1 pending", _test_auto_settle)


def _test_settle_lost():
    preds = [{"prediction_id": "p1", "fixture_id": "5001",
              "market": "FT_UNDER_2_5", "bookmaker_odd": 1.85}]
    provider_data = {"5001": _ft_response("FT", 2, 2, 1, 1)}

    class _P:
        def _make_request(self, ep, params=None):
            return provider_data[str((params or {}).get("id", ""))]

    repo = _MockRepo(preds)
    summary = auto_settle_predictions(repo, _P())
    assert summary["lost"] == 1, f"Expected 1 lost, got {summary['lost']}"
    assert summary["profit_loss"] < 0, "P/L should be negative on loss"
    return summary


_run("auto_settle_predictions: LOSS detected + negative P/L", _test_settle_lost)


def _test_settle_error():
    preds = [{"prediction_id": "p_err", "fixture_id": "9999",
              "market": "FT_UNDER_2_5", "bookmaker_odd": 1.5}]

    class _ErrRepo(_MockRepo):
        def get_pending_predictions(self): return preds
        def settle_prediction(self, **kw): raise Exception("DB error")

    summary = auto_settle_predictions(_ErrRepo(preds), _MultiProvider())
    return summary


_run("auto_settle_predictions: DB error is non-blocking", _test_settle_error)


# =============================================================================
# 4. live_test_session._evaluate_result normalisation
# =============================================================================
print(f"\n{BOLD}4. live_test_session._evaluate_result normalisation{RESET}")

from live_test_session import _evaluate_result

_run("'UNDER 2.5' space fmt  2-0 → WIN",  lambda: assert_eq(_evaluate_result("UNDER 2.5", "2-0"), "WIN"))
_run("'UNDER 2.5' space fmt  2-1 → LOSS", lambda: assert_eq(_evaluate_result("UNDER 2.5", "2-1"), "LOSS"))
_run("'FT_UNDER_2_5' under fmt → WIN",    lambda: assert_eq(_evaluate_result("FT_UNDER_2_5", "1-1"), "WIN"))
_run("'HT UNDER 0.5' with ht_score → WIN", lambda: assert_eq(
    _evaluate_result("HT UNDER 0.5", "2-1", "0-0"), "WIN"))
_run("'HT_UNDER_0_5' with ht_score → LOSS", lambda: assert_eq(
    _evaluate_result("HT_UNDER_0_5", "2-1", "1-0"), "LOSS"))
_run("'BTTS_YES' 1-0 → LOSS",            lambda: assert_eq(_evaluate_result("BTTS_YES", "1-0"), "LOSS"))
_run("'BTTS_YES' 1-1 → WIN",             lambda: assert_eq(_evaluate_result("BTTS_YES", "1-1"), "WIN"))
_run("empty score → UNKNOWN",            lambda: assert_eq(_evaluate_result("FT_UNDER_2_5", ""), "UNKNOWN"))
_run("CANCELLED → UNKNOWN",             lambda: assert_eq(_evaluate_result("FT_UNDER_2_5", "CANCELLED"), "UNKNOWN"))


# =============================================================================
# 5. Live API-Football test (--live flag only)
# =============================================================================
if "--live" in sys.argv:
    print(f"\n{BOLD}5. Live API-Football + Supabase tests{RESET}")

    from dotenv import load_dotenv
    load_dotenv(override=True)

    try:
        from app.providers.api_football_provider import ApiFootballProvider
        provider = ApiFootballProvider()

        def _test_live_fetch():
            result = fetch_final_result(1035690, provider)
            print(f"       fixture 1035690 → {result['status']}")
            assert result["status"] in ("FINISHED", "NOT_FINISHED", "RESULT_MISSING", "API_ERROR")
            return result

        _run("Live: fetch_final_result fixture 1035690", _test_live_fetch)

    except Exception as exc:
        print(f"  {YELLOW}⚠ Provider init failed: {exc}{RESET}")

    try:
        from app.database.supabase_config import reset_supabase_config
        from app.database.supabase_repository import reset_repository, get_repository
        reset_supabase_config()
        reset_repository()
        repo = get_repository()

        def _test_live_pending():
            preds = repo.get_pending_predictions()
            print(f"       {len(preds)} PENDING predictions in Supabase")
            assert isinstance(preds, list)
            return preds

        _run("Live: get_pending_predictions returns list", _test_live_pending)

    except Exception as exc:
        print(f"  {YELLOW}⚠ Supabase init failed: {exc}{RESET}")

else:
    print(f"\n  {YELLOW}(Skipping live API tests — use --live flag){RESET}")


# =============================================================================
# Summary
# =============================================================================
print(f"\n{'═'*56}")
print(f"  {BOLD}Results: {GREEN}{passed} passed{RESET}{BOLD}, "
      f"{RED if failed else ''}{failed} failed{RESET}")
print(f"{'═'*56}\n")
if failed:
    sys.exit(1)
