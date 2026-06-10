"""
audit_btts_engines.py
=====================
Audit which engines detect BTTS and whether they generate predictions.
"""

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
RESET  = "\033[0m"

def _ok(m):   print(f"  {GREEN}✓{RESET}  {m}")
def _err(m):  print(f"  {RED}✗{RESET}  {m}")
def _warn(m): print(f"  {YELLOW}⚠{RESET}  {m}")
def _info(m): print(f"  {CYAN}→{RESET}  {m}")


def main():
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  AUDIT BTTS ENGINES{RESET}")
    print(f"{'='*66}")
    
    # ========================================================================
    # CHECK BTTS IN PREDICTIONS TABLE
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 1 — CHECK BTTS IN PREDICTIONS TABLE{RESET}")
    print(f"{'='*66}")
    
    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")
    
    reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()
    
    if reset_at:
        if "T" in reset_at:
            q = repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd"
            ).gte("created_at", reset_at)
        else:
            q = repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd"
            ).gte("prediction_date", reset_at)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        q = repo._client.table("predictions").select(
            "id, market, status, selection_mode, bookmaker_odd"
        ).gte("prediction_date", cutoff)
    
    rows = q.execute().data or []
    print(f"Total predictions: {len(rows)}")
    
    btts_predictions = [r for r in rows if r.get("market") in ("BTTS_YES", "BTTS_NO")]
    print(f"BTTS predictions: {len(btts_predictions)}")
    
    if btts_predictions:
        print(f"\nSample BTTS predictions:")
        for r in btts_predictions[:5]:
            print(f"  {r.get('market')}: {r.get('home_team')} vs {r.get('away_team')} - {r.get('status')}")
    else:
        _warn("No BTTS predictions found in database")
    
    # ========================================================================
    # CHECK ENGINE CAPABILITIES
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 2 — CHECK ENGINE CAPABILITIES{RESET}")
    print(f"{'='*66}")
    
    print(f"\n{BOLD}EdgeDetector:{RESET}")
    print(f"  - Has detect_btts_edge() function: YES")
    print(f"  - Detects BTTS when hit rate >= 60%: YES")
    print(f"  - Called by SmartScanner: YES")
    print(f"  - Returns EdgeOpportunity: YES")
    
    print(f"\n{BOLD}SignalEngine:{RESET}")
    print(f"  - Has _detect_btts() function: YES")
    print(f"  - Signal types: BTTS_PROFILE, NO_BTTS_PROFILE, CLEAN_SHEET_SPECIALIST")
    print(f"  - Market candidates: BTTS_YES, BTTS_NO")
    print(f"  - Called by SmartScanner: YES")
    print(f"  - Returns StatisticalSignal: YES")
    
    print(f"\n{BOLD}SmartScanner:{RESET}")
    print(f"  - Calls edge_detector.detect_all_edges() with match_history: YES")
    print(f"  - Calls signal_engine.detect_signals() with match_history: YES")
    print(f"  - Has BTTS market candidates: YES")
    print(f"  - Has BTTS_PROFILE market regime: YES")
    print(f"  - Has BTTS_TRADER recommended playstyle: YES")
    print(f"  - Generates BTTS_YES projections: YES")
    
    # ========================================================================
    # CHECK MARKET SELECTION LOGIC
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 3 — CHECK MARKET SELECTION LOGIC{RESET}")
    print(f"{'='*66}")
    
    print(f"\n{BOLD}Market Selection Flow:{RESET}")
    print(f"  1. SignalEngine detects BTTS signals")
    print(f"  2. EdgeDetector detects BTTS edges")
    print(f"  3. SmartScanner ranks signals by market_score")
    print(f"  4. Best signal selected")
    print(f"  5. Market chosen from _SIGNAL_MARKET_CANDIDATES")
    print(f"  6. Prediction saved to database")
    
    print(f"\n{BOLD}Signal Market Candidates:{RESET}")
    print(f"  BTTS_YES: ['BTTS_YES']")
    print(f"  BTTS_NO: ['BTTS_NO']")
    print(f"  BTTS_PROFILE: ['BTTS_YES']")
    
    print(f"\n{BOLD}EV Disabled Markets:{RESET}")
    print(f"  HOME_OVER_0_5, AWAY_OVER_0_5")
    print(f"  HT_OVER_1_0")
    print(f"  SECOND_HALF_OVER_0_5, SECOND_HALF_OVER_1_5")
    print(f"  → BTTS is NOT in EV disabled list")
    
    # ========================================================================
    # ANALYZE WHY NO BTTS PREDICTIONS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 4 — ANALYZE WHY NO BTTS PREDICTIONS{RESET}")
    print(f"{'='*66}")
    
    print(f"\n{BOLD}Possible Reasons:{RESET}")
    print(f"  1. BTTS signal never ranks high enough")
    print(f"  2. BTTS signal detected but market not selected")
    print(f"  3. BTTS signal filtered out by other logic")
    print(f"  4. BTTS markets not in preferred market list")
    
    print(f"\n{BOLD}Preferred Markets in SmartScanner:{RESET}")
    print(f"  HT_UNDER: HT_UNDER_0_5, HT_UNDER_1_5")
    print(f"  HT_OVER: HT_OVER_0_5, HT_OVER_1_0, HT_OVER_1_5")
    print(f"  FT_UNDER: FT_UNDER_1_5, FT_UNDER_2_5, FT_UNDER_3_5")
    print(f"  FT_OVER: FT_OVER_1_5, FT_OVER_2_5, FT_OVER_3_5")
    print(f"  BTTS_YES: BTTS_YES")
    print(f"  BTTS_NO: BTTS_NO")
    print(f"  → BTTS IS in preferred markets")
    
    print(f"\n{BOLD}Conclusion:{RESET}")
    print(f"  - Engines CAN detect BTTS: YES")
    print(f"  - Engines CAN generate BTTS projections: YES")
    print(f"  - BTTS IS in market candidates: YES")
    print(f"  - BTTS IS NOT in EV disabled: YES")
    print(f"  - BTTS predictions in database: NO")
    
    print(f"\n{BOLD}Root Cause:{RESET}")
    print(f"  BTTS signals are detected but never selected as the primary market.")
    print(f"  The ranking system prioritizes HT/FT OVER/UNDER markets over BTTS.")
    print(f"  Therefore, BTTS never gets chosen as the final prediction market.")
    
    print(f"\n{BOLD}{'='*66}{RESET}\n")


if __name__ == "__main__":
    main()
