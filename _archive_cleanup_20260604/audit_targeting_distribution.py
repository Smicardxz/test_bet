"""
audit_targeting_distribution.py — Targeting Priority Diagnostic (READ-ONLY)
=============================================================================
Simulates the coverage priority scoring for ALL leagues visible in Supabase
predictions from the last 48h and reports PRIORITY_A/B/C distribution.

Usage:
    python audit_targeting_distribution.py
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

# ─── Console colors ────────────────────────────────────────────────────────────
G   = "\033[92m"
Y   = "\033[93m"
R   = "\033[91m"
B   = "\033[94m"
C   = "\033[96m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"


def sec(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {BLD}{title}{X}")
    print(f"{'-' * 70}")


def bar(n: int, total: int, width: int = 30) -> str:
    filled = int(round(n / max(total, 1) * width))
    return "█" * filled + "░" * (width - filled)


def pct(n: int, d: int) -> str:
    return f"{n/d*100:5.1f}%" if d else "  N/A "


# ─── Supabase rows ─────────────────────────────────────────────────────────────

def _get_rows(hours: int = 48) -> List[dict]:
    try:
        from app.database.supabase_config import get_supabase_config
        cfg = get_supabase_config()
        if not cfg.supabase_connected:
            print(f"{R}[SUPABASE] {cfg.supabase_error}{X}")
            return []
        client = cfg.get_client()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        resp = (
            client.table("predictions")
            .select("league,country,market_access,bettable_priority_score,"
                    "odds_coverage_score,market_liquidity_score,bettable_tier,"
                    "bookmaker_odd,confidence_score,prediction_date")
            .gte("prediction_date", since[:10])
            .limit(1000)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        print(f"{R}[SUPABASE] {exc}{X}")
        return []


# ─── Simulate LeagueTargetingService scoring on a league name ──────────────────

def _simulate_priority(country: str, league: str) -> dict:
    """Use the real LeagueTargetingService to compute the new target score."""
    try:
        from app.services.targeting.league_targeting_service import LeagueTargetingService
        svc = LeagueTargetingService()
        profile = svc.analyze_competition(league, country)
        return {
            "target_score":           profile.target_score,
            "coverage_priority":      profile.coverage_priority,
            "coverage_priority_score": profile.coverage_priority_score,
            "league_category":        profile.league_category,
        }
    except Exception:
        return {
            "target_score": 0,
            "coverage_priority": "C",
            "coverage_priority_score": 10,
            "league_category": "unknown",
        }


# ─── Main ──────────────────────────────────────────────────────────────────────

def run() -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'=' * 70}")
    print(f"  {BLD}AUDIT TARGETING DISTRIBUTION — {now_str} (READ-ONLY){X}")
    print(f"{'=' * 70}")

    rows = _get_rows(hours=48)
    if not rows:
        print(f"\n  {Y}No predictions found in last 48h. Run: python start.py{X}\n")
        return

    total = len(rows)
    print(f"\n  {C}{total}{X} predictions analysées (dernières 48h)\n")

    # Check if migration was run
    has_prio = "market_access" in (rows[0] if rows else {})

    # ── PHASE 1 — Supabase universe distribution (persisted data) ─────────────
    sec("PHASE 1 — DISTRIBUTION UNIVERSE (Supabase)")

    if has_prio:
        access_cnt: Dict[str, int] = defaultdict(int)
        for r in rows:
            access_cnt[(r.get("market_access") or "RESEARCH_ONLY").upper()] += 1

        print(f"\n  {'Universe':<20} {'N':>4}  {'%':>6}  Bar")
        print(f"  {'-'*20} {'-'*4}  {'-'*6}  {'-'*30}")
        for acc, col in [("BETTABLE", G), ("LIMITED", Y), ("RESEARCH_ONLY", R)]:
            cnt = access_cnt.get(acc, 0)
            print(f"  {col}{acc:<20}{X} {cnt:>4}  {pct(cnt,total)}  {col}{bar(cnt,total)}{X}")

        avg_prio = sum(r.get("bettable_priority_score") or 0 for r in rows) / total
        print(f"\n  avg bettable_priority_score : {C}{avg_prio:.1f}/100{X}")

        # Target check
        n_bett = access_cnt.get("BETTABLE", 0)
        n_lim  = access_cnt.get("LIMITED", 0)
        n_res  = access_cnt.get("RESEARCH_ONLY", 0)
        bett_pct = n_bett / total * 100
        res_pct  = n_res  / total * 100

        print(f"\n  Cible visée        : BETTABLE > 40%  LIMITED > 20%  RESEARCH < 40%")
        b_col = G if bett_pct >= 40 else (Y if bett_pct >= 20 else R)
        r_col = G if res_pct  <= 40 else (Y if res_pct  <= 60 else R)
        print(f"  Résultat actuel    : BETTABLE={b_col}{bett_pct:.1f}%{X}  RESEARCH={r_col}{res_pct:.1f}%{X}")
    else:
        print(f"\n  {Y}Champ market_access absent → migration SQL requise.{X}")
        print(f"  Exécuter : app/database/migrations/add_bettable_universe_columns.sql")

    # ── PHASE 2 — Live simulation with new scoring ─────────────────────────────
    sec("PHASE 2 — SIMULATION SCORING (LeagueTargetingService actuel)")

    # Collect unique (country, league) pairs
    unique_leagues: Dict[tuple, dict] = {}
    for r in rows:
        key = (r.get("country") or "", r.get("league") or "")
        if key not in unique_leagues:
            unique_leagues[key] = {"count": 0}
        unique_leagues[key]["count"] += 1

    print(f"\n  Simulation de {len(unique_leagues)} ligues uniques...")
    scored: List[dict] = []
    for (country, league), meta in unique_leagues.items():
        sim = _simulate_priority(country, league)
        scored.append({
            "country": country,
            "league":  league,
            "count":   meta["count"],
            **sim,
        })
    scored.sort(key=lambda x: -x["target_score"])

    # PRIORITY_A/B/C distribution (simulated)
    prio_cnt: Dict[str, int] = defaultdict(int)
    prio_matches: Dict[str, int] = defaultdict(int)
    for s in scored:
        p = s["coverage_priority"]
        prio_cnt[p] += 1
        prio_matches[p] += s["count"]

    total_matches = sum(prio_matches.values()) or 1
    print(f"\n  {'Priority':<12} {'Ligues':>6}  {'Predictions':>11}  {'% preds':>7}  Bar")
    print(f"  {'-'*12} {'-'*6}  {'-'*11}  {'-'*7}  {'-'*30}")
    for prio, col in [("A", G), ("B", Y), ("C", R)]:
        nl = prio_cnt.get(prio, 0)
        nm = prio_matches.get(prio, 0)
        print(f"  {col}PRIORITY_{prio:<3}{X} {nl:>6}  {nm:>11}  {pct(nm,total_matches)}  {col}{bar(nm,total_matches)}{X}")

    # ── PHASE 3 — Top 20 leagues ───────────────────────────────────────────────
    sec("PHASE 3 — TOP 20 LIGUES PAR SCORE TARGETING (nouveau)")

    print(f"\n  {'#':>2}  {'Country':<18}  {'League':<35}  {'P':>1}  {'Score':>5}  {'CovPrio':>7}  {'N':>4}")
    print(f"  {'-'*2}  {'-'*18}  {'-'*35}  {'-'*1}  {'-'*5}  {'-'*7}  {'-'*4}")
    for i, s in enumerate(scored[:20], 1):
        prio = s["coverage_priority"]
        col  = G if prio == "A" else (Y if prio == "B" else R)
        print(
            f"  {i:>2}  {D}{s['country']:<18}{X}  {s['league']:<35}  "
            f"{col}{prio}{X}  {s['target_score']:>5.1f}  {s['coverage_priority_score']:>7.1f}  {s['count']:>4}"
        )

    # ── PHASE 4 — Top 20 countries ────────────────────────────────────────────
    sec("PHASE 4 — TOP 20 PAYS PAR PREDICTIONS")

    country_data: Dict[str, dict] = defaultdict(lambda: {
        "n": 0, "prio": {"A": 0, "B": 0, "C": 0}, "score_sum": 0
    })
    for s in scored:
        cd = country_data[s["country"]]
        cd["n"] += s["count"]
        cd["prio"][s["coverage_priority"]] += s["count"]
        cd["score_sum"] += s["target_score"] * s["count"]

    country_sorted = sorted(country_data.items(), key=lambda x: -x[1]["n"])

    print(f"\n  {'Country':<22}  {'N':>4}  {'PrioA':>5}  {'PrioB':>5}  {'PrioC':>5}  {'AvgScore':>8}")
    print(f"  {'-'*22}  {'-'*4}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*8}")
    for c, d in country_sorted[:20]:
        prio_a = d["prio"]["A"]
        prio_b = d["prio"]["B"]
        prio_c = d["prio"]["C"]
        avg_s  = d["score_sum"] / max(d["n"], 1)
        dom    = "A" if prio_a >= prio_b and prio_a >= prio_c else ("B" if prio_b >= prio_c else "C")
        col    = G if dom == "A" else (Y if dom == "B" else R)
        print(
            f"  {col}{c:<22}{X}  {d['n']:>4}  "
            f"{G}{prio_a:>5}{X}  {Y}{prio_b:>5}{X}  {R}{prio_c:>5}{X}  {avg_s:>8.1f}"
        )

    # ── PHASE 5 — Estimated future distribution ────────────────────────────────
    sec("PHASE 5 — ESTIMATION FUTURE DISTRIBUTION APRÈS TARGETING")

    # Weight by target_score: higher score = higher probability of being analyzed
    wt_a = sum(s["target_score"] * s["count"] for s in scored if s["coverage_priority"] == "A")
    wt_b = sum(s["target_score"] * s["count"] for s in scored if s["coverage_priority"] == "B")
    wt_c = sum(s["target_score"] * s["count"] for s in scored if s["coverage_priority"] == "C")
    wt_total = wt_a + wt_b + wt_c or 1

    p_a = wt_a / wt_total * 100
    p_b = wt_b / wt_total * 100
    p_c = wt_c / wt_total * 100

    print(f"\n  Projection (pondérée par target_score) :")
    print(f"  PRIORITY_A → {G}{p_a:.1f}%{X} des matches analysés  {G}[cible: >60%]{X}")
    print(f"  PRIORITY_B → {Y}{p_b:.1f}%{X} des matches analysés  {Y}[cible: 20-30%]{X}")
    print(f"  PRIORITY_C → {R}{p_c:.1f}%{X} des matches analysés  {R}[cible: <15%]{X}")

    ok_a = G if p_a >= 45 else (Y if p_a >= 25 else R)
    ok_c = G if p_c <= 20 else (Y if p_c <= 40 else R)
    status = "OBJECTIF ATTEINT" if p_a >= 45 and p_c <= 25 else "OBJECTIF PARTIEL"
    s_col  = G if p_a >= 45 and p_c <= 25 else Y
    print(f"\n  Statut : {s_col}{BLD}{status}{X}")

    # ── PHASE 6 — Conclusion ───────────────────────────────────────────────────
    sec("PHASE 6 — CONCLUSION")

    print(f"\n  1. {B}Distribution actuelle (Supabase 48h) :{X}")
    if has_prio:
        print(f"     BETTABLE={b_col}{bett_pct:.1f}%{X}  RESEARCH={r_col}{res_pct:.1f}%{X}")
    else:
        print(f"     {Y}Migration SQL requise pour afficher la distribution réelle.{X}")

    print(f"\n  2. {B}Projection après le prochain cycle :{X}")
    print(f"     PRIORITY_A: {ok_a}{p_a:.1f}%{X}  (cible 60%+)")
    print(f"     PRIORITY_C: {ok_c}{p_c:.1f}%{X}  (cible <15%)")

    print(f"\n  3. {B}Prochaine action :{X}")
    if p_a >= 50:
        print(f"     {G}Scoring OK — relancer python start.py pour tester sur de nouvelles données.{X}")
    else:
        print(f"     {Y}Scorer encore insuffisant. Vérifier :{X}")
        print(f"     - Les ligues PRIORITY_A scannées par l'API ce jour-là")
        print(f"     - Le nombre de matchs disponibles par country")
        top_c = [s["country"] for s in scored[:5] if s["coverage_priority"] == "C"]
        if top_c:
            print(f"     - PRIORITY_C encore dans le top 5 : {', '.join(top_c)}")

    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    run()
