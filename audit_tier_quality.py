"""
audit_tier_quality.py
======================
Determine whether tier assignment is correlated with real outcomes.

Uses POST_RESET only (TRACKING_RESET_AT filter).

For each settled prediction, collects:
  - tier
  - bookmaker_odd
  - market_probability
  - implied_probability
  - ev_percentage
  - result (WIN/LOSS)

Outputs:
  1. Accuracy by tier
  2. ROI by tier
  3. Average EV by tier
  4. Average bookmaker odd by tier
  5. Average market probability by tier
  6. Correlation: EV ↔ Result, Tier ↔ Result
  7. TOP 20 worst S_TIER losses
  8. TOP 20 winning WATCHLIST/B_TIER picks

Final verdict:
  TIERING_OK
  TIERING_BROKEN (if ROI(S) < ROI(B) or Accuracy(S) < Accuracy(B) or Accuracy(A) < Accuracy(WATCHLIST))

Usage:
  python audit_tier_quality.py
"""

import os
import sys
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

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
    print(f"{BOLD}  TIER QUALITY AUDIT{RESET}")
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

    # ── Fetch settled predictions with tier and EV fields ─────────────────────
    print(f"\n{BOLD}── Fetching settled predictions (POST_RESET) {'─'*30}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "prediction_id, fixture_id, home_team, away_team, market, "
                "statistical_tier, ev_tier, bookmaker_odd, market_probability, implied_probability, "
                "ev_percentage, edge_percentage, status, prediction_date, created_at"
            )
            .in_("status", ["WON", "LOST", "VOID"])
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.limit(5000).execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} settled predictions")

    # ── Parse and group by tier ────────────────────────────────────────────────
    tier_data: Dict[str, List[dict]] = defaultdict(list)
    all_data = []

    for r in rows:
        # Use statistical_tier (odds-independent) as primary tier
        tier = (r.get("statistical_tier") or r.get("ev_tier") or "NO_VALUE").upper()
        status = r.get("status", "")
        if status == "VOID":
            continue
        is_win = status == "WON"
        bookmaker_odd = r.get("bookmaker_odd")
        market_prob = r.get("market_probability")
        implied_prob = r.get("implied_probability")
        ev_pct = r.get("ev_percentage") or r.get("ev_percent") or 0

        try:
            bookmaker_odd = float(bookmaker_odd) if bookmaker_odd else None
            market_prob = float(market_prob) if market_prob else None
            implied_prob = float(implied_prob) if implied_prob else None
            ev_pct = float(ev_pct)
        except (TypeError, ValueError):
            continue

        row_data = {
            "tier": tier,
            "bookmaker_odd": bookmaker_odd,
            "market_probability": market_prob,
            "implied_probability": implied_prob,
            "ev_percentage": ev_pct,
            "is_win": is_win,
            "status": status,
            "match": f"{r.get('home_team','?')} v {r.get('away_team','?')}",
            "market": r.get("market", ""),
            "prediction_id": r.get("prediction_id", ""),
        }
        tier_data[tier].append(row_data)
        all_data.append(row_data)

    _info(f"Processed {len(all_data)} non-void predictions")

    # ── Metrics by tier ───────────────────────────────────────────────────────
    print(f"\n{BOLD}── Metrics by Tier {'─'*49}{RESET}")

    tier_metrics = {}
    for tier, rows in tier_data.items():
        if not rows:
            continue
        total = len(rows)
        wins = sum(1 for r in rows if r["is_win"])
        accuracy = wins / total if total > 0 else 0

        # ROI (only for rows with bookmaker_odd)
        with_odd = [r for r in rows if r["bookmaker_odd"]]
        if with_odd:
            pl = sum((1 if r["is_win"] else -1) * r["bookmaker_odd"] for r in with_odd)
            roi = pl / len(with_odd) * 100
            avg_odd = sum(r["bookmaker_odd"] for r in with_odd) / len(with_odd)
        else:
            pl = 0
            roi = 0
            avg_odd = 0

        avg_ev = sum(r["ev_percentage"] for r in rows) / total
        avg_market_prob = sum(r["market_probability"] or 0 for r in rows) / total

        tier_metrics[tier] = {
            "total": total,
            "wins": wins,
            "accuracy": accuracy,
            "pl": pl,
            "roi": roi,
            "avg_odd": avg_odd,
            "avg_ev": avg_ev,
            "avg_market_prob": avg_market_prob,
        }

    # Print table
    print(f"  {'Tier':<12} {'Count':<6} {'Wins':<6} {'Accuracy':<10} {'ROI':<10} {'AvgOdd':<10} {'AvgEV':<10}")
    print(f"  {'─'*12} {'─'*6} {'─'*6} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")
    for tier in sorted(tier_metrics.keys()):
        m = tier_metrics[tier]
        print(f"  {tier:<12} {m['total']:<6} {m['wins']:<6} {m['accuracy']*100:>8.1f}%  {m['roi']:>8.1f}%  {m['avg_odd']:>8.3f}  {m['avg_ev']:>8.2f}%")

    # ── Correlation analysis ───────────────────────────────────────────────────
    print(f"\n{BOLD}── Correlation Analysis {'─'*48}{RESET}")

    # EV ↔ Result correlation
    ev_win = [r["ev_percentage"] for r in all_data if r["is_win"]]
    ev_loss = [r["ev_percentage"] for r in all_data if not r["is_win"]]
    avg_ev_win = sum(ev_win) / len(ev_win) if ev_win else 0
    avg_ev_loss = sum(ev_loss) / len(ev_loss) if ev_loss else 0
    print(f"  EV ↔ Result:")
    print(f"    Avg EV (WIN)  : {avg_ev_win:.2f}%")
    print(f"    Avg EV (LOSS) : {avg_ev_loss:.2f}%")
    if avg_ev_win > avg_ev_loss:
        _ok("EV positively correlated with WIN")
    else:
        _warn("EV not correlated with WIN")

    # Tier ↔ Result correlation
    tier_win_rates = {tier: tier_metrics[tier]["accuracy"] for tier in tier_metrics}
    print(f"\n  Tier ↔ Result (win rates):")
    for tier in sorted(tier_win_rates.keys()):
        print(f"    {tier:<12}: {tier_win_rates[tier]*100:.1f}%")

    # ── TOP 20 worst S_TIER losses ─────────────────────────────────────────────
    print(f"\n{BOLD}── TOP 20 Worst S_TIER Losses {'─'*38}{RESET}")
    s_tier_losses = [r for r in all_data if r["tier"] == "S_TIER" and not r["is_win"]]
    s_tier_losses.sort(key=lambda r: r["bookmaker_odd"] or 0, reverse=True)
    print(f"  {'Match':<30} {'Market':<20} {'Odd':<8} {'Prob':<8} {'Implied':<8} {'EV%':<8} {'Result':<8}")
    print(f"  {'─'*30} {'─'*20} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for r in s_tier_losses[:20]:
        odd_str = f"{r['bookmaker_odd']:.3f}" if r['bookmaker_odd'] else "N/A"
        prob_str = f"{r['market_probability']:.3f}" if r['market_probability'] else "N/A"
        impl_str = f"{r['implied_probability']:.3f}" if r['implied_probability'] else "N/A"
        print(f"  {r['match'][:30]:<30} {r['market'][:20]:<20} {odd_str:<8} "
              f"{prob_str:<8} {impl_str:<8} {r['ev_percentage']:<8.2f} {r['status']:<8}")

    # ── TOP 20 winning WATCHLIST/B_TIER picks ─────────────────────────────────
    print(f"\n{BOLD}── TOP 20 Winning WATCHLIST/B_TIER Picks {'─'*33}{RESET}")
    wb_wins = [r for r in all_data if r["tier"] in ("WATCHLIST", "B_TIER") and r["is_win"]]
    wb_wins.sort(key=lambda r: r["bookmaker_odd"] or 0, reverse=True)
    print(f"  {'Match':<30} {'Market':<20} {'Odd':<8} {'Prob':<8} {'Implied':<8} {'EV%':<8} {'Result':<8}")
    print(f"  {'─'*30} {'─'*20} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for r in wb_wins[:20]:
        odd_str = f"{r['bookmaker_odd']:.3f}" if r['bookmaker_odd'] else "N/A"
        prob_str = f"{r['market_probability']:.3f}" if r['market_probability'] else "N/A"
        impl_str = f"{r['implied_probability']:.3f}" if r['implied_probability'] else "N/A"
        print(f"  {r['match'][:30]:<30} {r['market'][:20]:<20} {odd_str:<8} "
              f"{prob_str:<8} {impl_str:<8} {r['ev_percentage']:<8.2f} {r['status']:<8}")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")

    m_s = tier_metrics.get("S_TIER", {})
    m_a = tier_metrics.get("A_TIER", {})
    m_b = tier_metrics.get("B_TIER", {})
    m_watch = tier_metrics.get("WATCHLIST", {})

    broken = False
    reasons = []

    if m_s and m_b:
        if m_s["roi"] < m_b["roi"]:
            broken = True
            reasons.append(f"ROI(S) {m_s['roi']:.1f}% < ROI(B) {m_b['roi']:.1f}%")
        if m_s["accuracy"] < m_b["accuracy"]:
            broken = True
            reasons.append(f"Accuracy(S) {m_s['accuracy']*100:.1f}% < Accuracy(B) {m_b['accuracy']*100:.1f}%")

    if m_a and m_watch:
        if m_a["accuracy"] < m_watch["accuracy"]:
            broken = True
            reasons.append(f"Accuracy(A) {m_a['accuracy']*100:.1f}% < Accuracy(WATCHLIST) {m_watch['accuracy']*100:.1f}%")

    if broken:
        print(f"{BOLD}{RED}  TIERING_BROKEN{RESET}")
        for reason in reasons:
            _err(reason)
    else:
        print(f"{BOLD}{GREEN}  TIERING_OK{RESET}")
        _ok("Tier assignment correlates with outcomes")

    print()
    sys.exit(0 if not broken else 1)


if __name__ == "__main__":
    main()
