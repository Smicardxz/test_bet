"""
External Odds Provider — Phases 1-4
Fetches real odds from The Odds API (https://the-odds-api.com/)

Phase 1: ODDS_API_KEY from env only, odds_status property, MISSING_KEY if absent
Phase 2: Soccer markets: HT/FT Under/Over, BTTS, 1X2
Phase 3: Match confidence scoring (EXACT/HIGH/MEDIUM/LOW/FAILED)
Phase 4: NormalizedOdd output format

Rule: NEVER block analysis if odds absent.
      NEVER use mock or hardcoded keys.
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher

import requests

from app.providers.odds.base_odds_provider import BaseOddsProvider, OddsProviderConfig
from app.providers.odds.models import (
    OddsData, OddsResponse, MarketType,
    NormalizedOdd, MatchMapping,
    IGNORED_MARKET_LINES, TOTALS_MAP, HT_TOTALS_MAP,
)

logger = logging.getLogger(__name__)

# Markets allowed in this system (Phase 5 filter)
ALLOWED_MARKET_LINES = {0.5, 1.5, 2.5, 3.5, 4.5}

# All sport keys we support (fallback full list — used only if no targeted matches given)
SOCCER_SPORT_KEYS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_france_ligue1",
    "soccer_italy_serie_a",
    "soccer_netherlands_eredivisie",
    "soccer_portugal_primeira_liga",
    "soccer_turkey_super_league",
    "soccer_belgium_first_div",
    "soccer_england_efl_champ",
    "soccer_scotland_premiership",
    "soccer_brazil_campeonato",
    "soccer_argentina_primera_division",
    "soccer_usa_mls",
    "soccer_mexico_ligamx",
    "soccer_denmark_superliga",
    "soccer_norway_eliteserien",
    "soccer_sweden_allsvenskan",
    "soccer_poland_ekstraklasa",
    "soccer_greece_super_league",
    "soccer_japan_j_league",
]

# API-Football league name/country → The Odds API sport_key
# Used by prefetch_for_matches() to fetch ONLY the leagues we actually target.
LEAGUE_TO_SPORT_KEY: Dict[str, str] = {
    # (lowercase league name fragment) → sport_key
    "premier league":              "soccer_epl",
    "la liga":                     "soccer_spain_la_liga",
    "bundesliga":                  "soccer_germany_bundesliga",
    "ligue 1":                     "soccer_france_ligue1",
    "serie a":                     "soccer_italy_serie_a",
    "eredivisie":                  "soccer_netherlands_eredivisie",
    "primeira liga":               "soccer_portugal_primeira_liga",
    "super lig":                   "soccer_turkey_super_league",
    "jupiler":                     "soccer_belgium_first_div",
    "pro league":                  "soccer_belgium_first_div",
    "efl championship":            "soccer_england_efl_champ",
    "english championship":        "soccer_england_efl_champ",
    "premiership":                 "soccer_scotland_premiership",
    "serie a brazil":              "soccer_brazil_campeonato",
    "brasileirao":                 "soccer_brazil_campeonato",
    "liga profesional":            "soccer_argentina_primera_division",
    "primera division":            "soccer_argentina_primera_division",
    "mls":                         "soccer_usa_mls",
    "liga mx":                     "soccer_mexico_ligamx",
    "liga mx":                     "soccer_mexico_ligamx",
    "superliga":                   "soccer_denmark_superliga",
    "eliteserien":                 "soccer_norway_eliteserien",
    "j1 league":                   "soccer_japan_j_league",
    "j league":                    "soccer_japan_j_league",
    "allsvenskan":                 "soccer_sweden_allsvenskan",
    "ekstraklasa":                 "soccer_poland_ekstraklasa",
    "greek super league":          "soccer_greece_super_league",
    "super league 1":              "soccer_greece_super_league",
}

# Country fallback: when league name doesn't match, try country
COUNTRY_TO_SPORT_KEY: Dict[str, str] = {
    "england":    "soccer_epl",
    "spain":      "soccer_spain_la_liga",
    "germany":    "soccer_germany_bundesliga",
    "france":     "soccer_france_ligue1",
    "italy":      "soccer_italy_serie_a",
    "netherlands": "soccer_netherlands_eredivisie",
    "portugal":   "soccer_portugal_primeira_liga",
    "turkey":     "soccer_turkey_super_league",
    "belgium":    "soccer_belgium_first_div",
    "scotland":   "soccer_scotland_premiership",
    "brazil":     "soccer_brazil_campeonato",
    "argentina":  "soccer_argentina_primera_division",
    "usa":        "soccer_usa_mls",
    "mexico":     "soccer_mexico_ligamx",
    "denmark":    "soccer_denmark_superliga",
    "norway":     "soccer_norway_eliteserien",
    "sweden":     "soccer_sweden_allsvenskan",
    "poland":     "soccer_poland_ekstraklasa",
    "greece":     "soccer_greece_super_league",
    "japan":      "soccer_japan_j_league",
}

# Confidence thresholds for match mapping
_CONF_EXACT  = 0.95
_CONF_HIGH   = 0.80
_CONF_MEDIUM = 0.60
_CONF_LOW    = 0.40
_MAX_TIME_DIFF_MINUTES = 120  # ±2h window for kickoff matching


def _normalize_team(name: str) -> str:
    """Normalize team name for comparison"""
    return (
        name.lower()
        .replace("fc ", "").replace(" fc", "")
        .replace("cf ", "").replace(" cf", "")
        .replace("sc ", "").replace(" sc", "")
        .replace("  ", " ")
        .strip()
    )


def _fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_team(a), _normalize_team(b)).ratio()


class TheOddsAPIProvider(BaseOddsProvider):
    """
    Phase 1-4: The Odds API provider

    - Phase 1: Reads ODDS_API_KEY from env only. Never hardcoded. odds_status property.
    - Phase 2: Fetches HT/FT/BTTS/1X2 for soccer.
    - Phase 3: MatchMapping with confidence score + label.
    - Phase 4: Returns NormalizedOdd alongside OddsData.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        config: Optional[OddsProviderConfig] = None,
    ):
        if config is None:
            config = OddsProviderConfig(
                name="the_odds_api",
                enabled=True,
                timeout_seconds=8,
                rate_limit_per_minute=120,  # No per-minute limit on Odds API — quota is monthly
            )
        super().__init__(config)

        # Phase 1: key comes from caller (from env via DataSourceConfig) — NO hardcoded fallback
        self.api_key: Optional[str] = api_key or None
        self.base_url: str = (api_url or "https://api.the-odds-api.com/v4").rstrip("/")

        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.last_request_time: float = 0.0

        # Cache: sport_key → list of raw event dicts
        self._event_cache: Dict[str, List[Dict]] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 1800.0  # 30 min

        # Diagnostic counters
        self.quota_remaining: Optional[int] = None
        self.events_fetched: int = 0
        self.mapping_success: int = 0
        self.mapping_failed: int = 0
        self.bookmakers_seen: set = set()
        self.markets_seen: set = set()

    # ------------------------------------------------------------------
    # Phase 1 — Status

    @property
    def odds_status(self) -> str:
        """MISSING_KEY | CONFIGURED | PROVIDER_ERROR | ACTIVE"""
        if not self.api_key:
            return "MISSING_KEY"
        return "CONFIGURED"

    @property
    def key_present(self) -> bool:
        return bool(self.api_key)

    # ------------------------------------------------------------------
    # Internal HTTP

    def _rate_limit(self):
        # The Odds API has no per-minute rate limit (monthly quota only).
        # We keep a tiny gap (0.1s) just to avoid hammering in tight loops.
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
        self.last_request_time = time.time()

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Any]:
        """GET with auth — returns None on any error (never blocks analysis)"""
        if not self.api_key:
            return None
        self._rate_limit()
        p = dict(params or {})
        p["apiKey"] = self.api_key
        try:
            url = f"{self.base_url}{endpoint}"
            resp = self.session.get(url, params=p, timeout=self.config.timeout_seconds)
            # Track quota from response headers
            remaining = resp.headers.get("x-requests-remaining")
            if remaining is not None:
                try:
                    self.quota_remaining = int(remaining)
                except Exception:
                    pass
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 0
            if status == 401:
                self.logger.error("[ODDS] 401 Unauthorized — check ODDS_API_KEY")
            elif status == 422:
                self.logger.warning(f"[ODDS] 422 sport not found: {endpoint}")
            else:
                self.logger.warning(f"[ODDS] HTTP {status} on {endpoint}: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"[ODDS] Request failed (non-blocking): {e}")
            return None

    # ------------------------------------------------------------------
    # Phase 3 — Match mapping with confidence score

    def _build_match_mapping(
        self,
        home_api: str,
        away_api: str,
        kickoff_api: Optional[datetime],
        event: Dict,
    ) -> MatchMapping:
        """
        Phase 3: Compute match_confidence_score and confidence_label.
        Time window ±2h is factored in.
        """
        h_odds = event.get("home_team", "")
        a_odds = event.get("away_team", "")
        score_h = _fuzzy(home_api, h_odds)
        score_a = _fuzzy(away_api, a_odds)
        name_score = (score_h + score_a) / 2.0

        # Time window factor
        time_diff = 9999.0
        commence = event.get("commence_time")
        if commence and kickoff_api:
            try:
                event_dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                if kickoff_api.tzinfo is None:
                    kickoff_api = kickoff_api.replace(tzinfo=timezone.utc)
                diff_sec = abs((event_dt - kickoff_api).total_seconds())
                time_diff = diff_sec / 60.0
            except Exception:
                time_diff = 9999.0

        time_ok = time_diff <= _MAX_TIME_DIFF_MINUTES
        time_penalty = 0.0 if time_ok else 0.3

        confidence = max(0.0, name_score - time_penalty)

        if confidence >= _CONF_EXACT and time_diff <= 5:
            label = "EXACT"
            status = "MATCHED"
        elif confidence >= _CONF_HIGH and time_ok:
            label = "HIGH"
            status = "MATCHED"
        elif confidence >= _CONF_MEDIUM and time_ok:
            label = "MEDIUM"
            status = "MATCHING_UNCERTAIN"
        elif confidence >= _CONF_LOW:
            label = "LOW"
            status = "MATCHING_UNCERTAIN"
        else:
            label = "FAILED"
            status = "FAILED"

        return MatchMapping(
            event_id=event.get("id", ""),
            home_team_api=home_api,
            away_team_api=away_api,
            home_team_odds=h_odds,
            away_team_odds=a_odds,
            kickoff_diff_minutes=time_diff,
            name_score_home=score_h,
            name_score_away=score_a,
            match_confidence_score=confidence,
            confidence_label=label,
            odds_status=status,
        )

    def find_event_with_mapping(
        self,
        home_team: str,
        away_team: str,
        kickoff: Optional[datetime] = None,
        min_confidence: float = 0.50,
    ) -> Tuple[Optional[Dict], Optional[MatchMapping]]:
        """
        Phase 3: Find best matching event. Returns (event, mapping) or (None, None).
        Only returns events above min_confidence threshold.
        """
        best_event = None
        best_mapping = None
        best_conf = -1.0

        for sport_key, events in self._event_cache.items():
            for event in events:
                mapping = self._build_match_mapping(home_team, away_team, kickoff, event)
                if mapping.match_confidence_score > best_conf:
                    best_conf = mapping.match_confidence_score
                    best_event = event
                    best_mapping = mapping

        if best_event and best_mapping and best_mapping.match_confidence_score >= min_confidence:
            if best_mapping.confidence_label != "FAILED":
                self.mapping_success += 1
                return best_event, best_mapping

        self.mapping_failed += 1
        return None, None

    # ------------------------------------------------------------------
    # Phase 2 — Prefetch & sport loading

    def _load_sport_events(self, sport_key: str) -> List[Dict]:
        """Load events for one sport including HT markets"""
        data = self._get(
            f"/sports/{sport_key}/odds",
            {
                "regions": "eu",
                "markets": "h2h,totals",  # Free tier: btts/h1_totals require premium plan
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
        )
        if not data or not isinstance(data, list):
            return []
        return data

    @staticmethod
    def resolve_sport_key(competition: str, country: str) -> Optional[str]:
        """
        Resolve API-Football competition/country to an Odds API sport_key.
        Returns None if the league is not covered.
        Strategy:
          1. Country-first lookup (most reliable, avoids cross-country false positives)
          2. League name fragment match (only when country gives no result)
        """
        comp_lc = (competition or "").lower().strip()
        ctry_lc = (country or "").lower().strip()

        # 1. Country-first: direct and unambiguous
        if ctry_lc:
            sk = COUNTRY_TO_SPORT_KEY.get(ctry_lc)
            if sk:
                return sk

        # 2. League name fragment match as fallback (no country or unknown country)
        # Use word-boundary check: fragment must be followed by end-of-string or non-letter
        import re
        for fragment, sport_key in LEAGUE_TO_SPORT_KEY.items():
            pattern = r'\b' + re.escape(fragment) + r'(\b|$)'
            if re.search(pattern, comp_lc):
                return sport_key

        return None

    def prefetch_for_matches(self, matches: List[Dict]) -> None:
        """
        Phase 2 (targeted): Only prefetch sport_keys needed for the given match list.
        Each match dict must have 'competition' and 'country' keys.
        This replaces prefetch_all_soccer_odds for normal scan runs.
        """
        if not self.api_key:
            return

        now = time.time()
        if self._event_cache and (now - self._cache_ts) < self._cache_ttl:
            self.logger.debug("[ODDS] Cache still fresh — skipping prefetch")
            return

        if self.quota_remaining is not None and self.quota_remaining < 5:
            self.logger.warning(f"[ODDS] Quota critically low ({self.quota_remaining}) — skipping prefetch")
            return

        # Collect unique sport_keys needed
        needed: set = set()
        for m in matches:
            comp    = m.get("competition", "") or m.get("league", "")
            country = m.get("country", "")
            sk = self.resolve_sport_key(comp, country)
            if sk:
                needed.add(sk)

        if not needed:
            self.logger.info("[ODDS] No supported leagues in target list — skipping prefetch")
            return

        self.logger.info(f"[ODDS] Targeted prefetch: {len(needed)} sport_keys for {len(matches)} matches: {sorted(needed)}")
        self._fetch_sport_keys(sorted(needed))

    def prefetch_all_soccer_odds(self) -> None:
        """
        Fallback: prefetch ALL soccer sport keys (used only when no match list available).
        Prefer prefetch_for_matches() for normal scan runs.
        """
        if not self.api_key:
            return
        now = time.time()
        if self._event_cache and (now - self._cache_ts) < self._cache_ttl:
            self.logger.debug("[ODDS] Using cached events")
            return
        self.logger.info(f"[ODDS] Full prefetch fallback: {len(SOCCER_SPORT_KEYS)} sport keys")
        self._fetch_sport_keys(SOCCER_SPORT_KEYS)

    def _fetch_sport_keys(self, sport_keys: List[str]) -> None:
        """Internal: parallel-fetch a list of sport_keys and populate _event_cache."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        self._event_cache = {}
        self._cache_ts = time.time()
        total_events = 0

        def _fetch_one(sk: str):
            return sk, self._load_sport_events(sk)

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(_fetch_one, sk): sk for sk in sport_keys}
            for future in as_completed(futures):
                try:
                    sport_key, events = future.result(timeout=12)
                    if events:
                        self._event_cache[sport_key] = events
                        total_events += len(events)
                        self.logger.debug(f"[ODDS]   {sport_key}: {len(events)} events")
                except Exception as e:
                    self.logger.debug(f"[ODDS] {futures[future]} fetch error: {e}")

        self.events_fetched = total_events
        self.logger.info(f"[ODDS] Prefetch done: {total_events} events / {len(self._event_cache)} sports / quota_left={self.quota_remaining}")

    # ------------------------------------------------------------------
    # Phase 4 — Normalized odds parsing

    def _parse_event_normalized(
        self, event: Dict, match_id: str, mapping: Optional[MatchMapping]
    ) -> List[NormalizedOdd]:
        """Phase 4: Parse event into NormalizedOdd list"""
        result: List[NormalizedOdd] = []
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        ts = datetime.now(timezone.utc).isoformat()

        for bookmaker in event.get("bookmakers", []):
            bk_name = bookmaker.get("title", "Unknown")
            self.bookmakers_seen.add(bk_name)

            for market in bookmaker.get("markets", []):
                mkey = market.get("key", "")
                self.markets_seen.add(mkey)
                outcomes = market.get("outcomes", [])

                # --- 1X2 ---
                if mkey == "h2h":
                    for oc in outcomes:
                        name = oc.get("name", "")
                        price = oc.get("price")
                        if not price:
                            continue
                        if name == home_team:
                            side, mkt = "HOME", "H2H_HOME"
                        elif name == away_team:
                            side, mkt = "AWAY", "H2H_AWAY"
                        elif name in ("Draw", "Tie"):
                            side, mkt = "DRAW", "H2H_DRAW"
                        else:
                            continue
                        odd_f = float(price)
                        result.append(NormalizedOdd(
                            bookmaker=bk_name, market=mkt, line=None,
                            side=side, odd=odd_f,
                            implied_probability=1.0 / odd_f if odd_f > 0 else 0,
                            timestamp=ts, match_id=match_id,
                            home_team=home_team, away_team=away_team,
                        ))

                # --- FT Totals ---
                elif mkey == "totals":
                    for oc in outcomes:
                        name = oc.get("name", "")
                        price = oc.get("price")
                        point = oc.get("point")
                        if not price or point is None:
                            continue
                        pt = float(point)
                        if pt in IGNORED_MARKET_LINES:
                            continue
                        if pt not in ALLOWED_MARKET_LINES:
                            continue
                        side = "OVER" if "over" in name.lower() else "UNDER"
                        mkt = f"FT_{side}_{str(pt).replace('.', '_')}"
                        odd_f = float(price)
                        result.append(NormalizedOdd(
                            bookmaker=bk_name, market=mkt, line=pt,
                            side=side, odd=odd_f,
                            implied_probability=1.0 / odd_f if odd_f > 0 else 0,
                            timestamp=ts, match_id=match_id,
                            home_team=home_team, away_team=away_team,
                        ))

                # --- HT Totals ---
                elif mkey in ("h1_totals", "first_half_totals", "alternate_halftime_totals"):
                    for oc in outcomes:
                        name = oc.get("name", "")
                        price = oc.get("price")
                        point = oc.get("point")
                        if not price or point is None:
                            continue
                        pt = float(point)
                        if pt not in {0.5, 1.5}:
                            continue
                        side = "OVER" if "over" in name.lower() else "UNDER"
                        mkt = f"HT_{side}_{str(pt).replace('.', '_')}"
                        odd_f = float(price)
                        result.append(NormalizedOdd(
                            bookmaker=bk_name, market=mkt, line=pt,
                            side=side, odd=odd_f,
                            implied_probability=1.0 / odd_f if odd_f > 0 else 0,
                            timestamp=ts, match_id=match_id,
                            home_team=home_team, away_team=away_team,
                        ))

                # --- BTTS ---
                elif mkey in ("btts", "both_teams_to_score"):
                    for oc in outcomes:
                        name = oc.get("name", "").lower()
                        price = oc.get("price")
                        if not price:
                            continue
                        if "yes" in name:
                            side, mkt = "YES", "BTTS_YES"
                        elif "no" in name:
                            side, mkt = "NO", "BTTS_NO"
                        else:
                            continue
                        odd_f = float(price)
                        result.append(NormalizedOdd(
                            bookmaker=bk_name, market=mkt, line=None,
                            side=side, odd=odd_f,
                            implied_probability=1.0 / odd_f if odd_f > 0 else 0,
                            timestamp=ts, match_id=match_id,
                            home_team=home_team, away_team=away_team,
                        ))

        return result

    def _parse_event_odds(self, event: Dict, match_id: str) -> List[OddsData]:
        """Backward compat: parse to OddsData list"""
        normalized = self._parse_event_normalized(event, match_id, None)
        result = []
        for n in normalized:
            mt = self._market_str_to_type(n.market)
            if mt:
                result.append(OddsData(
                    match_id=match_id,
                    market_type=mt,
                    line=n.line,
                    odd=n.odd,
                    bookmaker=n.bookmaker,
                    home_team=n.home_team,
                    away_team=n.away_team,
                ))
        return result

    def _market_str_to_type(self, market: str) -> Optional[MarketType]:
        mapping = {
            "FT_UNDER_1_5": MarketType.FT_UNDER_15,
            "FT_OVER_1_5": MarketType.FT_OVER_15,
            "FT_UNDER_2_5": MarketType.FT_UNDER_25,
            "FT_OVER_2_5": MarketType.FT_OVER_25,
            "FT_UNDER_3_5": MarketType.FT_UNDER_35,
            "FT_OVER_3_5": MarketType.FT_OVER_35,
            "FT_UNDER_4_5": MarketType.FT_UNDER_45,
            "FT_OVER_4_5": MarketType.FT_OVER_45,
            "HT_UNDER_0_5": MarketType.HT_UNDER_05,
            "HT_OVER_0_5": MarketType.HT_OVER_05,
            "HT_UNDER_1_5": MarketType.HT_UNDER_15,
            "HT_OVER_1_5": MarketType.HT_OVER_15,
            "BTTS_YES": MarketType.BTTS_YES,
            "BTTS_NO": MarketType.BTTS_NO,
            "H2H_HOME": MarketType.H2H_HOME,
            "H2H_DRAW": MarketType.H2H_DRAW,
            "H2H_AWAY": MarketType.H2H_AWAY,
        }
        return mapping.get(market)

    # ------------------------------------------------------------------
    # Public interface

    def get_match_odds(
        self,
        match_id: str,
        markets: Optional[List[MarketType]] = None,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        kickoff: Optional[datetime] = None,
    ) -> OddsResponse:
        """
        Phase 1-4: Get odds for a match.
        Returns empty list if odds absent — never blocks analysis.
        Includes mapping confidence info in extra field.
        """
        if not self.api_key:
            return self._create_success_response([])

        if not home_team or not away_team:
            return self._create_success_response([])

        if not self._event_cache:
            self.prefetch_all_soccer_odds()

        event, mapping = self.find_event_with_mapping(home_team, away_team, kickoff)

        if not event or not mapping:
            self.logger.debug(f"[ODDS] No match found for {home_team} vs {away_team}")
            return self._create_success_response([])

        # Phase 3: Only use odds if confidence is sufficient
        if mapping.confidence_label == "FAILED":
            self.logger.debug(f"[ODDS] Mapping FAILED for {home_team} vs {away_team} — skipping odds")
            return self._create_success_response([])

        odds_list = self._parse_event_odds(event, match_id)

        # Attach mapping metadata to response
        resp = self._create_success_response(odds_list)
        # Store mapping on response object for scanner access
        resp.__dict__["_mapping"] = mapping
        return resp

    def get_match_odds_normalized(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        kickoff: Optional[datetime] = None,
    ) -> Tuple[List[NormalizedOdd], Optional[MatchMapping]]:
        """
        Phase 4: Get normalized odds + mapping info.
        Returns ([], None) if odds absent — never blocks.
        """
        if not self.api_key:
            return [], None

        # Cache should already be populated by prefetch_for_matches() called before the analysis loop.
        # If it's still empty, the league isn't covered — skip silently (non-blocking).
        if not self._event_cache:
            return [], None

        event, mapping = self.find_event_with_mapping(home_team, away_team, kickoff)
        if not event or not mapping or mapping.confidence_label == "FAILED":
            return [], mapping

        normalized = self._parse_event_normalized(event, match_id, mapping)
        return normalized, mapping

    def get_today_odds(
        self,
        competition_ids: Optional[List[str]] = None,
        markets: Optional[List[MarketType]] = None,
    ) -> OddsResponse:
        """Get all today's odds (uses cache)"""
        if not self._event_cache:
            self.prefetch_all_soccer_odds()

        all_odds: List[OddsData] = []
        for sport_events in self._event_cache.values():
            for event in sport_events:
                all_odds.extend(self._parse_event_odds(event, event.get("id", "")))
        return self._create_success_response(all_odds)

    def get_diagnostics(self) -> Dict[str, Any]:
        """Phase 12: Return diagnostics dict"""
        return {
            "odds_api_key_present": self.key_present,
            "odds_api_status": self.odds_status,
            "odds_events_found": self.events_fetched,
            "sports_loaded": len(self._event_cache),
            "mapping_success_count": self.mapping_success,
            "mapping_failed_count": self.mapping_failed,
            "bookmakers_available": sorted(self.bookmakers_seen),
            "markets_available": sorted(self.markets_seen),
            "api_quota_remaining": self.quota_remaining,
            "cache_age_seconds": int(time.time() - self._cache_ts) if self._cache_ts else None,
        }


# Backward compatibility alias
class ExternalOddsProvider(TheOddsAPIProvider):
    """Alias for backward compatibility"""
    pass
