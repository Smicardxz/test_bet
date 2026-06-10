"""
audit_bettable_universe.py — Bettable Universe Diagnostic (READ-ONLY)
======================================================================
Audits predictions from the last 24h and classifies them by universe.
Shows odds coverage, bettable league priority, and EV exploitability.

Usage:
    python audit_bettable_universe.py
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

# ─── Console colors ────────────────────────────────────────────────────────────
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
R  = "\033[91m"   # red
B  = "\033[94m"   # blue
C  = "\033[96m"   # cyan
D  = "\033[90m"   # dark gray
X  = "\033[0m"    # reset
BLD = "\033[1m"


def sec(title: str) -> None:
    print(f"\n{'=' * 68}")
    print(f"  {BLD}{title}{X}")
    print(f"{'-' * 68}")


def bar(n: int, total: int, width: int = 28) -> str:
    filled = int(round(n / max(total, 1) * width))
    return "█" * filled + "░" * (width - filled)


def pct(n: int, d: int) -> str:
    return f"{n/d*100:5.1f}%" if d else "  N/A "


# ─── Supabase connection ───────────────────────────────────────────────────────

def _get_rows(hours: int = 24) -> List[dict]:
    try:
        from app.database.supabase_config import get_supabase_config
        cfg = get_supabase_config()
        if not cfg.supabase_connected:
            print(f"{R}[SUPABASE] Connection failed: {cfg.supabase_error}{X}")
            return []
        client = cfg.get_client()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        resp = (
            client.table("predictions")
            .select(
                "prediction_id,fixture_id,home_team,away_team,league,country,"
                "market,statistical_tier,ev_tier,confidence_score,bookmaker_odd,"
                "prediction_date,status,"
                "market_access,bettable_priority_score,odds_coverage_score,"
                "market_liquidity_score,bettable_tier,"
                "market_regime,recommended_market_direction,best_market,"
                "best_over_market,best_under_market"
            )
            .gte("prediction_date", since[:10])
            .order("confidence_score", desc=True)
            .limit(500)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        print(f"{R}[SUPABASE] Error: {exc}{X}")
        return []


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _access(r: dict) -> str:
    return (r.get("market_access") or "RESEARCH_ONLY").upper()


def _has_odds(r: dict) -> bool:
    return bool(r.get("bookmaker_odd")) or (r.get("odds_coverage_score") or 0) >= 55


# ─── Main ──────────────────────────────────────────────────────────────────────

def run() -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'=' * 68}")
    print(f"  {BLD}AUDIT BETTABLE UNIVERSE — {now_str} (READ-ONLY){X}")
    print(f"{'=' * 68}")

    rows = _get_rows(hours=24)
    if not rows:
        print(f"\n  {Y}No predictions found in last 24h.{X}")
        print(f"  Run: python start.py   then retry.\n")
        return

    total = len(rows)
    print(f"\n  {C}{total}{X} predictions analysées (dernieres 24h)\n")

    # Universe detection
    has_new = "market_access" in (rows[0] if rows else {})

    # ── PHASE 1 — Universe distribution ───────────────────────────────────────
    sec("PHASE 1 — UNIVERSE DISTRIBUTION")

    if not has_new:
        print(f"\n  {Y}Champ market_access absent de Supabase.{X}")
        print(f"  Executer : app/database/migrations/add_bettable_universe_columns.sql")
        print(f"  Puis relancer un cycle.")
        access_counts: Dict[str, int] = {"RESEARCH_ONLY": total}
    else:
        access_counts = defaultdict(int)
        for r in rows:
            access_counts[_access(r)] += 1

    cols = {"BETTABLE": G, "LIMITED": Y, "RESEARCH_ONLY": R}
    print(f"\n  {'Universe':<20} {'N':>4}  {'%':>5}  Bar")
    print(f"  {'-'*20} {'-'*4}  {'-'*5}  {'-'*28}")
    for access, col in cols.items():
        cnt = access_counts.get(access, 0)
        print(f"  {col}{access:<20}{X} {cnt:>4}  {pct(cnt, total)}  {col}{bar(cnt, total)}{X}")

    n_bettable = access_counts.get("BETTABLE", 0)
    n_limited  = access_counts.get("LIMITED", 0)
    n_research = access_counts.get("RESEARCH_ONLY", 0)

    # ── PHASE 2 — Odds coverage ────────────────────────────────────────────────
    sec("PHASE 2 — ODDS COVERAGE")

    total_with_odds = sum(1 for r in rows if _has_odds(r))
    bettable_with_odds  = sum(1 for r in rows if _access(r) == "BETTABLE" and _has_odds(r))
    limited_with_odds   = sum(1 for r in rows if _access(r) == "LIMITED"  and _has_odds(r))
    research_with_odds  = sum(1 for r in rows if _access(r) == "RESEARCH_ONLY" and _has_odds(r))

    print(f"\n  Global odds coverage        : {C}{total_with_odds:>4}{X} / {total}  ({pct(total_with_odds, total)})")
    print(f"  BETTABLE  avec odds         : {G}{bettable_with_odds:>4}{X} / {max(n_bettable,1)}  ({pct(bettable_with_odds, max(n_bettable,1))})")
    print(f"  LIMITED   avec odds         : {Y}{limited_with_odds:>4}{X} / {max(n_limited,1)}  ({pct(limited_with_odds, max(n_limited,1))})")
    print(f"  RESEARCH  avec odds         : {R}{research_with_odds:>4}{X} / {max(n_research,1)}  ({pct(research_with_odds, max(n_research,1))})")

    if has_new:
        avg_cov = sum(r.get("odds_coverage_score") or 0 for r in rows) / total
        avg_prio = sum(r.get("bettable_priority_score") or 0 for r in rows) / total
        print(f"\n  avg odds_coverage_score     : {C}{avg_cov:.1f}/100{X}")
        print(f"  avg bettable_priority_score : {G}{avg_prio:.1f}/100{X}")

    # ── PHASE 3 — Top ligues par couverture ────────────────────────────────────
    sec("PHASE 3 — TOP LEAGUES PAR COUVERTURE BOOKMAKER")

    league_data: Dict[str, dict] = defaultdict(
        lambda: {"access": "RESEARCH_ONLY", "n": 0, "odds": 0, "prio": 0, "country": ""}
    )
    for r in rows:
        lg = (r.get("league") or "?")[:35]
        d  = league_data[lg]
        d["n"]       += 1
        d["odds"]    += 1 if _has_odds(r) else 0
        d["prio"]    += r.get("bettable_priority_score") or 0
        d["country"]  = r.get("country") or d["country"]
        # BETTABLE > LIMITED > RESEARCH_ONLY
        cur = d["access"]
        new = _access(r)
        if new == "BETTABLE" or (new == "LIMITED" and cur == "RESEARCH_ONLY"):
            d["access"] = new

    leagues_sorted = sorted(league_data.items(), key=lambda x: (-x[1]["odds"], -x[1]["prio"]))

    with_odds    = [(lg, d) for lg, d in leagues_sorted if d["odds"] > 0]
    without_odds = [(lg, d) for lg, d in leagues_sorted if d["odds"] == 0]

    print(f"\n  {G}Ligues AVEC odds bookmaker :{X}")
    if with_odds:
        print(f"  {'Ligue':<35} {'Country':<16} {'N':>3}  {'Odds':>4}  {'OddsPct':>7}  {'Access'}")
        print(f"  {'-'*35} {'-'*16} {'-'*3}  {'-'*4}  {'-'*7}  {'-'*13}")
        for lg, d in with_odds[:20]:
            col = G if d["access"] == "BETTABLE" else (Y if d["access"] == "LIMITED" else R)
            print(f"  {col}{lg:<35}{X} {d['country']:<16} {d['n']:>3}  {d['odds']:>4}  {pct(d['odds'],d['n'])}  {col}{d['access']}{X}")
    else:
        print(f"  {R}  Aucune ligue avec odds aujourd'hui.{X}")

    print(f"\n  {R}Ligues SANS odds (top 15 par volume) :{X}")
    if without_odds:
        print(f"  {'Ligue':<35} {'Country':<16} {'N':>3}  Access")
        print(f"  {'-'*35} {'-'*16} {'-'*3}  {'-'*13}")
        for lg, d in without_odds[:15]:
            col = G if d["access"] == "BETTABLE" else (Y if d["access"] == "LIMITED" else D)
            print(f"  {col}{lg:<35}{X} {d['country']:<16} {d['n']:>3}  {col}{d['access']}{X}")
    else:
        print(f"  {G}  Toutes les ligues ont des odds aujourd'hui !{X}")

    # ── PHASE 4 — Country breakdown ────────────────────────────────────────────
    sec("PHASE 4 — COUNTRY COVERAGE")

    country_data: Dict[str, dict] = defaultdict(lambda: {"n": 0, "odds": 0, "bettable": 0})
    for r in rows:
        c = (r.get("country") or "Unknown")[:25]
        country_data[c]["n"]       += 1
        country_data[c]["odds"]    += 1 if _has_odds(r) else 0
        country_data[c]["bettable"] += 1 if _access(r) == "BETTABLE" else 0

    countries_sorted = sorted(country_data.items(), key=lambda x: (-x[1]["odds"], -x[1]["n"]))

    print(f"\n  {'Country':<25} {'N':>3}  {'Odds':>4}  {'OddsPct':>7}  Bar")
    print(f"  {'-'*25} {'-'*3}  {'-'*4}  {'-'*7}  {'-'*16}")
    for c, d in countries_sorted[:25]:
        col = G if d["bettable"] > 0 else (Y if d["odds"] > 0 else D)
        print(f"  {col}{c:<25}{X} {d['n']:>3}  {d['odds']:>4}  {pct(d['odds'],d['n'])}  {col}{bar(d['odds'], max(d['n'],1), 16)}{X}")

    # ── PHASE 5 — Bettable picks ───────────────────────────────────────────────
    sec("PHASE 5 — TOP BETTABLE PICKS (priorité + odds)")

    bettable = [r for r in rows if _access(r) == "BETTABLE"]
    if bettable:
        bettable_sorted = sorted(
            bettable,
            key=lambda r: (-(r.get("bettable_priority_score") or 0),
                           -(r.get("confidence_score") or 0))
        )[:20]
        print(f"\n  {'#':>2}  {'League':<22}  {'Market':<18}  {'Tier':<18}  {'Prio':>4}  {'Conf':>4}  {'Odds':>5}  Dir")
        print(f"  {'--':>2}  {'-'*22}  {'-'*18}  {'-'*18}  {'-'*4}  {'-'*4}  {'-'*5}  ---")
        for i, r in enumerate(bettable_sorted, 1):
            bt    = (r.get("bettable_tier") or "?")[:18]
            mkt   = (r.get("market") or "?")[:18]
            lg    = (r.get("league") or "?")[:22]
            prio  = r.get("bettable_priority_score") or 0
            conf  = r.get("confidence_score") or 0
            odd   = r.get("bookmaker_odd") or 0
            dirn  = (r.get("recommended_market_direction") or "?")[:6]
            col   = G if "_EV" in bt else Y
            dcol  = G if dirn == "OVER" else (Y if "UNDER" in dirn else D)
            print(f"  {i:>2}  {D}{lg:<22}{X}  {col}{mkt:<18}{X}  {col}{bt:<18}{X}  {prio:>4}  {conf:>4.0f}  {odd:>5.2f}  {dcol}{dirn}{X}")
    else:
        print(f"\n  {Y}Aucun pick BETTABLE dans les 24h.{X}")
        print(f"  Causes possibles :")
        print(f"    - Migration SQL pas encore jouée")
        print(f"    - Aucun match des ligues BETTABLE scané aujourd'hui")
        print(f"    - LeagueTargetingService ne cible pas encore ces ligues")

    # ── PHASE 6 — EV exploitable ───────────────────────────────────────────────
    sec("PHASE 6 — EV EXPLOITABLE (BETTABLE + odds + S/A TIER)")

    ev_exploitable = [
        r for r in rows
        if _access(r) == "BETTABLE"
        and _has_odds(r)
        and (r.get("bettable_tier") or "").endswith("_EV")
    ]
    ev_statistical = [
        r for r in rows
        if (r.get("bettable_tier") or "").endswith("_STATISTICAL")
        and (r.get("statistical_tier") or "") in ("S_TIER", "A_TIER")
    ]

    print(f"\n  {G}Picks S/A_TIER_EV (BETTABLE + odds)    : {len(ev_exploitable):>4}{X}")
    print(f"  {Y}Picks S/A_TIER_STATISTICAL (no odds)   : {len(ev_statistical):>4}{X}")
    print(f"  {R}Picks RESEARCH_ONLY                    : {n_research:>4}{X}")

    if ev_exploitable:
        print(f"\n  {G}TOP EV exploitable :{X}")
        for r in ev_exploitable[:10]:
            lg  = (r.get("league") or "?")[:25]
            mkt = (r.get("market") or "?")[:18]
            odd = r.get("bookmaker_odd") or 0
            bt  = r.get("bettable_tier") or "?"
            print(f"  {G}  {lg:<25}  {mkt:<18}  odd={odd:.2f}  [{bt}]{X}")

    # ── PHASE 7 — Conclusion ───────────────────────────────────────────────────
    sec("PHASE 7 — CONCLUSION")

    print(f"\n  1. {B}Mismatch ligue/bookmaker :{X}")
    research_pct = n_research / total * 100 if total else 0
    if research_pct > 60:
        print(f"     {R}CRITIQUE{X} — {research_pct:.1f}% des predictions sont RESEARCH_ONLY.")
        print(f"     Les ligues analysées sont majoritairement non-couvertes par les bookmakers.")
    elif research_pct > 30:
        print(f"     {Y}MODERE{X} — {research_pct:.1f}% RESEARCH_ONLY. Optimisation possible.")
    else:
        print(f"     {G}BON{X} — {research_pct:.1f}% RESEARCH_ONLY. Universe bien équilibré.")

    print(f"\n  2. {B}EV réellement exploitable :{X}")
    if ev_exploitable:
        print(f"     {G}OUI{X} — {len(ev_exploitable)} picks avec odds réels en univers BETTABLE.")
    elif n_bettable > 0:
        print(f"     {Y}PARTIEL{X} — {n_bettable} picks BETTABLE mais sans odds matchés.")
        print(f"     Vérifier : The Odds API coverage sur ces ligues.")
    else:
        print(f"     {R}NON{X} — 0 pick BETTABLE détecté.")
        if not has_new:
            print(f"     Migration SQL requise : app/database/migrations/add_bettable_universe_columns.sql")
        else:
            print(f"     Le targeting ne cible pas encore les ligues BETTABLE en priorité.")

    print(f"\n  3. {B}Recommandation :{X}")
    if research_pct > 50:
        print(f"     Orienter LeagueTargetingService vers les pays BETTABLE.")
        print(f"     {C}Pays prioritaires : Japan, Korea, Brazil, Argentina, Poland,{X}")
        print(f"     {C}Colombia, Chile, Czech Rep., Croatia, Sweden, Norway, Finland.{X}")
    else:
        print(f"     {G}Distribution acceptable.{X} Surveiller odds coverage au prochain cycle.")

    print(f"\n{'=' * 68}\n")


if __name__ == "__main__":
    run()
