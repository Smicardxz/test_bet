"""
audit_shadow_tier_performance.py
=================================
Compares OLD tier vs SHADOW tier performance.

Metrics:
- count
- settled
- accuracy
- ROI
- avg odd
- avg EV

Output:
- old tier ranking
- shadow tier ranking
- whether shadow improves monotonicity

Success condition:
SHADOW_S accuracy >= SHADOW_A >= SHADOW_B >= SHADOW_WATCH
or at least SHADOW_S ROI > OLD_S ROI

Usage:
  python audit_shadow_tier_performance.py
"""

import os
import sys
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _ok(m):   print(f"  {GREEN}✓{RESET}  {m}")
def _err(m):  print(f"  {RED}✗{RESET}  {m}")
def _warn(m): print(f"  {YELLOW}⚠{RESET}  {m}")
def _info(m): print(f"  {CYAN}→{RESET}  {m}")


def _parse_reset_at() -> str:
    """Return TRACKING_RESET_AT exactly as set in env (full ISO datetime or date), or ''."""
    raw = os.environ.get("TRACKING_RESET_AT", "").strip()
    if not raw:
        return ""
    try:
        if "T" in raw:
            datetime.fromisoformat(raw.replace("Z", "+00:00"))  # validate
        else:
            from datetime import date as _date
            _date.fromisoformat(raw[:10])  # validate
        return raw
    except Exception:
        return ""


def _apply_since_filter(query, since_date: str):
    """Apply date/datetime filter to a Supabase query builder."""
    if not since_date:
        return query
    if "T" in since_date:
        return query.gte("created_at", since_date)
    return query.gte("prediction_date", since_date)


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  SHADOW TIER PERFORMANCE AUDIT{RESET}")
    print(f"{'═'*66}")

    reset_at = _parse_reset_at()
    if reset_at:
        _info(f"TRACKING_RESET_AT = {reset_at}")
    else:
        _warn("TRACKING_RESET_AT not set — using all predictions")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Fetch POST_RESET predictions with both tier systems ───────────────────
    print(f"\n{BOLD}── Fetching POST_RESET predictions {'─'*43}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "statistical_tier, ev_tier, shadow_tier, shadow_tier_score, "
                "status, bookmaker_odd, ev_percentage, market_probability, "
                "implied_probability, edge_percentage, confidence_score"
            )
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} POST_RESET predictions")

    if not rows:
        _warn("No predictions found")
        sys.exit(0)

    # Check if shadow tiers are populated
    shadow_populated = sum(1 for r in rows if r.get("shadow_tier"))
    if shadow_populated == 0:
        _warn("Shadow tiers not populated - run backfill_shadow_tiers.py first")
        sys.exit(1)

    _ok(f"Shadow tiers populated: {shadow_populated}/{len(rows)}")

    # ── Group by old tier (statistical_tier or ev_tier) ───────────────────────
    old_tier_data: Dict[str, list] = defaultdict(list)
    for r in rows:
        old_tier = (r.get("statistical_tier") or r.get("ev_tier") or "NO_VALUE").upper()
        old_tier_data[old_tier].append(r)

    # ── Group by shadow tier ───────────────────────────────────────────────────
    shadow_tier_data: Dict[str, list] = defaultdict(list)
    for r in rows:
        shadow_tier = r.get("shadow_tier") or "SHADOW_RESEARCH"
        shadow_tier_data[shadow_tier].append(r)

    # ── Compute metrics for old tiers ───────────────────────────────────────────
    print(f"\n{BOLD}── OLD TIER PERFORMANCE{RESET}")
    old_metrics = {}
    for tier in ["S_TIER", "A_TIER", "B_TIER", "WATCHLIST", "NO_VALUE"]:
        if tier not in old_tier_data:
            continue
        data = old_tier_data[tier]
        total = len(data)
        settled = [r for r in data if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        accuracy = len(wins) / len(settled) if settled else 0

        with_odd = [r for r in settled if r.get("bookmaker_odd")]
        if with_odd:
            pl = sum((1 if r.get("status") == "WON" else -1) * r.get("bookmaker_odd", 0) for r in with_odd)
            roi = pl / len(with_odd) * 100
            avg_odd = sum(r.get("bookmaker_odd", 0) for r in with_odd) / len(with_odd)
        else:
            pl = 0
            roi = 0
            avg_odd = 0

        avg_ev = sum(r.get("ev_percentage") or 0 for r in data) / len(data) if data else 0

        old_metrics[tier] = {
            "total": total,
            "settled": len(settled),
            "accuracy": accuracy,
            "roi": roi,
            "avg_odd": avg_odd,
            "avg_ev": avg_ev,
        }

        print(f"  {tier:<12}: total={total:>3}  settled={len(settled):>3}  "
              f"acc={accuracy*100:>5.1f}%  roi={roi:>6.1f}%  avg_odd={avg_odd:.2f}  avg_ev={avg_ev:.1f}%")

    # ── Compute metrics for shadow tiers ─────────────────────────────────────────
    print(f"\n{BOLD}── SHADOW TIER PERFORMANCE{RESET}")
    shadow_metrics = {}
    for tier in ["SHADOW_S", "SHADOW_A", "SHADOW_B", "SHADOW_WATCH", "SHADOW_RESEARCH"]:
        if tier not in shadow_tier_data:
            continue
        data = shadow_tier_data[tier]
        total = len(data)
        settled = [r for r in data if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        accuracy = len(wins) / len(settled) if settled else 0

        with_odd = [r for r in settled if r.get("bookmaker_odd")]
        if with_odd:
            pl = sum((1 if r.get("status") == "WON" else -1) * r.get("bookmaker_odd", 0) for r in with_odd)
            roi = pl / len(with_odd) * 100
            avg_odd = sum(r.get("bookmaker_odd", 0) for r in with_odd) / len(with_odd)
        else:
            pl = 0
            roi = 0
            avg_odd = 0

        avg_ev = sum(r.get("ev_percentage") or 0 for r in data) / len(data) if data else 0

        shadow_metrics[tier] = {
            "total": total,
            "settled": len(settled),
            "accuracy": accuracy,
            "roi": roi,
            "avg_odd": avg_odd,
            "avg_ev": avg_ev,
        }

        print(f"  {tier:<12}: total={total:>3}  settled={len(settled):>3}  "
              f"acc={accuracy*100:>5.1f}%  roi={roi:>6.1f}%  avg_odd={avg_odd:.2f}  avg_ev={avg_ev:.1f}%")

    # ── Compare rankings ───────────────────────────────────────────────────────
    print(f"\n{BOLD}── RANKING COMPARISON{RESET}")

    # Old tier ranking by accuracy
    old_acc_ranking = sorted(old_metrics.items(), key=lambda x: x[1]["accuracy"], reverse=True)
    print(f"\n  OLD TIER (by accuracy):")
    for i, (tier, m) in enumerate(old_acc_ranking):
        print(f"    {i+1}. {tier:<12} {m['accuracy']*100:>5.1f}%")

    # Shadow tier ranking by accuracy
    shadow_acc_ranking = sorted(shadow_metrics.items(), key=lambda x: x[1]["accuracy"], reverse=True)
    print(f"\n  SHADOW TIER (by accuracy):")
    for i, (tier, m) in enumerate(shadow_acc_ranking):
        print(f"    {i+1}. {tier:<12} {m['accuracy']*100:>5.1f}%")

    # ── Check monotonicity ───────────────────────────────────────────────────────
    print(f"\n{BOLD}── MONOTONICITY CHECK{RESET}")

    expected_order = ["SHADOW_S", "SHADOW_A", "SHADOW_B", "SHADOW_WATCH"]
    shadow_acc_values = [shadow_metrics.get(t, {}).get("accuracy", 0) for t in expected_order]

    is_monotonic = all(shadow_acc_values[i] >= shadow_acc_values[i+1] for i in range(len(shadow_acc_values)-1))

    if is_monotonic:
        _ok("Shadow tiers are monotonic (S >= A >= B >= WATCH)")
    else:
        _err("Shadow tiers are NOT monotonic")
        for i in range(len(expected_order)-1):
            if shadow_acc_values[i] < shadow_acc_values[i+1]:
                _err(f"  {expected_order[i]} ({shadow_acc_values[i]*100:.1f}%) < {expected_order[i+1]} ({shadow_acc_values[i+1]*100:.1f}%)")

    # ── Compare SHADOW_S vs OLD_S ───────────────────────────────────────────────
    print(f"\n{BOLD}── SHADOW_S vs OLD_S{RESET}")
    if "SHADOW_S" in shadow_metrics and "S_TIER" in old_metrics:
        shadow_s = shadow_metrics["SHADOW_S"]
        old_s = old_metrics["S_TIER"]

        print(f"  OLD_S:    acc={old_s['accuracy']*100:>5.1f}%  roi={old_s['roi']:>6.1f}%  settled={old_s['settled']}")
        print(f"  SHADOW_S: acc={shadow_s['accuracy']*100:>5.1f}%  roi={shadow_s['roi']:>6.1f}%  settled={shadow_s['settled']}")

        if shadow_s['accuracy'] > old_s['accuracy']:
            _ok(f"SHADOW_S accuracy ({shadow_s['accuracy']*100:.1f}%) > OLD_S ({old_s['accuracy']*100:.1f}%)")
        elif shadow_s['roi'] > old_s['roi']:
            _ok(f"SHADOW_S ROI ({shadow_s['roi']:.1f}%) > OLD_S ROI ({old_s['roi']:.1f}%)")
        else:
            _warn("SHADOW_S does not outperform OLD_S")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")

    success = is_monotonic or (
        "SHADOW_S" in shadow_metrics and "S_TIER" in old_metrics and
        (shadow_metrics["SHADOW_S"]["accuracy"] > old_metrics["S_TIER"]["accuracy"] or
         shadow_metrics["SHADOW_S"]["roi"] > old_metrics["S_TIER"]["roi"])
    )

    if success:
        print(f"{BOLD}{GREEN}  SHADOW_TIER_READY{RESET}")
        _ok("Shadow tier system meets success criteria")
    else:
        print(f"{BOLD}{RED}  SHADOW_TIER_FAILED{RESET}")
        _err("Shadow tier system does not meet success criteria")

    print()


if __name__ == "__main__":
    main()
