"""
scripts/performance_report.py
================================
Performance report from Supabase settled predictions.

Shows (5 phases):
  Phase 1 — Odds audit (bookmaker_odd coverage)
  Phase 2 — Statistical accuracy vs Real ROI (separated)
  Phase 3 — Break-even analysis per market
  Phase 4 — Market viability classification
  Phase 5 — Full structured report

Usage:
    python scripts/performance_report.py
    python scripts/performance_report.py --days 7
    python scripts/performance_report.py --days 30
    python scripts/performance_report.py --days 90
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def _color_pl(v: float) -> str:
    c = GREEN if v >= 0 else RED
    return f"{c}{v:+.2f}u{RESET}"


def _color_roi(v: float) -> str:
    c = GREEN if v >= 0 else RED
    return f"{c}{v:+.1f}%{RESET}"


def _hr(wins: int, total: int) -> str:
    if total == 0:
        return "—"
    return f"{wins}/{total} ({wins / total * 100:.0f}%)"


VIABILITY_COLOR = {
    "BETTABLE_EV_POSITIVE": GREEN,
    "BETTABLE_NO_EDGE":     YELLOW,
    "STAT_SIGNAL_ONLY":     CYAN,
    "NO_ODDS_AVAILABLE":    DIM,
    "UNBETTABLE_LOW_ODDS":  RED,
}


def _get_odds_source_breakdown(repo, days: int = 30, since_date: str = None, selection_mode: str = None) -> dict:
    """
    Phase 6: Query predictions grouped by odds_source.
    Returns {source: {picks, settled, wins, roi, avg_odd}}.
    Gracefully returns {} if column doesn't exist yet (migration pending).

    Args:
        selection_mode: If provided, filter by selection_mode (e.g., "LIVE_SAFE")
    """
    if not repo._client:
        return {}
    try:
        q = repo._client.table("predictions").select(
            "odds_source,status,bookmaker_odd,selection_mode"
        )
        if selection_mode:
            q = q.eq("selection_mode", selection_mode)
        if since_date:
            if "T" in since_date:
                q = q.gte("created_at", since_date)
            else:
                q = q.gte("prediction_date", since_date)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=days)).isoformat()
            q = q.gte("prediction_date", cutoff)
        rows = (q.limit(5000).execute()).data or []
    except Exception:
        return {}  # column may not exist yet

    result: dict = {}
    for row in rows:
        src    = (row.get("odds_source") or "NO_ODDS").upper()
        status = (row.get("status") or "PENDING").upper()
        odd    = float(row.get("bookmaker_odd") or 0)

        if src not in result:
            result[src] = {"picks": 0, "settled": 0, "wins": 0,
                           "pl": 0.0, "odd_sum": 0.0, "odd_count": 0}
        d = result[src]
        d["picks"] += 1
        if status in ("WON", "LOST", "VOID"):
            d["settled"] += 1
            if odd >= 1.1:
                pl = (odd - 1.0) if status == "WON" else (-1.0 if status == "LOST" else 0.0)
                d["pl"]        += pl
                d["odd_sum"]   += odd
                d["odd_count"] += 1
            if status == "WON":
                d["wins"] += 1

    # Compute derived metrics
    for src, d in result.items():
        n = d["odd_count"] or 1
        settled = d["settled"] or 1
        d["roi"]     = round(d["pl"] / settled * 100, 1)
        d["avg_odd"] = round(d["odd_sum"] / n, 3) if d["odd_count"] else None

    return result


def _parse_reset_at() -> str:
    """
    Return TRACKING_RESET_AT exactly as set in env (full ISO datetime or date), or ''.
    Preserves time component: '2026-06-02T15:19:00Z' returned as-is.
    """
    raw = os.environ.get("TRACKING_RESET_AT", "").strip()
    if not raw:
        return ""
    try:
        if "T" in raw:
            from datetime import datetime
            datetime.fromisoformat(raw.replace("Z", "+00:00"))  # validate
        else:
            from datetime import date as _date
            _date.fromisoformat(raw[:10])  # validate
        return raw  # return full string, not truncated
    except Exception:
        return ""


def run(days: int = 30, since_reset: bool = False) -> dict:
    reset_at = _parse_reset_at() if since_reset else ""
    safe_mode = os.environ.get("SAFE_SELECTION_MODE", "").lower() in ("1", "true", "yes")
    title_suffix = f"since {reset_at} (reset)" if reset_at else f"last {days} days"
    if safe_mode:
        title_suffix += " [SAFE_MODE]"
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PERFORMANCE REPORT — Supabase  ({title_suffix}){RESET}")
    if reset_at:
        print(f"  {CYAN}TRACKING_RESET_AT={reset_at} — only predictions after this date.{RESET}")
    if safe_mode:
        print(f"  {CYAN}SAFE_SELECTION_MODE=TRUE — ROI uses LIVE_SAFE picks only.{RESET}")
    print(f"{'═'*66}")

    from app.database.supabase_config import get_supabase_config
    from app.database.supabase_repository import get_repository, reset_repository

    reset_repository()
    cfg  = get_supabase_config()
    repo = get_repository()
    _since = reset_at or None  # will be passed to repo calls that support it

    if not cfg.supabase_connected:
        print(f"  {RED}✗ Supabase not connected: {cfg.supabase_error}{RESET}")
        sys.exit(1)
    print(f"  {GREEN}✓ Supabase connected{RESET}\n")

    # ── REPORT_RESET_FILTER banner ─────────────────────────────────────────
    if reset_at:
        try:
            gen = repo.get_generation_counts()
            legacy_n   = gen.get("legacy", 0)
            post_reset_n = gen.get("post_reset", 0)
            print(f"  {YELLOW}╔══ REPORT_RESET_FILTER active ══════════════════════════════╗{RESET}")
            print(f"  {YELLOW}║{RESET}  TRACKING_RESET_AT   : {CYAN}{reset_at}{RESET}")
            print(f"  {YELLOW}║{RESET}  Legacy picks ignored : {RED}{legacy_n}{RESET}")
            print(f"  {YELLOW}║{RESET}  Post-reset picks used: {GREEN}{post_reset_n}{RESET}")
            print(f"  {YELLOW}╚════════════════════════════════════════════════════════════╝{RESET}\n")
        except Exception:
            print(f"  {YELLOW}REPORT_RESET_FILTER active — since {reset_at}{RESET}\n")

    # ── SAFE_SELECTION_MODE banner ───────────────────────────────────────────
    if safe_mode:
        try:
            q = (
                repo._client.table("predictions")
                .select("selection_mode", count="exact")
                .in_("status", ["WON", "LOST", "VOID"])
            )
            if _since:
                cutoff = _since
                if "T" in cutoff:
                    q = q.gte("created_at", cutoff)
                else:
                    q = q.gte("prediction_date", cutoff)
            rows = q.execute().data or []
            live_safe = sum(1 for r in rows if r.get("selection_mode") == "LIVE_SAFE")
            research = sum(1 for r in rows if r.get("selection_mode") == "RESEARCH")
            total_all = len(rows)
            print(f"  {YELLOW}╔══ SAFE_SELECTION_MODE active ══════════════════════════════╗{RESET}")
            print(f"  {YELLOW}║{RESET}  ALL settled           : {CYAN}{total_all}{RESET}")
            print(f"  {YELLOW}║{RESET}  LIVE_SAFE picks       : {GREEN}{live_safe}{RESET}")
            print(f"  {YELLOW}║{RESET}  RESEARCH picks        : {RED}{research}{RESET}")
            print(f"  {YELLOW}╚════════════════════════════════════════════════════════════╝{RESET}\n")
            print(f"  {DIM}→ ROI and accuracy below use LIVE_SAFE picks only{RESET}\n")
        except Exception:
            print(f"  {YELLOW}SAFE_SELECTION_MODE active — filtering to LIVE_SAFE{RESET}\n")

    if _since:
        summary = repo.get_performance_summary(since_date=_since)
    else:
        summary  = repo.get_performance_summary(days=days)

    # If SAFE_SELECTION_MODE is enabled, filter summary to LIVE_SAFE only
    if safe_mode:
        try:
            # Fetch raw settled data and filter to LIVE_SAFE
            if _since:
                cutoff = _since
                if "T" in cutoff:
                    q = repo._client.table("predictions").select(
                        "status, profit_loss, bookmaker_odd, statistical_tier, "
                        "match_universe, league, market, confidence_score"
                    ).in_("status", ["WON", "LOST", "VOID"]).gte("created_at", cutoff)
                else:
                    q = repo._client.table("predictions").select(
                        "status, profit_loss, bookmaker_odd, statistical_tier, "
                        "match_universe, league, market, confidence_score"
                    ).in_("status", ["WON", "LOST", "VOID"]).gte("prediction_date", cutoff)
            else:
                from datetime import date, timedelta
                cutoff = (date.today() - timedelta(days=days)).isoformat()
                q = repo._client.table("predictions").select(
                    "status, profit_loss, bookmaker_odd, statistical_tier, "
                    "match_universe, league, market, confidence_score"
                ).in_("status", ["WON", "LOST", "VOID"]).gte("prediction_date", cutoff)

            q = q.eq("selection_mode", "LIVE_SAFE")
            rows = q.execute().data or []

            # Recompute stats from filtered rows
            from app.database.supabase_repository import SupabaseRepository
            summary = SupabaseRepository._compute_stats(rows)
        except Exception:
            pass  # Fall back to unfiltered summary if filtering fails

    wins     = int(summary.get("total_wins",   0))
    losses   = int(summary.get("total_losses", 0))
    void_    = int(summary.get("total_void",   0))
    total_wl = wins + losses
    pl       = float(summary.get("total_profit_loss") or 0)
    hr       = (wins / total_wl * 100) if total_wl > 0 else 0.0

    ev_total = int(summary.get("ev_total",  0))
    ev_wins  = int(summary.get("ev_wins",   0))
    ev_pl    = float(summary.get("ev_profit_loss") or 0)
    ev_roi   = float(summary.get("ev_roi")   or 0)
    ev_odd   = summary.get("ev_avg_odd")

    try:
        pending = repo.get_pending_count()
    except Exception:
        pending = 0

    no_odds_count = total_wl - ev_total

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1 — Odds audit
    # ══════════════════════════════════════════════════════════════════════════
    phase1_label = "Odds Audit (LIVE_SAFE only)" if safe_mode else "Odds Audit"
    print(f"  {BOLD}── PHASE 1 — {phase1_label} {'─'*42}{RESET}")
    print(f"  Settled total   : {BOLD}{total_wl}{RESET}  "
          f"(W:{GREEN}{wins}{RESET}  L:{RED}{losses}{RESET}  "
          f"V:{YELLOW}{void_}{RESET}  Pending:{CYAN}{pending}{RESET})")
    print(f"  With real odds  : {GREEN if ev_total > 0 else YELLOW}{ev_total}{RESET}  "
          f"({ev_total / max(total_wl, 1) * 100:.0f}% of settled)  "
          f"{DIM}[bookmaker_odd IS NOT NULL AND >= 1.1]{RESET}")
    print(f"  Without odds    : {RED if no_odds_count > 0 else GREEN}{no_odds_count}{RESET}  "
          f"{DIM}(P/L unreliable on these){RESET}")
    if no_odds_count > 0:
        print(f"  {YELLOW}  → ROI below is SIMULATED (default odd ~1.0) — see Phase 2B{RESET}")

    # Odds source breakdown (Phase 6)
    src_breakdown = _get_odds_source_breakdown(
        repo, days=days, since_date=_since if _since else None,
        selection_mode="LIVE_SAFE" if safe_mode else None
    )
    if src_breakdown:
        print(f"\n  {DIM}Provider breakdown  (bookmaker_odd >= 1.1 = real odds):{RESET}")
        for src, d in sorted(src_breakdown.items()):
            avg_o = f"{d['avg_odd']:.3f}" if d.get("avg_odd") else "  N/A"
            roi_s = f"{d['roi']:+.1f}%" if d.get("settled") else "   —"
            c_roi = GREEN if d.get("roi", 0) >= 0 else RED
            print(f"    {src:<22}: picks={d['picks']:>4}  settled={d['settled']:>4}  "
                  f"wins={d['wins']:>4}  AvgOdd={avg_o}  ROI={c_roi}{roi_s}{RESET}")
    else:
        print(f"  {DIM}(odds_source breakdown unavailable — run migration 003){RESET}")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2 — Statistical accuracy vs Real ROI
    # ══════════════════════════════════════════════════════════════════════════
    phase2_label = "Accuracy vs ROI (LIVE_SAFE only)" if safe_mode else "Accuracy vs ROI"
    print(f"\n  {BOLD}── PHASE 2 — {phase2_label} {'─'*37}{RESET}")

    # A. Statistical accuracy (all picks, regardless of odds)
    print(f"  {BOLD}{CYAN}A. Statistical Accuracy  (all {total_wl} settled picks){RESET}")
    if total_wl > 0:
        print(f"     accuracy_stat  : {BOLD}{hr:.1f}%{RESET}  ({wins}/{total_wl})")
        s_total = int(summary.get("s_tier_total", 0))
        s_wins_ = int(summary.get("s_tier_wins",  0))
        a_total = int(summary.get("a_tier_total", 0))
        a_wins_ = int(summary.get("a_tier_wins",  0))
        if s_total > 0:
            print(f"     acc_S_TIER     : {s_wins_ / s_total * 100:.1f}%  ({s_wins_}/{s_total})")
        if a_total > 0:
            print(f"     acc_A_TIER     : {a_wins_ / a_total * 100:.1f}%  ({a_wins_}/{a_total})")
        fp_count = int(summary.get("false_positive_count", 0))
        if fp_count:
            fp_rate = float(summary.get("false_positive_rate") or 0) * 100
            print(f"     false_pos      : {RED}{fp_count}{RESET}  ({fp_rate:.0f}% of losses) "
                  f"| Max DD: {summary.get('max_drawdown', 0):.2f}u "
                  f"| Streak: {summary.get('longest_losing_streak', 0)}")
    else:
        print(f"     {YELLOW}No settled predictions.{RESET}")

    # B. Real ROI (only picks with bookmaker_odd ≥ 1.1)
    print(f"\n  {BOLD}{GREEN}B. Real ROI  (only {ev_total} picks with bookmaker_odd ≥ 1.1){RESET}")
    if ev_total > 0:
        ev_hr_real = ev_wins / ev_total * 100
        print(f"     ev_hit_rate    : {BOLD}{ev_hr_real:.1f}%{RESET}  ({ev_wins}/{ev_total})")
        print(f"     real_profit    : {_color_pl(ev_pl)}")
        print(f"     real_roi       : {_color_roi(ev_roi)}  (per unit staked)")
        if ev_odd:
            print(f"     avg_odd        : {ev_odd:.3f}")
    else:
        print(f"     {YELLOW}No picks with real bookmaker odds in this period.{RESET}")
        print(f"     {DIM}→ Activate odds fetching to track real ROI.{RESET}")

    # C. Simulated P/L warning (shown only when no-odds picks exist)
    if no_odds_count > 0 and total_wl > 0:
        sim_roi = pl / max(total_wl, 1) * 100
        print(f"\n  {BOLD}{YELLOW}C. Simulated P/L  ({total_wl} picks, odd defaulted to ~1.0){RESET}")
        print(f"     sim_profit_loss: {_color_pl(pl)}  {DIM}[UNRELIABLE — no real odds]{RESET}")
        print(f"     sim_roi        : {_color_roi(sim_roi)}  {DIM}[UNRELIABLE]{RESET}")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 3+4 — Break-even analysis + Market viability
    # ══════════════════════════════════════════════════════════════════════════
    be_data = repo.get_market_break_even(days=days, since_date=_since)
    if be_data:
        print(f"\n  {BOLD}── PHASE 3+4 — Break-even & Viability {'─'*27}{RESET}")
        hdr = f"  {'Market':<22}  {'Stat':<11}  {'AvgOdd':>7}  {'BE%':>6}  {'Edge':>7}  Viability"
        print(hdr)
        print(f"  {'─'*66}")
        for row in be_data:
            mk     = (row["market"] or "?")[:21]
            stat_s = f"{row['stat_wins']}/{row['stat_total']} ({row['stat_hit_rate']:.0f}%)"
            avg_o  = f"{row['ev_avg_odd']:.2f}"  if row["ev_avg_odd"]       else "  N/A"
            be_s   = f"{row['break_even_rate']:.1f}%" if row["break_even_rate"] else "  N/A"
            ev     = row["edge_vs_break_even"]
            if ev is None:
                e_s, e_c = "   N/A", DIM
            elif ev > 0:
                e_s, e_c = f"+{ev:.1f}%", GREEN
            else:
                e_s, e_c = f"{ev:.1f}%",  RED
            vis    = row["viability"]
            v_c    = VIABILITY_COLOR.get(vis, RESET)
            print(f"  {mk:<22}  {stat_s:<11}  {avg_o:>7}  {be_s:>6}  "
                  f"{e_c}{e_s:>7}{RESET}  {v_c}{vis}{RESET}")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 5 — Accuracy by tier + top leagues
    # ══════════════════════════════════════════════════════════════════════════
    tier_data = repo.get_tier_performance(since_date=_since)
    if tier_data:
        print(f"\n  {BOLD}── PHASE 5 — Accuracy par tier {'─'*34}{RESET}")
        for row in tier_data:
            tier = row.get("tier") or row.get("statistical_tier") or "?"
            tw   = int(row.get("total_wins", 0))
            tl   = int(row.get("total_losses", 0))
            ev_t = int(row.get("ev_total", 0))
            print(f"    {tier:<12}: {_hr(tw, tw + tl):<14}  "
                  f"ev_picks:{ev_t}  "
                  f"pl:{_color_pl(float(row.get('total_profit_loss') or 0))}")

    lg_data = repo.get_league_profitability(limit=10, since_date=_since)
    if lg_data:
        top = sorted(lg_data, key=lambda x: -int(x.get("total_wins", 0)))
        print(f"\n  {BOLD}── Top ligues par accuracy {'─'*38}{RESET}")
        for row in top[:10]:
            lw  = int(row.get("total_wins",  0))
            ll  = int(row.get("total_losses", 0))
            lev = int(row.get("ev_total", 0))
            print(f"    {row.get('league','?')[:32]:<34}: "
                  f"{_hr(lw, lw + ll):<12}  ev:{lev}")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 6 — Odds Source Breakdown
    # ══════════════════════════════════════════════════════════════════════════
    try:
        src_data = _get_odds_source_breakdown(
            repo, days=days, since_date=_since,
            selection_mode="LIVE_SAFE" if safe_mode else None
        )
        if src_data:
            phase6_label = "LIVE_SAFE Source Breakdown" if safe_mode else "ALL POST_RESET Source Breakdown"
            print(f"\n  {BOLD}── PHASE 6 — {phase6_label} {'─'*29}{RESET}")
            print(f"  {'Source':<16}  {'Picks':>5}  {'Settled':>7}  {'Wins':>4}  "
                  f"{'ROI':>7}  {'AvgOdd':>7}")
            print(f"  {'─'*16}  {'─'*5}  {'─'*7}  {'─'*4}  {'─'*7}  {'─'*7}")
            for src, d in sorted(src_data.items()):
                n_picks   = d["picks"]
                n_settled = d["settled"]
                n_wins    = d["wins"]
                roi       = d["roi"]
                avg_odd   = d["avg_odd"]
                src_color = (GREEN if src == "API_FOOTBALL" else
                             CYAN  if "odds_api" in src.lower() else
                             YELLOW if src == "NO_ODDS" else RESET)
                roi_str   = _color_roi(roi) if n_settled > 0 else f"{DIM}N/A{RESET}"
                odd_str   = f"{avg_odd:.3f}" if avg_odd else f"{DIM}N/A{RESET}"
                print(f"  {src_color}{src:<16}{RESET}  {n_picks:>5}  {n_settled:>7}  "
                      f"{n_wins:>4}  {roi_str:>7}  {odd_str:>7}")
    except Exception as _src_err:
        pass  # non-blocking

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 7 — Event Mode Performance
    # ══════════════════════════════════════════════════════════════════════════
    try:
        # Query event context breakdown
        if _since:
            cutoff = _since
            if "T" in cutoff:
                q = repo._client.table("predictions").select(
                    "event_context, event_name, status, profit_loss, bookmaker_odd, selection_mode"
                ).in_("status", ["WON", "LOST"]).gte("created_at", cutoff)
            else:
                q = repo._client.table("predictions").select(
                    "event_context, event_name, status, profit_loss, bookmaker_odd, selection_mode"
                ).in_("status", ["WON", "LOST"]).gte("prediction_date", cutoff)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=days)).isoformat()
            q = repo._client.table("predictions").select(
                "event_context, event_name, status, profit_loss, bookmaker_odd, selection_mode"
            ).in_("status", ["WON", "LOST"]).gte("prediction_date", cutoff)

        if safe_mode:
            q = q.eq("selection_mode", "LIVE_SAFE")

        rows = q.execute().data or []

        if rows:
            # Group by event context
            event_data = {}
            for r in rows:
                ctx = r.get("event_context") or "DOMESTIC_LEAGUE"
                if ctx not in event_data:
                    event_data[ctx] = {
                        "picks": 0,
                        "settled": 0,
                        "wins": 0,
                        "pl": 0.0,
                        "with_odd": 0
                    }
                event_data[ctx]["picks"] += 1
                event_data[ctx]["settled"] += 1
                if r.get("status") == "WON":
                    event_data[ctx]["wins"] += 1
                event_data[ctx]["pl"] += r.get("profit_loss") or 0
                if r.get("bookmaker_odd"):
                    event_data[ctx]["with_odd"] += 1

            # Calculate ROI
            for ctx, d in event_data.items():
                if d["with_odd"] > 0:
                    d["roi"] = d["pl"] / d["with_odd"] * 100
                else:
                    d["roi"] = 0.0
                d["accuracy"] = d["wins"] / d["settled"] * 100 if d["settled"] > 0 else 0.0

            print(f"\n  {BOLD}── PHASE 7 — Event Mode Performance {'─'*33}{RESET}")
            print(f"  {'Event Context':<25}  {'Picks':>5}  {'Settled':>7}  {'Wins':>4}  "
                  f"{'Acc':>6}  {'ROI':>7}  {'P/L':>7}")
            print(f"  {'─'*25}  {'─'*5}  {'─'*7}  {'─'*4}  {'─'*6}  {'─'*7}  {'─'*7}")
            for ctx, d in sorted(event_data.items()):
                acc_str = f"{d['accuracy']:.1f}%" if d['settled'] > 0 else "N/A"
                roi_str = _color_roi(d['roi']) if d['with_odd'] > 0 else f"{DIM}N/A{RESET}"
                pl_str = _color_pl(d['pl'])
                ctx_color = (CYAN if ctx == "DOMESTIC_LEAGUE" else
                            GREEN if ctx == "WORLD_CUP" else
                            YELLOW if "FRIENDLY" in ctx else RESET)
                print(f"  {ctx_color}{ctx:<25}{RESET}  {d['picks']:>5}  {d['settled']:>7}  "
                      f"{d['wins']:>4}  {acc_str:>6}  {roi_str:>7}  {pl_str:>7}")
    except Exception as _event_err:
        pass  # non-blocking (event columns may not exist yet)

    # ══════════════════════════════════════════════════════════════════════════
    # EVENT MODE SUMMARY (PHASE 8)
    # ══════════════════════════════════════════════════════════════════════════
    try:
        # Get EVENT_MODE data
        event_query = repo._client.table("predictions").select(
            "event_context, status, profit_loss, bookmaker_odd"
        ).gte("prediction_date", cutoff_date)

        event_rows = event_query.execute().data or []

        if event_rows:
            # Group by event context
            event_summary = {}
            for row in event_rows:
                ctx = row.get("event_context", "DOMESTIC_LEAGUE")
                if ctx not in event_summary:
                    event_summary[ctx] = {"picks": 0, "settled": 0, "wins": 0, "pl": 0.0, "with_odd": 0}
                
                event_summary[ctx]["picks"] += 1
                
                if row.get("status") in ("WON", "LOST"):
                    event_summary[ctx]["settled"] += 1
                    if row.get("status") == "WON":
                        event_summary[ctx]["wins"] += 1
                    
                    # Calculate P/L
                    if row.get("bookmaker_odd"):
                        pl = _calc_pl(row.get("status"), row.get("bookmaker_odd"))
                        event_summary[ctx]["pl"] += pl
                        event_summary[ctx]["with_odd"] += 1

            # Calculate metrics
            for ctx, d in event_summary.items():
                if d["with_odd"] > 0:
                    d["roi"] = d["pl"] / d["with_odd"] * 100
                else:
                    d["roi"] = 0.0
                d["accuracy"] = d["wins"] / d["settled"] * 100 if d["settled"] > 0 else 0.0

            print(f"\n  {BOLD}── EVENT MODE SUMMARY {'─'*38}{RESET}")
            print(f"  {'Category':<25}  {'Picks':>5}  {'Settled':>7}  {'Wins':>4}  "
                  f"{'Acc':>6}  {'ROI':>7}  {'P/L':>7}")
            print(f"  {'─'*25}  {'─'*5}  {'─'*7}  {'─'*4}  {'─'*6}  {'─'*7}  {'─'*7}")
            
            # Domestic summary
            domestic_data = event_summary.get("DOMESTIC_LEAGUE", {})
            if domestic_data:
                acc_str = f"{domestic_data['accuracy']:.1f}%" if domestic_data['settled'] > 0 else "N/A"
                roi_str = _color_roi(domestic_data['roi']) if domestic_data['with_odd'] > 0 else f"{DIM}N/A{RESET}"
                pl_str = _color_pl(domestic_data['pl'])
                print(f"  {CYAN}Domestic:{' ' * 20}{RESET}  {domestic_data['picks']:>5}  {domestic_data['settled']:>7}  "
                      f"{domestic_data['wins']:>4}  {acc_str:>6}  {roi_str:>7}  {pl_str:>7}")
            
            # Events summary
            event_picks = sum(d["picks"] for ctx, d in event_summary.items() if ctx != "DOMESTIC_LEAGUE")
            event_settled = sum(d["settled"] for ctx, d in event_summary.items() if ctx != "DOMESTIC_LEAGUE")
            event_wins = sum(d["wins"] for ctx, d in event_summary.items() if ctx != "DOMESTIC_LEAGUE")
            event_pl = sum(d["pl"] for ctx, d in event_summary.items() if ctx != "DOMESTIC_LEAGUE")
            event_with_odd = sum(d["with_odd"] for ctx, d in event_summary.items() if ctx != "DOMESTIC_LEAGUE")
            
            if event_picks > 0:
                event_acc = (event_wins / event_settled * 100) if event_settled > 0 else 0.0
                event_roi = (event_pl / event_with_odd * 100) if event_with_odd > 0 else 0.0
                acc_str = f"{event_acc:.1f}%" if event_settled > 0 else "N/A"
                roi_str = _color_roi(event_roi) if event_with_odd > 0 else f"{DIM}N/A{RESET}"
                pl_str = _color_pl(event_pl)
                print(f"  {GREEN}Events:{' ' * 21}{RESET}  {event_picks:>5}  {event_settled:>7}  "
                      f"{event_wins:>4}  {acc_str:>6}  {roi_str:>7}  {pl_str:>7}")
            
            # International Friendlies
            friendly_data = event_summary.get("INTERNATIONAL_FRIENDLY", {})
            if friendly_data:
                acc_str = f"{friendly_data['accuracy']:.1f}%" if friendly_data['settled'] > 0 else "N/A"
                roi_str = _color_roi(friendly_data['roi']) if friendly_data['with_odd'] > 0 else f"{DIM}N/A{RESET}"
                pl_str = _color_pl(friendly_data['pl'])
                print(f"  {YELLOW}Friendlies:{' ' * 18}{RESET}  {friendly_data['picks']:>5}  {friendly_data['settled']:>7}  "
                      f"{friendly_data['wins']:>4}  {acc_str:>6}  {roi_str:>7}  {pl_str:>7}")
            
            # World Cup
            world_cup_data = event_summary.get("WORLD_CUP", {})
            if world_cup_data:
                acc_str = f"{world_cup_data['accuracy']:.1f}%" if world_cup_data['settled'] > 0 else "N/A"
                roi_str = _color_roi(world_cup_data['roi']) if world_cup_data['with_odd'] > 0 else f"{DIM}N/A{RESET}"
                pl_str = _color_pl(world_cup_data['pl'])
                print(f"  {GREEN}World Cup:{' ' * 18}{RESET}  {world_cup_data['picks']:>5}  {world_cup_data['settled']:>7}  "
                      f"{world_cup_data['wins']:>4}  {acc_str:>6}  {roi_str:>7}  {pl_str:>7}")

    except Exception as _event_summary_err:
        pass  # non-blocking (event columns may not exist yet)

    print(f"\n{'═'*66}\n")

    return {
        "total_won":       wins,      "total_lost":     losses,
        "total_void":      void_,     "total_pending":  pending,
        "stat_hit_rate":   round(hr, 2),
        "ev_total":        ev_total,  "ev_roi":         round(ev_roi, 2),
        "ev_profit_loss":  round(ev_pl, 4),
        "sim_profit_loss": round(pl, 4),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Performance report from Supabase")
    parser.add_argument("--days",         type=int,  default=30,
                        help="Lookback window in days (default: 30)")
    parser.add_argument("--since-reset",  action="store_true", dest="since_reset",
                        help="Filter from TRACKING_RESET_AT in .env (fresh view)")
    args = parser.parse_args()
    run(days=args.days, since_reset=args.since_reset)
