"""
SupabaseRepository — Phases 3, 5, 6, 7
=========================================
All DB operations: save, settle, aggregate.
Fully non-blocking: every method catches exceptions and returns a
safe default so the scan pipeline is never interrupted by DB errors.

Usage:
    from app.database.supabase_repository import get_repository
    repo = get_repository()
    if repo.supabase_connected:
        repo.save_fixture(match_item)
"""

import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.database.supabase_config import get_supabase_config

logger = logging.getLogger(__name__)

# Stake per prediction (1 unit)
DEFAULT_STAKE = 1.0


# ─── Market evaluation helpers ───────────────────────────────────────────────
def _parse_line(market: str) -> float:
    """FT_UNDER_2_5 → 2.5 · HT_UNDER_0_5 → 0.5 · FT_OVER_3_5 → 3.5"""
    parts = market.upper().split("_")
    try:
        if len(parts) >= 2 and parts[-1].isdigit() and parts[-2].isdigit():
            return float(f"{parts[-2]}.{parts[-1]}")
        if len(parts) >= 1 and parts[-1].isdigit():
            return float(parts[-1])
    except (ValueError, IndexError):
        pass
    return 0.0


def evaluate_market_result(
    market: str,
    home_score: int, away_score: int,
    ht_home: int = 0, ht_away: int = 0,
) -> str:
    """
    Returns "WIN", "LOSS", or "VOID".
    Phase 5 — settlement evaluation logic.
    Normalises: spaces → _, dots → _ (handles "UNDER 2.5", "HT UNDER 1.5", etc.)
    """
    # Normalise: uppercase + spaces/dots → underscores
    m        = market.upper().replace(" ", "_").replace(".", "_")
    total_ft = (home_score or 0) + (away_score or 0)
    total_ht = (ht_home  or 0) + (ht_away  or 0)
    h_scored = (home_score or 0) > 0
    a_scored = (away_score or 0) > 0

    try:
        # ── HT markets (must check before FT to avoid false match on "UNDER") ──
        if "HT_UNDER" in m:
            line = _parse_line(m)
            return "WIN" if total_ht < line else "LOSS"

        if "HT_OVER" in m:
            line = _parse_line(m)
            return "WIN" if total_ht > line else "LOSS"

        # ── FT markets (includes bare "UNDER_X_Y" / "OVER_X_Y" without prefix) ─
        if "FT_UNDER" in m or ("UNDER" in m and "HT" not in m):
            line = _parse_line(m)
            return "WIN" if total_ft < line else "LOSS"

        if "FT_OVER" in m or ("OVER" in m and "HT" not in m):
            line = _parse_line(m)
            return "WIN" if total_ft > line else "LOSS"

        # ── BTTS ──────────────────────────────────────────────────────────────
        if m in ("BTTS_YES", "FT_BTTS_YES", "BTTS"):
            return "WIN" if h_scored and a_scored else "LOSS"

        if m in ("BTTS_NO", "FT_BTTS_NO"):
            return "WIN" if not (h_scored and a_scored) else "LOSS"

    except Exception:
        pass

    return "VOID"


def calculate_profit_loss(
    result: str,
    bookmaker_odd: float,
    stake: float = DEFAULT_STAKE,
) -> float:
    # Defensive handling of invalid odds
    if bookmaker_odd is None or bookmaker_odd <= 0:
        return 0.0
    
    if result == "WIN":
        if bookmaker_odd >= 1.01:
            return round((bookmaker_odd - 1.0) * stake, 4)
        else:
            return 0.0  # Invalid odds, no profit
    if result == "LOSS":
        if bookmaker_odd >= 1.01:
            return -stake
        else:
            return 0.0  # Invalid odds, no loss
    return 0.0   # VOID


def _normalise_market(m: str) -> str:
    """Canonical form: uppercase, spaces→_, dots→_  e.g. 'HT OVER 0.5' → 'HT_OVER_0_5'."""
    return m.upper().replace(" ", "_").replace(".", "_")


def _extract_ev_pick(analysis: dict) -> Optional[dict]:
    """
    Return the primary EV pick dict from an analysis object.
    Priority: ev_qualified[0] > best_ev_opportunity > signals_with_value[0] > signals[0].
    """
    ev_qual = analysis.get("ev_qualified") or []
    if ev_qual and isinstance(ev_qual[0], dict):
        return ev_qual[0]
    beo = analysis.get("best_ev_opportunity")
    if isinstance(beo, dict):
        return beo
    for key in ("signals_with_value", "signals"):
        items = analysis.get(key) or []
        if items and isinstance(items[0], dict):
            return items[0]
    return None


def _extract_primary_market(analysis: dict) -> Optional[str]:
    """Phase 4 helper: pick the best market string from an analysis dict."""
    # NEW: check ev_qualified first (most reliable source)
    ev_pick = _extract_ev_pick(analysis)
    if ev_pick:
        mkt = ev_pick.get("market") or ev_pick.get("signal_type")
        if mkt:
            return _normalise_market(str(mkt))

    for key in ("signals_with_value", "best_edges", "signals"):
        items = analysis.get(key) or []
        if items and isinstance(items[0], dict):
            mkt = (items[0].get("market")
                   or items[0].get("signal_type")
                   or items[0].get("name"))
            if mkt:
                return _normalise_market(str(mkt))

    lse = analysis.get("league_specialization") or {}
    rmp = lse.get("recommended_market_priority") or []
    return _normalise_market(rmp[0]) if rmp else None


def _extract_bookmaker_odd(analysis: dict) -> Optional[float]:
    """Return the bookmaker_odd for the primary signal, or None if not available."""
    ev_pick = _extract_ev_pick(analysis)
    if ev_pick:
        raw = ev_pick.get("bookmaker_odd") or ev_pick.get("odd")
        if raw:
            try:
                v = float(raw)
                if v >= 1.01:
                    return v
            except (TypeError, ValueError):
                pass
    return None


def _safe_json(val) -> str:
    if val is None:
        return "[]"
    if isinstance(val, str):
        return val
    try:
        return json.dumps(val)
    except Exception:
        return "[]"


def _parse_reset_at() -> str:
    """
    Return TRACKING_RESET_AT exactly as stored in env (full ISO datetime or date), or ''.
    Preserves time component: '2026-06-02T15:19:00Z' is returned as-is.
    """
    import os
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


def _is_post_reset() -> bool:
    """
    Return True when current UTC time >= TRACKING_RESET_AT,
    or when no reset is configured (all predictions are POST_RESET by default).
    """
    reset = _parse_reset_at()
    if not reset:
        return True
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    try:
        if "T" in reset:
            reset_dt = datetime.fromisoformat(reset.replace("Z", "+00:00"))
        else:
            parts = [int(x) for x in reset[:10].split("-")]
            reset_dt = datetime(parts[0], parts[1], parts[2], tzinfo=timezone.utc)
        return now >= reset_dt
    except Exception:
        return True


def _apply_since_filter(query, since_date: str):
    """
    Route the 'since' filter to the correct Supabase column:
      - Full ISO datetime (contains 'T') → created_at  (precise to the second)
      - Date-only string (YYYY-MM-DD)   → prediction_date (day granularity)
    """
    if not since_date:
        return query
    if "T" in since_date:
        return query.gte("created_at", since_date)
    return query.gte("prediction_date", since_date)


# ─── Repository ───────────────────────────────────────────────────────────────
class SupabaseRepository:
    """
    All Supabase I/O.  Delegates credential management to SupabaseConfig.
    """

    def __init__(self):
        cfg = get_supabase_config()
        self._client                  = cfg.get_client()
        self.supabase_connected: bool = cfg.supabase_connected
        self.supabase_error           = cfg.supabase_error
        self.supabase_status          = cfg.supabase_status

    # ─── Phase 3 — Save ───────────────────────────────────────────────────────

    def save_fixture(self, match_item: dict) -> bool:
        """Upsert a fixture row from a scan match item."""
        if not self._client:
            return False
        md = match_item.get("match_data") or match_item
        fixture_id = str(md.get("match_id") or md.get("fixture_id") or "")
        if not fixture_id:
            return False

        an = match_item.get("analysis") or {}
        row = {
            "fixture_id":      fixture_id,
            "home_team":       str(md.get("home_team", "")),
            "away_team":       str(md.get("away_team", "")),
            "home_team_id":    str(md.get("home_team_id", "")),
            "away_team_id":    str(md.get("away_team_id", "")),
            "league":          str(md.get("competition") or md.get("league", "")),
            "country":         str(md.get("country", "")),
            "kickoff_time":    md.get("kickoff_time") or md.get("kickoff"),
            "status":          str(md.get("status", "NS")),
            "match_universe":  an.get("match_universe", "STATISTICAL_ONLY"),
            "coverage_quality": an.get("coverage_quality", "NONE"),
        }
        try:
            self._client.table("fixtures").upsert(
                row, on_conflict="fixture_id"
            ).execute()
            return True
        except Exception as exc:
            logger.debug(f"[REPO] save_fixture {fixture_id}: {exc}")
            return False

    def save_prediction(self, match_item: dict) -> bool:
        """
        Upsert one prediction row (primary market only).
        Skips if no market can be identified.
        """
        import os
        if not self._client:
            return False

        md = match_item.get("match_data") or match_item
        an = match_item.get("analysis")
        if not an:
            return False

        fixture_id = str(md.get("match_id") or md.get("fixture_id") or "")
        if not fixture_id:
            return False

        market = _extract_primary_market(an)
        if not market:
            return False

        today         = date.today().isoformat()
        prediction_id = f"{fixture_id}_{market}_{today}"
        profile       = (an.get("match_profile") or {})
        lse           = (an.get("league_specialization") or {})
        eae           = (an.get("pick_explanation") or {})
        fs            = (an.get("false_signal_analysis") or {})
        va            = (an.get("volatility_analysis") or {})

        # ── EV pick extraction (Phase 2) ────────────────────────────────────
        # Priority: ev_qualified[0] > best_ev_opportunity > signals_with_value[0]
        ev_pick       = _extract_ev_pick(an)
        bookmaker_odd = None
        bookmaker_name    = None
        market_prob       = None
        implied_prob      = None
        ev_pct            = None
        edge_pct          = None
        expected_val      = None
        fair_odd_val      = None
        sample_sz         = None
        prob_source       = None
        ev_quality_val    = an.get("ev_quality")
        rejection_reason  = None

        if ev_pick:
            raw_odd = ev_pick.get("bookmaker_odd") or ev_pick.get("odd")
            if raw_odd:
                try:
                    v = float(raw_odd)
                    bookmaker_odd = v if v >= 1.01 else None
                except (TypeError, ValueError):
                    pass
            bookmaker_name   = ev_pick.get("bookmaker") or ev_pick.get("bookmaker_name")
            market_prob      = (ev_pick.get("market_probability")
                                or ev_pick.get("model_probability"))
            implied_prob     = ev_pick.get("implied_probability")
            ev_pct           = (ev_pick.get("ev_percentage")
                                or ev_pick.get("ev_percent")
                                or ev_pick.get("ev"))
            edge_pct         = (ev_pick.get("edge_percentage")
                                or ev_pick.get("edge_percent")
                                or ev_pick.get("edge"))
            expected_val     = ev_pick.get("expected_value") or ev_pick.get("ev_value")
            fair_odd_val     = ev_pick.get("fair_odd")
            sample_sz        = ev_pick.get("sample_size")
            prob_source      = ev_pick.get("probability_source")
            if not ev_quality_val:
                ev_quality_val = ev_pick.get("ev_grade") or ev_pick.get("ev_quality")

        # ── Probability scale guard — normalize to 0-1 ───────────────────────
        # Some EV calculators emit percentage (e.g. 32.79) instead of 0-1 (0.3279).
        # Rule: market_probability → 0-1 | implied_probability → 0-1
        if market_prob is not None:
            try:
                market_prob = float(market_prob)
                if market_prob > 1.0:
                    market_prob = round(market_prob / 100.0, 4)
            except (TypeError, ValueError):
                market_prob = None

        if implied_prob is not None:
            try:
                implied_prob = float(implied_prob)
                if implied_prob > 1.0:
                    implied_prob = round(implied_prob / 100.0, 4)
            except (TypeError, ValueError):
                implied_prob = None

        # Auto-compute implied_probability from bookmaker_odd when not provided
        if implied_prob is None and bookmaker_odd and bookmaker_odd >= 1.01:
            implied_prob = round(1.0 / bookmaker_odd, 4)

        # Rejection reason — from first rejected pick if no qualified pick
        ev_rejected = an.get("ev_rejected") or []
        if ev_rejected and isinstance(ev_rejected[0], dict):
            rejection_reason = (ev_rejected[0].get("rejection_reason")
                                or ev_rejected[0].get("reason"))

        # odds_source — prefer direct field, then matched_odds, then derive from bookmaker
        _matched = an.get("matched_odds") or []
        odds_src = (
            an.get("odds_source")
            or (_matched[0].get("source") if _matched else None)
            or ("API_FOOTBALL" if bookmaker_odd else "NO_ODDS")
        )

        # ── SAFE_SELECTION_MODE check ───────────────────────────────────────────
        safe_mode = os.environ.get("SAFE_SELECTION_MODE", "").lower() in ("1", "true", "yes")
        selection_mode = "RESEARCH"
        selection_reason = ""

        if safe_mode:
            # Check all safe criteria
            tier_val = (an.get("statistical_tier") or an.get("tier_level") or "NO_VALUE").upper()
            reasons = []

            if tier_val not in ("S_TIER", "B_TIER"):
                reasons.append("RESEARCH_TOXIC_TIER")
            if odds_src not in ("API_FOOTBALL", "ODDS_API"):
                reasons.append("RESEARCH_NO_ODDS_SOURCE")
            if bookmaker_odd is None or bookmaker_odd < 1.20:
                reasons.append("RESEARCH_ODD_TOO_LOW")
            if bookmaker_odd and bookmaker_odd > 2.50:
                reasons.append("RESEARCH_ODD_TOO_HIGH")
            if ev_pct is None or ev_pct < 3:
                reasons.append("RESEARCH_EV_TOO_LOW")
            if ev_pct and ev_pct > 25:
                reasons.append("RESEARCH_EV_TOO_HIGH")
            if market_prob is None or market_prob < 0.50:
                reasons.append("RESEARCH_PROB_TOO_LOW")
            if market_prob and market_prob > 0.80:
                reasons.append("RESEARCH_PROB_TOO_HIGH")
            if market in ("FT_UNDER_1_5", "FT_OVER_3_5"):
                reasons.append("RESEARCH_TOXIC_MARKET")

            if not reasons:
                selection_mode = "LIVE_SAFE"
                selection_reason = "PASSED_SAFE_MODE"
            else:
                selection_mode = "RESEARCH"
                selection_reason = "; ".join(reasons)
        else:
            selection_mode = "LIVE"
            selection_reason = "SAFE_MODE_DISABLED"

        # ── Phase 1 — DEBUG_PERSIST_EV logging ──────────────────────────────
        import os as _os
        if _os.environ.get("DEBUG_PERSIST_EV", "").lower() in ("1", "true", "yes"):
            logger.warning(
                "[PERSIST_EV] market=%s | tier=%s | odds_src=%s | bk_odd=%s | "
                "bookmaker=%s | mkt_prob=%s | impl_prob=%s | ev_pct=%s | "
                "edge_pct=%s | expected_val=%s | prob_src=%s | ev_quality=%s",
                market, an.get("tier_level"), odds_src, bookmaker_odd,
                bookmaker_name, market_prob, implied_prob, ev_pct,
                edge_pct, expected_val, prob_source, ev_quality_val,
            )

        row = {
            "prediction_id":         prediction_id,
            "fixture_id":            fixture_id,
            "home_team":             str(md.get("home_team", "")),
            "away_team":             str(md.get("away_team", "")),
            "league":                str(md.get("competition") or md.get("league", "")),
            "country":               str(md.get("country", "")),
            "kickoff_time":          md.get("kickoff_time") or md.get("kickoff"),
            "prediction_date":       today,
            "market":                market,
            "statistical_tier":      an.get("statistical_tier"),
            "ev_tier":               an.get("tier_level"),
            "match_universe":        an.get("match_universe"),
            "coverage_quality":      an.get("coverage_quality"),
            "confidence_score":      profile.get("confidence_score"),
            "volatility_score":      profile.get("volatility_score"),
            "chaos_score":           va.get("chaos_score"),
            "false_signal_score":    fs.get("false_signal_score"),
            "ranking_score":         an.get("ranking_score"),
            # LSE
            "league_edge_rating":             lse.get("league_edge_rating", "NO_DATA"),
            "market_historical_profitability": lse.get("market_historical_profitability", "NO_DATA"),
            # EAE
            "historical_failure_penalty": eae.get("historical_failure_penalty", 0),
            "failure_pattern_warning":    eae.get("failure_pattern_warning", ""),
            "why_pick":               _safe_json(eae.get("why_pick", [])),
            "risk_factors":           _safe_json(eae.get("risk_factors", [])),
            "why_not_s_tier":         _safe_json(eae.get("why_not_s_tier", [])),
            # ── EV / odds fields (Phase 2) ───────────────────────────────────
            "bookmaker_odd":          bookmaker_odd,
            "bookmaker":              bookmaker_name,
            "model_probability":      market_prob,
            "market_probability":     market_prob,
            "implied_probability":    implied_prob,
            "ev_percent":             ev_pct,
            "ev_percentage":          ev_pct,
            "edge_percent":           edge_pct,
            "edge_percentage":        edge_pct,
            "expected_value":         expected_val,
            "fair_odd":               fair_odd_val,
            "probability_source":     prob_source,
            "ev_quality":             ev_quality_val,
            "rejection_reason":       rejection_reason,
            "status":                 "PENDING",
            "tracking_generation":    "POST_RESET" if _is_post_reset() else "LEGACY",
            # Multi-market regime fields (Phase 2/4/5)
            "market_regime":                 an.get("market_regime"),
            "best_market":                   an.get("best_market"),
            "secondary_market":              an.get("secondary_market"),
            "best_over_market":              an.get("best_over_market"),
            "best_under_market":             an.get("best_under_market"),
            "recommended_market_direction":  (
                an.get("recommended_market_direction")
                or (an.get("defensive_profile") or {}).get("recommended_direction")
            ),
            "offensive_profile":            _safe_json(an.get("offensive_profile") or {}),
            "defensive_profile":            _safe_json(an.get("defensive_profile") or {}),
            "avoid_markets":                _safe_json(an.get("avoid_markets") or []),
            "market_generation_stats":      _safe_json(an.get("market_generation_stats") or {}),
            "rejection_reasons_by_market":  _safe_json(an.get("rejection_reasons_by_market") or {}),
            # Bettable Universe
            "market_access":           an.get("market_access", "RESEARCH_ONLY"),
            "bettable_priority_score": an.get("bettable_priority_score", 0),
            "odds_coverage_score":     an.get("odds_coverage_score", 0),
            "market_liquidity_score":  an.get("market_liquidity_score", 0),
            "bettable_tier":           an.get("bettable_tier"),
            # Odds source tracking
            "odds_source": odds_src,
            # Safe selection mode
            "selection_mode":          selection_mode,
            "selection_reason":        selection_reason,
        }
        try:
            self._client.table("predictions").upsert(
                row, on_conflict="fixture_id,market,prediction_date"
            ).execute()
            return True
        except Exception as exc:
            logger.warning(f"[REPO] save_prediction FAILED {prediction_id}: {exc}")
            return False

    def save_odds_snapshots(self, fixture_id: str, odds_list: List[dict]) -> int:
        """Bulk-insert odds snapshot rows. Returns rows inserted."""
        if not self._client or not odds_list:
            return 0
        rows = []
        for o in odds_list:
            rows.append({
                "fixture_id":               fixture_id,
                "market":                   str(o.get("market", "")),
                "bookmaker":                str(o.get("bookmaker", "")),
                "bookmaker_odd":            o.get("bookmaker_odd") or o.get("odd"),
                "fair_odd":                 o.get("fair_odd"),
                "ev_percent":               o.get("ev_percent"),
                "market_mapping_confidence": o.get("market_mapping_confidence"),
                "odds_status":              o.get("status"),
            })
        try:
            self._client.table("odds_snapshots").insert(rows).execute()
            return len(rows)
        except Exception as exc:
            logger.debug(f"[REPO] save_odds_snapshots {fixture_id}: {exc}")
            return 0

    # ─── Phase 5 — Settlement ─────────────────────────────────────────────────

    def update_fixture_result(
        self,
        fixture_id: str,
        home_score: int, away_score: int,
        ht_home: int = 0, ht_away: int = 0,
        status: str = "FINISHED",
    ) -> bool:
        """Update a fixture with final scores."""
        if not self._client:
            return False
        try:
            self._client.table("fixtures").update({
                "status":         status,
                "home_score":     home_score,
                "away_score":     away_score,
                "ht_home_score":  ht_home,
                "ht_away_score":  ht_away,
            }).eq("fixture_id", fixture_id).execute()
            return True
        except Exception as exc:
            logger.debug(f"[REPO] update_fixture_result {fixture_id}: {exc}")
            return False

    def settle_prediction(
        self,
        prediction_id: str,
        home_score: int, away_score: int,
        ht_home: int = 0, ht_away: int = 0,
        bookmaker_odd: float = 1.0,
        notes: str = "",
    ) -> bool:
        """
        Phase 6: Evaluate market result, compute P/L, persist.
        Transitions PENDING → WON | LOST | VOID.
        """
        if not self._client:
            return False

        # Fetch prediction to get market
        try:
            resp = (
                self._client.table("predictions")
                .select("market, bookmaker_odd, status")
                .eq("prediction_id", prediction_id)
                .single()
                .execute()
            )
            row = resp.data or {}
        except Exception as exc:
            logger.debug(f"[REPO] settle fetch {prediction_id}: {exc}")
            return False

        if row.get("status") != "PENDING":
            return False  # Already settled

        market  = row.get("market", "")
        odd     = float(row.get("bookmaker_odd") or bookmaker_odd or 1.0)
        result  = evaluate_market_result(market, home_score, away_score, ht_home, ht_away)
        pl      = calculate_profit_loss(result, odd)

        status_map = {"WIN": "WON", "LOSS": "LOST", "VOID": "VOID"}
        new_status = status_map.get(result, "ERROR")

        try:
            self._client.table("predictions").update({
                "status":             new_status,
                "final_result":       result,
                "actual_home_score":  home_score,
                "actual_away_score":  away_score,
                "actual_ht_home_score": ht_home,
                "actual_ht_away_score": ht_away,
                "profit_loss":        pl,
                "settled_at":         datetime.now(timezone.utc).isoformat(),
                "settlement_notes":   notes,
            }).eq("prediction_id", prediction_id).execute()
            logger.info(
                f"[REPO] Settled {prediction_id}: {result} ({pl:+.3f}u)"
            )
            return True
        except Exception as exc:
            logger.debug(f"[REPO] settle_prediction {prediction_id}: {exc}")
            return False

    def get_pending_predictions(
        self,
        before_kickoff: Optional[datetime] = None,
        limit: int = 200,
        since_date: str = "",
    ) -> List[dict]:
        """Return PENDING predictions whose kickoff has passed."""
        if not self._client:
            return []
        try:
            q = (
                self._client.table("predictions")
                .select(
                    "prediction_id, fixture_id, market, kickoff_time, "
                    "bookmaker_odd, league, country"
                )
                .eq("status", "PENDING")
                .limit(limit)
            )
            if before_kickoff:
                q = q.lt("kickoff_time", before_kickoff.isoformat())
            if since_date:
                q = _apply_since_filter(q, since_date)
            return (q.execute().data) or []
        except Exception as exc:
            logger.debug(f"[REPO] get_pending_predictions: {exc}")
            return []

    def get_pending_count(self) -> int:
        """Fast count of all PENDING predictions (no kickoff filter)."""
        if not self._client:
            return 0
        try:
            resp = (
                self._client.table("predictions")
                .select("prediction_id", count="exact")
                .eq("status", "PENDING")
                .limit(1)
                .execute()
            )
            return resp.count or 0
        except Exception as exc:
            logger.debug(f"[REPO] get_pending_count: {exc}")
            return 0

    # ─── Phase 7 — Performance aggregation ───────────────────────────────────

    # Minimum bookmaker_odd to be considered a "real" odds pick (not default 1.0)
    REAL_ODDS_THRESHOLD = 1.1

    def _fetch_settled(self, days: int = 365, since_date: str = "") -> List[dict]:
        if not self._client:
            return []
        try:
            from datetime import timedelta
            if since_date:
                cutoff = since_date  # TRACKING_RESET_AT override
            else:
                cutoff = (date.today() - timedelta(days=days)).isoformat()
            q = (
                self._client.table("predictions")
                .select(
                    "status, profit_loss, bookmaker_odd, statistical_tier, "
                    "match_universe, league, market, confidence_score, prediction_date, selection_mode"
                )
                .in_("status", ["WON", "LOST", "VOID"])
            )
            # NOTE: SAFE_SELECTION_MODE filtering is handled in performance_report.py
            # to avoid environment variable context issues in repository layer
            q = _apply_since_filter(q, cutoff)
            resp = q.execute()
            logger.debug(f"[REPO] _fetch_settled: cutoff={cutoff}, returned={len(resp.data or [])}")
            return resp.data or []
        except Exception as exc:
            logger.debug(f"[REPO] _fetch_settled: {exc}")
            return []

    @staticmethod
    def _compute_stats(rows: List[dict]) -> dict:
        REAL_ODDS = SupabaseRepository.REAL_ODDS_THRESHOLD
        settled = [r for r in rows if r.get("status") in ("WON", "LOST")]
        wins    = [r for r in settled if r.get("status") == "WON"]
        losses  = [r for r in settled if r.get("status") == "LOST"]

        # ── Statistical accuracy (all settled, regardless of odds) ──────────
        hit_rate = len(wins) / max(len(settled), 1)

        # ── EV / Real-odds split ─────────────────────────────────────────────
        ev_settled = [r for r in settled
                      if float(r.get("bookmaker_odd") or 0) >= REAL_ODDS]
        ev_wins    = [r for r in ev_settled if r.get("status") == "WON"]
        ev_losses  = [r for r in ev_settled if r.get("status") == "LOST"]
        ev_pl      = sum(float(r.get("profit_loss") or 0) for r in ev_settled)
        ev_hit     = len(ev_wins) / max(len(ev_settled), 1)
        ev_roi     = ev_pl / max(len(ev_settled), 1) * 100

        # Average bookmaker_odd for EV picks
        ev_odds    = [float(r.get("bookmaker_odd")) for r in ev_settled
                      if r.get("bookmaker_odd") is not None]
        avg_odd    = sum(ev_odds) / len(ev_odds) if ev_odds else None
        break_even = round(1 / avg_odd, 4) if avg_odd else None
        edge_vs_be = round(ev_hit - break_even, 4) if break_even else None

        # Legacy total_pl / roi (kept for backwards compat — includes no-odds picks)
        total_pl = sum(float(r.get("profit_loss") or 0) for r in settled)
        roi      = total_pl / max(len(settled), 1) * 100

        # Drawdown & streak
        pl_series = [float(r.get("profit_loss") or 0) for r in settled]
        max_dd = 0.0
        peak = 0.0
        cumul = 0.0
        for pl in pl_series:
            cumul += pl
            if cumul > peak:
                peak = cumul
            dd = peak - cumul
            if dd > max_dd:
                max_dd = dd

        streak = 0
        max_streak = 0
        for r in settled:
            if r.get("status") == "LOST":
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

        # False positives (LOST with high confidence or S/A tier)
        fp = [
            r for r in losses
            if float(r.get("confidence_score") or 0) >= 65
            or r.get("statistical_tier") in ("S_TIER", "A_TIER")
        ]
        fp_rate = len(fp) / max(len(losses), 1)

        s_rows  = [r for r in settled if r.get("statistical_tier") == "S_TIER"]
        s_wins  = [r for r in s_rows  if r.get("status") == "WON"]
        a_rows  = [r for r in settled if r.get("statistical_tier") == "A_TIER"]
        a_wins  = [r for r in a_rows  if r.get("status") == "WON"]

        return {
            # ── Counts ──────────────────────────────────────────────────────
            "total_predictions":   len(rows),
            "total_settled":       len(settled),
            "total_wins":          len(wins),
            "total_losses":        len(losses),
            "total_void":          len(rows) - len(settled),
            # ── Statistical accuracy (all picks) ────────────────────────────
            "stat_hit_rate":       round(hit_rate, 4),
            "hit_rate":            round(hit_rate, 4),  # alias
            # ── EV / Real-odds metrics ───────────────────────────────────────
            "ev_total":            len(ev_settled),
            "ev_wins":             len(ev_wins),
            "ev_losses":           len(ev_losses),
            "ev_hit_rate":         round(ev_hit, 4),
            "ev_profit_loss":      round(ev_pl, 4),
            "ev_roi":              round(ev_roi, 2),
            "ev_avg_odd":          round(avg_odd, 4) if avg_odd else None,
            "ev_break_even":       break_even,
            "ev_edge_vs_be":       edge_vs_be,
            # ── Legacy (all settled incl. no-odds) ──────────────────────────
            "roi":                 round(roi, 2),
            "total_profit_loss":   round(total_pl, 4),
            # ── Tier breakdown ──────────────────────────────────────────────
            "s_tier_total":        len(s_rows),
            "s_tier_wins":         len(s_wins),
            "s_tier_hit_rate":     round(len(s_wins) / max(len(s_rows), 1), 4),
            "a_tier_total":        len(a_rows),
            "a_tier_wins":         len(a_wins),
            "a_tier_hit_rate":     round(len(a_wins) / max(len(a_rows), 1), 4),
            # ── Risk metrics ────────────────────────────────────────────────
            "false_positive_count": len(fp),
            "false_positive_rate":  round(fp_rate, 4),
            "max_drawdown":         round(max_dd, 4),
            "longest_losing_streak": max_streak,
            # ── Universe counts ─────────────────────────────────────────────
            "stat_only_count": sum(
                1 for r in rows if r.get("match_universe") == "STATISTICAL_ONLY"
            ),
            "market_ev_count": sum(
                1 for r in rows if r.get("match_universe") == "MARKET_EV"
            ),
        }

    def get_performance_summary(self, days: int = 30, since_date: str = "") -> dict:
        """Phase 7: Overall performance for the past N days (or since a reset date)."""
        rows  = self._fetch_settled(days=days, since_date=since_date)
        stats = self._compute_stats(rows)
        return {"days": days, "since_date": since_date or None, **stats}

    def get_generation_counts(self) -> dict:
        """
        Return total prediction counts split by tracking_generation.
        Uses date-based counting so it works even before migration 002.
        """
        reset_at = _parse_reset_at()
        if not self._client:
            return {"legacy": 0, "post_reset": 0, "total": 0, "reset_at": reset_at}
        try:
            total_resp = (
                self._client.table("predictions")
                .select("prediction_id", count="exact")
                .execute()
            )
            total = total_resp.count or 0
            if reset_at:
                post_resp = _apply_since_filter(
                    self._client.table("predictions")
                    .select("prediction_id", count="exact"),
                    reset_at,
                ).execute()
                post_reset = post_resp.count or 0
            else:
                post_reset = total
            legacy = total - post_reset
            return {
                "legacy":      legacy,
                "post_reset":  post_reset,
                "total":       total,
                "reset_at":    reset_at or None,
            }
        except Exception as exc:
            logger.debug(f"[REPO] get_generation_counts: {exc}")
            return {"legacy": 0, "post_reset": 0, "total": 0, "reset_at": reset_at or None}

    def get_league_profitability(
        self, league: str = "", limit: int = 50, since_date: str = ""
    ) -> List[dict]:
        """Phase 7: Per-league performance from settled predictions."""
        rows = self._fetch_settled(days=365, since_date=since_date)
        by_league: Dict[str, List[dict]] = {}
        for r in rows:
            lg = r.get("league", "Unknown")
            by_league.setdefault(lg, []).append(r)

        result = []
        for lg, lg_rows in by_league.items():
            if league and league.lower() not in lg.lower():
                continue
            s = self._compute_stats(lg_rows)
            result.append({
                "league":   lg,
                "country":  (lg_rows[0].get("country") or ""),
                **s,
            })

        return sorted(result, key=lambda x: -x["roi"])[:limit]

    def get_market_performance(self, limit: int = 30, since_date: str = "") -> List[dict]:
        """Phase 7: Per-market performance from settled predictions."""
        rows = self._fetch_settled(days=365, since_date=since_date)
        by_market: Dict[str, List[dict]] = {}
        for r in rows:
            mk = r.get("market", "Unknown")
            by_market.setdefault(mk, []).append(r)

        result = []
        for mk, mk_rows in by_market.items():
            s = self._compute_stats(mk_rows)
            result.append({"market": mk, **s})

        return sorted(result, key=lambda x: -x["roi"])[:limit]

    def get_market_break_even(self, days: int = 365, since_date: str = "") -> List[dict]:
        """
        Phase 3+4: Break-even analysis and viability classification per market.
        Returns one dict per market with:
            market, stat_wins, stat_losses, stat_hit_rate,
            ev_total, ev_avg_odd, break_even_rate, edge_vs_break_even,
            viability  (STAT_SIGNAL_ONLY | BETTABLE_EV_POSITIVE |
                        BETTABLE_NO_EDGE | UNBETTABLE_LOW_ODDS | NO_ODDS_AVAILABLE)
        """
        REAL_ODDS = self.REAL_ODDS_THRESHOLD
        rows = self._fetch_settled(days=days, since_date=since_date)
        by_market: Dict[str, List[dict]] = {}
        for r in rows:
            mk = r.get("market", "Unknown")
            by_market.setdefault(mk, []).append(r)

        result = []
        for mk, mk_rows in by_market.items():
            settled  = [r for r in mk_rows if r.get("status") in ("WON", "LOST")]
            s_wins   = sum(1 for r in settled if r.get("status") == "WON")
            s_losses = len(settled) - s_wins
            stat_hr  = s_wins / max(len(settled), 1)

            ev_rows  = [r for r in settled
                        if float(r.get("bookmaker_odd") or 0) >= REAL_ODDS]
            ev_odds  = [float(r["bookmaker_odd"]) for r in ev_rows
                        if r.get("bookmaker_odd") is not None]
            avg_odd  = sum(ev_odds) / len(ev_odds) if ev_odds else None

            break_even = round(1 / avg_odd, 4) if avg_odd else None
            edge       = round(stat_hr - break_even, 4) if break_even else None

            # Viability classification
            if not ev_rows:
                viability = "NO_ODDS_AVAILABLE"
            elif avg_odd and avg_odd < 1.05:
                viability = "UNBETTABLE_LOW_ODDS"
            elif len(ev_rows) < 5:
                viability = "STAT_SIGNAL_ONLY"
            elif edge is not None and edge > 0.03:
                viability = "BETTABLE_EV_POSITIVE"
            else:
                viability = "BETTABLE_NO_EDGE"

            ev_wins = sum(1 for r in ev_rows if r.get("status") == "WON")
            ev_pl   = sum(float(r.get("profit_loss") or 0) for r in ev_rows)
            ev_roi  = ev_pl / max(len(ev_rows), 1) * 100

            result.append({
                "market":             mk,
                "stat_total":         len(settled),
                "stat_wins":          s_wins,
                "stat_losses":        s_losses,
                "stat_hit_rate":      round(stat_hr * 100, 1),
                "ev_total":           len(ev_rows),
                "ev_wins":            ev_wins,
                "ev_avg_odd":         round(avg_odd, 3) if avg_odd else None,
                "break_even_rate":    round(break_even * 100, 1) if break_even else None,
                "edge_vs_break_even": round(edge * 100, 1) if edge is not None else None,
                "ev_profit_loss":     round(ev_pl, 4),
                "ev_roi":             round(ev_roi, 1),
                "viability":          viability,
            })

        return sorted(result, key=lambda x: -x["stat_total"])

    def get_tier_performance(self, since_date: str = "") -> List[dict]:
        """Phase 7: Per-tier performance from settled predictions."""
        rows = self._fetch_settled(days=365, since_date=since_date)
        by_tier: Dict[str, List[dict]] = {}
        for r in rows:
            t = r.get("statistical_tier") or "UNKNOWN"
            by_tier.setdefault(t, []).append(r)

        result = []
        for tier, t_rows in by_tier.items():
            s = self._compute_stats(t_rows)
            result.append({"tier": tier, **s})

        order = {"S_TIER": 0, "A_TIER": 1, "WATCHLIST": 2, "UNKNOWN": 9}
        return sorted(result, key=lambda x: order.get(x["tier"], 5))

    def get_prediction_history(
        self, limit: int = 100, status: str = "", since_date: str = ""
    ) -> List[dict]:
        """Return recent predictions for the history endpoint."""
        if not self._client:
            return []
        try:
            q = (
                self._client.table("predictions")
                .select("*")  # select(*) avoids silent failures from missing columns
                .order("prediction_date", desc=True)
                .limit(limit)
            )
            if status:
                q = q.eq("status", status.upper())
            if since_date:
                q = _apply_since_filter(q, since_date)
            return q.execute().data or []
        except Exception as exc:
            logger.warning(f"[REPO] get_prediction_history FAILED: {exc}")
            return []

    def save_model_performance(self, stats: dict, period_type: str = "DAILY") -> bool:
        """Persist a performance snapshot."""
        if not self._client:
            return False
        today = date.today().isoformat()
        row = {
            "period_type":  period_type,
            "period_start": today,
            "period_end":   today,
            **stats,
        }
        try:
            self._client.table("model_performance").upsert(
                row, on_conflict="period_type,period_start"
            ).execute()
            return True
        except Exception as exc:
            logger.debug(f"[REPO] save_model_performance: {exc}")
            return False

    def upsert_false_positive_patterns(self, patterns: List[dict]) -> int:
        """Sync EAE patterns into DB."""
        if not self._client or not patterns:
            return 0
        try:
            self._client.table("false_positive_patterns").upsert(
                patterns,
                on_conflict="league,country,market,failure_reason",
            ).execute()
            return len(patterns)
        except Exception as exc:
            logger.debug(f"[REPO] upsert_false_positive_patterns: {exc}")
            return 0


# ─── Module singleton ─────────────────────────────────────────────────────────
_repo: Optional[SupabaseRepository] = None


def get_repository() -> SupabaseRepository:
    global _repo
    if _repo is None:
        _repo = SupabaseRepository()
    return _repo


def reset_repository() -> None:
    global _repo
    _repo = None
