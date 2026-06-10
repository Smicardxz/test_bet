"""
audit_multimarket_today.py — Diagnostic multi-market (READ-ONLY)
=================================================================
Audit factuel des predictions des dernieres 24h depuis Supabase.
Ne modifie rien. Ne recalibre rien.

Usage:
    python audit_multimarket_today.py
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import List, Dict

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"
B = "\033[1m"; D = "\033[2m"; X = "\033[0m"

OVER_SIGNALS = {
    "FT_OVER", "HT_OVER", "BTTS_PROFILE", "HOME_DOMINANT",
    "ASYMMETRIC_SCORING", "SECOND_HALF_EXPLOSION", "BTTS_YES",
}
UNDER_SIGNALS = {
    "FT_UNDER", "HT_UNDER", "EXTREME_UNDER", "LOW_VARIANCE", "BTTS_NO",
}

ALL_EXPECTED = [
    "HT_UNDER_0_5", "HT_UNDER_1_5",
    "HT_OVER_0_5", "HT_OVER_1_0", "HT_OVER_1_5",
    "FT_UNDER_1_5", "FT_UNDER_2_5", "FT_UNDER_3_5",
    "FT_OVER_1_5", "FT_OVER_2_5", "FT_OVER_3_5", "FT_OVER_4_5",
    "BTTS_YES", "BTTS_NO",
    "HOME_OVER_0_5", "AWAY_OVER_0_5",
    "SECOND_HALF_OVER_1_5",
    "FT_OVER", "HT_OVER", "BTTS_PROFILE",
    "HOME_DOMINANT", "ASYMMETRIC_SCORING", "SECOND_HALF_EXPLOSION",
    "FT_UNDER", "HT_UNDER", "EXTREME_UNDER", "LOW_VARIANCE",
]


def classify(m: str) -> str:
    if not m:
        return "OTHER"
    u = m.upper()
    if any(k in u for k in ["_OVER_", "BTTS_YES", "HOME_DOMINANT",
                             "ASYMMETRIC_SCORING", "SECOND_HALF_EXPLOSION",
                             "BTTS_PROFILE"]):
        return "OVER"
    if u in OVER_SIGNALS:
        return "OVER"
    if any(k in u for k in ["_UNDER_", "BTTS_NO", "EXTREME_UNDER", "LOW_VARIANCE"]):
        return "UNDER"
    if u in UNDER_SIGNALS:
        return "UNDER"
    return "OTHER"


def bar(n: int, t: int, w: int = 28) -> str:
    if t == 0:
        return " " * w
    f = int(n / t * w)
    return chr(0x2588) * f + chr(0x2591) * (w - f)


def sec(title: str):
    print(f"\n{'=' * 68}")
    print(f"{B}  {title}{X}")
    print(f"{'-' * 68}")


def fetch(client, hours: int = 24) -> List[Dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    try:
        resp = (
            client.table("predictions")
            .select("*")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"{R}  Query failed: {e}{X}")
        return []


def run():
    print(f"\n{B}{'=' * 68}{X}")
    print(f"{B}  AUDIT MULTI-MARKET — {datetime.now().strftime('%Y-%m-%d %H:%M')} (READ-ONLY){X}")
    print(f"{B}{'=' * 68}{X}")

    from app.database.supabase_config import get_supabase_config
    cfg = get_supabase_config()
    if not cfg.supabase_connected:
        print(f"{R}  ERREUR Supabase: {cfg.supabase_error}{X}")
        sys.exit(1)

    client = cfg.get_client()
    print(f"  {G}Supabase OK{X}  status={cfg.supabase_status}")

    rows = fetch(client, hours=24)
    total = len(rows)
    if total == 0:
        print(f"\n{Y}  Aucune prediction dans les 24 dernieres heures.{X}")
        print(f"  Lance python start.py pour generer un scan avec les nouvelles modifications.")
        return

    print(f"\n  {C}Predictions (24h) : {B}{total}{X}   "
          f"pending={sum(1 for r in rows if r.get('status')=='PENDING')}  "
          f"won={sum(1 for r in rows if r.get('status')=='WON')}  "
          f"lost={sum(1 for r in rows if r.get('status')=='LOST')}")

    mkt_counts  = defaultdict(int)
    mkt_tiers   = defaultdict(list)
    mkt_conf    = defaultdict(list)
    over_rows   = []
    under_rows  = []
    other_rows  = []

    for r in rows:
        m    = (r.get("market") or "UNKNOWN").upper()
        tier = r.get("statistical_tier") or r.get("ev_tier") or "UNRANKED"
        conf = r.get("confidence_score") or 0.0
        mkt_counts[m] += 1
        mkt_tiers[m].append(tier)
        mkt_conf[m].append(conf)
        cat = classify(m)
        (over_rows if cat == "OVER" else under_rows if cat == "UNDER" else other_rows).append(r)

    n_over  = len(over_rows)
    n_under = len(under_rows)
    n_other = len(other_rows)

    # ── PHASE 1 ───────────────────────────────────────────────────────────────
    sec("PHASE 1 — DISTRIBUTION DES MARCHES (24h)")
    print(f"\n  {'Marche':<28} {'N':>4}  {'%':>5}  {'Direction':>8}  Bar")
    print(f"  {'-'*28} {'-'*4}  {'-'*5}  {'-'*8}  {'-'*28}")
    seen = set()
    for m, cnt in sorted(mkt_counts.items(), key=lambda x: -x[1]):
        pct = cnt / total * 100
        cat = classify(m)
        col = G if cat == "OVER" else (Y if cat == "UNDER" else D)
        tl  = max(set(mkt_tiers[m]), key=mkt_tiers[m].count) if mkt_tiers[m] else "?"
        print(f"  {col}{m:<28}{X} {cnt:>4}  {pct:>4.1f}%  {col}{cat:>8}{X}  {col}{bar(cnt, total)}{X}  {D}{tl}{X}")
        seen.add(m)
    # Zero markets
    zeros = [m for m in ALL_EXPECTED if m.upper() not in seen]
    if zeros:
        print(f"\n  {Y}Marches attendus avec 0 prediction :{X}")
        for m in zeros:
            cat = classify(m)
            col = G if cat == "OVER" else (Y if cat == "UNDER" else D)
            print(f"  {col}  {m}{X}")

    print(f"\n  {B}Direction globale :{X}")
    print(f"  {G}OVER  : {n_over:>4}  ({n_over/total*100:>5.1f}%)  {bar(n_over, total)}{X}")
    print(f"  {Y}UNDER : {n_under:>4}  ({n_under/total*100:>5.1f}%)  {bar(n_under, total)}{X}")
    print(f"  {D}AUTRE : {n_other:>4}  ({n_other/total*100:>5.1f}%)  {bar(n_other, total)}{X}")

    # ── PHASE 2 ───────────────────────────────────────────────────────────────
    sec("PHASE 2 — MARKET RANKING AUDIT")

    # Check if new fields are present
    sample = rows[0] if rows else {}
    has_new_fields = "market_regime" in sample

    if not has_new_fields:
        print(f"\n  {Y}Nouveaux champs pas encore en DB.{X}")
        print(f"  Executer la migration SQL : app/database/migrations/add_multimarket_columns.sql")
        print(f"  Puis relancer un cycle scan.")
    else:
        # Generated vs Selected stats
        total_gen = total_sel = total_rej = 0
        mkt_gen_detail: Dict[str, dict] = defaultdict(lambda: {"gen": 0, "sel": 0, "rej": 0})
        rej_reason_counts: Dict[str, int] = defaultdict(int)

        for r in rows:
            stats = r.get("market_generation_stats") or {}
            if isinstance(stats, str):
                import json as _json
                try: stats = _json.loads(stats)
                except: stats = {}
            total_gen += stats.get("generated_count", 0)
            total_sel += stats.get("selected_count", 0)
            total_rej += stats.get("rejected_count", 0)

            reasons = r.get("rejection_reasons_by_market") or {}
            if isinstance(reasons, str):
                try: reasons = _json.loads(reasons)
                except: reasons = {}
            for mkt, reason in reasons.items():
                rej_reason_counts[reason] += 1

        print(f"\n  {B}Stats generation globale (cumul {total} predictions) :{X}")
        print(f"  Generated : {C}{total_gen}{X}  Selected : {G}{total_sel}{X}  Rejected : {Y}{total_rej}{X}")
        if total_gen > 0:
            sel_pct = total_sel / total_gen * 100
            rej_pct = total_rej / total_gen * 100
            print(f"  Selection rate : {G}{sel_pct:.1f}%{X}   Rejection rate : {Y}{rej_pct:.1f}%{X}")

        if rej_reason_counts:
            print(f"\n  {B}Raisons de rejet :{X}")
            for reason, cnt in sorted(rej_reason_counts.items(), key=lambda x: -x[1]):
                print(f"    {Y}{reason:<35}{X}  {cnt:>4} fois")

    # ── PHASE 3 ───────────────────────────────────────────────────────────────
    sec("PHASE 3 — REGIMES DETECTES")

    if not has_new_fields:
        print(f"  {Y}Champs non disponibles — migration SQL requise.{X}")
    else:
        regime_counts: Dict[str, int] = defaultdict(int)
        regime_best_market: Dict[str, List[str]] = defaultdict(list)
        for r in rows:
            regime = r.get("market_regime") or "UNKNOWN"
            regime_counts[regime] += 1
            bm = r.get("best_market")
            if bm:
                regime_best_market[regime].append(bm)

        print(f"\n  {'Regime':<28} {'N':>4}  {'%':>5}  {'Best market dominant':>24}")
        print(f"  {'-'*28} {'-'*4}  {'-'*5}  {'-'*24}")
        for regime, cnt in sorted(regime_counts.items(), key=lambda x: -x[1]):
            pct    = cnt / total * 100
            is_over = regime in ("HIGH_TEMPO_OVER", "BTTS_PROFILE", "EARLY_GOAL_PROFILE",
                                  "HOME_DOMINANT", "ASYMMETRIC_MATCHUP", "SECOND_HALF_CHAOS")
            col    = G if is_over else (Y if "UNDER" in regime else D)
            bm_list = regime_best_market[regime]
            top_bm  = max(set(bm_list), key=bm_list.count) if bm_list else "—"
            print(f"  {col}{regime:<28}{X} {cnt:>4}  {pct:>4.1f}%  {col}{top_bm:<24}{X}  {col}{bar(cnt, total, 16)}{X}")

    # ── PHASE 4 ───────────────────────────────────────────────────────────────
    sec("PHASE 4 — OVER AUDIT")

    # Always-available (from market field)
    over_picks  = sum(1 for r in rows if classify((r.get("market") or "").upper()) == "OVER")
    under_picks = sum(1 for r in rows if classify((r.get("market") or "").upper()) == "UNDER")
    print(f"\n  Picks retenus OVER  : {G}{over_picks:>4}{X}  ({over_picks/total*100:.1f}%)")
    print(f"  Picks retenus UNDER : {Y}{under_picks:>4}{X}  ({under_picks/total*100:.1f}%)")

    if has_new_fields:
        # New fields available
        n_best_over   = sum(1 for r in rows if r.get("best_over_market"))
        n_best_under  = sum(1 for r in rows if r.get("best_under_market"))
        n_best_market = sum(1 for r in rows if r.get("best_market"))

        dir_counts: Dict[str, int] = defaultdict(int)
        for r in rows:
            d = r.get("recommended_market_direction") or "NEUTRAL"
            dir_counts[d] += 1

        print(f"\n  {B}Champs Phase 5 (depuis Supabase) :{X}")
        print(f"  best_over_market  non-null  : {G}{n_best_over:>4}{X}  ({n_best_over/total*100:.1f}%)")
        print(f"  best_under_market non-null  : {Y}{n_best_under:>4}{X}  ({n_best_under/total*100:.1f}%)")
        print(f"  best_market       non-null  : {C}{n_best_market:>4}{X}  ({n_best_market/total*100:.1f}%)")

        print(f"\n  {B}recommended_market_direction :{X}")
        for d, cnt in sorted(dir_counts.items(), key=lambda x: -x[1]):
            col = G if d == "OVER" else (Y if "UNDER" in d else D)
            pct = cnt / total * 100
            print(f"  {col}{d:<20}{X}  {cnt:>4}  ({pct:>5.1f}%)  {col}{bar(cnt, total, 22)}{X}")
    else:
        print(f"\n  {Y}Champs Phase 5 non disponibles — migration SQL requise.{X}")

        high_chaos = [r for r in rows if (r.get("chaos_score") or 0) > 50]
        low_chaos  = [r for r in rows if (r.get("chaos_score") or 0) <= 50]
        if high_chaos:
            ho = sum(1 for r in high_chaos if classify((r.get("market") or "").upper()) == "OVER")
            print(f"  Matchs chaos > 50 : {len(high_chaos)} — dont OVER retenus : {ho}")

    # ── PHASE 5 ───────────────────────────────────────────────────────────────
    sec("PHASE 5 — TOP 20 PICKS DU JOUR")
    top = sorted(rows, key=lambda r: r.get("confidence_score") or 0, reverse=True)[:20]
    if has_new_fields:
        print(f"\n  {'#':>2}  {'League':<20}  {'Marche':<20}  {'Regime':<20}  {'Dir':<12}  {'BestOver':<18}  Conf")
        print(f"  {'--':>2}  {'-'*20}  {'-'*20}  {'-'*20}  {'-'*12}  {'-'*18}  ----")
        for i, r in enumerate(top, 1):
            league  = (r.get("league") or "")[:20]
            market  = (r.get("market") or "")[:20]
            regime  = (r.get("market_regime") or "?")[:20]
            direction = (r.get("recommended_market_direction") or "?")[:12]
            best_ov = (r.get("best_over_market") or "—")[:18]
            conf    = r.get("confidence_score") or 0.0
            cat     = classify(market)
            col     = G if cat == "OVER" else (Y if cat == "UNDER" else D)
            dcol    = G if direction == "OVER" else (Y if "UNDER" in direction else D)
            print(f"  {i:>2}  {D}{league:<20}{X}  {col}{market:<20}{X}  {D}{regime:<20}{X}  {dcol}{direction:<12}{X}  {G}{best_ov:<18}{X}  {conf:>4.1f}")
    else:
        print(f"\n  {'#':>2}  {'League':<22}  {'Marche':<22}  {'Tier':<16}  {'Conf':>5}  {'Chaos':>6}")
        print(f"  {'--':>2}  {'-'*22}  {'-'*22}  {'-'*16}  {'-----':>5}  {'------':>6}")
        for i, r in enumerate(top, 1):
            league = (r.get("league") or "")[:22]
            market = (r.get("market") or "")[:22]
            tier   = (r.get("statistical_tier") or r.get("ev_tier") or "?")[:16]
            conf   = r.get("confidence_score") or 0.0
            chaos  = r.get("chaos_score") or 0.0
            cat    = classify(market)
            col    = G if cat == "OVER" else (Y if cat == "UNDER" else D)
            print(f"  {i:>2}  {D}{league:<22}{X}  {col}{market:<22}{X}  {D}{tier:<16}{X}  {conf:>5.1f}  {D}{chaos:>6.1f}{X}")

    # ── PHASE 6 ───────────────────────────────────────────────────────────────
    sec("PHASE 6 — CONCLUSION FACTUELLE")

    over_pct   = n_over  / total * 100 if total else 0
    under_pct  = n_under / total * 100 if total else 0
    ratio_uo   = n_under / max(n_over, 1)
    over_markets_in_db  = [m for m in mkt_counts if classify(m) == "OVER"]

    print(f"\n  1. {B}Le moteur produit-il reellement des OVER ?{X}")
    if n_over > 0:
        print(f"     {G}OUI{X} — {n_over} picks OVER ({over_pct:.1f}%) sur {total} predictions.")
        print(f"     Marches : {', '.join(sorted(over_markets_in_db)[:8])}")
    else:
        print(f"     {R}NON{X} — 0 pick OVER sur les {total} predictions recentes.")
        print(f"     Relancer un cycle APRES migration SQL.")

    print(f"\n  2. {B}Les OVER sont-ils generes mais rejects ?{X}")
    if has_new_fields:
        import json as _json2
        gen_total = sum(
            (lambda s: s.get("generated_count", 0))(
                _json2.loads(r.get("market_generation_stats") or "{}")
                if isinstance(r.get("market_generation_stats"), str)
                else (r.get("market_generation_stats") or {})
            )
            for r in rows
        )
        sel_total = sum(
            (lambda s: s.get("selected_count", 0))(
                _json2.loads(r.get("market_generation_stats") or "{}")
                if isinstance(r.get("market_generation_stats"), str)
                else (r.get("market_generation_stats") or {})
            )
            for r in rows
        )
        if gen_total > 0:
            rej_total = gen_total - sel_total
            print(f"     {C}Generes : {gen_total}  Selectionnes : {sel_total}  Rejetes : {Y}{rej_total}{X}")
            print(f"     Selection rate : {sel_total/gen_total*100:.1f}%")
        else:
            print(f"     {Y}Donnees market_generation_stats vides (cycle pre-migration).{X}")
    else:
        print(f"     {Y}Champ market_generation_stats non disponible.{X}")
        print(f"     Migration requise : app/database/migrations/add_multimarket_columns.sql")

    print(f"\n  3. {B}Les UNDER dominent-ils encore ?{X}")
    if under_pct > 60:
        print(f"     {Y}OUI{X} — UNDER={under_pct:.1f}% vs OVER={over_pct:.1f}%  (ratio {ratio_uo:.1f}x)")
    elif under_pct > over_pct:
        print(f"     {Y}LEGER BIAIS UNDER{X} — {under_pct:.1f}% vs {over_pct:.1f}%")
    else:
        print(f"     {G}NON{X} — OVER={over_pct:.1f}% >= UNDER={under_pct:.1f}%")

    print(f"\n  4. {B}Le market ranking favorise-t-il excessivement les UNDER ?{X}")
    if n_over == 0 and n_under > 5:
        print(f"     {R}OUI — 0 OVER selectionne sur {n_under} UNDER.{X}")
        print(f"     Verifier : seuils OVER non atteints ou cycle pre-modifications.")
    elif ratio_uo > 3:
        print(f"     {Y}PROBABLE{X} — ratio UNDER/OVER = {ratio_uo:.1f}x")
    else:
        print(f"     {G}NON{X} — distribution equilibree (ratio {ratio_uo:.1f}x)")

    print(f"\n  5. {B}Les modifications multi-market sont-elles visibles ?{X}")
    if has_new_fields:
        n_rm = sum(1 for r in rows if r.get("market_regime"))
        n_rd = sum(1 for r in rows if r.get("recommended_market_direction"))
        n_bo = sum(1 for r in rows if r.get("best_over_market"))
        if n_rm > 0 or n_rd > 0:
            print(f"     {G}OUI (complet){X} — champs Phase 2/4/5 persistes :")
            print(f"     market_regime set            : {n_rm}/{total}")
            print(f"     recommended_direction set    : {n_rd}/{total}")
            print(f"     best_over_market set         : {n_bo}/{total}")
        else:
            print(f"     {Y}MIGRATION OK mais donnees vides.{X}")
            print(f"     Les colonnes existent mais aucun cycle n'a tourne apres migration.")
            print(f"     Relancer : python start.py")
    else:
        print(f"     {Y}MIGRATION REQUISE{X}")
        print(f"     Executer : app/database/migrations/add_multimarket_columns.sql")
        if n_over > 0:
            print(f"     {G}Note: des OVER sont detectes ({n_over}) — le moteur fonctionne.{X}")

    print(f"\n{'=' * 68}\n")


if __name__ == "__main__":
    run()
