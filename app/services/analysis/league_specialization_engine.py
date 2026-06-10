"""
League Specialization Engine
============================
Phase 1: League Profitability Matrix  (league × market × tier stats)
Phase 2: League Market Ranking        (best/worst markets per league)
Phase 3: Edge Discovery               (edge_score, profitable/dangerous)
Phase 4: Dynamic Confidence Adjustment (historical performance multiplier)
Phase 5: Dangerous League Detection   (blacklist, false_signal, unstable)
Phase 6: Smart Recommendations        (per-match edge rating + warnings)

Data:   live_test_session_*.csv  (predictions + results)
Rules:  No ML · No auto-recalibration · Read-only historical analysis
"""

import csv
import glob
import logging
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
MIN_SAMPLE          = 5      # minimum evaluated predictions for meaningful stats
HIGH_CONF_THRESH    = 65.0   # confidence % above which a loss counts as false positive
ROI_STRONG_EDGE     = 12.0   # ROI % threshold for strong edge
ROI_BLACKLIST       = -12.0  # ROI % threshold for blacklist
FPR_DANGER          = 0.40   # false positive rate → dangerous
DRAWDOWN_UNSTABLE   = 5      # unit drawdown → unstable market
STREAK_UNSTABLE     = 4      # consecutive losses → unstable

# Edge score thresholds
EDGE_STRONG   = 0.55
EDGE_MODERATE = 0.30
EDGE_NEUTRAL  = 0.10
EDGE_WEAK     = -0.10

# Phase 4: confidence multipliers by edge label
CONF_MULTIPLIERS: Dict[str, float] = {
    "STRONG_EDGE": 1.15,
    "EDGE":        1.07,
    "NEUTRAL":     1.00,
    "WEAK":        0.90,
    "NO_EDGE":     0.80,
}
CONF_BLACKLIST_MULT = 0.65


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _compute_drawdown_streak(sequence: List[str]) -> Tuple[int, int]:
    """Returns (max_units_drawdown, longest_losing_streak) from WIN/LOSS sequence."""
    max_dd = 0
    current_dd = 0
    max_streak = 0
    current_streak = 0
    for r in sequence:
        if r == "LOSS":
            current_dd += 1
            current_streak += 1
            max_dd = max(max_dd, current_dd)
            max_streak = max(max_streak, current_streak)
        else:
            current_dd = max(0, current_dd - 1)
            current_streak = 0
    return max_dd, max_streak


# ─── Phase 1 — Data Model ─────────────────────────────────────────────────────
@dataclass
class LeagueMarketStats:
    """Profitability stats for one (league, country, market) combination."""
    league: str
    country: str
    market: str

    # Counters
    total_predictions: int = 0
    wins: int = 0
    losses: int = 0

    # Derived — computed in finalize()
    hit_rate: float = 0.0
    roi: float = 0.0
    average_ev: float = 0.0
    average_confidence: float = 0.0
    average_volatility: float = 0.0
    false_positive_rate: float = 0.0
    max_drawdown: int = 0
    longest_losing_streak: int = 0
    edge_score: float = 0.0
    edge_label: str = "UNKNOWN"

    # Internal accumulators (not exported)
    _ev_sum: float = field(default=0.0, repr=False)
    _conf_sum: float = field(default=0.0, repr=False)
    _vol_sum: float = field(default=0.0, repr=False)
    _net_return: float = field(default=0.0, repr=False)
    _high_conf_losses: int = field(default=0, repr=False)
    _sequence: List[str] = field(default_factory=list, repr=False)
    tier_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def add_prediction(
        self, result: str, ev_pct: float, confidence: float,
        volatility: float, bookmaker_odd: Optional[float], tier: str,
    ):
        if result not in ("WIN", "LOSS"):
            return
        self.total_predictions += 1
        self._ev_sum += ev_pct
        self._conf_sum += confidence
        self._vol_sum += volatility
        self._sequence.append(result)

        bk = bookmaker_odd if (bookmaker_odd and bookmaker_odd > 1.0) else None
        if result == "WIN":
            self.wins += 1
            self._net_return += (bk - 1.0) if bk else 0.9
        else:
            self.losses += 1
            self._net_return -= 1.0
            if confidence >= HIGH_CONF_THRESH:
                self._high_conf_losses += 1

        t = tier or "UNKNOWN"
        self.tier_breakdown.setdefault(t, {"wins": 0, "losses": 0})
        self.tier_breakdown[t]["wins" if result == "WIN" else "losses"] += 1

    def finalize(self):
        """Compute all derived stats — call once after all add_prediction()."""
        n = self.total_predictions
        if n == 0:
            return
        self.hit_rate = round(self.wins / n, 4)
        self.roi = round((self._net_return / n) * 100, 2)
        self.average_ev = round(self._ev_sum / n, 2)
        self.average_confidence = round(self._conf_sum / n, 2)
        self.average_volatility = round(self._vol_sum / n, 2)
        self.false_positive_rate = round(self._high_conf_losses / max(1, n), 4)
        self.max_drawdown, self.longest_losing_streak = _compute_drawdown_streak(self._sequence)
        self.edge_score = _compute_edge_score(self)
        self.edge_label = _edge_label(self.edge_score)

    def to_dict(self) -> dict:
        return {
            "league":                   self.league,
            "country":                  self.country,
            "market":                   self.market,
            "total_predictions":        self.total_predictions,
            "wins":                     self.wins,
            "losses":                   self.losses,
            "hit_rate":                 self.hit_rate,
            "roi":                      self.roi,
            "average_ev":               self.average_ev,
            "average_confidence":       self.average_confidence,
            "average_volatility":       self.average_volatility,
            "false_positive_rate":      self.false_positive_rate,
            "max_drawdown":             self.max_drawdown,
            "longest_losing_streak":    self.longest_losing_streak,
            "edge_score":               round(self.edge_score, 3),
            "edge_label":               self.edge_label,
            "sample_size":              self.total_predictions,
            "tier_breakdown":           self.tier_breakdown,
        }


# ─── Phase 2 — League Market Ranking ──────────────────────────────────────────
@dataclass
class LeagueMarketRanking:
    """Best/worst markets per league — Phase 2."""
    league: str
    country: str
    best_markets: List[str] = field(default_factory=list)
    worst_markets: List[str] = field(default_factory=list)
    overall_roi: float = 0.0
    overall_hit_rate: float = 0.0
    total_predictions: int = 0
    specialization_score: float = 0.0   # spread between best/worst edge

    def to_dict(self) -> dict:
        return {
            "league":                self.league,
            "country":               self.country,
            "best_markets":          self.best_markets,
            "worst_markets":         self.worst_markets,
            "overall_roi":           self.overall_roi,
            "overall_hit_rate":      self.overall_hit_rate,
            "total_predictions":     self.total_predictions,
            "specialization_score":  round(self.specialization_score, 3),
        }


# ─── Phase 6 — Smart Recommendation ──────────────────────────────────────────
@dataclass
class SmartRecommendation:
    """Per-match edge rating and warnings — Phase 6."""
    league_edge_rating: str = "UNKNOWN"            # STRONG_EDGE | EDGE | NEUTRAL | WEAK | AVOID | NO_DATA
    market_historical_profitability: str = "NO_DATA"
    recommended_market_priority: List[str] = field(default_factory=list)
    historical_model_performance: str = "NO_DATA"  # e.g. "72% hit-rate on 18 samples"
    market_warning: str = ""
    confidence_adjustment: float = 1.0             # multiplier (1.0 = no change)
    confidence_adjustment_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "league_edge_rating":              self.league_edge_rating,
            "market_historical_profitability": self.market_historical_profitability,
            "recommended_market_priority":     self.recommended_market_priority,
            "historical_model_performance":    self.historical_model_performance,
            "market_warning":                  self.market_warning,
            "confidence_adjustment":           round(self.confidence_adjustment, 3),
            "confidence_adjustment_reason":    self.confidence_adjustment_reason,
        }


# ─── Edge Scoring (Phase 3) ───────────────────────────────────────────────────
def _compute_edge_score(s: LeagueMarketStats) -> float:
    """
    edge_score ∈ [-1, 1] — weighted composite of all profitability signals.
    Weights: ROI 35% · hit_rate 25% · false_positive_rate 20%
             · stability 10% · sample_confidence 10%
    """
    n = s.total_predictions
    if n < MIN_SAMPLE:
        return 0.0

    roi_comp   = _clamp(s.roi / 30.0, -1.0, 1.0) * 0.35
    hr_comp    = ((s.hit_rate - 0.50) * 2.0) * 0.25
    fpr_comp   = (1.0 - _clamp(s.false_positive_rate * 4.0, 0.0, 1.0)) * 0.20
    stab_comp  = (1.0 - _clamp(s.max_drawdown / 6.0, 0.0, 1.0)) * 0.10
    samp_comp  = _clamp(math.log(max(n, 1)) / math.log(60), 0.0, 1.0) * 0.10

    return round(roi_comp + hr_comp + fpr_comp + stab_comp + samp_comp, 4)


def _edge_label(score: float) -> str:
    if score >= EDGE_STRONG:   return "STRONG_EDGE"
    if score >= EDGE_MODERATE: return "EDGE"
    if score >= EDGE_NEUTRAL:  return "NEUTRAL"
    if score >= EDGE_WEAK:     return "WEAK"
    return "NO_EDGE"


# ─── Main Engine ─────────────────────────────────────────────────────────────
class LeagueSpecializationEngine:
    """
    Phases 1-6: League Specialization Engine.
    Analyzes historical prediction data to find where the model has real edge.
    No ML · No auto-recalibration · Historical read-only.
    """

    def __init__(self):
        # Phase 1: matrix keyed by (league, country, market)
        self._matrix: Dict[Tuple[str, str, str], LeagueMarketStats] = {}
        # Phase 2: rankings keyed by (league, country)
        self._rankings: Dict[Tuple[str, str], LeagueMarketRanking] = {}
        # Phase 3: sorted discovery lists
        self._profitable_leagues: List[dict] = []
        self._unprofitable_leagues: List[dict] = []
        self._profitable_markets: List[dict] = []
        self._unprofitable_markets: List[dict] = []
        # Phase 5: danger sets
        self.blacklist_leagues: set = set()
        self.high_false_signal_leagues: set = set()
        self.unstable_markets: set = set()
        self.no_edge_detected: set = set()
        # State
        self.rows_loaded: int = 0
        self.is_ready: bool = False

    # ─── Loading ──────────────────────────────────────────────────────────────
    def load_from_csvs(self, search_dir: str = ".") -> int:
        """
        Scan for live_test_session_*.csv files and load all rows with results.
        Returns total rows loaded.
        """
        pattern = os.path.join(search_dir, "live_test_session_*.csv")
        files = sorted(glob.glob(pattern))
        total = 0
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        self._ingest_row(row)
                        total += 1
                logger.info(f"[LSE] Loaded {fpath}")
            except Exception as e:
                logger.warning(f"[LSE] Skipping {fpath}: {e}")
        self.rows_loaded += total
        if total > 0:
            self._finalize()
        logger.info(f"[LSE] {total} rows from {len(files)} CSV files — ready={self.is_ready}")
        return total

    def load_from_rows(self, rows: List[dict]) -> int:
        """Load from a list of dicts (same schema as CSV). Returns count."""
        added = 0
        for row in rows:
            if self._ingest_row(row):
                added += 1
        if added > 0:
            self._finalize()
        self.rows_loaded += added
        return added

    def _ingest_row(self, row: dict) -> bool:
        result = (row.get("result_correct") or "").strip().upper()
        if result not in ("WIN", "LOSS"):
            return False
        league  = (row.get("league") or "").strip()
        country = (row.get("country") or "").strip()
        market  = (row.get("market") or "").strip()
        tier    = (row.get("statistical_tier") or row.get("ev_tier") or "").strip()
        if not league or not market:
            return False

        def _f(k, d=0.0):
            try: return float(row.get(k) or d)
            except: return d

        key = (league, country, market)
        if key not in self._matrix:
            self._matrix[key] = LeagueMarketStats(league=league, country=country, market=market)

        bk_odd = _f("bookmaker_odd") or None
        if bk_odd and bk_odd <= 1.0:
            bk_odd = None

        self._matrix[key].add_prediction(
            result=result,
            ev_pct=_f("ev_percent"),
            confidence=_f("confidence_score", 50.0),
            volatility=_f("volatility_score", 50.0),
            bookmaker_odd=bk_odd,
            tier=tier,
        )
        return True

    # ─── Finalization pipeline ────────────────────────────────────────────────
    def _finalize(self):
        """Run all phases after data ingestion."""
        for s in self._matrix.values():
            s.finalize()
        self._compute_rankings()       # Phase 2
        self._discover_edges()         # Phase 3
        self._compute_danger_lists()   # Phase 5
        self.is_ready = True

    # ─── Phase 2 ──────────────────────────────────────────────────────────────
    def _compute_rankings(self):
        """Build LeagueMarketRanking for each (league, country)."""
        league_markets: Dict[Tuple[str, str], List[LeagueMarketStats]] = {}
        for (lg, ct, mk), s in self._matrix.items():
            if s.total_predictions < MIN_SAMPLE:
                continue
            k = (lg, ct)
            league_markets.setdefault(k, []).append(s)

        for (lg, ct), stats_list in league_markets.items():
            sorted_by_edge = sorted(stats_list, key=lambda s: s.edge_score, reverse=True)
            best  = [s.market for s in sorted_by_edge if s.edge_score >= EDGE_NEUTRAL][:3]
            worst = [s.market for s in reversed(sorted_by_edge) if s.edge_score < EDGE_NEUTRAL][:3]

            total_n = sum(s.total_predictions for s in stats_list)
            total_wins = sum(s.wins for s in stats_list)
            agg_roi = (sum(s.roi * s.total_predictions for s in stats_list)
                       / max(total_n, 1))
            agg_hr  = round(total_wins / max(total_n, 1), 4)

            spec_score = 0.0
            if sorted_by_edge:
                best_score  = sorted_by_edge[0].edge_score
                worst_score = sorted_by_edge[-1].edge_score
                spec_score  = round(best_score - worst_score, 3)

            self._rankings[(lg, ct)] = LeagueMarketRanking(
                league=lg,
                country=ct,
                best_markets=best,
                worst_markets=worst,
                overall_roi=round(agg_roi, 2),
                overall_hit_rate=agg_hr,
                total_predictions=total_n,
                specialization_score=spec_score,
            )

    # ─── Phase 3 ──────────────────────────────────────────────────────────────
    def _discover_edges(self):
        """Sort leagues and markets by edge_score into discovery lists."""
        # Per-league aggregate
        league_agg: Dict[Tuple[str, str], dict] = {}
        for (lg, ct, _mk), s in self._matrix.items():
            if s.total_predictions < MIN_SAMPLE:
                continue
            k = (lg, ct)
            if k not in league_agg:
                league_agg[k] = {"league": lg, "country": ct,
                                  "roi": 0.0, "n": 0, "edge_sum": 0.0, "count": 0}
            a = league_agg[k]
            a["roi"] = (a["roi"] * a["n"] + s.roi * s.total_predictions) / (a["n"] + s.total_predictions)
            a["n"] += s.total_predictions
            a["edge_sum"] += s.edge_score
            a["count"] += 1

        for a in league_agg.values():
            a["avg_edge"] = round(a["edge_sum"] / max(a["count"], 1), 3)
            a["roi"] = round(a["roi"], 2)

        by_edge = sorted(league_agg.values(), key=lambda x: x["avg_edge"], reverse=True)
        self._profitable_leagues   = [a for a in by_edge if a["avg_edge"] >= EDGE_NEUTRAL]
        self._unprofitable_leagues = [a for a in reversed(by_edge) if a["avg_edge"] < EDGE_NEUTRAL]

        # Per-market aggregate
        market_agg: Dict[str, dict] = {}
        for (_, _, mk), s in self._matrix.items():
            if s.total_predictions < MIN_SAMPLE:
                continue
            if mk not in market_agg:
                market_agg[mk] = {"market": mk, "roi": 0.0, "n": 0, "edge_sum": 0.0, "count": 0}
            a = market_agg[mk]
            a["roi"] = (a["roi"] * a["n"] + s.roi * s.total_predictions) / (a["n"] + s.total_predictions)
            a["n"] += s.total_predictions
            a["edge_sum"] += s.edge_score
            a["count"] += 1

        for a in market_agg.values():
            a["avg_edge"] = round(a["edge_sum"] / max(a["count"], 1), 3)
            a["roi"] = round(a["roi"], 2)

        by_mkt = sorted(market_agg.values(), key=lambda x: x["avg_edge"], reverse=True)
        self._profitable_markets   = [m for m in by_mkt if m["avg_edge"] >= EDGE_NEUTRAL]
        self._unprofitable_markets = [m for m in reversed(by_mkt) if m["avg_edge"] < EDGE_NEUTRAL]

    # ─── Phase 5 ──────────────────────────────────────────────────────────────
    def _compute_danger_lists(self):
        """Identify dangerous leagues and markets."""
        self.blacklist_leagues.clear()
        self.high_false_signal_leagues.clear()
        self.unstable_markets.clear()
        self.no_edge_detected.clear()

        league_roi: Dict[str, List[float]] = {}
        league_fpr: Dict[str, List[float]] = {}

        for (lg, ct, mk), s in self._matrix.items():
            if s.total_predictions < MIN_SAMPLE:
                continue
            key = f"{lg}|{ct}"
            league_roi.setdefault(key, []).append(s.roi)
            league_fpr.setdefault(key, []).append(s.false_positive_rate)

            # UNSTABLE_MARKET
            if s.max_drawdown >= DRAWDOWN_UNSTABLE or s.longest_losing_streak >= STREAK_UNSTABLE:
                self.unstable_markets.add(f"{lg}|{mk}")

            # NO_EDGE_DETECTED (large sample, still no edge)
            if s.total_predictions >= 15 and s.edge_score < EDGE_NEUTRAL:
                self.no_edge_detected.add(f"{lg}|{mk}")

        for key, rois in league_roi.items():
            avg_roi = sum(rois) / len(rois)
            avg_fpr = sum(league_fpr.get(key, [0.0])) / max(len(league_fpr.get(key, [1])), 1)
            if avg_roi <= ROI_BLACKLIST:
                self.blacklist_leagues.add(key)
            if avg_fpr >= FPR_DANGER:
                self.high_false_signal_leagues.add(key)

    # ─── Phase 4 — Dynamic Confidence Adjustment ─────────────────────────────
    def adjust_confidence(
        self,
        confidence: float,
        league: str,
        country: str,
        market: str,
    ) -> Tuple[float, str]:
        """
        Returns (multiplier, reason).
        multiplier = 1.0 → no change; < 1.0 → reduce; > 1.0 → boost.
        Bounded to [0.65, 1.15].
        """
        if not self.is_ready:
            return 1.0, ""

        league_key = f"{league}|{country}"

        # Phase 5: hard signals first
        if league_key in self.blacklist_leagues:
            return CONF_BLACKLIST_MULT, f"BLACKLISTED: historical ROI ≤ {ROI_BLACKLIST}% in {league}"
        if league_key in self.high_false_signal_leagues:
            return 0.75, f"HIGH_FALSE_SIGNAL: FPR ≥ {FPR_DANGER:.0%} in {league}"

        # Phase 4: market-level edge
        key = (league, country, market)
        stats = self._matrix.get(key)
        if stats and stats.total_predictions >= MIN_SAMPLE:
            mult = CONF_MULTIPLIERS.get(stats.edge_label, 1.0)
            reason = (f"LSE {stats.edge_label}: ROI={stats.roi:+.1f}% "
                      f"hit={stats.hit_rate:.0%} n={stats.total_predictions}")
            return _clamp(mult, 0.65, 1.15), reason

        # Phase 4: league-level fallback (any market)
        ranking = self._rankings.get((league, country))
        if ranking and ranking.total_predictions >= MIN_SAMPLE:
            if ranking.overall_roi >= ROI_STRONG_EDGE:
                return 1.08, f"LSE league boost: overall ROI={ranking.overall_roi:+.1f}% in {league}"
            if ranking.overall_roi <= ROI_BLACKLIST:
                return 0.82, f"LSE league penalty: overall ROI={ranking.overall_roi:+.1f}% in {league}"

        return 1.0, ""

    # ─── Phase 6 — Smart Recommendations ─────────────────────────────────────
    def get_smart_recommendations(
        self, league: str, country: str, market: str,
    ) -> SmartRecommendation:
        """Build a SmartRecommendation for a specific match."""
        rec = SmartRecommendation()
        if not self.is_ready:
            return rec

        league_key = f"{league}|{country}"
        ranking = self._rankings.get((league, country))

        # League edge rating
        if league_key in self.blacklist_leagues:
            rec.league_edge_rating = "AVOID"
            rec.market_warning = f"BLACKLIST_LEAGUE: modèle historiquement perdant dans {league}"
        elif league_key in self.high_false_signal_leagues:
            rec.league_edge_rating = "AVOID"
            rec.market_warning = f"HIGH_FALSE_SIGNAL_LEAGUE: taux de faux positifs élevé dans {league}"
        elif ranking:
            if ranking.overall_roi >= ROI_STRONG_EDGE:
                rec.league_edge_rating = "STRONG_EDGE"
            elif ranking.overall_roi >= 0:
                rec.league_edge_rating = "EDGE"
            elif ranking.overall_roi >= ROI_BLACKLIST:
                rec.league_edge_rating = "WEAK"
            else:
                rec.league_edge_rating = "AVOID"
            rec.recommended_market_priority = ranking.best_markets[:3]
        else:
            rec.league_edge_rating = "NO_DATA"

        # Market-level profitability
        key = (league, country, market)
        stats = self._matrix.get(key)
        if stats and stats.total_predictions >= MIN_SAMPLE:
            rec.market_historical_profitability = stats.edge_label
            rec.historical_model_performance = (
                f"{stats.hit_rate:.0%} hit-rate · ROI={stats.roi:+.1f}% "
                f"on {stats.total_predictions} samples"
            )
            if f"{league}|{market}" in self.unstable_markets:
                rec.market_warning = (
                    f"UNSTABLE_MARKET: drawdown={stats.max_drawdown} "
                    f"streak={stats.longest_losing_streak} in {market}"
                )
            if f"{league}|{market}" in self.no_edge_detected:
                if not rec.market_warning:
                    rec.market_warning = f"NO_EDGE_DETECTED: large sample, still no edge for {market} in {league}"
        else:
            rec.market_historical_profitability = "NO_DATA"
            rec.historical_model_performance = "NO_DATA (insufficient history)"

        # Confidence adjustment
        mult, reason = self.adjust_confidence(confidence=0.0, league=league, country=country, market=market)
        rec.confidence_adjustment = mult
        rec.confidence_adjustment_reason = reason

        return rec

    # ─── Public Query API ─────────────────────────────────────────────────────
    def get_profitability_matrix(self, min_sample: int = MIN_SAMPLE) -> List[dict]:
        """Phase 1: Full matrix sorted by edge_score desc."""
        return sorted(
            [s.to_dict() for s in self._matrix.values() if s.total_predictions >= min_sample],
            key=lambda x: x["edge_score"], reverse=True,
        )

    def get_league_rankings(self, min_sample: int = MIN_SAMPLE) -> List[dict]:
        """Phase 2: All league rankings sorted by overall_roi desc."""
        return sorted(
            [r.to_dict() for r in self._rankings.values() if r.total_predictions >= min_sample],
            key=lambda x: x["overall_roi"], reverse=True,
        )

    def get_edge_discovery(self) -> dict:
        """Phase 3: Edge discovery report."""
        return {
            "profitable_leagues":    self._profitable_leagues[:20],
            "unprofitable_leagues":  self._unprofitable_leagues[:20],
            "profitable_markets":    self._profitable_markets[:10],
            "unprofitable_markets":  self._unprofitable_markets[:10],
            "total_league_market_combinations": len(self._matrix),
            "evaluated_combinations": sum(
                1 for s in self._matrix.values() if s.total_predictions >= MIN_SAMPLE
            ),
        }

    def get_danger_report(self) -> dict:
        """Phase 5: All dangerous leagues and markets."""
        return {
            "BLACKLIST_LEAGUE":          sorted(self.blacklist_leagues),
            "HIGH_FALSE_SIGNAL_LEAGUE":  sorted(self.high_false_signal_leagues),
            "UNSTABLE_MARKET":           sorted(self.unstable_markets),
            "NO_EDGE_DETECTED":          sorted(self.no_edge_detected),
        }

    def get_best_markets(self, top_n: int = 10) -> List[dict]:
        """Top markets across all leagues by avg edge score."""
        return self._profitable_markets[:top_n]

    def get_worst_markets(self, top_n: int = 10) -> List[dict]:
        """Worst markets across all leagues."""
        return self._unprofitable_markets[:top_n]

    def summary(self) -> dict:
        evaluated = sum(1 for s in self._matrix.values() if s.total_predictions >= MIN_SAMPLE)
        return {
            "is_ready":           self.is_ready,
            "rows_loaded":        self.rows_loaded,
            "total_combinations": len(self._matrix),
            "evaluated":          evaluated,
            "blacklisted_leagues":       len(self.blacklist_leagues),
            "high_fpr_leagues":          len(self.high_false_signal_leagues),
            "unstable_markets":          len(self.unstable_markets),
            "no_edge_combinations":      len(self.no_edge_detected),
            "profitable_leagues_count":  len(self._profitable_leagues),
            "unprofitable_leagues_count": len(self._unprofitable_leagues),
        }


# ─── Module Singleton ────────────────────────────────────────────────────────
_global_engine: Optional[LeagueSpecializationEngine] = None


def get_engine() -> LeagueSpecializationEngine:
    """Return the module-level singleton (shared across scanner + Flask)."""
    global _global_engine
    if _global_engine is None:
        _global_engine = LeagueSpecializationEngine()
    return _global_engine


def reset_engine():
    """Reset singleton — useful for testing."""
    global _global_engine
    _global_engine = None
