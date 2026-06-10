"""
audit_ev_pick_quality.py — EV Pick Quality Gate Audit
======================================================
Runs the scanner and shows exactly how many picks survive each safety gate.

Gates (checked in order):
  1. has_real_odds = True
  2. odds_source in {API_FOOTBALL, ODDS_API}
  3. bookmaker_odd >= 1.20
  4. sample_size >= 10
  5. market_probability in [0.15, 0.95]
  6. ev_percentage >= 5.0 %

Each (fixture_id × market) pair appears exactly once (dedup already done in scanner).

Classification:
  S_TIER_EV            — passes all gates, value_level in {EXTREME, HIGH}
  A_TIER_EV            — passes all gates, value_level == MEDIUM
  B_TIER_EV            — passes all gates, value_level in {LOW}
  WATCHLIST_STATISTICAL — fails EV_TOO_LOW or PROBABILITY_OUT_OF_BOUNDS
  REJECTED_EV          — fails any other gate

Usage:
    python audit_ev_pick_quality.py
"""

import os
import sys
from datetime import date
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

G   = "\033[92m"
Y   = "\033[93m"
R   = "\033[91m"
C   = "\033[96m"
B   = "\033[94m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"


def _cls_color(c: str) -> str:
    if c == "S_TIER_EV":   return f"{G}{BLD}{c}{X}"
    if c == "A_TIER_EV":   return f"{G}{c}{X}"
    if c == "B_TIER_EV":   return f"{C}{c}{X}"
    if c == "WATCHLIST_STATISTICAL": return f"{Y}{c}{X}"
    return f"{R}{c}{X}"


def sec(title: str) -> None:
    print(f"\n{'═'*72}")
    print(f"  {BLD}{title}{X}")
    print(f"{'─'*72}")


def run() -> None:
    sec(f"EV PICK QUALITY AUDIT — {date.today().isoformat()}")
    print()

    # ── Run scanner ────────────────────────────────────────────────────────────
    print("  Loading scanner…")
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
        print(f"  Done — {len(analyzed)} matches analyzed.\n")
    except Exception as exc:
        print(f"  {R}Scanner failed: {exc}{X}")
        import traceback; traceback.print_exc()
        return

    # ── Collect all picks from ev_qualified + ev_rejected ─────────────────────
    all_qualified = []
    all_rejected  = []
    raw_ev_rows   = 0
    seen_pairs    = set()     # (fid, market) — enforce global uniqueness
    duplicates_removed = 0

    for item in analyzed:
        an = item.get("analysis") or {}
        md = item.get("match_data") or {}
        if an.get("status") == "DATA_INSUFFICIENT":
            continue

        fid     = str(an.get("fixture_id") or md.get("match_id") or "")
        league  = md.get("competition", "?")
        fixture = f"{md.get('home_team','?')} vs {md.get('away_team','?')}"

        # Count raw ev_opportunities (before gate, after dedup by market)
        raw_ev_rows += len(an.get("ev_opportunities") or [])

        for pick in (an.get("ev_qualified") or []):
            pair = (fid, pick["market"])
            if pair in seen_pairs:
                duplicates_removed += 1
                continue
            seen_pairs.add(pair)
            pick = dict(pick)
            pick["fixture"] = fixture
            pick["fid"]     = fid
            pick["league"]  = league
            all_qualified.append(pick)

        for pick in (an.get("ev_rejected") or []):
            pair = (fid, pick["market"])
            if pair in seen_pairs:
                duplicates_removed += 1
                continue
            seen_pairs.add(pair)
            pick = dict(pick)
            pick["fixture"] = fixture
            pick["fid"]     = fid
            pick["league"]  = league
            all_rejected.append(pick)

    unique_ev_picks = len(all_qualified) + len(all_rejected)

    # ── Rejection breakdown ────────────────────────────────────────────────────
    reject_counts: dict = defaultdict(int)
    for p in all_rejected:
        reject_counts[p.get("rejection_reason", "UNKNOWN")] += 1

    # ── SECTION 1: Qualified picks ─────────────────────────────────────────────
    sec("QUALIFIED EV PICKS")
    print()

    by_class: dict = defaultdict(list)
    for p in all_qualified:
        by_class[p["classification"]].append(p)

    for cls in ("S_TIER_EV", "A_TIER_EV", "B_TIER_EV"):
        picks = by_class.get(cls, [])
        if not picks:
            continue
        print(f"  {_cls_color(cls)}  ({len(picks)} picks)")
        print(f"  {'Fixture':<32} {'Market':<18} {'Prob':>6} {'Odd':>5} {'Impl':>6} {'EV%':>7} {'Edge%':>7} {'n':>3}")
        print(f"  {'─'*90}")
        for p in picks:
            prob_str  = f"{p['market_probability']:.3f}"
            odd_str   = f"{p['bookmaker_odd']:.2f}"
            impl_str  = f"{p['implied_probability']:.3f}"
            ev_str    = f"{p['ev_percentage']:+.1f}%"
            edge_str  = f"{p['edge_percentage']:+.1f}%"
            n_str     = str(p['sample_size'])
            print(f"  {p['fixture']:<32} {p['market']:<18} {prob_str:>6} {odd_str:>5} "
                  f"{impl_str:>6} {ev_str:>7} {edge_str:>7} {n_str:>3}")
            print(f"  {D}  sig_conf={p.get('signal_confidence','?')}  "
                  f"source={p['probability_source']}  "
                  f"odds_src={p['odds_source']}  "
                  f"bookmaker={p['bookmaker']}{X}")
        print()

    if not all_qualified:
        print(f"  {Y}No qualified picks passed all safety gates.{X}")
        print()

    # ── SECTION 2: Rejected picks ──────────────────────────────────────────────
    sec("REJECTED / WATCHLIST PICKS")
    print()

    by_rej_cls: dict = defaultdict(list)
    for p in all_rejected:
        by_rej_cls[p["classification"]].append(p)

    for cls in ("WATCHLIST_STATISTICAL", "REJECTED_EV"):
        picks = by_rej_cls.get(cls, [])
        if not picks:
            continue
        print(f"  {_cls_color(cls)}  ({len(picks)} picks)")
        print(f"  {'Fixture':<32} {'Market':<18} {'Reason':<28} {'Prob':>6} {'EV%':>7} {'n':>3}")
        print(f"  {'─'*90}")
        for p in picks:
            prob_str = f"{p['market_probability']:.3f}"
            ev_str   = f"{p['ev_percentage']:+.1f}%"
            n_str    = str(p['sample_size'])
            reason   = p.get("rejection_reason", "UNKNOWN")
            print(f"  {p['fixture']:<32} {p['market']:<18} {reason:<28} {prob_str:>6} {ev_str:>7} {n_str:>3}")
        print()

    if not all_rejected:
        print(f"  {G}No picks rejected.{X}")
        print()

    # ── SECTION 3: Summary counters ────────────────────────────────────────────
    sec("SUMMARY COUNTERS")
    print()

    total_q  = len(all_qualified)
    total_r  = len(all_rejected)
    s_tier   = len(by_class.get("S_TIER_EV", []))
    a_tier   = len(by_class.get("A_TIER_EV", []))
    b_tier   = len(by_class.get("B_TIER_EV", []))

    print(f"  raw_ev_rows              : {raw_ev_rows:<6}  (ev_opportunities before gates, after dedup by market)")
    print(f"  unique_ev_picks          : {unique_ev_picks:<6}  (qualified + rejected, one per fixture×market)")
    print(f"  duplicates_removed       : {duplicates_removed:<6}")
    print()
    print(f"  {'─ Rejection breakdown ─'}")
    print(f"  rejected_by_no_real_odds : {reject_counts.get('NO_REAL_ODDS', 0)}")
    print(f"  rejected_by_invalid_src  : {reject_counts.get('INVALID_ODDS_SOURCE', 0)}")
    print(f"  rejected_by_low_odd      : {reject_counts.get('ODD_TOO_LOW', 0)}")
    print(f"  rejected_by_low_sample   : {reject_counts.get('SAMPLE_TOO_SMALL', 0)}")
    print(f"  rejected_by_prob_bounds  : {reject_counts.get('PROBABILITY_OUT_OF_BOUNDS', 0)}")
    print(f"  rejected_by_low_ev       : {reject_counts.get('EV_TOO_LOW', 0)}")
    print(f"  total_rejected           : {total_r}")
    print(f"  watchlist_statistical    : {len(by_rej_cls.get('WATCHLIST_STATISTICAL', []))}")
    print()
    print(f"  {'─ Final qualified picks ─'}")
    print(f"  S_TIER_EV (EXTREME/HIGH) : {s_tier}")
    print(f"  A_TIER_EV (MEDIUM)       : {a_tier}")
    print(f"  B_TIER_EV (LOW)          : {b_tier}")
    print(f"  final_ev_picks           : {total_q}")
    print()

    # ── VERDICT ───────────────────────────────────────────────────────────────
    sec("VERDICT")
    print()

    if total_q == 0:
        print(f"  {Y}NO_EV_PICKS_TODAY{X}")
        print(f"  All {unique_ev_picks} unique market opportunities were filtered by the safety gates.")
        print(f"  Top rejection reasons: {dict(list(reject_counts.items())[:3])}")
    elif s_tier > 0:
        print(f"  {G}EV_PICKS_AVAILABLE — {s_tier} S_TIER + {a_tier} A_TIER + {b_tier} B_TIER{X}")
        best = sorted(all_qualified, key=lambda p: p["ev_percentage"], reverse=True)
        print(f"  Top pick: {best[0]['fixture']}  {best[0]['market']}")
        print(f"    market_probability={best[0]['market_probability']:.3f}  "
              f"odd={best[0]['bookmaker_odd']:.2f}  "
              f"ev={best[0]['ev_percentage']:+.1f}%  "
              f"edge={best[0]['edge_percentage']:+.1f}%  "
              f"n={best[0]['sample_size']}")
    else:
        print(f"  {C}EV_PICKS_AVAILABLE — {a_tier} A_TIER + {b_tier} B_TIER (no S_TIER today){X}")
    print()


if __name__ == "__main__":
    run()
