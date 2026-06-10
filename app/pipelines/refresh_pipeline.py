"""
Refresh Pipeline — Phases 4 + 9
==================================
Steps:
  1. Scan today's fixtures via SmartScanner
  2. Save fixtures to Supabase
  3. Save predictions (primary market per match)
  4. Save odds snapshots
  5. Sync EAE false positive patterns
  6. Save daily performance snapshot
  7. Return full summary

Non-blocking: DB failures never abort the scan.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RefreshPipeline:
    """
    Orchestrates: scan → persist fixtures/predictions/odds → update performance.
    """

    def __init__(self, scanner, repository):
        self.scanner    = scanner
        self.repository = repository

    # ─── Main entry ───────────────────────────────────────────────────────────
    def run(self) -> Dict[str, Any]:
        """
        Full refresh cycle.
        Returns a summary dict regardless of DB connectivity.
        """
        started = datetime.now(timezone.utc)
        result: Dict[str, Any] = {
            "started_at":       started.isoformat(),
            "scan_ok":          False,
            "db_connected":     self.repository.supabase_connected,
            "fixtures_saved":   0,
            "predictions_saved": 0,
            "odds_saved":       0,
            "eae_patterns_synced": 0,
            "errors":           [],
        }

        # ── Step 1: Scan ──────────────────────────────────────────────────────
        try:
            scan_result = self.scanner.scan_today()
            result["scan_ok"]           = True
            result["total_matches"]     = scan_result.get("total_matches", 0)
            result["analyzed_count"]    = scan_result.get("analyzed_count", 0)
            result["scan_result"]       = scan_result
        except Exception as exc:
            result["errors"].append(f"scan: {exc}")
            logger.error(f"[REFRESH] Scan failed: {exc}")
            return result

        # ── Steps 2-4: Persist ────────────────────────────────────────────────
        if self.repository.supabase_connected:
            analyzed = scan_result.get("analyzed_matches", []) or []
            remaining = scan_result.get("remaining_matches", []) or []
            all_matches = analyzed + remaining

            for match in all_matches:
                # 2. Fixture
                try:
                    if self.repository.save_fixture(match):
                        result["fixtures_saved"] += 1
                except Exception as exc:
                    result["errors"].append(f"fixture: {exc}")

                # 3. Prediction (only if analysis exists)
                if match.get("analysis"):
                    try:
                        if self.repository.save_prediction(match):
                            result["predictions_saved"] += 1
                    except Exception as exc:
                        result["errors"].append(f"prediction: {exc}")

                    # 4. Odds snapshots
                    try:
                        an = match.get("analysis", {}) or {}
                        odds_list = an.get("matched_odds", []) or []
                        if odds_list:
                            md = match.get("match_data") or match
                            fid = str(
                                md.get("match_id") or md.get("fixture_id") or ""
                            )
                            result["odds_saved"] += self.repository.save_odds_snapshots(
                                fid, odds_list
                            )
                    except Exception as exc:
                        result["errors"].append(f"odds: {exc}")

            # ── Step 5: Sync EAE patterns ─────────────────────────────────────
            try:
                from app.services.analysis.error_analysis_engine import get_eae
                eae = get_eae()
                if eae.is_ready:
                    patterns = eae.get_all_patterns(min_occurrences=1)
                    result["eae_patterns_synced"] = \
                        self.repository.upsert_false_positive_patterns(patterns)
            except Exception as exc:
                result["errors"].append(f"eae_sync: {exc}")

            # ── Step 6: Daily performance snapshot ────────────────────────────
            try:
                stats = self.repository.get_performance_summary(days=1)
                if stats.get("total_settled", 0) > 0:
                    self.repository.save_model_performance(stats, "DAILY")
            except Exception as exc:
                result["errors"].append(f"perf_snapshot: {exc}")
        else:
            result["errors"].append(
                f"DB skipped — {self.repository.supabase_status}"
            )

        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        result["elapsed_seconds"] = round(elapsed, 2)

        logger.info(
            f"[REFRESH] Done — fixtures={result['fixtures_saved']} "
            f"predictions={result['predictions_saved']} "
            f"odds={result['odds_saved']} "
            f"errors={len(result['errors'])}"
        )
        return result
