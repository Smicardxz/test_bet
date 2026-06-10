"""
audit_probability_persistence.py
==================================
Checks last 100 API_FOOTBALL rows for probability scale correctness.

Rules:
  bookmaker_odd       >= 1.1           (required for real odds rows)
  market_probability  BETWEEN 0 AND 1  (fraction, not percentage)
  implied_probability BETWEEN 0 AND 1  (fraction, not percentage)
  ev_percentage       any float        (percentage points, allowed > 1)
  edge_percentage     any float        (percentage points, allowed > 1)

Output:
  PROBABILITY_PERSISTENCE_OK   — if no invalid rows
  PROBABILITY_PERSISTENCE_FAIL — with invalid row details + SQL fix

Usage:
  python audit_probability_persistence.py
  python audit_probability_persistence.py --fix   # emit SQL to fix DB rows
"""

import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def _ok(m):   print(f"  {GREEN}✓{RESET}  {m}")
def _err(m):  print(f"  {RED}✗{RESET}  {m}")
def _warn(m): print(f"  {YELLOW}⚠{RESET}  {m}")
def _info(m): print(f"  {CYAN}→{RESET}  {m}")


# ── Rules ─────────────────────────────────────────────────────────────────────

RULES = {
    # column: (min_allowed, max_allowed, can_be_null, description)
    "market_probability":  (0.0, 1.0,   True,  "fraction 0-1"),
    "implied_probability": (0.0, 1.0,   True,  "fraction 0-1"),
    "ev_percentage":       (None, None,  True,  "percentage, any float OK"),
    "edge_percentage":     (None, None,  True,  "percentage, any float OK"),
    "bookmaker_odd":       (1.1,  None,  False, ">= 1.1"),
}

def _check_row(row: dict) -> list:
    """Return list of (column, value, expected, reason) for each violation."""
    violations = []
    for col, (lo, hi, can_null, desc) in RULES.items():
        val = row.get(col)
        if val is None:
            if not can_null:
                violations.append((col, None, desc, "NULL not allowed"))
            continue
        try:
            fval = float(val)
        except (TypeError, ValueError):
            violations.append((col, val, desc, "not a number"))
            continue
        if lo is not None and fval < lo:
            violations.append((col, fval, desc, f"< {lo}"))
        if hi is not None and fval > hi:
            violations.append((col, fval, desc, f"> {hi}"))
    return violations


def _fix_value(col: str, val: float) -> float:
    """Return corrected value for a column with a scale issue."""
    if col in ("market_probability", "implied_probability") and val > 1.0:
        return round(val / 100.0, 4)
    return val


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true",
                        help="Emit SQL UPDATE statements to correct invalid rows")
    parser.add_argument("--limit", type=int, default=100,
                        help="Number of API_FOOTBALL rows to check (default 100)")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PROBABILITY PERSISTENCE AUDIT{RESET}")
    print(f"{'═'*66}")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Fetch rows ────────────────────────────────────────────────────────────
    print(f"\n{BOLD}── Fetching last {args.limit} API_FOOTBALL rows {'─'*20}{RESET}")
    try:
        rows = (
            repo._client.table("predictions")
            .select(
                "prediction_id, fixture_id, home_team, away_team, market, "
                "prediction_date, bookmaker_odd, market_probability, "
                "implied_probability, ev_percentage, edge_percentage"
            )
            .eq("odds_source", "API_FOOTBALL")
            .order("prediction_date", desc=True)
            .limit(args.limit)
            .execute()
        ).data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} API_FOOTBALL rows")
    if not rows:
        _warn("No API_FOOTBALL rows found — run a scan first, then re-audit")
        print(f"\n{BOLD}{YELLOW}  PROBABILITY_PERSISTENCE_OK = N/A (no rows){RESET}\n")
        sys.exit(0)

    # ── Per-row analysis ──────────────────────────────────────────────────────
    total       = len(rows)
    valid       = 0
    invalid_rows = []
    sql_fixes   = []

    for row in rows:
        violations = _check_row(row)
        if violations:
            invalid_rows.append((row, violations))
            for col, val, expected, reason in violations:
                if val is not None and col in ("market_probability", "implied_probability") and float(val) > 1.0:
                    fixed = _fix_value(col, float(val))
                    sql_fixes.append(
                        f"UPDATE predictions SET {col} = {fixed} "
                        f"WHERE prediction_id = '{row['prediction_id']}';"
                    )
        else:
            valid += 1

    # ── Summary stats ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}── Results {'─'*54}{RESET}")
    _info(f"Total rows checked  : {total}")
    if valid == total:
        _ok(f"Valid rows          : {valid} / {total}  (100%)")
    else:
        _ok(f"Valid rows          : {valid} / {total}")
        _err(f"Invalid rows        : {len(invalid_rows)} / {total}")

    # ── Per-column stats ──────────────────────────────────────────────────────
    print(f"\n  {DIM}Per-column stats:{RESET}")
    for col, (lo, hi, can_null, desc) in RULES.items():
        vals = [float(r.get(col)) for r in rows
                if r.get(col) is not None]
        null_count = sum(1 for r in rows if r.get(col) is None)
        if not vals:
            print(f"    {col:<26}: all NULL ({null_count})")
            continue
        mn, mx, av = min(vals), max(vals), sum(vals) / len(vals)
        scale_ok = True
        if lo is not None and mx > hi if hi is not None else False:
            scale_ok = False
        if hi is not None and mx > hi:
            scale_ok = False
        flag = f"{GREEN}OK{RESET}" if scale_ok else f"{RED}SCALE_ERR{RESET}"
        print(f"    {col:<26}: min={mn:.4f}  max={mx:.4f}  avg={av:.4f}  null={null_count}  {flag}")

    # ── Invalid row detail ────────────────────────────────────────────────────
    if invalid_rows:
        print(f"\n{BOLD}── Invalid rows (first 10) {'─'*38}{RESET}")
        for row, violations in invalid_rows[:10]:
            match = f"{row.get('home_team','?')} v {row.get('away_team','?')}"
            print(f"\n  {DIM}{match}  |  {row.get('market')}  |  date={row.get('prediction_date')}{RESET}")
            for col, val, expected, reason in violations:
                fixed = _fix_value(col, float(val)) if val is not None else "N/A"
                print(f"    {RED}✗{RESET} {col:<28}: {val}  (expected {expected}: {reason}  → fix={fixed})")

    # ── SQL fix output ────────────────────────────────────────────────────────
    if args.fix and sql_fixes:
        print(f"\n{BOLD}── SQL fixes (paste in Supabase SQL Editor) {'─'*20}{RESET}")
        print(f"\n  -- Fix {len(sql_fixes)} rows with incorrect probability scale")
        for stmt in sql_fixes[:50]:
            print(f"  {stmt}")
        if len(sql_fixes) > 50:
            print(f"  -- ... and {len(sql_fixes) - 50} more (run with --limit to see all)")
        # Also emit a bulk fix
        print(f"""
  -- ── Bulk back-fill fix (safer, run this instead of per-row fixes) ─────────
  UPDATE predictions
    SET market_probability  = ROUND((market_probability  / 100.0)::NUMERIC, 4)
  WHERE odds_source = 'API_FOOTBALL'
    AND market_probability IS NOT NULL
    AND market_probability > 1.0;

  UPDATE predictions
    SET implied_probability = ROUND((implied_probability / 100.0)::NUMERIC, 4)
  WHERE odds_source = 'API_FOOTBALL'
    AND implied_probability IS NOT NULL
    AND implied_probability > 1.0;""")
    elif not args.fix and sql_fixes:
        _warn(f"{len(sql_fixes)} rows need SQL fixes — re-run with --fix to emit SQL")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    if len(invalid_rows) == 0:
        print(f"{BOLD}{GREEN}  PROBABILITY_PERSISTENCE_OK{RESET}")
        _ok("All probability fields are correctly scaled")
    else:
        print(f"{BOLD}{RED}  PROBABILITY_PERSISTENCE_FAIL{RESET}")
        _err(f"{len(invalid_rows)} rows have invalid probability values")
        if not args.fix:
            _warn("Run with --fix to get SQL correction statements")
    print()
    sys.exit(0 if not invalid_rows else 1)


if __name__ == "__main__":
    main()
