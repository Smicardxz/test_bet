"""
Phase 8: Backtesting Engine

Tests historically:
- HT Under / HT Over
- FT Under / FT Over
- BTTS

Dimensions:
- Per league
- Per country
- Per confidence tier (HIGH/MEDIUM/LOW)

Metrics:
- hit_rate
- simulated_roi (assuming unit stake at given odds)
- false_positives
- performance_by_league
- performance_by_market
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Confidence tiers
TIER_HIGH   = "HIGH"    # confidence >= 0.80
TIER_MEDIUM = "MEDIUM"  # confidence >= 0.65
TIER_LOW    = "LOW"     # confidence < 0.65


@dataclass
class BacktestRecord:
    """Single historical match used for backtesting"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    country: str
    ft_goals: int
    ht_goals: int
    home_goals: int
    away_goals: int
    date: Optional[str] = None
    volatility_tag: str = "NORMAL"
    profile_tags: List[str] = field(default_factory=list)


@dataclass
class MarketResult:
    """Result for one market in one match"""
    market: str       # e.g., "FT_UNDER_2_5"
    line: float
    prediction: str   # "UNDER" or "OVER" or "YES" or "NO"
    hit: bool
    simulated_odd: float  # Assumed odds used in simulation
    pnl: float            # Profit/Loss: hit ? (odd-1)*stake : -stake (stake=1)
    confidence: float
    confidence_tier: str
    league: str
    country: str
    volatility_tag: str = "NORMAL"
    profile_tags: List[str] = field(default_factory=list)


@dataclass
class BacktestSummary:
    """Summary of backtesting results for one market"""
    market: str
    total_bets: int
    hits: int
    misses: int
    hit_rate: float
    simulated_roi: float       # total_pnl / total_bets * 100
    total_pnl: float
    false_positives: int       # predicted but wrong
    false_positive_rate: float

    # By league
    by_league: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # By country
    by_country: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # By confidence tier
    by_tier: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # STEP 6: By volatility profile
    by_volatility: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # STEP 6: By match profile tag
    by_profile: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # STEP 6: Drawdown tracking
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    longest_losing_streak: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": self.market,
            "total_bets": self.total_bets,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
            "hit_rate_pct": round(self.hit_rate * 100, 2),
            "simulated_roi": round(self.simulated_roi, 2),
            "total_pnl": round(self.total_pnl, 4),
            "false_positives": self.false_positives,
            "false_positive_rate": round(self.false_positive_rate, 4),
            "by_league": {
                lg: {k: round(v, 4) if isinstance(v, float) else v for k, v in data.items()}
                for lg, data in self.by_league.items()
            },
            "by_country": {
                co: {k: round(v, 4) if isinstance(v, float) else v for k, v in data.items()}
                for co, data in self.by_country.items()
            },
            "by_tier": {
                tr: {k: round(v, 4) if isinstance(v, float) else v for k, v in data.items()}
                for tr, data in self.by_tier.items()
            },
            "by_volatility": {
                vt: {k: round(v, 4) if isinstance(v, float) else v for k, v in data.items()}
                for vt, data in self.by_volatility.items()
            },
            "by_profile": {
                pf: {k: round(v, 4) if isinstance(v, float) else v for k, v in data.items()}
                for pf, data in self.by_profile.items()
            },
            "max_drawdown":           round(self.max_drawdown, 4),
            "avg_drawdown":           round(self.avg_drawdown, 4),
            "longest_losing_streak":  self.longest_losing_streak,
        }


class BacktestingEngine:
    """
    Phase 8: Backtesting Engine

    Usage:
        engine = BacktestingEngine()
        records = engine.build_records_from_history(match_history)
        summary = engine.run(records, min_confidence=0.70)
    """

    # Default simulated odds per market (used when real odds unavailable)
    DEFAULT_ODDS: Dict[str, float] = {
        "HT_UNDER_0_5": 1.30,
        "HT_UNDER_1_5": 1.12,
        "HT_OVER_0_5":  3.50,
        "HT_OVER_1_5":  7.00,
        "FT_UNDER_1_5": 1.70,
        "FT_UNDER_2_5": 1.85,
        "FT_UNDER_3_5": 1.30,
        "FT_OVER_1_5":  2.00,
        "FT_OVER_2_5":  2.05,
        "FT_OVER_3_5":  3.00,
        "BTTS_YES":     1.90,
        "BTTS_NO":      1.90,
    }

    def build_records_from_history(
        self,
        match_history: List[Dict[str, Any]],
        league: str = "Unknown",
        country: str = "Unknown",
        volatility_tag: str = "NORMAL",
        profile_tags: Optional[List[str]] = None,
    ) -> List[BacktestRecord]:
        """Convert raw match_history dicts to BacktestRecord list"""
        pt = profile_tags or []
        records = []
        for i, m in enumerate(match_history):
            ft = m.get("total_goals", m.get("ft_goals", 0)) or 0
            ht = m.get("ht_goals", 0) or 0
            home = m.get("home_goals", 0) or 0
            away = m.get("away_goals", 0) or 0
            rec = BacktestRecord(
                match_id=str(m.get("match_id", i)),
                home_team=m.get("home_team", ""),
                away_team=m.get("away_team", ""),
                league=m.get("league", league),
                country=m.get("country", country),
                ft_goals=int(ft),
                ht_goals=int(ht),
                home_goals=int(home),
                away_goals=int(away),
                date=m.get("date"),
            )
            # Attach volatility + profile tags for STEP 6 breakdown
            rec.volatility_tag = m.get("volatility_tag", volatility_tag)
            rec.profile_tags = m.get("profile_tags", pt)
            records.append(rec)
        return records

    def run(
        self,
        records: List[BacktestRecord],
        min_confidence: float = 0.65,
        confidence_thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, BacktestSummary]:
        """
        Run full backtest on all markets.

        Args:
            records: list of BacktestRecord
            min_confidence: minimum confidence to include (default 0.65)
            confidence_thresholds: optional overrides for tier thresholds

        Returns:
            Dict[market_name, BacktestSummary]
        """
        if not records:
            return {}

        thresholds = confidence_thresholds or {"HIGH": 0.80, "MEDIUM": 0.65}
        all_results: Dict[str, List[MarketResult]] = {}

        for record in records:
            for market_result in self._evaluate_record(record, thresholds):
                if market_result.confidence < min_confidence:
                    continue
                all_results.setdefault(market_result.market, []).append(market_result)

        summaries = {}
        for market, results in all_results.items():
            summaries[market] = self._summarize(market, results)

        return summaries

    def run_from_analyzed_matches(
        self,
        analyzed_matches: List[Dict[str, Any]],
        min_confidence: float = 0.65,
    ) -> Dict[str, "BacktestSummary"]:
        """
        STEP 6: Backtest sur les matchs déjà analysés par le scanner.
        Utilise les données réelles (match_history) de chaque match analysé.

        Args:
            analyzed_matches: Liste venant de scan_result["analyzed_matches"]
            min_confidence:   Seuil de confiance minimum

        Returns:
            Dict[market, BacktestSummary]
        """
        all_records: List[BacktestRecord] = []

        for item in analyzed_matches:
            match_data = item.get("match_data", {})
            analysis   = item.get("analysis", {}) or {}

            league  = match_data.get("competition", "Unknown")
            country = match_data.get("country", "Unknown")

            # Extraire l'historique des matchs (match_history dans l'analyse)
            raw_history = analysis.get("match_history", [])
            if not raw_history:
                continue

            # Volatility + profile tags
            v_result = analysis.get("volatility_analysis", {})
            v_tag = "HIGH_VOL" if v_result.get("volatility_score", 0) > 60 else "NORMAL"
            p_tags = analysis.get("match_profile", {}).get("specific_profiles", [])

            records = self.build_records_from_history(
                raw_history,
                league=league,
                country=country,
                volatility_tag=v_tag,
                profile_tags=p_tags,
            )
            all_records.extend(records)

        return self.run(all_records, min_confidence=min_confidence)

    def _evaluate_record(
        self,
        record: BacktestRecord,
        thresholds: Dict[str, float]
    ) -> List[MarketResult]:
        """Evaluate all markets for one historical match"""
        results = []

        # Derived confidence from pattern (heuristic based on goals range)
        # In production this would use actual signal confidence
        confidence = self._heuristic_confidence(record)
        tier = self._tier(confidence, thresholds)

        markets = [
            ("HT_UNDER_0_5", 0.5, "UNDER", record.ht_goals < 1),
            ("HT_UNDER_1_5", 1.5, "UNDER", record.ht_goals < 2),
            ("HT_OVER_0_5",  0.5, "OVER",  record.ht_goals >= 1),
            ("HT_OVER_1_5",  1.5, "OVER",  record.ht_goals >= 2),
            ("FT_UNDER_1_5", 1.5, "UNDER", record.ft_goals < 2),
            ("FT_UNDER_2_5", 2.5, "UNDER", record.ft_goals < 3),
            ("FT_UNDER_3_5", 3.5, "UNDER", record.ft_goals < 4),
            ("FT_OVER_1_5",  1.5, "OVER",  record.ft_goals >= 2),
            ("FT_OVER_2_5",  2.5, "OVER",  record.ft_goals >= 3),
            ("FT_OVER_3_5",  3.5, "OVER",  record.ft_goals >= 4),
            ("BTTS_YES",     None, "YES",  record.home_goals > 0 and record.away_goals > 0),
            ("BTTS_NO",      None, "NO",   not (record.home_goals > 0 and record.away_goals > 0)),
        ]

        for market, line, prediction, hit in markets:
            odd = self.DEFAULT_ODDS.get(market, 1.90)
            pnl = (odd - 1.0) if hit else -1.0
            results.append(MarketResult(
                market=market,
                line=line,
                prediction=prediction,
                hit=hit,
                simulated_odd=odd,
                pnl=pnl,
                confidence=confidence,
                confidence_tier=tier,
                league=record.league,
                country=record.country,
                volatility_tag=record.volatility_tag,
                profile_tags=list(record.profile_tags),
            ))

        return results

    def _summarize(self, market: str, results: List[MarketResult]) -> "BacktestSummary":
        """Summarize results for one market"""
        total = len(results)
        hits = sum(1 for r in results if r.hit)
        misses = total - hits
        hit_rate = hits / total if total > 0 else 0.0
        total_pnl = sum(r.pnl for r in results)
        roi = (total_pnl / total * 100) if total > 0 else 0.0
        false_positives = misses
        fpr = false_positives / total if total > 0 else 0.0

        # Breakdown by league
        by_league: Dict[str, Dict] = {}
        for r in results:
            lg = r.league
            if lg not in by_league:
                by_league[lg] = {"bets": 0, "hits": 0, "pnl": 0.0}
            by_league[lg]["bets"] += 1
            by_league[lg]["hits"] += int(r.hit)
            by_league[lg]["pnl"] += r.pnl
        for lg, data in by_league.items():
            data["hit_rate"] = data["hits"] / data["bets"] if data["bets"] else 0.0
            data["roi"] = (data["pnl"] / data["bets"] * 100) if data["bets"] else 0.0

        # Breakdown by country
        by_country: Dict[str, Dict] = {}
        for r in results:
            co = r.country
            if co not in by_country:
                by_country[co] = {"bets": 0, "hits": 0, "pnl": 0.0}
            by_country[co]["bets"] += 1
            by_country[co]["hits"] += int(r.hit)
            by_country[co]["pnl"] += r.pnl
        for co, data in by_country.items():
            data["hit_rate"] = data["hits"] / data["bets"] if data["bets"] else 0.0
            data["roi"] = (data["pnl"] / data["bets"] * 100) if data["bets"] else 0.0

        # Breakdown by confidence tier
        by_tier: Dict[str, Dict] = {}
        for r in results:
            tr = r.confidence_tier
            if tr not in by_tier:
                by_tier[tr] = {"bets": 0, "hits": 0, "pnl": 0.0}
            by_tier[tr]["bets"] += 1
            by_tier[tr]["hits"] += int(r.hit)
            by_tier[tr]["pnl"] += r.pnl
        for tr, data in by_tier.items():
            data["hit_rate"] = data["hits"] / data["bets"] if data["bets"] else 0.0
            data["roi"] = (data["pnl"] / data["bets"] * 100) if data["bets"] else 0.0

        # STEP 6: Breakdown by volatility tag
        by_volatility: Dict[str, Dict] = {}
        for r in results:
            vt = getattr(r, "volatility_tag", "NORMAL")
            if vt not in by_volatility:
                by_volatility[vt] = {"bets": 0, "hits": 0, "pnl": 0.0}
            by_volatility[vt]["bets"] += 1
            by_volatility[vt]["hits"] += int(r.hit)
            by_volatility[vt]["pnl"] += r.pnl
        for vt, data in by_volatility.items():
            data["hit_rate"] = data["hits"] / data["bets"] if data["bets"] else 0.0
            data["roi"] = (data["pnl"] / data["bets"] * 100) if data["bets"] else 0.0

        # STEP 6: Breakdown by profile tag
        by_profile: Dict[str, Dict] = {}
        for r in results:
            for tag in getattr(r, "profile_tags", []):
                if tag not in by_profile:
                    by_profile[tag] = {"bets": 0, "hits": 0, "pnl": 0.0}
                by_profile[tag]["bets"] += 1
                by_profile[tag]["hits"] += int(r.hit)
                by_profile[tag]["pnl"] += r.pnl
        for pf, data in by_profile.items():
            data["hit_rate"] = data["hits"] / data["bets"] if data["bets"] else 0.0
            data["roi"] = (data["pnl"] / data["bets"] * 100) if data["bets"] else 0.0

        # STEP 6: Drawdown tracking
        max_dd, avg_dd, longest_streak = self._compute_drawdown(results)

        return BacktestSummary(
            market=market,
            total_bets=total,
            hits=hits,
            misses=misses,
            hit_rate=hit_rate,
            simulated_roi=roi,
            total_pnl=total_pnl,
            false_positives=false_positives,
            false_positive_rate=fpr,
            by_league=by_league,
            by_country=by_country,
            by_tier=by_tier,
            by_volatility=by_volatility,
            by_profile=by_profile,
            max_drawdown=max_dd,
            avg_drawdown=avg_dd,
            longest_losing_streak=longest_streak,
        )

    def _heuristic_confidence(self, record: BacktestRecord) -> float:
        """Simple heuristic confidence based on goals pattern (placeholder)"""
        if record.ft_goals <= 1:
            return 0.82
        elif record.ft_goals <= 2:
            return 0.74
        elif record.ft_goals <= 3:
            return 0.65
        else:
            return 0.55

    def _compute_drawdown(self, results: List[MarketResult]):
        """Calcule le drawdown maximum, moyen, et la plus longue série perdante."""
        if not results:
            return 0.0, 0.0, 0

        cumulative = 0.0
        peak = 0.0
        drawdowns = []
        max_dd = 0.0

        losing_streak = 0
        max_streak = 0

        for r in results:
            cumulative += r.pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > 0:
                drawdowns.append(dd)
                max_dd = max(max_dd, dd)

            if not r.hit:
                losing_streak += 1
                max_streak = max(max_streak, losing_streak)
            else:
                losing_streak = 0

        avg_dd = sum(drawdowns) / len(drawdowns) if drawdowns else 0.0
        return round(max_dd, 4), round(avg_dd, 4), max_streak

    def _tier(self, confidence: float, thresholds: Dict[str, float]) -> str:
        if confidence >= thresholds.get("HIGH", 0.80):
            return TIER_HIGH
        elif confidence >= thresholds.get("MEDIUM", 0.65):
            return TIER_MEDIUM
        return TIER_LOW

    def report_text(self, summaries: Dict[str, BacktestSummary]) -> str:
        """Generate compact text report"""
        lines = ["=" * 60, "BACKTESTING REPORT", "=" * 60]
        for market, s in sorted(summaries.items(), key=lambda x: -x[1].hit_rate):
            lines.append(
                f"\n{market:25s} | {s.total_bets:4d} bets | "
                f"HR: {s.hit_rate*100:.1f}% | ROI: {s.simulated_roi:+.1f}% | "
                f"FP: {s.false_positive_rate*100:.1f}%"
            )
            if s.by_tier:
                for tier, data in sorted(s.by_tier.items()):
                    lines.append(
                        f"  [{tier:6s}] {data['bets']:3d} bets | "
                        f"HR: {data['hit_rate']*100:.1f}% | ROI: {data['roi']:+.1f}%"
                    )
        lines.append("=" * 60)
        return "\n".join(lines)
