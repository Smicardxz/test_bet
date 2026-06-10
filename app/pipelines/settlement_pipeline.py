"""
Settlement Pipeline — Phases 5 + 10
=====================================
Steps:
  1. Fetch all PENDING predictions whose kickoff has passed
  2. For each: look up fixture result from the data provider
  3. Evaluate market outcome (WIN / LOSS / VOID)
  4. Persist settled prediction + P/L
  5. Update league_profiles aggregates
  6. Save ALL_TIME performance snapshot

Non-blocking: every step is try/except guarded.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.database.supabase_repository import (
    SupabaseRepository,
    evaluate_market_result,
    calculate_profit_loss,
)

logger = logging.getLogger(__name__)


class SettlementPipeline:
    """
    Fetches finished matches from the data provider and settles
    all matching PENDING predictions in Supabase.
    """

    def __init__(self, repository: SupabaseRepository, provider=None):
        """
        provider: DataSourceManager or any object with
                  .get_match_result(fixture_id) → optional match object
        """
        self.repository = repository
        self.provider   = provider

    # ─── Main entry ───────────────────────────────────────────────────────────
    def run(self) -> Dict[str, Any]:
        started = datetime.now(timezone.utc)
        result: Dict[str, Any] = {
            "started_at":   started.isoformat(),
            "db_connected": self.repository.supabase_connected,
            "pending_found": 0,
            "settled":      0,
            "won":          0,
            "lost":         0,
            "void":         0,
            "errors":       [],
        }

        if not self.repository.supabase_connected:
            result["errors"].append(
                f"DB not connected — {self.repository.supabase_status}"
            )
            return result

        # ── Step 1: PENDING predictions with past kickoff ─────────────────────
        cutoff = datetime.now(timezone.utc) + timedelta(minutes=110)
        pending = self.repository.get_pending_predictions(
            before_kickoff=cutoff, limit=300
        )
        result["pending_found"] = len(pending)

        if not pending:
            logger.info("[SETTLEMENT] No pending predictions to settle")
            return result

        # ── Steps 2-4: Settle each prediction ─────────────────────────────────
        for pred in pending:
            fixture_id    = pred.get("fixture_id", "")
            prediction_id = pred.get("prediction_id", "")
            if not fixture_id or not prediction_id:
                continue

            match_result = self._fetch_result(fixture_id)
            if not match_result:
                continue  # Match not finished yet

            home_score   = match_result.get("home_score", 0) or 0
            away_score   = match_result.get("away_score", 0) or 0
            ht_home      = match_result.get("ht_home_score", 0) or 0
            ht_away      = match_result.get("ht_away_score", 0) or 0
            bookmaker_odd = float(pred.get("bookmaker_odd") or 1.0)

            try:
                # Update fixture scores
                self.repository.update_fixture_result(
                    fixture_id, home_score, away_score, ht_home, ht_away
                )
                # Settle prediction
                ok = self.repository.settle_prediction(
                    prediction_id,
                    home_score, away_score, ht_home, ht_away,
                    bookmaker_odd=bookmaker_odd,
                    notes=f"Auto-settled by SettlementPipeline",
                )
                if ok:
                    result["settled"] += 1
                    outcome = evaluate_market_result(
                        pred.get("market", ""),
                        home_score, away_score, ht_home, ht_away,
                    )
                    if outcome == "WIN":
                        result["won"]  += 1
                    elif outcome == "LOSS":
                        result["lost"] += 1
                    else:
                        result["void"] += 1
            except Exception as exc:
                result["errors"].append(f"{prediction_id}: {exc}")
                logger.debug(f"[SETTLEMENT] Error settling {prediction_id}: {exc}")

        # ── Step 5: Update league profiles ────────────────────────────────────
        if result["settled"] > 0:
            try:
                self._update_league_profiles()
            except Exception as exc:
                result["errors"].append(f"league_profiles: {exc}")

            # ── Step 6: ALL_TIME performance snapshot (POST_RESET only if set) ─
            try:
                from app.database.supabase_repository import _parse_reset_at
                _reset = _parse_reset_at()
                stats = self.repository.get_performance_summary(
                    days=3650, since_date=_reset
                )
                self.repository.save_model_performance(
                    {k: v for k, v in stats.items() if k != "days"},
                    period_type="ALL_TIME",
                )
            except Exception as exc:
                result["errors"].append(f"all_time_perf: {exc}")

        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        result["elapsed_seconds"] = round(elapsed, 2)

        logger.info(
            f"[SETTLEMENT] Done — settled={result['settled']} "
            f"won={result['won']} lost={result['lost']} void={result['void']} "
            f"errors={len(result['errors'])}"
        )
        return result

    # ─── Helpers ──────────────────────────────────────────────────────────────
    def _fetch_result(self, fixture_id: str) -> Optional[Dict]:
        """
        Attempt to get final scores from the data provider.
        Returns dict with home_score/away_score/ht_*_score or None.
        """
        if not self.provider:
            return None
        try:
            match = self.provider.get_match_result(fixture_id)
            if match is None:
                return None
            # Normalize different provider shapes
            if hasattr(match, "status") and str(match.status).upper() not in (
                "FINISHED", "FT", "AET", "PEN", "AWARDED"
            ):
                return None  # Not finished yet
            return {
                "home_score":    getattr(match, "home_score", None) or (match.get("home_score") if isinstance(match, dict) else None),
                "away_score":    getattr(match, "away_score", None) or (match.get("away_score") if isinstance(match, dict) else None),
                "ht_home_score": getattr(match, "ht_home_score", 0) or 0,
                "ht_away_score": getattr(match, "ht_away_score", 0) or 0,
            }
        except Exception as exc:
            logger.debug(f"[SETTLEMENT] _fetch_result {fixture_id}: {exc}")
            return None

    def _update_league_profiles(self) -> None:
        """Rebuild league_profiles from settled predictions."""
        if not self.repository.supabase_connected:
            return
        league_data = self.repository.get_league_profitability()
        if not league_data:
            return
        rows = []
        for ld in league_data:
            rows.append({
                "league":             ld.get("league", ""),
                "country":            ld.get("country", ""),
                "total_predictions":  ld.get("total_predictions", 0),
                "total_wins":         ld.get("total_wins", 0),
                "total_losses":       ld.get("total_losses", 0),
                "hit_rate":           ld.get("hit_rate", 0),
                "roi":                ld.get("roi", 0),
                "total_profit_loss":  ld.get("total_profit_loss", 0),
                "false_positive_count": ld.get("false_positive_count", 0),
                "false_positive_rate":  ld.get("false_positive_rate", 0),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            })
        if rows:
            try:
                self.repository._client.table("league_profiles").upsert(
                    rows, on_conflict="league,country"
                ).execute()
            except Exception as exc:
                logger.debug(f"[SETTLEMENT] _update_league_profiles: {exc}")
