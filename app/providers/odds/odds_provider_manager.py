"""
OddsProviderManager — Phase 1
===============================
Priority fallback chain for odds providers.

Hierarchy:
  1. API-Football /odds    (primary — 46% coverage, direct fixture_id match)
  2. The Odds API          (fallback — broader sport-key coverage)
  3. NO_ODDS               (never blocks analysis)

Exposes the same interface as TheOddsAPIProvider so the scanner
requires zero modification.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.providers.odds.base_odds_provider import BaseOddsProvider, OddsProviderConfig
from app.providers.odds.models import (
    NormalizedOdd, MatchMapping, OddsResponse, MarketType, OddsData,
)

logger = logging.getLogger(__name__)


class OddsProviderManager(BaseOddsProvider):
    """
    Priority-based odds provider.

    Call flow for get_match_odds_normalized:
      try ApiFootballOddsProvider  → if odds found: return with source=API_FOOTBALL
      try TheOddsAPIProvider       → if odds found: return with source=ODDS_API
      return ([], None)            → never blocks analysis
    """

    def __init__(
        self,
        apifootball_key: Optional[str] = None,
        apifootball_url: Optional[str] = None,
        oddsapi_key: Optional[str] = None,
        oddsapi_url: Optional[str] = None,
    ):
        config = OddsProviderConfig(
            name="odds_provider_manager",
            enabled=True,
            timeout_seconds=20,
        )
        super().__init__(config)

        # Build sub-providers (lazy-imported to avoid circular imports)
        from app.providers.odds.apifootball_odds_provider import ApiFootballOddsProvider
        from app.providers.odds.external_odds_provider import TheOddsAPIProvider

        self._apifb  = ApiFootballOddsProvider(
            api_key=apifootball_key,
            api_url=apifootball_url,
        )
        self._oddsapi = TheOddsAPIProvider(
            api_key=oddsapi_key,
            api_url=oddsapi_url,
        )

        # Diagnostic counters
        self._matched_apifb:   int = 0
        self._matched_oddsapi: int = 0
        self._matched_none:    int = 0
        self._total_calls:     int = 0

    # ------------------------------------------------------------------
    # api_key property — scanner checks this before calling prefetch
    # True if at least one provider has a configured key

    @property
    def api_key(self) -> Optional[str]:
        return self._apifb.api_key or self._oddsapi.api_key

    @property
    def odds_status(self) -> str:
        parts = []
        if self._apifb.key_present:
            parts.append("APIFB")
        if self._oddsapi.key_present:
            parts.append("ODDSAPI")
        return "+".join(parts) if parts else "MISSING_KEY"

    # ------------------------------------------------------------------
    # Prefetch — call both providers

    def prefetch_for_matches(self, matches: list) -> None:
        """Prefetch both providers in sequence (non-blocking on any error)."""
        # Provider 1 — API-Football (batch by date)
        if self._apifb.key_present:
            try:
                self._apifb.prefetch_for_matches(matches)
            except Exception as exc:
                logger.debug(f"[OPM] ApiFootball prefetch non-blocking: {exc}")

        # Provider 2 — The Odds API (targeted sport-key prefetch)
        if self._oddsapi.key_present and getattr(self._oddsapi, '_event_cache', None) is None or \
                self._oddsapi.key_present:
            try:
                self._oddsapi.prefetch_for_matches(matches)
            except Exception as exc:
                logger.debug(f"[OPM] OddsAPI prefetch non-blocking: {exc}")

    def prefetch_all_soccer_odds(self) -> None:
        """Alias — delegates to prefetch_for_matches([])."""
        self.prefetch_for_matches([])

    # ------------------------------------------------------------------
    # Primary interface — used by SmartScanner

    @property
    def events_fetched(self) -> int:
        """Total events across both providers."""
        apifb_n  = getattr(self._apifb,   "events_fetched", 0)
        oddsapi_n = getattr(self._oddsapi, "events_fetched", 0)
        return apifb_n + oddsapi_n

    def get_match_odds_normalized(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        kickoff: Optional[datetime] = None,
    ) -> Tuple[List[NormalizedOdd], Optional[MatchMapping]]:
        """
        Phase 1 — Priority fallback:
          1. API-Football (direct fixture_id match)
          2. The Odds API (fuzzy team-name match)
          3. return ([], None)
        """
        self._total_calls += 1

        # ── Provider 1: API-Football ───────────────────────────────────
        if self._apifb.key_present:
            try:
                odds, mapping = self._apifb.get_match_odds_normalized(
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    kickoff=kickoff,
                )
                if odds:
                    self._matched_apifb += 1
                    logger.debug(
                        f"[OPM] {home_team} vs {away_team} → API_FOOTBALL "
                        f"({len(odds)} odds, fixture_id={match_id})"
                    )
                    return odds, mapping
            except Exception as exc:
                logger.debug(f"[OPM] ApiFootball odds non-blocking: {exc}")

        # ── Provider 2: The Odds API ───────────────────────────────────
        if self._oddsapi.key_present and getattr(self._oddsapi, '_event_cache', None):
            try:
                odds, mapping = self._oddsapi.get_match_odds_normalized(
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    kickoff=kickoff,
                )
                if odds:
                    self._matched_oddsapi += 1
                    logger.debug(
                        f"[OPM] {home_team} vs {away_team} → ODDS_API "
                        f"({len(odds)} odds)"
                    )
                    return odds, mapping
            except Exception as exc:
                logger.debug(f"[OPM] OddsAPI odds non-blocking: {exc}")

        # ── No odds found ──────────────────────────────────────────────
        self._matched_none += 1
        return [], None

    # ------------------------------------------------------------------
    # BaseOddsProvider abstract methods

    def get_match_odds(self, match_id, markets=None, **kwargs) -> OddsResponse:
        odds, _ = self.get_match_odds_normalized(
            match_id=match_id,
            home_team=kwargs.get("home_team", ""),
            away_team=kwargs.get("away_team", ""),
        )
        data = []
        for n in odds:
            if hasattr(self._apifb, "_market_str_to_type"):
                mt = self._apifb._market_str_to_type(n.market)
                if mt:
                    data.append(OddsData(
                        match_id=match_id,
                        market_type=mt,
                        line=n.line,
                        odd=n.odd,
                        bookmaker=n.bookmaker,
                    ))
        return self._create_success_response(data)

    def get_today_odds(self, competition_ids=None, markets=None) -> OddsResponse:
        all_data = []
        for provider in (self._apifb, self._oddsapi):
            try:
                resp = provider.get_today_odds()
                if resp.success and resp.data:
                    all_data.extend(resp.data)
            except Exception:
                pass
        return self._create_success_response(all_data)

    # ------------------------------------------------------------------
    # Diagnostics — Phase 5

    def get_diagnostics(self) -> dict:
        apifb_diag  = {}
        oddsapi_diag = {}
        try:
            apifb_diag  = self._apifb.get_diagnostics()
        except Exception:
            pass
        try:
            oddsapi_diag = self._oddsapi.get_diagnostics()
        except Exception:
            pass

        total = max(self._total_calls, 1)
        cov_apifb  = round(self._matched_apifb  / total * 100, 1)
        cov_oddsapi = round(self._matched_oddsapi / total * 100, 1)

        return {
            # Phase 5 required fields
            "odds_provider_primary":   "API_FOOTBALL" if self._apifb.key_present else "ODDS_API",
            "odds_provider_secondary": "ODDS_API"      if self._oddsapi.key_present else "NONE",
            "odds_provider_status":    self.odds_status,

            "coverage_apifootball": cov_apifb,
            "coverage_oddsapi":     cov_oddsapi,

            "matched_odds_apifootball": self._matched_apifb,
            "matched_odds_oddsapi":     self._matched_oddsapi,
            "matched_none":             self._matched_none,
            "total_calls":              self._total_calls,

            # Sub-provider details
            "apifootball": apifb_diag,
            "the_odds_api": oddsapi_diag,
        }

    # ------------------------------------------------------------------
    # Coverage summary (used by /api/diagnostics)

    def coverage_summary(self) -> dict:
        """Lightweight summary for Flask diagnostics endpoint."""
        apifb_fixtures  = getattr(self._apifb, "events_fetched", 0)
        oddsapi_events  = getattr(self._oddsapi, "events_fetched", 0)
        return {
            "api_football_fixtures_with_odds": apifb_fixtures,
            "odds_api_events_loaded":          oddsapi_events,
            "matched_from_apifootball":        self._matched_apifb,
            "matched_from_oddsapi":            self._matched_oddsapi,
            "no_odds_count":                   self._matched_none,
        }
