"""
AutoSettler — Phases 1-4
=========================
Automatic prediction settlement via API-Football.

Functions:
    fetch_final_result(fixture_id, provider)  → dict | str sentinel
    auto_settle_predictions(repo, provider)   → dict summary
    settle_csv_row(row, provider)             → dict with result fields

Sentinels returned by fetch_final_result:
    "NOT_FINISHED"    — match still in progress / not started
    "RESULT_MISSING"  — finished but goals data missing from API
    "API_ERROR"       — network / key error

Markets supported (all case-insensitive, underscore or space):
    HT_UNDER_0_5  HT_UNDER_1_5  HT_OVER_0_5  HT_OVER_1_5
    FT_UNDER_1_5  FT_UNDER_2_5  FT_UNDER_3_5
    FT_OVER_1_5   FT_OVER_2_5   FT_OVER_3_5
    BTTS_YES      BTTS_NO
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Status codes from API-Football that mean the match is finished
FINISHED_STATUSES = {"FT", "AET", "PEN"}
# Status codes that mean the match is still running / not started
LIVE_STATUSES = {"1H", "HT", "2H", "ET", "P", "BT"}


# ─── Result fetch ──────────────────────────────────────────────────────────────

def fetch_final_result(fixture_id: Any, provider) -> Dict:
    """
    Fetch match final result from API-Football.

    Args:
        fixture_id : int or str fixture ID
        provider   : ApiFootballProvider instance

    Returns:
        On success (finished):
            {
                "status":          "FINISHED",
                "ft_home_goals":   int,
                "ft_away_goals":   int,
                "ht_home_goals":   int,
                "ht_away_goals":   int,
                "total_ft_goals":  int,
                "total_ht_goals":  int,
                "api_status":      str   (e.g. "FT")
            }
        On not finished:  {"status": "NOT_FINISHED", "api_status": str}
        On missing score: {"status": "RESULT_MISSING"}
        On error:         {"status": "API_ERROR", "error": str}
    """
    try:
        data = provider._make_request("fixtures", {"id": str(fixture_id)})
        response = data.get("response", [])
        if not response:
            return {"status": "RESULT_MISSING"}

        fixture_data = response[0]
        fixture_info = fixture_data.get("fixture", {})
        status_short = fixture_info.get("status", {}).get("short", "")
        goals        = fixture_data.get("goals", {})
        score        = fixture_data.get("score", {})

        if status_short not in FINISHED_STATUSES:
            return {"status": "NOT_FINISHED", "api_status": status_short}

        ft_home = goals.get("home")
        ft_away = goals.get("away")
        if ft_home is None or ft_away is None:
            return {"status": "RESULT_MISSING"}

        ht_data = score.get("halftime", {})
        ht_home = ht_data.get("home") or 0
        ht_away = ht_data.get("away") or 0

        return {
            "status":         "FINISHED",
            "ft_home_goals":  int(ft_home),
            "ft_away_goals":  int(ft_away),
            "ht_home_goals":  int(ht_home),
            "ht_away_goals":  int(ht_away),
            "total_ft_goals": int(ft_home) + int(ft_away),
            "total_ht_goals": int(ht_home) + int(ht_away),
            "api_status":     status_short,
        }

    except Exception as exc:
        logger.warning(f"[AUTO_SETTLE] fetch_final_result({fixture_id}): {exc}")
        return {"status": "API_ERROR", "error": str(exc)}


# ─── Market evaluation ────────────────────────────────────────────────────────

def evaluate_market(market: str, result: Dict) -> str:
    """
    Evaluate a market given a finished result dict.
    Returns "WIN", "LOSS", or "VOID".

    Args:
        market : canonical market string, e.g. "FT_UNDER_2_5" or "HT UNDER 1.5"
        result : dict from fetch_final_result (must have status="FINISHED")
    """
    if result.get("status") != "FINISHED":
        return "VOID"

    # Normalise: upper + replace spaces/dots with underscores
    m = market.upper().replace(" ", "_").replace(".", "_")

    ft_home = result.get("ft_home_goals", 0) or 0
    ft_away = result.get("ft_away_goals", 0) or 0
    ht_home = result.get("ht_home_goals", 0) or 0
    ht_away = result.get("ht_away_goals", 0) or 0
    total_ft = ft_home + ft_away
    total_ht = ht_home + ht_away

    try:
        # ── HT markets ────────────────────────────────────────────────────────
        if "HT_UNDER" in m:
            line = _parse_line(m)
            return "WIN" if total_ht < line else "LOSS"
        if "HT_OVER" in m:
            line = _parse_line(m)
            return "WIN" if total_ht > line else "LOSS"

        # ── FT markets ────────────────────────────────────────────────────────
        if "FT_UNDER" in m or ("UNDER" in m and "HT" not in m):
            line = _parse_line(m)
            return "WIN" if total_ft < line else "LOSS"
        if "FT_OVER" in m or ("OVER" in m and "HT" not in m):
            line = _parse_line(m)
            return "WIN" if total_ft > line else "LOSS"

        # ── BTTS ──────────────────────────────────────────────────────────────
        if "BTTS_YES" in m or m == "BTTS":
            return "WIN" if ft_home > 0 and ft_away > 0 else "LOSS"
        if "BTTS_NO" in m:
            return "WIN" if not (ft_home > 0 and ft_away > 0) else "LOSS"

    except Exception:
        pass

    return "VOID"


def _parse_line(market_upper: str) -> float:
    """
    Extract the decimal line from a normalised market string.
    Examples:
        "FT_UNDER_2_5"  → 2.5
        "HT_UNDER_1_5"  → 1.5
        "FT_OVER_3_5"   → 3.5
        "UNDER_0_5"     → 0.5
    """
    parts = market_upper.split("_")
    try:
        # Last two parts are digits: "2","5" → 2.5
        if len(parts) >= 2 and parts[-1].isdigit() and parts[-2].isdigit():
            return float(f"{parts[-2]}.{parts[-1]}")
        # Last part only: "2" → 2.0
        if parts[-1].isdigit():
            return float(parts[-1])
    except (ValueError, IndexError):
        pass
    return 0.0


# ─── Auto-settle Supabase predictions ────────────────────────────────────────

def auto_settle_predictions(repo, provider) -> Dict:
    """
    Phase 2+4: Settle all PENDING predictions in Supabase.

    For each PENDING prediction:
      1. fetch_final_result via API-Football
      2. If FINISHED: evaluate market → WON / LOST / VOID → persist
      3. If NOT_FINISHED: leave PENDING
      4. Update fixture scores in DB

    Returns:
        {
            "settled":    int,
            "won":        int,
            "lost":       int,
            "void":       int,
            "pending":    int,
            "errors":     int,
            "profit_loss": float,
            "details":    list
        }
    """
    summary = {"settled": 0, "won": 0, "lost": 0, "void": 0,
               "pending": 0, "errors": 0, "profit_loss": 0.0, "details": []}

    if not repo or not repo.supabase_connected:
        logger.warning("[AUTO_SETTLE] Supabase not connected — skipping")
        return summary

    pending = repo.get_pending_predictions()
    if not pending:
        logger.info("[AUTO_SETTLE] No PENDING predictions found")
        return summary

    logger.info(f"[AUTO_SETTLE] Processing {len(pending)} PENDING predictions")

    settled_fixtures: Dict[str, Dict] = {}

    for pred in pending:
        fixture_id    = str(pred.get("fixture_id", ""))
        prediction_id = str(pred.get("prediction_id", ""))
        market        = str(pred.get("market", ""))
        bookmaker_odd = float(pred.get("bookmaker_odd") or 1.0)
        detail        = {"prediction_id": prediction_id, "fixture_id": fixture_id,
                         "market": market}

        if not fixture_id or not market:
            summary["errors"] += 1
            continue

        # Cache result per fixture to avoid duplicate API calls
        if fixture_id not in settled_fixtures:
            settled_fixtures[fixture_id] = fetch_final_result(fixture_id, provider)

        result = settled_fixtures[fixture_id]
        detail["api_status"] = result.get("api_status") or result.get("status")

        if result["status"] == "NOT_FINISHED":
            summary["pending"] += 1
            detail["outcome"] = "PENDING"
            summary["details"].append(detail)
            continue

        if result["status"] in ("RESULT_MISSING", "API_ERROR"):
            summary["errors"] += 1
            detail["outcome"] = result["status"]
            summary["details"].append(detail)
            continue

        # Evaluate
        outcome = evaluate_market(market, result)
        pl = _calc_pl(outcome, bookmaker_odd)

        # Persist to Supabase
        ok = repo.settle_prediction(
            prediction_id  = prediction_id,
            home_score     = result["ft_home_goals"],
            away_score     = result["ft_away_goals"],
            ht_home        = result["ht_home_goals"],
            ht_away        = result["ht_away_goals"],
            bookmaker_odd  = bookmaker_odd,
            notes          = f"auto_settled via API-Football status={result['api_status']}",
        )

        # Update fixture scores once (non-blocking)
        try:
            repo.update_fixture_result(
                fixture_id = fixture_id,
                home_score = result["ft_home_goals"],
                away_score = result["ft_away_goals"],
                ht_home    = result["ht_home_goals"],
                ht_away    = result["ht_away_goals"],
                status     = "FINISHED",
            )
        except Exception as _ufr_exc:
            logger.debug(f"[AUTO_SETTLE] update_fixture_result {fixture_id}: {_ufr_exc}")

        # Only count if DB write succeeded
        if ok:
            summary["settled"] += 1
            summary["profit_loss"] = round(summary["profit_loss"] + pl, 4)
            if outcome == "WIN":
                summary["won"] += 1
            elif outcome == "LOSS":
                summary["lost"] += 1
            else:
                summary["void"] += 1
        else:
            summary["errors"] += 1
            logger.warning(f"[AUTO_SETTLE] settle_prediction failed for {prediction_id}")

        detail.update({
            "outcome":  outcome,
            "score":    f"{result['ft_home_goals']}-{result['ft_away_goals']}",
            "ht_score": f"{result['ht_home_goals']}-{result['ht_away_goals']}",
            "pl":       pl,
            "persisted": ok,
        })
        summary["details"].append(detail)
        logger.info(
            f"[AUTO_SETTLE] {prediction_id}: {market} {outcome} "
            f"({result['ft_home_goals']}-{result['ft_away_goals']}) P/L={pl:+.2f}"
        )

    return summary


# ─── One-time repair: fix misclassified VOID predictions ─────────────────────

def fix_voided_predictions(repo) -> dict:
    """
    Re-evaluate all VOID predictions that have actual_home_score stored.
    Corrects predictions misclassified as VOID due to market normalisation bug.

    Safe to run multiple times (idempotent).
    Returns: {"fixed": int, "skipped": int, "errors": int}
    """
    from app.database.supabase_repository import evaluate_market_result, calculate_profit_loss

    result = {"fixed": 0, "skipped": 0, "errors": 0}

    if not repo or not repo.supabase_connected:
        return result

    try:
        resp = (
            repo._client.table("predictions")
            .select(
                "prediction_id, market, bookmaker_odd, "
                "actual_home_score, actual_away_score, "
                "actual_ht_home_score, actual_ht_away_score"
            )
            .eq("status", "VOID")
            .not_.is_("actual_home_score", "null")
            .execute()
        )
        void_rows = resp.data or []
    except Exception as exc:
        logger.error(f"[FIX_VOID] fetch failed: {exc}")
        return result

    logger.info(f"[FIX_VOID] Found {len(void_rows)} VOID predictions with scores to re-evaluate")

    for row in void_rows:
        pid    = row.get("prediction_id", "")
        market = row.get("market", "")
        h      = int(row.get("actual_home_score") or 0)
        a      = int(row.get("actual_away_score") or 0)
        ht_h   = int(row.get("actual_ht_home_score") or 0)
        ht_a   = int(row.get("actual_ht_away_score") or 0)
        odd    = float(row.get("bookmaker_odd") or 1.0)

        if not pid or not market:
            result["skipped"] += 1
            continue

        outcome    = evaluate_market_result(market, h, a, ht_h, ht_a)
        if outcome == "VOID":
            result["skipped"] += 1
            continue  # Still VOID after fix — truly unrecognised market

        status_map = {"WIN": "WON", "LOSS": "LOST"}
        new_status = status_map[outcome]
        pl         = calculate_profit_loss(outcome, odd)

        try:
            repo._client.table("predictions").update({
                "status":       new_status,
                "final_result": outcome,
                "profit_loss":  pl,
                "settlement_notes": "re-settled by fix_voided_predictions (normalisation fix)",
            }).eq("prediction_id", pid).execute()
            result["fixed"] += 1
            logger.info(f"[FIX_VOID] {pid}: VOID → {new_status} ({pl:+.3f}u)")
        except Exception as exc:
            result["errors"] += 1
            logger.warning(f"[FIX_VOID] update failed for {pid}: {exc}")

    return result


def _calc_pl(outcome: str, odd: float, stake: float = 1.0) -> float:
    if outcome == "WIN":
        return round((max(float(odd), 1.01) - 1.0) * stake, 4)
    if outcome == "LOSS":
        return -stake
    return 0.0


# ─── CSV row auto-fill ────────────────────────────────────────────────────────

def settle_csv_row(row: dict, provider) -> dict:
    """
    Try to auto-fill a single CSV row (from live_test_session).

    Returns updated fields dict:
        {
            "final_result":   "1-0",
            "result_correct": "WIN" | "LOSS" | "VOID" | "UNKNOWN",
            "result_notes":   str,
            "ht_score":       "0-0",    # populated when available
            "settled":        True/False
        }
    """
    fixture_id = str(row.get("fixture_id", "")).strip()
    market     = str(row.get("market", "")).strip()

    if not fixture_id or not market:
        return {"settled": False, "result_correct": "UNKNOWN",
                "final_result": "", "result_notes": "missing fixture_id or market",
                "ht_score": ""}

    result = fetch_final_result(fixture_id, provider)

    if result["status"] == "NOT_FINISHED":
        return {"settled": False, "result_correct": "",
                "final_result": "", "result_notes": "NOT_FINISHED",
                "ht_score": ""}

    if result["status"] in ("RESULT_MISSING", "API_ERROR"):
        return {"settled": False, "result_correct": "UNKNOWN",
                "final_result": result.get("error", result["status"]),
                "result_notes": result["status"], "ht_score": ""}

    outcome = evaluate_market(market, result)
    ft_str  = f"{result['ft_home_goals']}-{result['ft_away_goals']}"
    ht_str  = f"{result['ht_home_goals']}-{result['ht_away_goals']}"

    return {
        "settled":        True,
        "final_result":   ft_str,
        "ht_score":       ht_str,
        "result_correct": outcome,
        "result_notes":   f"auto via API-Football (HT:{ht_str})",
    }
