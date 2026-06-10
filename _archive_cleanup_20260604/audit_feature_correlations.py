"""
audit_feature_correlations.py
===============================
Calculates which features actually predict wins.

Features analyzed:
- confidence_score
- market_probability
- implied_probability
- edge_percentage
- ev_percentage
- bookmaker_odd
- false_signal_score
- chaos_score
- volatility_score
- ranking_score

Calculates correlation vs outcome (WIN=1, LOSS=0, VOID excluded).

Ranks predictors strongest → weakest.

Usage:
  python audit_feature_correlations.py
"""

import os
import sys
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
import math

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


def _correlation(x_values: List[float], y_values: List[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    if len(x_values) < 2 or len(y_values) < 2:
        return 0.0

    n = len(x_values)
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x2 = sum(x * x for x in x_values)
    sum_y2 = sum(y * y for y in y_values)

    numerator = n * sum_xy - sum_x * sum_y
    denominator = math.sqrt((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2))

    if denominator == 0:
        return 0.0
    return numerator / denominator


def _avg_win_rate_by_feature(values: List[float], outcomes: List[int], bins: int = 5) -> Dict[str, float]:
    """Calculate average win rate by feature value bins."""
    if not values:
        return {}

    # Filter out None values
    paired = [(v, o) for v, o in zip(values, outcomes) if v is not None]
    if not paired:
        return {}

    vals, outs = zip(*paired)
    min_val = min(vals)
    max_val = max(vals)

    if min_val == max_val:
        return {"all": sum(outs) / len(outs)}

    bin_width = (max_val - min_val) / bins
    bin_rates = {}

    for i in range(bins):
        bin_min = min_val + i * bin_width
        bin_max = min_val + (i + 1) * bin_width
        bin_key = f"{bin_min:.2f}-{bin_max:.2f}"

        bin_outcomes = [o for v, o in paired if bin_min <= v < bin_max]
        if bin_outcomes:
            bin_rates[bin_key] = sum(bin_outcomes) / len(bin_outcomes)

    return bin_rates


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  FEATURE CORRELATION ANALYSIS{RESET}")
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

    # ── Fetch POST_RESET predictions with features ─────────────────────────────
    print(f"\n{BOLD}── Fetching POST_RESET predictions with features {'─'*29}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "prediction_id, status, confidence_score, market_probability, "
                "implied_probability, edge_percentage, ev_percentage, "
                "bookmaker_odd, false_signal_score, chaos_score, "
                "volatility_score, ranking_score, created_at"
            )
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} POST_RESET predictions")

    # ── Parse features and outcomes ────────────────────────────────────────────
    features = {
        "confidence_score": [],
        "market_probability": [],
        "implied_probability": [],
        "edge_percentage": [],
        "ev_percentage": [],
        "bookmaker_odd": [],
        "false_signal_score": [],
        "chaos_score": [],
        "volatility_score": [],
        "ranking_score": [],
    }
    outcomes = []

    for r in rows:
        status = r.get("status", "")
        if status == "VOID":
            continue
        outcome = 1 if status == "WON" else 0
        outcomes.append(outcome)

        features["confidence_score"].append(r.get("confidence_score"))
        features["market_probability"].append(r.get("market_probability"))
        features["implied_probability"].append(r.get("implied_probability"))
        features["edge_percentage"].append(r.get("edge_percentage"))
        features["ev_percentage"].append(r.get("ev_percentage"))
        features["bookmaker_odd"].append(r.get("bookmaker_odd"))
        features["false_signal_score"].append(r.get("false_signal_score"))
        features["chaos_score"].append(r.get("chaos_score"))
        features["volatility_score"].append(r.get("volatility_score"))
        features["ranking_score"].append(r.get("ranking_score"))

    _info(f"Processed {len(outcomes)} settled predictions (excluding VOID)")

    # ── Calculate correlations ─────────────────────────────────────────────────
    print(f"\n{BOLD}── Feature Correlations vs Outcome (WIN=1, LOSS=0) {'─'*27}{RESET}")
    print(f"  {'Feature':<25} {'Correlation':<15} {'Direction':<15}")
    print(f"  {'─'*25} {'─'*15} {'─'*15}")

    correlations = {}
    for feature_name, values in features.items():
        # Filter out None values
        paired = [(v, o) for v, o in zip(values, outcomes) if v is not None]
        if len(paired) < 10:
            continue

        vals, outs = zip(*paired)
        corr = _correlation(list(vals), list(outs))
        correlations[feature_name] = corr

        direction = "POSITIVE" if corr > 0 else "NEGATIVE" if corr < 0 else "NONE"
        color = GREEN if abs(corr) > 0.1 else YELLOW if abs(corr) > 0.05 else RED
        print(f"  {feature_name:<25} {color}{corr:>10.3f}{RESET}{'':<5} {direction:<15}")

    # ── Rank predictors by absolute correlation ────────────────────────────────
    print(f"\n{BOLD}── Predictors Ranked by Strength (strongest → weakest) {'─'*23}{RESET}")
    ranked = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)
    print(f"  {'Rank':<6} {'Feature':<25} {'|Correlation|':<15}")
    print(f"  {'─'*6} {'─'*25} {'─'*15}")
    for i, (feature, corr) in enumerate(ranked, 1):
        color = GREEN if abs(corr) > 0.1 else YELLOW if abs(corr) > 0.05 else RED
        print(f"  {i:<6} {feature:<25} {color}{abs(corr):>10.3f}{RESET}")

    # ── Win rate by feature bins for top predictors ───────────────────────────
    print(f"\n{BOLD}── Win Rate by Feature Bins (top 3 predictors) {'─'*31}{RESET}")
    for feature, _ in ranked[:3]:
        print(f"\n  {feature}:")
        rates = _avg_win_rate_by_feature(features[feature], outcomes, bins=5)
        for bin_key, rate in sorted(rates.items()):
            print(f"    {bin_key:<15}: {rate*100:>5.1f}%")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    if ranked:
        best_feature, best_corr = ranked[0]
        if abs(best_corr) > 0.1:
            _ok(f"Strongest predictor: {best_feature} (corr={best_corr:.3f})")
        elif abs(best_corr) > 0.05:
            _warn(f"Weakest predictors overall — best is {best_feature} (corr={best_corr:.3f})")
        else:
            _err(f"No meaningful predictors found — best is {best_feature} (corr={best_corr:.3f})")
    print()


if __name__ == "__main__":
    main()
