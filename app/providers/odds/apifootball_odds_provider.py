"""
ApiFootballOddsProvider — Phase 2+3
=====================================
Fetches odds from API-Football /odds endpoint.
Normalises to NormalizedOdd (same format as TheOddsAPIProvider).

Phase 3 — No team-name fuzzy matching.
Fixture IDs come from the same API  →  direct lookup, zero MATCHING_UNCERTAIN.

Rule: NEVER block analysis if odds absent.
      NEVER use mock or hardcoded keys.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from app.providers.odds.base_odds_provider import BaseOddsProvider, OddsProviderConfig
from app.providers.odds.models import (
    NormalizedOdd, MatchMapping, OddsResponse,
    MarketType, OddsData,
)

logger = logging.getLogger(__name__)

# Bet name → our internal market family
_BET_NAME_MATCH_WINNER   = "match winner"
_BET_NAME_GOALS_OU       = "goals over/under"
_BET_NAME_BTTS           = "both teams score"
_BET_NAME_HT_GOALS       = {"first half goals", "first half - over/under",
                             "goals over/under first half", "1st half goals",
                             "1st half - over/under", "half time - over/under",
                             "half-time goals", "first half total goals"}

ALLOWED_FT_LINES: frozenset = frozenset({1.5, 2.5, 3.5, 4.5})
ALLOWED_HT_LINES: frozenset = frozenset({0.5, 1.5})


class ApiFootballOddsProvider(BaseOddsProvider):
    """
    Odds provider backed by API-Football /odds endpoint.

    Prefetch strategy  : batch by date  (/odds?date=YYYY-MM-DD)
    Match strategy     : fixture_id direct lookup  (Phase 3 — no fuzzy needed)
    Output format      : NormalizedOdd  (source="API_FOOTBALL")
    """

    SOURCE_TAG = "API_FOOTBALL"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        config: Optional[OddsProviderConfig] = None,
    ):
        if config is None:
            config = OddsProviderConfig(
                name="api_football_odds",
                enabled=True,
                timeout_seconds=20,
                rate_limit_per_minute=30,
            )
        super().__init__(config)

        self.api_key: Optional[str] = api_key or None
        self.base_url: str = (api_url or "https://v3.football.api-sports.io").rstrip("/")

        # Cache: fixture_id (str) → list of NormalizedOdd
        self._fixture_cache: Dict[str, List[NormalizedOdd]] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 1800.0  # 30 min

        # Diagnostics
        self.events_fetched: int = 0
        self.bookmakers_seen: set = set()
        self.markets_seen: set = set()
        self.mapping_success: int = 0
        self.mapping_failed: int = 0

    # ------------------------------------------------------------------
    # Status

    @property
    def odds_status(self) -> str:
        if not self.api_key:
            return "MISSING_KEY"
        return "CONFIGURED"

    @property
    def key_present(self) -> bool:
        return bool(self.api_key)

    # ------------------------------------------------------------------
    # Internal HTTP

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        if not self.api_key:
            return None
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = requests.get(
                url,
                params=params or {},
                headers={"x-apisports-key": self.api_key},
                timeout=self.config.timeout_seconds,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.debug(f"[APIFB_ODDS] HTTP {resp.status_code} on {url}")
            return None
        except Exception as exc:
            logger.debug(f"[APIFB_ODDS] Request error (non-blocking): {exc}")
            return None

    # ------------------------------------------------------------------
    # Phase 2 — Normalisation

    @staticmethod
    def _parse_value_line(value_str: str) -> Tuple[Optional[str], Optional[float]]:
        """
        Parse 'Over 2.5' or 'Under 0.5' etc.
        Returns ('OVER'|'UNDER'|None, line_float|None).
        """
        v = value_str.strip().lower()
        for prefix in ("over ", "under "):
            if v.startswith(prefix):
                side = "OVER" if prefix == "over " else "UNDER"
                try:
                    line = float(v[len(prefix):])
                    return side, line
                except ValueError:
                    return None, None
        return None, None

    def _normalise_fixture(
        self,
        fixture_id: str,
        bookmakers: list,
        league_name: str = "",
        country: str = "",
    ) -> List[NormalizedOdd]:
        """
        Phase 2: Convert API-Football bookmakers list to NormalizedOdd objects.
        """
        result: List[NormalizedOdd] = []
        ts = datetime.now(timezone.utc).isoformat()

        for bk in bookmakers:
            bk_name = bk.get("name", "?")
            self.bookmakers_seen.add(bk_name)

            for bet in bk.get("bets", []):
                bet_name_raw = bet.get("name", "")
                bet_name = bet_name_raw.lower().strip()
                self.markets_seen.add(bet_name_raw)
                values = bet.get("values", [])

                # ── 1X2 / Match Winner ─────────────────────────────────────
                if bet_name == _BET_NAME_MATCH_WINNER:
                    _side_map = {"home": ("HOME", "FT_H2H_HOME"),
                                 "draw": ("DRAW", "FT_H2H_DRAW"),
                                 "away": ("AWAY", "FT_H2H_AWAY")}
                    for v in values:
                        val  = v.get("value", "").lower()
                        odd_s = v.get("odd", "")
                        if val not in _side_map or not odd_s:
                            continue
                        try:
                            odd_f = float(odd_s)
                        except ValueError:
                            continue
                        side, mkt = _side_map[val]
                        result.append(NormalizedOdd(
                            bookmaker=bk_name,
                            market=mkt,
                            line=None,
                            side=side,
                            odd=odd_f,
                            implied_probability=1.0 / odd_f if odd_f > 0 else 0.0,
                            timestamp=ts,
                            source=self.SOURCE_TAG,
                            match_id=fixture_id,
                        ))

                # ── FT Goals Over/Under ────────────────────────────────────
                elif bet_name == _BET_NAME_GOALS_OU:
                    for v in values:
                        side, line = self._parse_value_line(v.get("value", ""))
                        if side is None or line is None:
                            continue
                        if line not in ALLOWED_FT_LINES:
                            continue
                        odd_s = v.get("odd", "")
                        if not odd_s:
                            continue
                        try:
                            odd_f = float(odd_s)
                        except ValueError:
                            continue
                        mkt = f"FT_{side}_{str(line).replace('.', '_')}"
                        result.append(NormalizedOdd(
                            bookmaker=bk_name,
                            market=mkt,
                            line=line,
                            side=side,
                            odd=odd_f,
                            implied_probability=1.0 / odd_f if odd_f > 0 else 0.0,
                            timestamp=ts,
                            source=self.SOURCE_TAG,
                            match_id=fixture_id,
                        ))

                # ── BTTS ───────────────────────────────────────────────────
                elif bet_name == _BET_NAME_BTTS:
                    for v in values:
                        val   = v.get("value", "").lower()
                        odd_s = v.get("odd", "")
                        if not odd_s:
                            continue
                        try:
                            odd_f = float(odd_s)
                        except ValueError:
                            continue
                        if "yes" in val:
                            side, mkt = "YES", "BTTS_YES"
                        elif "no" in val:
                            side, mkt = "NO", "BTTS_NO"
                        else:
                            continue
                        result.append(NormalizedOdd(
                            bookmaker=bk_name,
                            market=mkt,
                            line=None,
                            side=side,
                            odd=odd_f,
                            implied_probability=1.0 / odd_f if odd_f > 0 else 0.0,
                            timestamp=ts,
                            source=self.SOURCE_TAG,
                            match_id=fixture_id,
                        ))

                # ── HT Goals Over/Under ────────────────────────────────────
                elif bet_name in _BET_NAME_HT_GOALS:
                    for v in values:
                        side, line = self._parse_value_line(v.get("value", ""))
                        if side is None or line is None:
                            continue
                        if line not in ALLOWED_HT_LINES:
                            continue
                        odd_s = v.get("odd", "")
                        if not odd_s:
                            continue
                        try:
                            odd_f = float(odd_s)
                        except ValueError:
                            continue
                        mkt = f"HT_{side}_{str(line).replace('.', '_')}"
                        result.append(NormalizedOdd(
                            bookmaker=bk_name,
                            market=mkt,
                            line=line,
                            side=side,
                            odd=odd_f,
                            implied_probability=1.0 / odd_f if odd_f > 0 else 0.0,
                            timestamp=ts,
                            source=self.SOURCE_TAG,
                            match_id=fixture_id,
                        ))

        return result

    # ------------------------------------------------------------------
    # Phase 2 — Batch prefetch by date

    def _fetch_date_batch(self, target_date: str) -> Dict[str, List[NormalizedOdd]]:
        """
        Fetch ALL fixtures' odds for a date in one or few paginated requests.
        Returns {fixture_id: [NormalizedOdd]}.
        """
        cache: Dict[str, List[NormalizedOdd]] = {}
        page = 1
        total_pages = 1

        while page <= total_pages and page <= 10:  # safety cap at 10 pages
            data = self._get("odds", {"date": target_date, "page": page})
            if not data:
                break

            response = data.get("response", [])
            paging   = data.get("paging", {})
            total_pages = int(paging.get("total", 1))

            for item in response:
                fix_obj = item.get("fixture", {})
                fid = str(fix_obj.get("id", ""))
                if not fid:
                    continue

                lg_obj = item.get("league", {})
                bookmakers = item.get("bookmakers", [])
                normalized = self._normalise_fixture(
                    fixture_id=fid,
                    bookmakers=bookmakers,
                    league_name=lg_obj.get("name", ""),
                    country=lg_obj.get("country", ""),
                )
                if normalized:
                    cache[fid] = normalized

            page += 1
            if page <= total_pages:
                time.sleep(0.3)  # gentle rate limiting

        return cache

    # ------------------------------------------------------------------
    # Phase 2 — Prefetch interface (same as TheOddsAPIProvider)

    def prefetch_for_matches(self, matches: list) -> None:
        """
        Batch-fetch all odds for today via /odds?date=...
        Ignores the matches list (we always fetch the full day batch).
        """
        if not self.api_key:
            return

        now = time.time()
        if self._fixture_cache and (now - self._cache_ts) < self._cache_ttl:
            logger.debug("[APIFB_ODDS] Cache still fresh — skipping prefetch")
            return

        target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logger.info(f"[APIFB_ODDS] Batch prefetch for {target_date}")

        self._fixture_cache = self._fetch_date_batch(target_date)
        self._cache_ts = time.time()
        self.events_fetched = len(self._fixture_cache)

        total_odds = sum(len(v) for v in self._fixture_cache.values())
        logger.info(
            f"[APIFB_ODDS] Prefetch done: {self.events_fetched} fixtures / "
            f"{total_odds} NormalizedOdd entries"
        )

    def prefetch_all_soccer_odds(self) -> None:
        """Alias — delegates to prefetch_for_matches."""
        self.prefetch_for_matches([])

    # ------------------------------------------------------------------
    # Phase 3 — Direct fixture_id lookup

    def get_match_odds_normalized(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        kickoff: Optional[datetime] = None,
    ) -> Tuple[List[NormalizedOdd], Optional[MatchMapping]]:
        """
        Phase 3: Direct fixture_id lookup — no fuzzy matching.
        Returns ([], None) if not found (non-blocking).
        """
        if not self.api_key:
            return [], None

        if not self._fixture_cache:
            return [], None

        fid = str(match_id)
        odds = self._fixture_cache.get(fid, [])

        import os as _os_apifb
        if _os_apifb.getenv('DEBUG_ODDS_WIRING', '').lower() == 'true':
            _sample_keys = list(self._fixture_cache.keys())[:10]
            logger.info(
                f"[WIRE_CACHE] lookup fid={fid!r}"
                f" | cache_size={len(self._fixture_cache)}"
                f" | cache_hit={bool(odds)}"
                f" | cache_keys_sample={_sample_keys}"
            )

        if odds:
            self.mapping_success += 1
            mapping = MatchMapping(
                event_id=fid,
                home_team_api=home_team,
                away_team_api=away_team,
                home_team_odds=home_team,
                away_team_odds=away_team,
                kickoff_diff_minutes=0.0,
                name_score_home=1.0,
                name_score_away=1.0,
                match_confidence_score=1.0,
                confidence_label="EXACT",    # Phase 3 — same API, same ID
                odds_status="MATCHED",
            )
            return odds, mapping

        self.mapping_failed += 1
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
            mt = self._market_str_to_type(n.market)
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
        for fid, norms in self._fixture_cache.items():
            for n in norms:
                mt = self._market_str_to_type(n.market)
                if mt:
                    all_data.append(OddsData(
                        match_id=fid,
                        market_type=mt,
                        line=n.line,
                        odd=n.odd,
                        bookmaker=n.bookmaker,
                    ))
        return self._create_success_response(all_data)

    @staticmethod
    def _market_str_to_type(market: str) -> Optional[MarketType]:
        _map = {
            "FT_UNDER_1_5": MarketType.FT_UNDER_15,
            "FT_OVER_1_5":  MarketType.FT_OVER_15,
            "FT_UNDER_2_5": MarketType.FT_UNDER_25,
            "FT_OVER_2_5":  MarketType.FT_OVER_25,
            "FT_UNDER_3_5": MarketType.FT_UNDER_35,
            "FT_OVER_3_5":  MarketType.FT_OVER_35,
            "FT_UNDER_4_5": MarketType.FT_UNDER_45,
            "FT_OVER_4_5":  MarketType.FT_OVER_45,
            "HT_UNDER_0_5": MarketType.HT_UNDER_05,
            "HT_OVER_0_5":  MarketType.HT_OVER_05,
            "HT_UNDER_1_5": MarketType.HT_UNDER_15,
            "HT_OVER_1_5":  MarketType.HT_OVER_15,
            "BTTS_YES":     MarketType.BTTS_YES,
            "BTTS_NO":      MarketType.BTTS_NO,
            "FT_H2H_HOME":  MarketType.H2H_HOME,
            "FT_H2H_DRAW":  MarketType.H2H_DRAW,
            "FT_H2H_AWAY":  MarketType.H2H_AWAY,
        }
        return _map.get(market)

    # ------------------------------------------------------------------
    # Diagnostics

    def get_diagnostics(self) -> dict:
        return {
            "provider":              "api_football_odds",
            "api_key_present":       self.key_present,
            "odds_status":           self.odds_status,
            "fixtures_with_odds":    self.events_fetched,
            "mapping_success_count": self.mapping_success,
            "mapping_failed_count":  self.mapping_failed,
            "bookmakers_available":  sorted(self.bookmakers_seen),
            "markets_available":     sorted(self.markets_seen),
            "cache_fixtures":        len(self._fixture_cache),
            "cache_age_seconds": (
                int(time.time() - self._cache_ts) if self._cache_ts else None
            ),
        }
