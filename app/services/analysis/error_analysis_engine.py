"""
Error Analysis Engine
=====================
Phase 1: Loss Reason Detection  — WHY did the model lose?
Phase 2: False Positive Database — Catalog high-confidence losses
Phase 3: Pattern Frequency       — Which patterns fail most?
Phase 4: Confidence Penalty Learning — Penalize known bad patterns
Phase 5: Prediction Explainability   — WHY_PICK / RISK_FACTORS / WHY_NOT_S_TIER

Data:   live_test_session_*.csv  (predictions + results)
Rules:  No ML · No auto-recalibration · Read-only historical analysis
"""

import csv
import glob
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
HIGH_CONF_THRESH      = 65.0   # above → loss = false positive
HIGH_VOLATILITY_THR   = 70.0
CHAOS_THR             = 65.0
FSS_THR               = 45.0
OQM_THR               = 35.0
SMALL_SAMPLE_THR      = 50.0
FORM_DRIFT_THR        = 35.0   # weighted_form_score below → FORM_DRIFT

# Phase 4: FP penalty thresholds
FP_RATE_LOW    = 0.15
FP_RATE_MED    = 0.30
FP_RATE_HIGH   = 0.50

# Phase 4: multipliers
FP_MULT_LOW  = 0.93
FP_MULT_MED  = 0.85
FP_MULT_HIGH = 0.75

# All possible failure reasons
ALL_REASONS = (
    "HIGH_VOLATILITY", "EXPLOSIVE_MATCH", "EARLY_GOAL", "LATE_GOAL",
    "LEAGUE_CHAOS", "FALSE_UNDER", "FALSE_OVER", "H2H_MISLEADING",
    "SMALL_SAMPLE", "FORM_DRIFT", "HOME_AWAY_MISMATCH",
    "OPPOSITION_MISMATCH", "MOMENTUM_SHIFT", "UNKNOWN",
)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _f(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key) or default)
    except (TypeError, ValueError):
        return default


def _has_tag(field_val, tag: str) -> bool:
    return tag.upper() in str(field_val).upper()


# ─── Phase 1 — Loss Reason Detection ─────────────────────────────────────────
def detect_failure_reasons(row: dict) -> List[str]:
    """
    Rule-based detection of why a prediction failed.
    Uses available CSV fields (volatility_score, chaos_score, tags, etc.)
    """
    vol         = _f(row, "volatility_score")
    chaos       = _f(row, "chaos_score")
    fss         = _f(row, "false_signal_score")
    conf        = _f(row, "confidence_score")
    small_smp   = _f(row, "small_sample_risk")
    oqm         = _f(row, "opposition_quality_mismatch")
    h2h_bias    = _f(row, "h2h_bias_risk")
    wform       = _f(row, "weighted_form_score", -1.0)
    home_str    = _f(row, "home_strength_index", -1.0)
    away_wk     = _f(row, "away_weakness_index", -1.0)

    market      = str(row.get("market", "")).upper()
    lg_tags     = str(row.get("league_tags", ""))
    vol_tags    = str(row.get("volatility_tags", ""))

    reasons: List[str] = []

    # ── Volatility-based ──────────────────────────────────────────────────────
    if vol >= HIGH_VOLATILITY_THR:
        reasons.append("HIGH_VOLATILITY")

    if chaos >= CHAOS_THR or _has_tag(vol_tags, "EXPLOSIVE"):
        reasons.append("EXPLOSIVE_MATCH")

    # ── Market × League interaction ───────────────────────────────────────────
    if _has_tag(lg_tags, "HIGH_VOLATILITY_LEAGUE") and "UNDER" in market:
        reasons.append("EARLY_GOAL")

    if _has_tag(lg_tags, "LATE_GOAL") and "UNDER" in market:
        reasons.append("LATE_GOAL")

    if (_has_tag(lg_tags, "CHAOTIC") or _has_tag(lg_tags, "YOUTH_CHAOS")
            or _has_tag(lg_tags, "WOMEN_HIGH_VARIANCE")):
        reasons.append("LEAGUE_CHAOS")

    if _has_tag(vol_tags, "FAKE_UNDER") and "UNDER" in market:
        reasons.append("FALSE_UNDER")

    if _has_tag(lg_tags, "STABLE_UNDER") and "OVER" in market:
        reasons.append("FALSE_OVER")

    # ── Data quality ──────────────────────────────────────────────────────────
    if h2h_bias >= 40 or (_has_tag(vol_tags, "H2H") and conf >= HIGH_CONF_THRESH):
        reasons.append("H2H_MISLEADING")

    if small_smp >= SMALL_SAMPLE_THR or fss >= FSS_THR:
        reasons.append("SMALL_SAMPLE")

    # FORM_DRIFT: model was confident but team form was poor
    if 0 < wform <= FORM_DRIFT_THR and conf >= HIGH_CONF_THRESH:
        reasons.append("FORM_DRIFT")

    # ── Matchup mismatch ──────────────────────────────────────────────────────
    if home_str > 0 and away_wk > 0 and abs(home_str - away_wk) > 30:
        reasons.append("HOME_AWAY_MISMATCH")

    if oqm >= OQM_THR:
        reasons.append("OPPOSITION_MISMATCH")

    # MOMENTUM_SHIFT: high volatility + UNDER, not already FAKE_UNDER
    if vol >= 60 and "UNDER" in market and "FALSE_UNDER" not in reasons:
        reasons.append("MOMENTUM_SHIFT")

    return reasons if reasons else ["UNKNOWN"]


def is_false_positive(row: dict) -> bool:
    """A loss from a high-confidence or S/A-tier prediction."""
    result = str(row.get("result_correct", "")).strip().upper()
    if result != "LOSS":
        return False
    conf  = _f(row, "confidence_score")
    tier  = str(row.get("statistical_tier", ""))
    return conf >= HIGH_CONF_THRESH or tier in ("S_TIER", "A_TIER")


# ─── Data Structures ──────────────────────────────────────────────────────────
@dataclass
class FailureRecord:
    """Phase 2: One diagnosed losing prediction."""
    league: str
    country: str
    market: str
    statistical_tier: str
    confidence: float
    volatility: float
    chaos: float
    false_signal_score: float
    failure_reasons: List[str]
    is_fp: bool             # high-confidence false positive

    def to_dict(self) -> dict:
        return {
            "league":             self.league,
            "country":            self.country,
            "market":             self.market,
            "statistical_tier":   self.statistical_tier,
            "confidence":         round(self.confidence, 1),
            "volatility":         round(self.volatility, 1),
            "chaos":              round(self.chaos, 1),
            "false_signal_score": round(self.false_signal_score, 1),
            "failure_reasons":    self.failure_reasons,
            "is_false_positive":  self.is_fp,
        }


@dataclass
class FalsePositivePattern:
    """Phase 3: Aggregated pattern for a (league, market, failure_reason) combo."""
    league: str
    country: str
    market: str
    failure_reason: str
    occurrence_count: int = 0
    total_losses: int = 0
    avg_confidence: float = 0.0
    avg_volatility: float = 0.0
    fp_rate: float = 0.0        # FP occurrences / total losses for this combo
    penalty: float = 0.0        # confidence multiplier deduction [0.0, 0.25]

    def to_dict(self) -> dict:
        return {
            "league":           self.league,
            "country":          self.country,
            "market":           self.market,
            "failure_reason":   self.failure_reason,
            "occurrence_count": self.occurrence_count,
            "total_losses":     self.total_losses,
            "avg_confidence":   round(self.avg_confidence, 1),
            "avg_volatility":   round(self.avg_volatility, 1),
            "fp_rate":          round(self.fp_rate, 3),
            "penalty":          round(self.penalty, 3),
        }


@dataclass
class PickExplanation:
    """Phase 5: Human-readable explanation for a pick decision."""
    why_pick: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    why_not_s_tier: List[str] = field(default_factory=list)
    historical_failure_penalty: float = 0.0   # 0.0 = no penalty, 0.25 = max
    failure_pattern_warning: str = ""

    def to_dict(self) -> dict:
        return {
            "why_pick":                   self.why_pick,
            "risk_factors":               self.risk_factors,
            "why_not_s_tier":             self.why_not_s_tier,
            "historical_failure_penalty": round(self.historical_failure_penalty, 3),
            "failure_pattern_warning":    self.failure_pattern_warning,
        }


# ─── Main Engine ─────────────────────────────────────────────────────────────
class ErrorAnalysisEngine:
    """
    Phases 1-5: Error Analysis Engine.
    Learns from past losses to reduce false positives.
    No ML · No auto-recalibration · Historical read-only.
    """

    def __init__(self):
        # Phase 2: raw failure records
        self._records: List[FailureRecord] = []
        # Phase 3: aggregated patterns keyed by (league, country, market, reason)
        self._patterns: Dict[Tuple, FalsePositivePattern] = {}
        # Phase 4: fastest lookup by (league, country, market)
        self._patterns_by_key: Dict[Tuple, List[FalsePositivePattern]] = defaultdict(list)
        # State
        self.rows_loaded: int = 0
        self.is_ready: bool = False

    # ─── Loading ──────────────────────────────────────────────────────────────
    def load_from_csvs(self, search_dir: str = ".") -> int:
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
                logger.info(f"[EAE] Loaded {fpath}")
            except Exception as e:
                logger.warning(f"[EAE] Skipping {fpath}: {e}")
        self.rows_loaded += total
        if total > 0:
            self._finalize()
        logger.info(f"[EAE] {total} rows, {len(self._records)} failures — ready={self.is_ready}")
        return total

    def load_from_rows(self, rows: List[dict]) -> int:
        added = sum(1 for row in rows if self._ingest_row(row))
        if added > 0:
            self._finalize()
        self.rows_loaded += added
        return added

    def _ingest_row(self, row: dict) -> bool:
        result = str(row.get("result_correct", "")).strip().upper()
        if result != "LOSS":
            return False

        league  = (row.get("league") or "").strip()
        country = (row.get("country") or "").strip()
        market  = (row.get("market") or "").strip()
        tier    = (row.get("statistical_tier") or "").strip()
        if not league or not market:
            return False

        reasons = detect_failure_reasons(row)
        fp      = is_false_positive(row)

        rec = FailureRecord(
            league=league, country=country, market=market,
            statistical_tier=tier,
            confidence=_f(row, "confidence_score"),
            volatility=_f(row, "volatility_score"),
            chaos=_f(row, "chaos_score"),
            false_signal_score=_f(row, "false_signal_score"),
            failure_reasons=reasons,
            is_fp=fp,
        )
        self._records.append(rec)
        return True

    # ─── Finalization (Phase 2+3+4) ───────────────────────────────────────────
    def _finalize(self):
        self._patterns.clear()
        self._patterns_by_key.clear()

        # Accumulate per (league, country, market, reason)
        _conf_sum:  Dict[Tuple, float] = defaultdict(float)
        _vol_sum:   Dict[Tuple, float] = defaultdict(float)
        _total_losses: Dict[Tuple[str, str, str], int] = defaultdict(int)

        for rec in self._records:
            mk_key = (rec.league, rec.country, rec.market)
            _total_losses[mk_key] += 1
            for reason in rec.failure_reasons:
                pkey = (rec.league, rec.country, rec.market, reason)
                if pkey not in self._patterns:
                    self._patterns[pkey] = FalsePositivePattern(
                        league=rec.league, country=rec.country,
                        market=rec.market, failure_reason=reason,
                    )
                p = self._patterns[pkey]
                if rec.is_fp:
                    p.occurrence_count += 1
                p.total_losses += 1
                _conf_sum[pkey] += rec.confidence
                _vol_sum[pkey]  += rec.volatility

        # Compute derived stats
        for pkey, p in self._patterns.items():
            n = p.total_losses
            if n > 0:
                p.avg_confidence = round(_conf_sum[pkey] / n, 1)
                p.avg_volatility  = round(_vol_sum[pkey]  / n, 1)
            mk_key = (p.league, p.country, p.market)
            total = _total_losses.get(mk_key, 1)
            p.fp_rate = round(p.occurrence_count / max(total, 1), 4)
            p.penalty = self._compute_penalty(p.fp_rate)
            self._patterns_by_key[mk_key].append(p)

        self.is_ready = True

    @staticmethod
    def _compute_penalty(fp_rate: float) -> float:
        if fp_rate < FP_RATE_LOW:    return 0.0
        if fp_rate < FP_RATE_MED:    return round(1.0 - FP_MULT_LOW, 3)
        if fp_rate < FP_RATE_HIGH:   return round(1.0 - FP_MULT_MED, 3)
        return round(1.0 - FP_MULT_HIGH, 3)

    # ─── Phase 3 — Pattern Frequency ─────────────────────────────────────────
    def top_failure_reasons(self, top_n: int = 10) -> List[dict]:
        """Most frequent failure reasons (by FP occurrence count)."""
        agg: Dict[str, int] = defaultdict(int)
        for p in self._patterns.values():
            agg[p.failure_reason] += p.occurrence_count
        return sorted(
            [{"reason": r, "fp_count": c} for r, c in agg.items()],
            key=lambda x: -x["fp_count"],
        )[:top_n]

    def top_false_positive_leagues(self, top_n: int = 10) -> List[dict]:
        """Leagues with most false positives."""
        agg: Dict[str, dict] = defaultdict(lambda: {"fp_count": 0, "total": 0, "country": ""})
        for p in self._patterns.values():
            k = p.league
            agg[k]["fp_count"] += p.occurrence_count
            agg[k]["total"]    += p.total_losses
            agg[k]["country"]   = p.country
        result = []
        for lg, d in agg.items():
            fp_rate = d["fp_count"] / max(d["total"], 1)
            result.append({
                "league":   lg,
                "country":  d["country"],
                "fp_count": d["fp_count"],
                "total_losses": d["total"],
                "fp_rate":  round(fp_rate, 3),
            })
        return sorted(result, key=lambda x: -x["fp_count"])[:top_n]

    def top_dangerous_markets(self, top_n: int = 10) -> List[dict]:
        """Markets with most false positives."""
        agg: Dict[str, dict] = defaultdict(lambda: {"fp_count": 0, "total": 0})
        for p in self._patterns.values():
            k = p.market
            agg[k]["fp_count"] += p.occurrence_count
            agg[k]["total"]    += p.total_losses
        result = []
        for mk, d in agg.items():
            fp_rate = d["fp_count"] / max(d["total"], 1)
            result.append({
                "market":       mk,
                "fp_count":     d["fp_count"],
                "total_losses": d["total"],
                "fp_rate":      round(fp_rate, 3),
            })
        return sorted(result, key=lambda x: -x["fp_count"])[:top_n]

    def get_all_patterns(self, min_occurrences: int = 1) -> List[dict]:
        """All false positive patterns sorted by occurrence_count desc."""
        return sorted(
            [p.to_dict() for p in self._patterns.values()
             if p.occurrence_count >= min_occurrences],
            key=lambda x: (-x["occurrence_count"], -x["fp_rate"]),
        )

    def get_false_positive_table(self, league: str = "", market: str = "") -> List[dict]:
        """Phase 2: Filter the false positive database."""
        result = []
        for p in self._patterns.values():
            if league and league.lower() not in p.league.lower():
                continue
            if market and market.lower() not in p.market.lower():
                continue
            result.append(p.to_dict())
        return sorted(result, key=lambda x: -x["occurrence_count"])

    # ─── Phase 4 — Confidence Penalty ────────────────────────────────────────
    def get_historical_failure_penalty(
        self, league: str, country: str, market: str,
    ) -> Tuple[float, str]:
        """
        Returns (multiplier, reason).
        multiplier = 1.0 → no penalty, 0.75 → -25% max.
        """
        if not self.is_ready:
            return 1.0, ""
        key = (league, country, market)
        patterns = self._patterns_by_key.get(key, [])
        if not patterns:
            return 1.0, ""
        worst = max(patterns, key=lambda p: p.fp_rate)
        if worst.fp_rate < FP_RATE_LOW:
            return 1.0, ""
        mult = 1.0 - worst.penalty
        reason = (
            f"EAE {worst.failure_reason}: FP rate={worst.fp_rate:.0%} "
            f"n={worst.occurrence_count} in {league}/{market}"
        )
        return round(mult, 3), reason

    def _get_worst_pattern(
        self, league: str, country: str, market: str,
    ) -> Optional[FalsePositivePattern]:
        key = (league, country, market)
        pts = self._patterns_by_key.get(key, [])
        return max(pts, key=lambda p: p.fp_rate) if pts else None

    # ─── Phase 5 — Prediction Explainability ─────────────────────────────────
    def generate_pick_explanation(
        self,
        league: str,
        country: str,
        market: str,
        confidence: float,
        volatility: float,
        chaos: float,
        false_signal_score: float,
        league_tags,
        volatility_tags,
        tier_downgrade: bool,
        refuse_pick: bool,
        refuse_reason: str,
        league_reliability: float,
        lse_edge_rating: str = "NO_DATA",
        lse_market_prof: str = "NO_DATA",
    ) -> PickExplanation:
        """Build WHY_PICK / RISK_FACTORS / WHY_NOT_S_TIER for one match."""
        expl = PickExplanation()

        lt = str(league_tags)
        vt = str(volatility_tags)
        mk = market.upper()

        # ── WHY_PICK ─────────────────────────────────────────────────────────
        if league_reliability >= 70:
            expl.why_pick.append(f"Ligue fiable (reliability={league_reliability:.0f}%)")
        if lse_edge_rating in ("STRONG_EDGE", "EDGE"):
            expl.why_pick.append(f"Edge historique détecté: {lse_edge_rating}")
        if lse_market_prof in ("STRONG_EDGE", "EDGE"):
            expl.why_pick.append(f"Marché historiquement rentable ({lse_market_prof})")
        if false_signal_score < 25:
            expl.why_pick.append(f"Faux signal faible (FSS={false_signal_score:.0f})")
        if volatility < 40:
            expl.why_pick.append(f"Volatilité contrôlée ({volatility:.0f}/100)")
        if chaos < 35:
            expl.why_pick.append(f"Faible chaos ({chaos:.0f}/100)")
        if _has_tag(lt, "STABLE_UNDER_LEAGUE") and "UNDER" in mk:
            expl.why_pick.append("STABLE_UNDER_LEAGUE — marché UNDER cohérent")
        if _has_tag(lt, "HT_UNDER_FRIENDLY") and "HT_UNDER" in mk:
            expl.why_pick.append("HT_UNDER_FRIENDLY — ligue adaptée à ce marché")

        # ── RISK_FACTORS ─────────────────────────────────────────────────────
        if volatility >= 60:
            expl.risk_factors.append(f"Volatilité élevée ({volatility:.0f}/100)")
        if chaos >= 55:
            expl.risk_factors.append(f"Match potentiellement chaotique ({chaos:.0f}/100)")
        if _has_tag(vt, "FAKE_UNDER") and "UNDER" in mk:
            expl.risk_factors.append("FAKE_UNDER détecté — le UNDER pourrait sauter")
        if _has_tag(lt, "CHAOTIC_LEAGUE") or _has_tag(lt, "YOUTH_CHAOS"):
            expl.risk_factors.append("Ligue chaotique par historique")
        if _has_tag(lt, "HIGH_VOLATILITY_LEAGUE") and "UNDER" in mk:
            expl.risk_factors.append("HIGH_VOLATILITY_LEAGUE — buts précoces fréquents")
        if _has_tag(lt, "LATE_GOAL_LEAGUE") and "UNDER" in mk:
            expl.risk_factors.append("LATE_GOAL_LEAGUE — tendance aux buts tardifs")
        if false_signal_score >= 40:
            expl.risk_factors.append(f"Faux signal modéré (FSS={false_signal_score:.0f})")
        if lse_edge_rating in ("AVOID", "WEAK"):
            expl.risk_factors.append(f"LSE avertit: {lse_edge_rating} dans {league}")

        # Historical false positive pattern
        worst = self._get_worst_pattern(league, country, market)
        if worst and worst.fp_rate >= FP_RATE_LOW:
            expl.risk_factors.append(
                f"Pattern historique: {worst.failure_reason} "
                f"({worst.occurrence_count}× · FP={worst.fp_rate:.0%})"
            )
            expl.failure_pattern_warning = (
                f"{worst.failure_reason}: {worst.occurrence_count} faux positifs "
                f"({worst.fp_rate:.0%} taux) dans {league}/{market}"
            )

        # ── WHY_NOT_S_TIER ───────────────────────────────────────────────────
        if refuse_pick:
            expl.why_not_s_tier.append(
                f"VolatilityEngine REFUSE: {(refuse_reason or 'volatilité excessive')[:60]}"
            )
        if tier_downgrade:
            expl.why_not_s_tier.append(
                "FalseSignalDetector: tier dégradé (FSS trop élevé)"
            )
        if volatility >= HIGH_VOLATILITY_THR:
            expl.why_not_s_tier.append(
                f"Volatilité trop élevée ({volatility:.0f}/100 ≥ {HIGH_VOLATILITY_THR:.0f})"
            )
        if league_reliability < 50:
            expl.why_not_s_tier.append(
                f"Ligue peu fiable (reliability={league_reliability:.0f}%)"
            )
        if lse_edge_rating in ("AVOID",):
            expl.why_not_s_tier.append(
                f"LSE AVOID: historique très négatif dans {league}"
            )
        if false_signal_score >= 55:
            expl.why_not_s_tier.append(
                f"FSS trop élevé pour S_TIER ({false_signal_score:.0f})"
            )

        # ── Penalty ───────────────────────────────────────────────────────────
        if worst and worst.penalty > 0:
            expl.historical_failure_penalty = worst.penalty

        return expl

    # ─── Summary ──────────────────────────────────────────────────────────────
    def get_error_analysis_report(self) -> dict:
        """Full error analysis report for /api/error-analysis."""
        total_losses  = len(self._records)
        total_fp      = sum(1 for r in self._records if r.is_fp)
        total_patterns = len(self._patterns)
        return {
            "is_ready":           self.is_ready,
            "rows_loaded":        self.rows_loaded,
            "total_losses":       total_losses,
            "total_false_positives": total_fp,
            "fp_rate_overall":    round(total_fp / max(total_losses, 1), 3),
            "total_patterns":     total_patterns,
            "top_failure_reasons":       self.top_failure_reasons(10),
            "top_fp_leagues":            self.top_false_positive_leagues(10),
            "top_dangerous_markets":     self.top_dangerous_markets(10),
        }

    def summary(self) -> dict:
        total_fp = sum(1 for r in self._records if r.is_fp)
        return {
            "is_ready":             self.is_ready,
            "rows_loaded":          self.rows_loaded,
            "total_losses":         len(self._records),
            "total_false_positives": total_fp,
            "total_patterns":       len(self._patterns),
            "leagues_affected":     len({r.league for r in self._records}),
            "markets_affected":     len({r.market for r in self._records}),
        }


# ─── Module Singleton ────────────────────────────────────────────────────────
_global_eae: Optional[ErrorAnalysisEngine] = None


def get_eae() -> ErrorAnalysisEngine:
    """Return the module-level singleton."""
    global _global_eae
    if _global_eae is None:
        _global_eae = ErrorAnalysisEngine()
    return _global_eae


def reset_eae():
    """Reset singleton — useful for testing."""
    global _global_eae
    _global_eae = None
