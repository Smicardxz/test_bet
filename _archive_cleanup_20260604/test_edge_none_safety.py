"""
test_edge_none_safety.py
========================
Validates that EdgeDetector never raises TypeError on None values in
analysis tables or bookmaker odds dictionaries.

Run:
    python test_edge_none_safety.py
"""

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.analysis.edge_detector import EdgeDetector

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"

ed = EdgeDetector()
passed = 0
failed = 0


def _run(name, fn):
    global passed, failed
    try:
        result = fn()
        print(f"  {GREEN}✓{RESET} {name}")
        passed += 1
        return result
    except Exception as exc:
        print(f"  {RED}✗{RESET} {name}")
        print(f"       {RED}{exc}{RESET}")
        traceback.print_exc()
        failed += 1
        return None


print(f"\n{BOLD}EdgeDetector — None Safety Tests{RESET}\n")

# ─── 1. detect_ht_edges: fair_odd = None in table row ─────────────────────────
_run(
    "HT: fair_odd=None in table row → no crash",
    lambda: ed.detect_ht_edges(
        ht_goals=[0, 0, 1, 0, 0, 1, 0, 0],
        ht_analysis={"table": [
            {"line": "U0.5", "hit_rate": 75, "fair_odd": None, "sample_size": 8},
        ]},
    ),
)

# ─── 2. detect_ht_edges: hit_rate = None ──────────────────────────────────────
_run(
    "HT: hit_rate=None in table row → no crash",
    lambda: ed.detect_ht_edges(
        ht_goals=[0, 0, 1, 0, 0, 0, 0, 1],
        ht_analysis={"table": [
            {"line": "U0.5", "hit_rate": None, "fair_odd": 1.5, "sample_size": 8},
        ]},
    ),
)

# ─── 3. detect_ht_edges: sample_size = None ───────────────────────────────────
_run(
    "HT: sample_size=None in table row → no crash",
    lambda: ed.detect_ht_edges(
        ht_goals=[0, 1, 0, 0, 0, 0, 0, 1],
        ht_analysis={"table": [
            {"line": "U0.5", "hit_rate": 80, "fair_odd": 1.4, "sample_size": None},
        ]},
    ),
)

# ─── 4. detect_ht_edges: all None ─────────────────────────────────────────────
_run(
    "HT: all fields None → no crash, returns []",
    lambda: ed.detect_ht_edges(
        ht_goals=[0, 0, 0, 0, 0, 1, 0, 0],
        ht_analysis={"table": [
            {"line": "U0.5", "hit_rate": None, "fair_odd": None, "sample_size": None},
            {"line": "U1.5", "hit_rate": None, "fair_odd": None, "sample_size": None},
        ]},
    ),
)

# ─── 5. detect_ft_edges: fair_odd = None ──────────────────────────────────────
_run(
    "FT: fair_odd=None in table row → no crash",
    lambda: ed.detect_ft_edges(
        ft_goals=[1, 2, 0, 1, 2, 1, 0, 1, 2, 1],
        ft_analysis={"table": [
            {"line": "U2.5", "hit_rate": 70, "fair_odd": None, "sample_size": 10},
        ]},
    ),
)

# ─── 6. detect_ft_edges: hit_rate = None ──────────────────────────────────────
_run(
    "FT: hit_rate=None in table row → no crash",
    lambda: ed.detect_ft_edges(
        ft_goals=[1, 2, 0, 1, 2, 1, 0, 1, 2, 1],
        ft_analysis={"table": [
            {"line": "U2.5", "hit_rate": None, "fair_odd": 1.8, "sample_size": 10},
        ]},
    ),
)

# ─── 7. detect_all_edges: bookmaker_odds = None ───────────────────────────────
_run(
    "detect_all_edges: bookmaker_odds=None → no crash",
    lambda: ed.detect_all_edges(
        ht_goals=[0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        ft_goals=[1, 2, 0, 1, 2, 1, 0, 1, 2, 1],
        ht_analysis={"table": [
            {"line": "U0.5", "hit_rate": 80, "fair_odd": 1.4, "sample_size": 10},
        ]},
        ft_analysis={"table": [
            {"line": "U2.5", "hit_rate": 70, "fair_odd": 1.8, "sample_size": 10},
        ]},
        bookmaker_odds=None,
    ),
)

# ─── 8. detect_all_edges: bookmaker_odds with None values ─────────────────────
_run(
    "detect_all_edges: bookmaker_odds has None values → no crash",
    lambda: ed.detect_all_edges(
        ht_goals=[0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
        ft_goals=[1, 2, 0, 1, 2, 1, 0, 1, 2, 1],
        ht_analysis={"table": [
            {"line": "U0.5", "hit_rate": 80, "fair_odd": 1.4, "sample_size": 10},
        ]},
        ft_analysis={"table": [
            {"line": "U2.5", "hit_rate": 70, "fair_odd": 1.8, "sample_size": 10},
        ]},
        bookmaker_odds={"HT_U0.5": None, "FT_U2.5": None},
    ),
)

# ─── 9. select_best_edges: EdgeOpportunity with None fields ───────────────────
from app.services.analysis.edge_detector import EdgeOpportunity

def _test_select_none():
    edges = [
        EdgeOpportunity(
            market="HT UNDER 0.5", market_type="HT_UNDER",
            line=0.5, historical_probability=0.8,
            implied_probability=0.7, market_odd=None, fair_odd=None,
            edge_percent=None, edge_value=None,
            sample_size=None, hit_rate=80, confidence="HIGH",
            variance="LOW", reasons=[], avg_goals=0.2, max_goals=1,
        ),
    ]
    return ed.select_best_edges(edges)

_run("select_best_edges: None edge_percent / fair_odd → no crash", _test_select_none)

# ─── 10. Full pipeline: None table → empty list result ────────────────────────
def _test_empty_table():
    result = ed.detect_all_edges(
        ht_goals=[0, 0, 0, 0, 0, 0, 0, 0],
        ft_goals=[1, 0, 1, 0, 1, 0, 1, 0],
        ht_analysis={"table": []},
        ft_analysis={"table": []},
        bookmaker_odds=None,
    )
    best = result.get("best_edges", [])
    assert isinstance(best, list), f"Expected list, got {type(best)}"
    return best

_run("detect_all_edges: empty tables → returns empty best_edges list", _test_empty_table)


# ─── Summary ──────────────────────────────────────────────────────────────────
print(f"\n  {BOLD}Results: {GREEN}{passed} passed{RESET}{BOLD}, "
      f"{RED if failed else ''}{failed} failed{RESET}\n")
if failed:
    sys.exit(1)
