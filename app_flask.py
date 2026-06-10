"""
Flask Dashboard - Alternative à Streamlit
Compatible avec toutes versions Python
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from typing import Dict, Any
import json
import logging
import os

load_dotenv(override=True)

# Imports principaux (PHASE 1-9: V2 connectée partout)
from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner
from app.services.targeting.league_targeting_service import LeagueTargetingService
from app.services.analysis.league_specialization_engine import get_engine as _get_lse
from app.services.analysis.error_analysis_engine import get_eae as _get_eae
from app.database.supabase_config import get_supabase_config as _get_sb_cfg
from app.database.supabase_repository import get_repository as _get_repo
from app.services.events.event_mode_tagger import _determine_event_context, _determine_event_name, _determine_event_phase

logger = logging.getLogger(__name__)

app = Flask(__name__)

# ─── CORS configuration for Lovable + ngrok + local dev ──────────────────────
ALLOWED_ORIGINS = [
    "https://833ac7a4-8511-4c83-895c-10d51e8607be.lovableproject.com",
    "https://lovable.dev",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
CORS(app,
     resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
     supports_credentials=False,
     allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning", "bypass-tunnel-reminder", "Accept"],
     methods=["GET", "POST", "OPTIONS"])

@app.after_request
def _cors_after_request(response):
    """Ensure CORS headers on ALL responses including errors (403/500)."""
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, ngrok-skip-browser-warning, bypass-tunnel-reminder, Accept"
        response.headers["Access-Control-Allow-Credentials"] = "false"
    return response

# Cache global pour éviter de recharger à chaque requête
cache = {
    "data": None,
    "timestamp": None
}

# ─── League Specialization Engine ────────────────────────────────────────────
_lse_engine = _get_lse()
try:
    _lse_rows = _lse_engine.load_from_csvs(".")
    if _lse_rows > 0:
        logger.info(f"[LSE] Loaded {_lse_rows} rows from historical CSVs")
    else:
        logger.info("[LSE] No historical CSV data yet — specialization inactive")
except Exception as _lse_err:
    logger.warning(f"[LSE] Startup load non-blocking: {_lse_err}")

# ─── Error Analysis Engine ──────────────────────────────────────────────
_eae_engine = _get_eae()
try:
    _eae_rows = _eae_engine.load_from_csvs(".")
    if _eae_rows > 0:
        logger.info(f"[EAE] Loaded {_eae_rows} rows from historical CSVs")
    else:
        logger.info("[EAE] No historical CSV data yet — error analysis inactive")
except Exception as _eae_err:
    logger.warning(f"[EAE] Startup load non-blocking: {_eae_err}")

# ─── Supabase ────────────────────────────────────────────────────────
_sb_cfg = _get_sb_cfg()
_repo   = _get_repo()
logger.info(f"[SUPABASE] Status: {_sb_cfg.supabase_status}")




def _normalize_global_match(match_item: Dict[str, Any]) -> Dict[str, Any]:
    """Transforme un match du Global Scanner en format Lovable"""
    match_id = match_item.get("match_id", "")
    home_team = match_item.get("home_team", "")
    away_team = match_item.get("away_team", "")
    league = match_item.get("league", "")
    country = match_item.get("country", "")
    match_date = match_item.get("match_date", "")
    kickoff_time = match_item.get("kickoff_time", "")
    
    match_profile = match_item.get("match_profile", {}) or {}
    statistical_signals = match_item.get("statistical_signals", []) or []
    intelligence_score = match_item.get("intelligence_score", 0.0)
    pattern_rarity_score = match_item.get("pattern_rarity_score", 0.0)
    stability_score = match_item.get("stability_score", 0.0)
    market_edge_score = match_item.get("market_edge_score", 0.0)
    
    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "league": league,
        "country": country,
        "match_date": match_date,
        "kickoff_time": kickoff_time,
        "status": "UPCOMING",
        
        # Nouveaux scores d'intelligence
        "intelligence_score": intelligence_score,
        "pattern_rarity_score": pattern_rarity_score,
        "stability_score": stability_score,
        "market_edge_score": market_edge_score,
        
        # Profile information
        "scoring_profile": match_profile.get("scoring_profile", "UNKNOWN"),
        "tempo_profile": match_profile.get("tempo_profile", "UNKNOWN"),
        "specific_profiles": match_profile.get("specific_profiles", []),
        "characteristics": match_profile.get("characteristics", []),
        
        # Statistical signals
        "statistical_signals": [
            {
                "signal_type": signal.get("signal_type", ""),
                "signal_strength": signal.get("signal_strength", ""),
                "confidence": signal.get("confidence", 0.0),
                "reasons": signal.get("reasons", [])
            }
            for signal in statistical_signals[:5]
        ],
        
        "why_interesting": match_item.get("why_interesting", ""),
        "pattern_explanation": match_item.get("pattern_explanation", ""),
        "key_insights": match_item.get("key_insights", []),
        
        "data_quality_score": match_item.get("data_quality_score", 0.0),
        "sample_size_home": match_item.get("sample_size_home", 0),
        "sample_size_away": match_item.get("sample_size_away", 0),
        "provider": match_item.get("provider", ""),
        "scan_timestamp": match_item.get("scan_timestamp", "")
    }


def _va(analysis: dict) -> dict:
    """Safe accessor for volatility_analysis sub-dict."""
    return (analysis or {}).get("volatility_analysis") or {}

def _fs(analysis: dict) -> dict:
    """Safe accessor for false_signal_analysis sub-dict."""
    return (analysis or {}).get("false_signal_analysis") or {}

def _ha(analysis: dict) -> dict:
    """Safe accessor for home_away_analysis sub-dict."""
    return (analysis or {}).get("home_away_analysis") or {}

def _li(analysis: dict) -> dict:
    """Safe accessor for league_intelligence sub-dict."""
    return (analysis or {}).get("league_intelligence") or {}


def _normalize_match(match_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforme un match brut (from scanner) en format propre et stable pour Lovable.
    C'est le CONTRAT API principal — ne pas changer les clés sans mise à jour de la doc.
    """
    match_data = match_item.get("match_data", {}) or {}
    profile = match_item.get("profile", {}) or {}
    analysis = match_item.get("analysis", {}) or {}
    match_profile = analysis.get("match_profile", {}) or {}
    best_edges = analysis.get("best_edges", []) or []

    # --- Status normalisé ---
    status = "UPCOMING"
    if match_data.get("is_live"):
        status = "LIVE"
    elif match_data.get("is_finished"):
        status = "FINISHED"
    
    # --- Live score fields ---
    # Extract from match_data dict (now populated by scanner)
    home_score = match_data.get("home_score")
    away_score = match_data.get("away_score")
    minute = match_data.get("minute")
    elapsed = match_data.get("elapsed")
    ht_home_score = match_data.get("ht_home_score")
    ht_away_score = match_data.get("ht_away_score")
    status_short = match_data.get("status_short")
    status_long = match_data.get("status_long")
    
    # For live matches, ensure we have at least null values for required fields
    if status == "LIVE":
        status_short = status_short or "LIVE"
        status_long = status_long or "In Progress"

    # --- Target type ---
    target_level = profile.get("target_level", "")
    target_type = "MAJOR"
    if "extreme" in target_level.lower():
        target_type = "EXTREME_OBSCURE"
    elif "minor" in target_level.lower() or "semi" in target_level.lower():
        target_type = "BETTABLE_MINOR"

    # --- Best angle (value bet ou angle statistique) ---
    best_angle = None
    if best_edges:
        best = best_edges[0]
        edge_pct = best.get("edge_percent", 0) or 0
        conf_str = best.get("confidence", "")
        confidence_val = 90 if conf_str == "HIGH" else 75 if conf_str == "MEDIUM" else 60
        best_angle = {
            "market": best.get("market", ""),
            "label": best.get("market", "").replace("_", " "),
            "confidence": confidence_val,
            "fair_odd": best.get("fair_odd"),
            "market_odd": best.get("market_odd"),
            "sample_size": best.get("sample_size", 0),
            "status": "VALUE_DETECTED" if edge_pct > 0.05 else "WAITING_FOR_ODDS",
            "edge_percent": round(edge_pct * 100, 1) if edge_pct else 0.0
        }
    elif match_profile:
        angles = match_profile.get("statistical_angles", [])
        best_angle = {
            "market": angles[0] if angles else "PENDING",
            "label": (angles[0] if angles else "PENDING").replace("_", " "),
            "confidence": int(match_profile.get("confidence_score", 0)),
            "fair_odd": None,
            "market_odd": None,
            "sample_size": match_profile.get("sample_size", 0),
            "status": "NO_VALUE",
            "edge_percent": 0.0
        }
    else:
        best_angle = {
            "market": "PENDING",
            "label": "Not analyzed yet",
            "confidence": 0,
            "fair_odd": None,
            "market_odd": None,
            "sample_size": 0,
            "status": "NOT_ANALYZED",
            "edge_percent": 0.0
        }

    # --- Profile tags fusionnées ---
    profile_tags = []
    profile_tags.extend(match_profile.get("specific_profiles", []) or [])
    profile_tags.extend(match_profile.get("characteristics", []) or [])
    # Also add tempo/scoring as tags for filtering
    if match_profile.get("tempo_profile"):
        profile_tags.append(match_profile["tempo_profile"])
    if match_profile.get("scoring_profile"):
        profile_tags.append(match_profile["scoring_profile"])

    # --- Data quality normalisée ---
    dq = match_profile.get("data_quality", "UNKNOWN")
    if dq not in ["EXCELLENT", "GOOD", "FAIR", "LIMITED", "INSUFFICIENT", "UNKNOWN"]:
        dq = "UNKNOWN"

    # --- Phase 7+11: Tier / EV / Odds fields ---
    tier_level = analysis.get("tier_level", "NO_VALUE")
    ranking_score = analysis.get("ranking_score", 0.0)
    ev_opps = analysis.get("ev_opportunities", [])
    best_ev = analysis.get("best_ev_opportunity")
    odds_status = analysis.get("odds_status", "NO_KEY")
    matched_odds = analysis.get("matched_odds", [])
    market_mapping_confidence = analysis.get("market_mapping_confidence", 0.0)
    waiting_for_odds = analysis.get("waiting_for_odds", True)
    matchup_profile = analysis.get("matchup_profile", {})

    # --- Phase 7b: Statistical Tier (odds-independent) ---
    statistical_tier = analysis.get("statistical_tier", "NO_VALUE")
    statistical_ranking_score = analysis.get("statistical_ranking_score", 0.0)

    # --- Universe & Coverage ---
    match_universe   = analysis.get("match_universe", "STATISTICAL_ONLY")
    coverage_quality = analysis.get("coverage_quality", "NONE")
    # Derive if not set by scanner (backward compat)
    if match_universe == "STATISTICAL_ONLY" and bool(analysis.get("odds_count", 0)) and odds_status in ("MATCHED", "MATCHING_UNCERTAIN"):
        match_universe   = "MARKET_EV"
        coverage_quality = "FULL" if market_mapping_confidence >= 0.80 else "PARTIAL"

    # has_odds: true if odds were available and matched
    has_odds = bool(analysis.get("odds_count", 0)) and odds_status not in ("NO_KEY", "ODDS_MISSING", "")

    # ev_tier: tier_level is only meaningful when odds are present
    EV_TIERS = {"S_TIER", "A_TIER", "WATCHLIST"}
    if has_odds and tier_level in EV_TIERS:
        ev_tier = tier_level
    elif has_odds and tier_level == "NO_VALUE":
        ev_tier = "NO_EV"
    else:
        ev_tier = "WAITING_FOR_ODDS"

    # Derived booleans
    is_ev_pick          = ev_tier in ("S_TIER", "A_TIER")
    is_statistical_pick = statistical_tier in ("S_TIER", "A_TIER", "B_TIER")

    # --- statistical_interest: derived from signals/edges ---
    signals_data = analysis.get("signals", [])
    stat_interest = "NONE"
    if signals_data:
        best_sig_conf = max((s.get("confidence", 0) for s in signals_data), default=0)
        if best_sig_conf >= 0.80:
            stat_interest = "HIGH"
        elif best_sig_conf >= 0.65:
            stat_interest = "MEDIUM"
        elif best_sig_conf >= 0.50:
            stat_interest = "LOW"

    # --- best_statistical_angle ---
    best_stat_angle = None
    if signals_data:
        best_s = max(signals_data, key=lambda s: s.get("confidence", 0), default=None)
        if best_s:
            markets = best_s.get("suggested_markets", [])
            best_stat_angle = {
                "signal_type": best_s.get("type", ""),
                "confidence": round(best_s.get("confidence", 0), 3),
                "market": markets[0] if markets else "",
                "strength": best_s.get("strength", ""),
            }

    return {
        "fixture_id": str(match_data.get("match_id", "")),
        "home_team": match_data.get("home_team", ""),
        "away_team": match_data.get("away_team", ""),
        "home_team_id": str(match_data.get("home_team_id", "")),
        "away_team_id": str(match_data.get("away_team_id", "")),
        "country": match_data.get("country", ""),
        "league": match_data.get("competition", ""),
        "kickoff_time": match_data.get("kickoff_time", "") or match_data.get("time_display", "TBD"),
        "status": status,
        "target_type": target_type,
        # Live score fields
        "home_score": home_score,
        "away_score": away_score,
        "minute": minute,
        "elapsed": elapsed,
        "ht_home_score": ht_home_score,
        "ht_away_score": ht_away_score,
        "status_short": status_short,
        "status_long": status_long,
        "profile_tags": list(set(profile_tags)),
        "best_angle": best_angle,
        # Phase 11 fields
        "statistical_interest": stat_interest,
        "best_statistical_angle": best_stat_angle,
        # Phase 7: EV tier (odds-dependent)
        "tier_level": tier_level,
        "ranking_score": round(ranking_score, 3),
        "ev_tier": ev_tier,
        # Phase 7b: Statistical tier (odds-independent)
        "statistical_tier": statistical_tier,
        "statistical_ranking_score": round(statistical_ranking_score, 3),
        # Universe classification
        "match_universe":   match_universe,    # STATISTICAL_ONLY | MARKET_EV
        "coverage_quality": coverage_quality,  # FULL | PARTIAL | NONE
        # Derived flags
        "has_odds": has_odds,
        "is_ev_pick": is_ev_pick,
        "is_statistical_pick": is_statistical_pick,
        "ev_opportunities": ev_opps,
        "best_ev_opportunity": best_ev,
        "odds_status": odds_status if has_odds else "ODDS_MISSING",
        "matched_odds": matched_odds,
        "odds_count": analysis.get("odds_count", 0),
        "market_mapping_confidence": round(market_mapping_confidence, 3),
        "waiting_for_odds": waiting_for_odds,
        "matchup_profile": matchup_profile,
        # Scores
        "interest_score": round(match_profile.get("interest_score", 0), 1),
        "confidence_score": round(match_profile.get("confidence_score", 0), 1),
        "volatility_score": round(match_profile.get("volatility_score", 0), 1),
        "variance_score": round(match_profile.get("variance_score", 0), 3),
        "data_quality": dq,
        "analyzed": bool(analysis),
        "has_profile": bool(match_profile) and match_profile.get("tempo_profile") != "UNKNOWN",

        # ── Intelligence Engines (STEP 1-5) ──────────────────────────────

        # STEP 2: Volatility Engine
        "chaos_score":            round(_va(analysis).get("chaos_score", 0), 1),
        "stability_index":        round(_va(analysis).get("stability_index", 50), 1),
        "explosive_match_rate":   round(_va(analysis).get("explosive_match_rate", 0), 1),
        "fake_under_risk":        round(match_profile.get("fake_under_risk", 0), 1),
        "refuse_pick":            _va(analysis).get("refuse_pick", False),
        "refuse_pick_reason":     _va(analysis).get("refuse_reason", ""),
        "volatility_tags":        _va(analysis).get("tags", []),

        # STEP 3: False Signal Detector
        "false_signal_score":     round(_fs(analysis).get("false_signal_score", 0), 1),
        "false_signal_reasons":   _fs(analysis).get("warnings", []),
        "false_signal_tags":      _fs(analysis).get("tags", []),
        "tier_downgrade":         _fs(analysis).get("tier_downgrade", False),
        "small_sample_risk":      round(_fs(analysis).get("small_sample_risk", 0), 1),
        "opposition_quality_mismatch": round(_fs(analysis).get("opposition_quality_mismatch", 0), 1),

        # STEP 4: Weighted Recent Form
        "weighted_goal_projection": round(match_profile.get("weighted_goal_projection", 0), 2),
        "weighted_ht_projection":   round(match_profile.get("weighted_ht_projection", 0), 2),
        "weighted_tempo_projection": match_profile.get("weighted_tempo_projection", ""),
        "weighted_form_score":      round(match_profile.get("weighted_form_score", 0), 1),

        # STEP 5: Home/Away Context Engine
        "home_strength_index":    round(_ha(analysis).get("home_strength_index", 50), 1),
        "away_weakness_index":    round(_ha(analysis).get("away_weakness_index", 50), 1),
        "matchup_asymmetry_score": round(_ha(analysis).get("matchup_asymmetry_score", 0), 1),
        "expected_home_goals":    round(_ha(analysis).get("expected_home_goals", 0), 2),
        "expected_away_goals":    round(_ha(analysis).get("expected_away_goals", 0), 2),
        "home_away_tags":         _ha(analysis).get("tags", []),

        # STEP 1: League Intelligence
        "league_volatility_score":  round(_li(analysis).get("volatility_score", 0), 1),
        "league_reliability_score": round(_li(analysis).get("reliability_score", 0), 1),
        "league_stability_score":   round(_li(analysis).get("stability_score", 0), 1),
        "league_tags":              _li(analysis).get("tags", []),
        "league_btts_rate":         round(_li(analysis).get("btts_rate", 0), 1),
        "league_under_2_5_rate":    round(_li(analysis).get("under_2_5_rate", 0), 1),
        "league_avg_goals":         round(_li(analysis).get("avg_goals", 0), 2),
        "confidence_adjustments":   _li(analysis).get("confidence_adjustments", []),

        # STEP 4 (LSE): League Specialization Engine — Phase 6 fields
        **{k: v for k, v in (analysis.get("league_specialization") or {}).items()},

        # STEP 4b (EAE): Pick Explainability
        "why_pick":                   (analysis.get("pick_explanation") or {}).get("why_pick", []),
        "risk_factors":               (analysis.get("pick_explanation") or {}).get("risk_factors", []),
        "why_not_s_tier":             (analysis.get("pick_explanation") or {}).get("why_not_s_tier", []),
        "historical_failure_penalty": (analysis.get("pick_explanation") or {}).get("historical_failure_penalty", 0.0),
        "failure_pattern_warning":    (analysis.get("pick_explanation") or {}).get("failure_pattern_warning", ""),
        
        # EVENT_MODE fields - same logic as predictions tagging
        "event_context": _determine_event_context(match_data.get("competition", "")),
        "event_name": _determine_event_name(match_data.get("competition", ""), _determine_event_context(match_data.get("competition", ""))),
        "event_phase": _determine_event_phase(match_data.get("competition", ""), _determine_event_context(match_data.get("competition", ""))),
        "is_event_match": _determine_event_context(match_data.get("competition", "")) != "DOMESTIC_LEAGUE",
    }


def _convert_scan_result_format(new_scan_result, scanner):
    """Convertit le format du nouveau scanner vers l'ancien format attendu par l'API"""
    try:
        # Extraire les données du nouveau format
        raw_anomalies = new_scan_result.get("raw_anomalies", [])
        status_breakdown = new_scan_result.get("status_breakdown", {})
        
        # Créer les matches analysés (ancien format)
        analyzed_matches = []
        remaining_matches = []
        
        # Récupérer tous les matches depuis le provider pour avoir les données complètes
        try:
            all_matches_response = scanner.provider.get_today_matches()
            all_matches = all_matches_response.data if all_matches_response.success else []
        except:
            all_matches = []
        
        # Créer un mapping des IDs de matches analysés
        analyzed_match_ids = set()
        for anomaly in raw_anomalies:
            analyzed_match_ids.add(anomaly.get("fixture_id"))
        
        # Traiter tous les matches
        for match in all_matches:
            match_id = str(match.id)
            
            # Données de base du match
            match_data = {
                "match_id": match_id,
                "home_team": match.home_team.name,
                "away_team": match.away_team.name,
                "home_team_id": str(match.home_team.id),
                "away_team_id": str(match.away_team.id),
                "country": match.competition.country.name if hasattr(match.competition, 'country') and hasattr(match.competition.country, 'name') else "Unknown",
                "competition": match.competition.name,
                "kickoff_time": match.kickoff_time.isoformat() if match.kickoff_time else None,
                "time_display": match.kickoff_time.strftime("%H:%M") if match.kickoff_time else "TBD",
                "status": match.status,
                "is_upcoming": match.status.upper() in ['UPCOMING', 'NS', 'SCHEDULED', 'TBD'],
                "is_live": match.status.upper() in ['LIVE', 'IN_PLAY', 'PAUSED', '1H', '2H', 'HT', 'ET', 'P'],
                "is_finished": match.status.upper() in ['FINISHED', 'FT', 'AET', 'PEN', 'AWARDED', 'WALKOVER'],
                "badge_text": _get_status_badge(match.status)
            }
            
            # Profile (targeting)
            profile = {
                "target_level": "MINOR_TOP_TIER" if match_data["country"] in ["China", "Kazakhstan", "Vietnam", "Ethiopia", "Egypt"] else "STANDARD",
                "target_score": 80.0 if match_data["country"] in ["China", "Kazakhstan", "Vietnam", "Ethiopia", "Egypt"] else 50.0,
                "bookmaker_coverage": {"coverage_score": 0.5, "coverage_level": "MEDIUM"}
            }
            
            # Analysis si le match a été analysé
            analysis = None
            if match_id in analyzed_match_ids:
                # Trouver l'anomalie correspondante
                anomaly = next((a for a in raw_anomalies if a.get("fixture_id") == match_id), None)
                if anomaly:
                    analysis = {
                        "best_edges": [{
                            "market": anomaly.get("market_type", ""),
                            "label": anomaly.get("market_type", ""),
                            "hit_rate": anomaly.get("anomaly_result", {}).get("hit_rate", 0) * 100,
                            "fair_odd": 1 / anomaly.get("anomaly_result", {}).get("hit_rate", 0.5) if anomaly.get("anomaly_result", {}).get("hit_rate", 0.5) > 0 else 0,
                            "sample_size": anomaly.get("anomaly_result", {}).get("sample_size", 0),
                            "confidence": "HIGH",
                            "why": [anomaly.get("anomaly_result", {}).get("pattern_description", "Statistical pattern")]
                        }],
                        "match_profile": {
                            "profile_tags": [anomaly.get("market_type", "")],
                            "interest_score": getattr(anomaly, "interest_score", 75),
                            "confidence_score": getattr(anomaly, "confidence_score", 70),
                            "volatility_score": getattr(anomaly, "volatility_score", 50),
                            "data_quality_score": getattr(anomaly, "data_quality_score", 80)
                        },
                        "statistical_angles": [{
                            "type": anomaly.get("market_type", ""),
                            "confidence": getattr(anomaly, "confidence_score", 70),
                            "description": anomaly.get("anomaly_result", {}).get("pattern_description", "")
                        }]
                    }
            
            # Créer le match au format attendu
            match_entry = {
                "match_data": match_data,
                "profile": profile,
                "analysis": analysis
            }
            
            if analysis:
                analyzed_matches.append(match_entry)
            else:
                remaining_matches.append(match_entry)
        
        # Calculer les totaux
        total_matches = len(all_matches)
        target_count = len([m for m in all_matches if m.status.upper() in ['UPCOMING', 'NS', 'LIVE', 'IN_PLAY', 'PAUSED']])
        analyzed_count = len(analyzed_matches)
        
        return {
            "success": True,
            "total_matches": total_matches,
            "target_count": target_count,
            "analyzed_count": analyzed_count,
            "analyzed_matches": analyzed_matches,
            "remaining_matches": remaining_matches,
            "scan_duration_seconds": 0,
            "status_breakdown": status_breakdown
        }
        
    except Exception as e:
        logger.error(f"Error converting scan result format: {e}")
        # Retourner un format minimal en cas d'erreur
        return {
            "success": False,
            "total_matches": 0,
            "target_count": 0,
            "analyzed_count": 0,
            "analyzed_matches": [],
            "remaining_matches": [],
            "scan_duration_seconds": 0,
            "status_breakdown": {}
        }

def _get_status_badge(status):
    """Convertit le status en badge text"""
    status = status.upper() if status else "UNKNOWN"
    if status in ['UPCOMING', 'NS']:
        return "⏰ UPCOMING"
    elif status in ['LIVE', 'IN_PLAY', 'PAUSED']:
        return "🔴 LIVE"
    elif status in ['FINISHED', 'FT']:
        return "✅ FINISHED"
    elif status in ['CANCELLED', 'POSTPONED']:
        return "❌ CANCELLED"
    else:
        return f"📊 {status}"

def _get_all_matches_from_cache():
    """Récupère tous les matchs (analysés + non analysés) depuis le cache."""
    # Try direct cache first (for testing)
    if cache.get("data") and cache.get("timestamp"):
        data = cache["data"]
        if data.get("scan_result"):
            scan_result = data.get("scan_result", {})
            analyzed = scan_result.get("analyzed_matches", []) or []
            remaining = scan_result.get("remaining_matches", []) or []
            return analyzed + remaining
    
    # Fallback to load_data()
    data = load_data()
    if not data or data.get("manager") is None:
        return []
    scan_result = data.get("scan_result", {})
    analyzed = scan_result.get("analyzed_matches", []) or []
    remaining = scan_result.get("remaining_matches", []) or []
    return analyzed + remaining

def _run_scan_background():
    """Background thread: run scan and warm the cache. Thread-safe."""
    if cache.get("scan_running"):
        return  # already running
    cache["scan_running"] = True
    logger.info("[SCAN] Background scan started")
    try:
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            odds_provider=manager.odds_provider,
        )
        scan_result = scanner.scan_today()
        data = {
            "manager": manager,
            "scanner": scanner,
            "scan_result": scan_result,
            "timestamp": datetime.now()
        }
        cache["data"] = data
        cache["timestamp"] = datetime.now()
        logger.info(f"[SCAN] Background scan done — {scan_result.get('analyzed_count', 0)} matches")
        # ── Auto-persistence (Phase 4) ──────────────────────────────────────
        try:
            repo = _get_repo()
            if repo.supabase_connected:
                all_m = (
                    scan_result.get("analyzed_matches", []) or []
                ) + (
                    scan_result.get("remaining_matches", []) or []
                )
                f_saved = p_saved = o_saved = 0
                for m in all_m:
                    if repo.save_fixture(m):
                        f_saved += 1
                    if m.get("analysis"):
                        if repo.save_prediction(m):
                            p_saved += 1
                        md = m.get("match_data") or m
                        fid = str(md.get("match_id") or md.get("fixture_id") or "")
                        odds = (m.get("analysis") or {}).get("matched_odds", []) or []
                        if odds:
                            o_saved += repo.save_odds_snapshots(fid, odds)
                logger.info(
                    f"[SUPABASE] Persisted: fixtures={f_saved} "
                    f"predictions={p_saved} odds={o_saved}"
                )
        except Exception as _sb_err:
            logger.debug(f"[SUPABASE] Persistence non-blocking: {_sb_err}")
    except Exception as e:
        logger.error(f"[SCAN] Background scan error: {e}")
        import traceback; traceback.print_exc()
    finally:
        cache["scan_running"] = False


def load_data():
    """Retourne le cache immédiatement. Lance un scan en arrière-plan si besoin."""
    import threading
    now = datetime.now()

    # Cache frais → retour immédiat
    if cache.get("data") and cache.get("timestamp"):
        age = (now - cache["timestamp"]).total_seconds()
        if age < 1800:
            logger.info(f"[CACHE] Using cached data (age: {age:.0f}s)")
            return cache["data"]

    # Cache périmé/vide → lancer le scan en background si pas déjà en cours
    if not cache.get("scan_running"):
        logger.info("[CACHE] Cache stale — launching background scan")
        t = threading.Thread(target=_run_scan_background, daemon=True)
        t.start()

    # Si on a des données (même périmées), les retourner pendant le refresh
    if cache.get("data"):
        logger.info("[CACHE] Returning stale data while background scan runs")
        return cache["data"]

    # Premier démarrage : attendre max 5s pour que le scan démarre et retourne qqch
    import time
    for _ in range(10):
        time.sleep(0.5)
        if cache.get("data"):
            return cache["data"]

    # Encore rien → retourner structure vide (scan toujours en cours)
    logger.warning("[CACHE] Scan still running, returning empty structure")
    return {
        "manager": None,
        "scanner": None,
        "scan_result": {
            "success": False,
            "error": "scan_in_progress",
            "total_matches": 0,
            "target_count": 0,
            "analyzed_count": 0,
            "analyzed_matches": [],
            "remaining_matches": []
        },
        "timestamp": now
    }


@app.route('/')
def index():
    """Page principale - Intelligence Dashboard"""
    return render_template('dashboard_intelligence.html')

@app.route('/compact')
def compact_dashboard():
    """Ancien dashboard - Compact Mode"""
    return render_template('dashboard_compact.html')

@app.route('/full')
def full_dashboard():
    """Page complète - Full Mode"""
    return render_template('dashboard.html')


@app.route('/api/data')
def get_data():
    """API pour récupérer les données"""
    try:
        data = load_data()
        
        # Check if data loading failed
        if data.get("manager") is None:
            return jsonify({
                "success": False,
                "error": data["scan_result"].get("error", "Failed to load data"),
                "stats": {
                    "total_matches": 0,
                    "target_count": 0,
                    "analyzed_count": 0,
                    "scan_duration": 0
                },
                "diagnostic": {
                    "awaiting_user_action": 0,
                    "finished_matches": 0,
                    "live_matches": 0,
                    "analyzed": 0
                },
                "categories": {
                    "upcoming_inefficiencies": [],
                    "upcoming_no_value": [],
                    "upcoming_statistical": [],
                    "upcoming_pending": [],
                    "live": [],
                    "finished": []
                },
                "filters": {
                    "countries": [],
                    "regions": [],
                    "value_levels": []
                }
            })
        
        scan_result = data["scan_result"]
        
        # Debug logging
        logger.info(f"Scan result keys: {scan_result.keys() if isinstance(scan_result, dict) else 'NOT A DICT'}")
        logger.info(f"Total matches: {scan_result.get('total_matches', 0)}")
        logger.info(f"Analyzed matches: {len(scan_result.get('analyzed_matches', []))}")
        logger.info(f"Remaining matches: {len(scan_result.get('remaining_matches', []))}")
        
        # Préparer les données pour JSON
        response = {
            "success": True,
            "provider": data["manager"].provider.config.name,
            "is_real_data": data["manager"].is_real_data,
            "timestamp": data["timestamp"].isoformat(),
            "stats": {
                "total_matches":   scan_result.get("total_matches", 0),
                "target_count":    scan_result.get("target_count", 0),
                "analyzed_count":  scan_result.get("analyzed_count", 0),
                "scan_duration":   scan_result.get("scan_duration_seconds", 0),
                # KPI aliases for Lovable (populated after scan)
                "odds_coverage":   scan_result.get("odds_coverage_pct", 0),
                "bettable_count":  scan_result.get("bettable_count", 0),
                "limited_count":   scan_result.get("limited_count", 0),
                "research_count":  scan_result.get("research_count", 0),
            },
            "tracking": {
                "reset_at":             os.environ.get("TRACKING_RESET_AT", "")[:10] or None,
                "report_reset_filter":  bool(os.environ.get("TRACKING_RESET_AT", "").strip()),
            },
            "diagnostic": {
                "awaiting_user_action": 0,
                "finished_matches": 0,
                "live_matches": 0,
                "analyzed": 0
            },
            "categories": {
                "upcoming_inefficiencies": [],
                "upcoming_no_value": [],
                "upcoming_statistical": [],
                "upcoming_pending": [],  # Matchs ciblés mais pas encore analysés
                "live": [],
                "finished": []
            },
            "filters": {
                "countries": set(),
                "regions": set(),
                "value_levels": set()
            }
        }
        
        # Catégoriser les matchs analysés ET non analysés
        all_matches = scan_result.get("analyzed_matches", []) + scan_result.get("remaining_matches", [])
        
        for match in all_matches:
            # Safety checks
            if not isinstance(match, dict):
                continue
            if "match_data" not in match or "profile" not in match:
                continue
                
            match_data = match["match_data"]
            profile = match["profile"]
            analysis = match.get("analysis", {})
            
            # Collecter filtres
            country = match_data.get("country", "")
            response["filters"]["countries"].add(country)
            
            # Fix status - default to upcoming if not set
            is_upcoming = match_data.get("is_upcoming", True)
            is_live = match_data.get("is_live", False)
            is_finished = match_data.get("is_finished", False)
            
            # If all false or status unknown, assume upcoming
            if not (is_upcoming or is_live or is_finished):
                is_upcoming = True
            
            # Determine why not analyzed
            analysis_status = "analyzed" if analysis else "pending"
            not_analyzed_reason = None
            
            if not analysis:
                if is_finished:
                    not_analyzed_reason = "finished_match"
                elif is_live:
                    not_analyzed_reason = "live_match"
                else:
                    not_analyzed_reason = "awaiting_user_action"
            
            # PHASE 7: Structure API propre avec tous les champs requis
            match_info = {
                # Champs de base
                "fixture_id": match_data.get("match_id", ""),
                "home_team": match_data.get("home_team", ""),
                "away_team": match_data.get("away_team", ""),
                "country": country,
                "league": match_data.get("competition", ""),
                "kickoff_time": match_data.get("time_display", "TBD"),
                "status": match_data.get("badge_text", "⏰ UPCOMING"),
                
                # Targeting
                "target_category": profile.get("target_level", ""),
                "analysis_status": analysis_status,
                "skip_reason": not_analyzed_reason,
                
                # Profils (PHASE 4)
                "profile_tags": [],
                
                # Best pick (PHASE 5)
                "best_pick": None,
                
                # Statistical angles
                "statistical_angles": [],
                
                # Scores (PHASE 6)
                "interest_score": 0,
                "confidence_score": 0,
                "volatility_score": 0,
                "data_quality_score": 0,
                
                # Odds status
                "waiting_for_odds": True,
                
                # Champs legacy pour compatibilité
                "home_team_id": match_data.get("home_team_id", ""),
                "away_team_id": match_data.get("away_team_id", ""),
                "is_upcoming": is_upcoming,
                "is_live": is_live,
                "is_finished": is_finished,
                "target_level": profile.get("target_level", ""),
                "target_score": profile.get("target_score", 0),
                "coverage_score": profile.get("bookmaker_coverage", {}).get("coverage_score", 0),
                "coverage_level": profile.get("bookmaker_coverage", {}).get("coverage_level", ""),
                "signals": [],
                "top_value_level": "NO_VALUE",
                "top_priority": 0,
                # EV contract fields (populated below if analysis exists)
                "ev_qualified":              [],
                "ev_rejected":               [],
                "tier_level":                "NO_VALUE",
                "odds_source":               None,
                "ev_quality":                "NO_EV",
                "why_pick":                  [],
                "why_not_pick":              [],
                "risk_factors":              [],
            }
            
            # Ajouter les données d'analyse (PHASE 4-6)
            if analysis:
                # PHASE 4: Profils variés
                match_profile = analysis.get("match_profile", {})
                profile_tags = match_profile.get("profile_tags", [])
                match_info["profile_tags"] = profile_tags
                
                # PHASE 5: Best pick
                best_edges = analysis.get("best_edges", [])
                if best_edges:
                    best_edge = best_edges[0]  # Prendre le meilleur
                    match_info["best_pick"] = {
                        "market": best_edge.get("market", ""),
                        "label": best_edge.get("label", ""),
                        "hit_rate": best_edge.get("hit_rate", 0),
                        "fair_odd": best_edge.get("fair_odd", 0.0),
                        "sample_size": best_edge.get("sample_size", 0),
                        "confidence": best_edge.get("confidence", "MEDIUM"),
                        "why": best_edge.get("why", [])
                    }
                
                # PHASE 6: Scores
                match_info["interest_score"] = match_profile.get("interest_score", 0)
                match_info["confidence_score"] = match_profile.get("confidence_score", 0)
                match_info["volatility_score"] = match_profile.get("volatility_score", 0)
                match_info["data_quality_score"] = match_profile.get("data_quality_score", 0)
                
                # Statistical angles
                statistical_angles = analysis.get("statistical_angles", [])
                match_info["statistical_angles"] = statistical_angles
                
                # Odds status
                match_info["waiting_for_odds"] = not any(edge.get("has_odds", False) for edge in best_edges)
                
                # Multi-market regime fields
                match_info["market_regime"]                 = analysis.get("market_regime")
                match_info["recommended_market_direction"]  = analysis.get("recommended_market_direction")
                match_info["best_market"]                   = analysis.get("best_market")
                match_info["secondary_market"]              = analysis.get("secondary_market")
                match_info["best_over_market"]              = analysis.get("best_over_market")
                match_info["best_under_market"]             = analysis.get("best_under_market")
                match_info["avoid_markets"]                 = analysis.get("avoid_markets", [])
                match_info["recommended_playstyle"]         = analysis.get("recommended_playstyle")
                match_info["offensive_profile"]             = analysis.get("offensive_profile", {})
                match_info["defensive_profile"]             = analysis.get("defensive_profile", {})
                match_info["market_generation_stats"]       = analysis.get("market_generation_stats", {})
                match_info["rejection_reasons_by_market"]   = analysis.get("rejection_reasons_by_market", {})
                # EV Safety Gates — ev_qualified / ev_rejected lists
                match_info["ev_qualified"] = analysis.get("ev_qualified", [])
                match_info["ev_rejected"]  = analysis.get("ev_rejected", [])
                match_info["tier_level"]   = analysis.get("tier_level", "NO_VALUE")
                match_info["odds_source"]  = analysis.get("odds_source")
                _ev_q = analysis.get("ev_qualified") or []
                match_info["ev_quality"]   = _ev_q[0].get("classification", "NO_EV") if _ev_q else "NO_EV"
                # Pick Explainability (Phase 4b)
                _pe = analysis.get("pick_explanation") or {}
                match_info["why_pick"]     = _pe.get("why_pick", [])
                match_info["why_not_pick"] = _pe.get("why_not_s_tier", [])
                match_info["risk_factors"] = _pe.get("risk_factors", [])
                # Bettable Universe
                match_info["market_access"]           = analysis.get("market_access", "RESEARCH_ONLY")
                match_info["bettable_priority_score"] = analysis.get("bettable_priority_score", 0)
                match_info["odds_coverage_score"]     = analysis.get("odds_coverage_score", 0)
                match_info["market_liquidity_score"]  = analysis.get("market_liquidity_score", 0)
                match_info["bettable_tier"]           = analysis.get("bettable_tier")
                # Legacy fields
                match_info["ht_analysis"] = analysis.get("ht_analysis", {})
                match_info["ft_analysis"] = analysis.get("ft_analysis", {})
                match_info["match_history"] = analysis.get("match_history", [])
                match_info["match_profile"] = match_profile
                match_info["best_edges"] = best_edges
                match_info["edge_detection"] = analysis.get("edge_detection", {})
                
                # Ajouter les signaux
                for signal in analysis.get("signals", [])[:2]:
                    value_assessment = signal.get("value_assessment", {})
                    value_level = value_assessment.get("value_level", "NO_VALUE")
                    
                    response["filters"]["value_levels"].add(value_level)
                    
                    signal_info = {
                        "type": signal.get("type", ""),
                        "confidence": signal.get("confidence", 0),
                        "strength": signal.get("strength", ""),
                        "value_level": value_level,
                        "has_odds": value_assessment.get("has_odds", False),
                        "value_gap": value_assessment.get("value_gap"),
                        "priority_score": value_assessment.get("priority_score", 0)
                    }
                    match_info["signals"].append(signal_info)
                    
                    # Garder le meilleur signal
                    if signal_info["priority_score"] > match_info["top_priority"]:
                        match_info["top_priority"] = signal_info["priority_score"]
                        match_info["top_value_level"] = value_level
            
            # Update diagnostic counters
            if match_info["analysis_status"] == "analyzed":
                response["diagnostic"]["analyzed"] += 1
            elif match_info["skip_reason"] == "awaiting_user_action":
                response["diagnostic"]["awaiting_user_action"] += 1
            elif match_info["skip_reason"] == "finished_match":
                response["diagnostic"]["finished_matches"] += 1
            elif match_info["skip_reason"] == "live_match":
                response["diagnostic"]["live_matches"] += 1
            
            # Catégoriser le match
            if match_info["is_live"]:
                response["categories"]["live"].append(match_info)
            elif match_info["is_finished"]:
                response["categories"]["finished"].append(match_info)
            elif match_info["is_upcoming"]:
                # DISCOVERY ENGINE: Si analysé (a un profil), afficher
                if analysis and match_info.get("match_profile"):
                    # Si a des edges, mettre en inefficiencies
                    if match_info.get("best_edges") and len(match_info["best_edges"]) > 0:
                        response["categories"]["upcoming_inefficiencies"].append(match_info)
                    # Sinon mettre en statistical (profil intéressant mais pas d'edge)
                    else:
                        response["categories"]["upcoming_statistical"].append(match_info)
                # Si pas analysé, mettre en pending
                else:
                    response["categories"]["upcoming_pending"].append(match_info)
        
        # PHASE 8: Ajouter status breakdown et données de diagnostic
        if hasattr(scan_result, 'get') and scan_result.get("status_breakdown"):
            response["status_breakdown"] = scan_result["status_breakdown"]
        else:
            response["status_breakdown"] = {
                "upcoming_count": response["diagnostic"]["analyzed"] + response["diagnostic"]["awaiting_user_action"],
                "live_count": response["diagnostic"]["live_matches"],
                "finished_count": response["diagnostic"]["finished_matches"],
                "cancelled_count": 0,
                "target_matches_count": len([m for m in all_matches if m.get("match_data", {}).get("is_upcoming", False) or m.get("match_data", {}).get("is_live", False)]),
                "analyzed_upcoming": len([m for m in response["categories"]["upcoming_inefficiencies"] + response["categories"]["upcoming_statistical"]]),
                "analyzed_live": len([m for m in response["categories"]["live"] if m.get("analysis_status") == "analyzed"]),
                "skipped_finished": response["diagnostic"]["finished_matches"],
                "skipped_cancelled": 0
            }
        
        # PHASE 8: Ajouter données de couverture par pays/ligues
        countries_leagues = {}
        for match in all_matches:
            match_data = match.get("match_data", {})
            country = match_data.get("country", "Unknown")
            league = match_data.get("competition", "Unknown")
            
            if country not in countries_leagues:
                countries_leagues[country] = set()
            countries_leagues[country].add(league)
        
        response["coverage"] = {
            "countries": sorted(countries_leagues.keys()),
            "leagues_by_country": {k: sorted(list(v)) for k, v in countries_leagues.items()},
            "total_countries": len(countries_leagues),
            "total_leagues": sum(len(leagues) for leagues in countries_leagues.values())
        }
        
        # Convertir sets en listes pour JSON
        response["filters"]["countries"] = sorted(list(response["filters"]["countries"]))
        response["filters"]["value_levels"] = sorted(list(response["filters"]["value_levels"]))
        response["filters"]["regions"] = []  # TODO: ajouter détection région
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# NEW CLEAN API ENDPOINTS FOR LOVABLE
# ============================================================================

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """
    Health check endpoint.
    Returns: { status, timestamp, version, data_source, cache_age_seconds }
    Does NOT trigger a data scan — instant response.
    """
    cache_age = None
    if cache["timestamp"]:
        cache_age = (datetime.now() - cache["timestamp"]).total_seconds()

    # Check data_source from cached data WITHOUT loading fresh data
    is_real = False
    if cache.get("data") and cache["data"].get("manager"):
        is_real = getattr(cache["data"]["manager"], "is_real_data", False)

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0-lovable",
        "data_source": "api_football" if is_real else "unknown",
        "cache_age_seconds": round(cache_age, 1) if cache_age is not None else None,
        "cache_active": cache_age is not None and cache_age < 1800,
        "endpoints": [
            "/api/health",
            "/api/dashboard/summary",
            "/api/matches",
            "/api/analyze_match",
            "/api/leagues/coverage",
            "/api/data",
            "/api/refresh"
        ]
    })


@app.route('/api/dashboard/summary', methods=['GET', 'OPTIONS'])
def dashboard_summary():
    """
    Clean dashboard summary for Lovable.
    Returns high-level KPIs only — no match details.
    """
    try:
        data = load_data()

        if data.get("manager") is None:
            return jsonify({
                "success": False,
                "error": "Data loading failed",
                "total_matches": 0,
                "target_matches": 0,
                "analyzed_matches": 0,
                "awaiting_matches": 0,
                "live_matches": 0,
                "finished_matches": 0,
                "opportunities_count": 0,
                "data_source": "unknown",
                "last_refresh": None
            })

        scan_result = data["scan_result"]
        all_raw = (scan_result.get("analyzed_matches", []) or []) + (scan_result.get("remaining_matches", []) or [])

        # Normalize to compute counts
        normalized = [_normalize_match(m) for m in all_raw]

        total = len(normalized)
        target = len(normalized)
        analyzed = sum(1 for m in normalized if m["analyzed"])
        awaiting = total - analyzed
        live = sum(1 for m in normalized if m["status"] == "LIVE")
        finished = sum(1 for m in normalized if m["status"] == "FINISHED")
        opportunities = sum(1 for m in normalized if m["best_angle"]["status"] == "VALUE_DETECTED")

        return jsonify({
            "success": True,
            "total_matches": total,
            "target_matches": target,
            "analyzed_matches": analyzed,
            "awaiting_matches": awaiting,
            "live_matches": live,
            "finished_matches": finished,
            "opportunities_count": opportunities,
            "data_source": "api_football" if data["manager"].is_real_data else "mock",
            "last_refresh": data["timestamp"].isoformat() if data.get("timestamp") else None,
            "is_real_data": data["manager"].is_real_data
        })

    except Exception as e:
        logger.error(f"[API] dashboard_summary error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/matches', methods=['GET', 'OPTIONS'])
def get_matches():
    """
    Clean match list endpoint with filtering.
    Query params:
      - status: upcoming|live|finished|all  (default: all)
      - country: filter by country
      - league: filter by league name
      - confidence: min confidence_score (0-100)
      - profile_type: e.g. LOW_TEMPO, HIGH_SCORING, BTTS_PROFILE
      - analyzed: true|false
      - limit: max results (default 50)
      - offset: pagination offset (default 0)
    """
    try:
        # Parse query params
        status_filter = request.args.get('status', 'all').lower()
        country_filter = request.args.get('country', '').strip()
        league_filter = request.args.get('league', '').strip()
        confidence_min = request.args.get('confidence', type=float)
        profile_type = request.args.get('profile_type', '').strip()
        analyzed_only = request.args.get('analyzed', '').lower()
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        all_raw = _get_all_matches_from_cache()
        if not all_raw:
            return jsonify({
                "success": True,
                "total": 0,
                "returned": 0,
                "matches": []
            })

        # Normalize all
        normalized = [_normalize_match(m) for m in all_raw]

        # Apply filters
        filtered = normalized

        if status_filter != 'all':
            filtered = [m for m in filtered if m["status"].lower() == status_filter]

        if country_filter:
            filtered = [m for m in filtered if m["country"].lower() == country_filter.lower()]

        if league_filter:
            filtered = [m for m in filtered if league_filter.lower() in m["league"].lower()]

        if confidence_min is not None:
            filtered = [m for m in filtered if m["confidence_score"] >= confidence_min]

        if profile_type:
            pt_lower = profile_type.lower()
            filtered = [m for m in filtered if any(pt_lower in tag.lower() for tag in m["profile_tags"])]

        if analyzed_only == 'true':
            filtered = [m for m in filtered if m["analyzed"]]
        elif analyzed_only == 'false':
            filtered = [m for m in filtered if not m["analyzed"]]

        # Sort by interest_score desc, then confidence desc
        filtered.sort(key=lambda m: (m["interest_score"], m["confidence_score"]), reverse=True)

        total = len(filtered)
        paginated = filtered[offset:offset + limit]

        return jsonify({
            "success": True,
            "total": total,
            "returned": len(paginated),
            "offset": offset,
            "limit": limit,
            "matches": paginated
        })

    except Exception as e:
        logger.error(f"[API] get_matches error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/leagues/coverage', methods=['GET', 'OPTIONS'])
def leagues_coverage():
    """
    Returns coverage stats per country and league for the current scan.
    """
    try:
        all_raw = _get_all_matches_from_cache()
        if not all_raw:
            return jsonify({
                "success": True,
                "countries": [],
                "total_leagues": 0,
                "total_matches": 0
            })

        normalized = [_normalize_match(m) for m in all_raw]

        # Group by country then league
        from collections import defaultdict
        country_leagues = defaultdict(lambda: {"leagues": set(), "matches": 0, "analyzed": 0})

        for m in normalized:
            country = m["country"] or "Unknown"
            country_leagues[country]["leagues"].add(m["league"] or "Unknown")
            country_leagues[country]["matches"] += 1
            if m["analyzed"]:
                country_leagues[country]["analyzed"] += 1

        countries = []
        for country, info in sorted(country_leagues.items()):
            # Coverage level heuristic
            analyzed_ratio = info["analyzed"] / info["matches"] if info["matches"] > 0 else 0
            if analyzed_ratio >= 0.8:
                coverage = "FULL"
            elif analyzed_ratio >= 0.5:
                coverage = "PARTIAL"
            else:
                coverage = "MINIMAL"

            # Target type heuristic based on country
            target_type = "MAJOR"
            obscure_keywords = ['ethiopia', 'tanzania', 'uganda', 'zambia', 'zimbabwe', 'botswana',
                                'mozambique', 'namibia', 'lesotho', 'swaziland', 'eswatini',
                                'youth', 'u19', 'u20', 'u21', 'women', 'w-']
            if any(kw in country.lower() for kw in obscure_keywords):
                target_type = "EXTREME_OBSCURE"

            countries.append({
                "country": country,
                "leagues": sorted(list(info["leagues"])),
                "league_count": len(info["leagues"]),
                "matches_today": info["matches"],
                "analyzed_count": info["analyzed"],
                "coverage_level": coverage,
                "target_type": target_type
            })

        return jsonify({
            "success": True,
            "countries": countries,
            "total_leagues": sum(c["league_count"] for c in countries),
            "total_matches": sum(c["matches_today"] for c in countries)
        })

    except Exception as e:
        logger.error(f"[API] leagues_coverage error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/event-mode', methods=['GET'])
def event_mode_status():
    """
    PHASE 6: Event Mode Status Endpoint
    Returns current event mode statistics and status
    """
    try:
        from app.database.supabase_config import get_supabase_config
        from app.database.supabase_repository import get_repository
        
        cfg = get_supabase_config()
        if not cfg.supabase_connected:
            return jsonify({
                "success": False,
                "error": "Supabase not connected",
                "event_mode_available": False
            }), 503
        
        repo = get_repository()
        
        # Get event mode statistics
        try:
            # Query recent predictions with event context
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            
            q = repo._client.table("predictions").select(
                "event_context, event_name, event_phase, is_event_match, status, created_at"
            ).gte("prediction_date", cutoff)
            
            rows = q.execute().data or []
            
            # Calculate statistics
            total_predictions = len(rows)
            event_predictions = [r for r in rows if r.get("is_event_match", False)]
            domestic_predictions = [r for r in rows if not r.get("is_event_match", False)]
            
            # Breakdown by event context
            event_breakdown = {}
            for pred in event_predictions:
                ctx = pred.get("event_context", "UNKNOWN_EVENT")
                if ctx not in event_breakdown:
                    event_breakdown[ctx] = 0
                event_breakdown[ctx] += 1
            
            # Breakdown by event phase
            phase_breakdown = {}
            for pred in event_predictions:
                phase = pred.get("event_phase", "unknown_phase")
                if phase not in phase_breakdown:
                    phase_breakdown[phase] = 0
                phase_breakdown[phase] += 1
            
            # Recent activity (last 7 days)
            recent_cutoff = (date.today() - timedelta(days=7)).isoformat()
            recent_event_predictions = [
                r for r in event_predictions 
                if r.get("created_at", "") >= recent_cutoff or r.get("prediction_date", "") >= recent_cutoff
            ]
            
            # Get upcoming events from matches (same source as /api/matches)
            upcoming_matches = []
            try:
                all_raw_matches = _get_all_matches_from_cache()
                if all_raw_matches:
                    normalized_matches = [_normalize_match(m) for m in all_raw_matches]
                    # Filter for upcoming/live matches that are events
                    upcoming_matches = [
                        m for m in normalized_matches 
                        if m.get("is_event_match", False) and m["status"] in ["UPCOMING", "LIVE"]
                    ]
            except Exception as upcoming_err:
                logger.warning(f"[EVENT-MODE] Could not get upcoming matches: {upcoming_err}")
            
            # Calculate upcoming events statistics
            upcoming_total = len(upcoming_matches)
            upcoming_friendlies = len([m for m in upcoming_matches if m.get("event_context") == "INTERNATIONAL_FRIENDLY"])
            upcoming_youth = len([m for m in upcoming_matches if m.get("event_context") == "YOUTH_TOURNAMENT"])
            upcoming_world_cup = len([m for m in upcoming_matches if m.get("event_context") == "WORLD_CUP"])
            
            # Prepare upcoming events rows
            upcoming_events_rows = []
            for match in upcoming_matches[:50]:  # Limit to 50 for performance
                upcoming_events_rows.append({
                    "fixture_id": match.get("fixture_id"),
                    "home_team": match.get("home_team"),
                    "away_team": match.get("away_team"),
                    "league": match.get("league"),
                    "country": match.get("country"),
                    "kickoff_time": match.get("kickoff_time"),
                    "event_context": match.get("event_context"),
                    "event_name": match.get("event_name"),
                    "event_phase": match.get("event_phase"),
                    "is_event_match": match.get("is_event_match"),
                    "has_odds": match.get("has_odds", False),
                    "best_ev_opportunity": match.get("best_ev_opportunity")
                })
            
            return jsonify({
                "success": True,
                "event_mode_available": True,
                "statistics": {
                    "total_predictions_last_30_days": total_predictions,
                    "event_predictions": len(event_predictions),
                    "domestic_predictions": len(domestic_predictions),
                    "event_prediction_percentage": round(len(event_predictions) / total_predictions * 100, 1) if total_predictions > 0 else 0,
                    "recent_event_predictions_7_days": len(recent_event_predictions)
                },
                "event_breakdown": event_breakdown,
                "event_phase_breakdown": phase_breakdown,
                "detected_events": list(set(r.get("event_name", "Unknown") for r in event_predictions)),
                "sample_predictions": [
                    {
                        "event_context": r.get("event_context"),
                        "event_name": r.get("event_name"),
                        "event_phase": r.get("event_phase"),
                        "status": r.get("status"),
                        "created_at": r.get("created_at")
                    }
                    for r in recent_event_predictions[:10]
                ],
                "upcoming_events": {
                    "total": upcoming_total,
                    "international_friendlies": upcoming_friendlies,
                    "youth_tournaments": upcoming_youth,
                    "world_cup": upcoming_world_cup,
                    "rows": upcoming_events_rows
                }
            })
            
        except Exception as e:
            logger.error(f"[EVENT-MODE] Error querying event statistics: {e}")
            return jsonify({
                "success": False,
                "error": f"Database error: {str(e)}",
                "event_mode_available": False
            }), 500
            
    except Exception as e:
        logger.error(f"[EVENT-MODE] Unexpected error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "event_mode_available": False
        }), 500


# ============================================================================
# LEGACY / INTERNAL ENDPOINTS (kept for existing dashboard)
# ============================================================================

@app.route('/api/refresh')
def refresh():
    """Force le rechargement des données"""
    cache["data"] = None
    cache["timestamp"] = None
    return jsonify({"success": True, "message": "Cache cleared"})


@app.route('/api/test-live-scores')
def test_live_scores():
    """Test endpoint for live scores - temporary"""
    try:
        from app.providers.data_source_manager import DataSourceManager
        from app.services.scanner.smart_scanner import SmartScanner
        
        # Create manager and scanner
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            odds_provider=manager.odds_provider,
        )
        
        # Run scan
        scan_result = scanner.scan_today()
        
        analyzed_matches = scan_result.get('analyzed_matches', [])
        remaining_matches = scan_result.get('remaining_matches', [])
        all_matches = analyzed_matches + remaining_matches
        
        # Find live matches
        live_matches = [m for m in all_matches if m.get('match_data', {}).get('is_live')]
        
        # Normalize live matches
        normalized_live = [_normalize_match(m) for m in live_matches]
        
        return jsonify({
            "success": True,
            "total_matches": len(all_matches),
            "live_matches": len(live_matches),
            "sample_live_match": normalized_live[0] if normalized_live else None,
            "all_live_matches": normalized_live[:5]  # First 5 for testing
        })
        
    except Exception as e:
        logger.error(f"[API] test_live_scores error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _build_analyze_response(fixture_id, analysis=None, bundle=None, errors=None, status="ERROR"):
    """
    Build a STABLE, CLEAN response for POST /api/analyze_match.
    Same schema regardless of data quality or analysis status.
    """
    # Default empty structures
    match_profile = {
        "profile_tags": [],
        "interest_score": 0,
        "confidence_score": 0,
        "volatility_score": 0,
        "sample_size": 0,
        "summary": "No analysis available"
    }
    top_angles = []
    ht_rows = []
    ft_rows = []
    recent_history = []
    h2h_list = []
    warnings = []
    errors_out = errors or []
    data_origin = "REAL"

    if bundle:
        data_origin = "REAL"
        warnings = bundle.warnings or []
        errors_out = bundle.errors or []

    if analysis:
        mp = analysis.get("match_profile", {})
        if mp and mp.get("tempo_profile") != "UNKNOWN":
            tags = []
            tags.extend(mp.get("specific_profiles", []))
            tags.extend(mp.get("characteristics", []))
            if mp.get("tempo_profile"):
                tags.append(mp["tempo_profile"])
            if mp.get("scoring_profile"):
                tags.append(mp["scoring_profile"])

            match_profile = {
                "profile_tags": list(set(tags)),
                "interest_score": round(mp.get("interest_score", 0), 1),
                "confidence_score": round(mp.get("confidence_score", 0), 1),
                "volatility_score": round(mp.get("volatility_score", 0), 1),
                "sample_size": mp.get("sample_size", 0),
                "summary": f"{mp.get('tempo_profile', 'UNKNOWN').replace('_', ' ')} | {mp.get('scoring_profile', 'UNKNOWN').replace('_', ' ')} | Interest {mp.get('interest_score', 0):.0f}/100"
            }

        # Build top_angles from best_edges + signals
        edges = analysis.get("best_edges", [])
        signals = analysis.get("signals", [])

        # Edges first (value bets)
        for edge in edges[:3]:
            top_angles.append({
                "market": edge.get("market", ""),
                "label": edge.get("market", "").replace("_", " "),
                "hit_rate": round((edge.get("hit_rate", 0) or 0) * 100, 1),
                "fair_odd": edge.get("fair_odd"),
                "sample_size": edge.get("sample_size", 0),
                "confidence": edge.get("confidence", "UNKNOWN"),
                "edge_percent": round((edge.get("edge_percent", 0) or 0) * 100, 1),
                "why": edge.get("reasons", []) or []
            })

        # Then signals (statistical angles)
        for sig in signals[:2]:
            top_angles.append({
                "market": sig.get("type", ""),
                "label": (sig.get("suggested_markets", [])+[sig.get("type", "")])[0].replace("_", " "),
                "hit_rate": round((sig.get("confidence", 0) or 0) * 100, 1),
                "fair_odd": sig.get("fair_odds", {}).get("fair_odd") if sig.get("fair_odds") else None,
                "sample_size": sig.get("sample_size", 0),
                "confidence": sig.get("strength", "UNKNOWN"),
                "edge_percent": 0.0,
                "why": sig.get("reasons", []) or []
            })

        # HT / FT tables cleaned
        ht = analysis.get("ht_analysis", {})
        ft = analysis.get("ft_analysis", {})
        ht_rows = ht.get("table", []) or []
        ft_rows = ft.get("table", []) or []

        # Recent history
        mh = analysis.get("match_history", [])
        recent_history = [
            {
                "match_number": m.get("match_number", i+1),
                "total_goals": m.get("total_goals"),
                "ht_goals": m.get("ht_goals")
            }
            for i, m in enumerate(mh[:10])
        ]

        # H2H from debug if available
        debug = analysis.get("debug", {})
        if debug:
            data_origin = debug.get("data_origin", "REAL")
            h2h_count = debug.get("h2h_count", 0)
            if h2h_count > 0:
                h2h_list = [f"H2H match {i+1}" for i in range(min(h2h_count, 5))]
            warnings = debug.get("warnings", []) or []
            errors_out = debug.get("errors", []) or []

    return {
        "fixture_id": str(fixture_id),
        "data_origin": data_origin,
        "analysis_status": status,
        "match_profile": match_profile,
        "top_angles": top_angles,
        "ht_analysis": ht_rows,
        "ft_analysis": ft_rows,
        "recent_history": recent_history,
        "h2h": h2h_list,
        "warnings": warnings,
        "errors": errors_out
    }


@app.route('/api/analyze_match', methods=['POST', 'OPTIONS'])
def analyze_match_on_demand():
    """
    PHASE 1-9 V2: Analyze a specific match on demand.
    Since analysis is now automatic, this endpoint:
    1. Forces a cache refresh
    2. Returns updated match data
    3. Maintains compatibility with front-end expectations
    """
    try:
        from flask import request
        
        req_data = request.get_json() or {}
        fixture_id = req_data.get('fixture_id')
        
        logger.info(f"[ANALYZE V2] fixture_id={fixture_id}")
        
        if not fixture_id:
            return jsonify({
                "success": False,
                "error": "Missing required field: fixture_id"
            }), 400

        # Force cache refresh to get latest data
        logger.info(f"[ANALYZE V2] Forcing cache refresh...")
        global cache
        cache["data"] = None
        cache["timestamp"] = None
        
        # Load fresh data
        fresh_data = load_data()
        
        # Find the specific match in the fresh data
        target_match = None
        all_matches = []
        
        # Check analyzed matches
        for match in fresh_data["scan_result"].get("analyzed_matches", []):
            match_data = match.get("match_data", {})
            if match_data.get("fixture_id") == str(fixture_id):
                target_match = match
                break
            all_matches.append(match_data)
        
        # Check remaining matches if not found
        if not target_match:
            for match in fresh_data["scan_result"].get("remaining_matches", []):
                match_data = match.get("match_data", {})
                if match_data.get("fixture_id") == str(fixture_id):
                    target_match = match
                    break
                all_matches.append(match_data)
        
        if not target_match:
            return jsonify({
                "success": False,
                "error": f"Match {fixture_id} not found in current data",
                "fixture_id": fixture_id
            }), 404
        
        # Build V2 compatible response
        match_data = target_match.get("match_data", {})
        analysis = target_match.get("analysis", {})
        
        # Determine analysis status
        if analysis:
            status = "ANALYZED"
            if match_data.get("waiting_for_odds", False):
                status = "ANALYZABLE_NO_ODDS"
        else:
            status = "PENDING"
        
        # Build response in expected format
        response = {
            "success": True,
            "fixture_id": fixture_id,
            "status": status,
            "match_data": match_data,
            "analysis": analysis,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": f"Match {fixture_id} analysis refreshed"
        }
        
        # Add V2 fields if available
        if analysis:
            response.update({
                "interest_score": analysis.get("interest_score", 0),
                "confidence_score": analysis.get("confidence_score", 0),
                "volatility_score": analysis.get("volatility_score", 0),
                "data_quality_score": analysis.get("data_quality_score", 0),
                "profile_tags": analysis.get("profile_tags", []),
                "best_pick": analysis.get("best_pick", {}),
                "statistical_angles": analysis.get("statistical_angles", [])
            })
        
        logger.info(f"[ANALYZE V2] Success: {fixture_id} -> {status}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"[ANALYZE V2] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "fixture_id": req_data.get('fixture_id', 'unknown'),
            "status": "ERROR",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500


@app.route('/api/analyze/<match_id>', methods=['POST'])
def analyze_match_legacy(match_id):
    """Legacy endpoint - redirects to new endpoint"""
    try:
        data = load_data()
        scan_result = data["scan_result"]
        
        # Find match in all_matches
        all_matches = scan_result.get("analyzed_matches", []) + scan_result.get("remaining_matches", [])
        
        target_match = None
        for match in all_matches:
            match_data = match["match_data"]
            if match_data.get("match_id") == match_id or \
               f"{match_data.get('home_team')}_vs_{match_data.get('away_team')}" == match_id:
                target_match = match
                break
        
        if not target_match:
            return jsonify({
                "success": False,
                "error": "Match not found"
            }), 404
        
        # If already analyzed, return existing analysis
        if target_match.get("analysis"):
            return jsonify({
                "success": True,
                "match_id": match_id,
                "analysis": target_match["analysis"],
                "message": "Analysis already available"
            })
        
        # TODO: Fetch real historical data from provider
        # For now, return message that analysis is pending
        return jsonify({
            "success": False,
            "match_id": match_id,
            "message": "On-demand analysis not yet implemented. Real historical data fetch required.",
            "status": "pending_implementation"
        }), 501
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/ev', methods=['POST'])
def calculate_ev():
    """
    Phase 7: Calculate EV for a market.

    Body JSON:
    {
        "model_probability": 0.72,
        "bookmaker_odd": 1.85,
        "market_type": "FT_UNDER_2_5",
        "line": 2.5,
        "sample_size": 30,
        "bookmaker": "Bet365",
        "signal_type": "FT_UNDER"
    }
    """
    try:
        from app.services.analysis.ev_calculator import EVCalculator
        body = request.get_json() or {}

        model_prob = float(body.get("model_probability", 0))
        bk_odd = float(body.get("bookmaker_odd", 0))

        if not model_prob or not bk_odd:
            return jsonify({"success": False, "error": "model_probability and bookmaker_odd required"}), 400

        calc = EVCalculator()
        result = calc.calculate(
            model_probability=model_prob,
            bookmaker_odd=bk_odd,
            market_type=body.get("market_type", "UNKNOWN"),
            line=body.get("line"),
            sample_size=int(body.get("sample_size", 0)),
            bookmaker=body.get("bookmaker", "unknown"),
            signal_type=body.get("signal_type", "")
        )

        if not result:
            return jsonify({"success": False, "error": "Could not compute EV (invalid inputs)"}), 400

        return jsonify({"success": True, "ev": result.to_dict()})

    except Exception as e:
        logger.error(f"EV calculation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/backtest', methods=['GET'])
def run_backtest():
    """
    Phase 8: Run backtest on today's analyzed matches history.

    Query params:
    - min_confidence: float (default 0.65)
    - market: filter to specific market (optional)
    """
    try:
        from app.services.analysis.backtesting_engine import BacktestingEngine

        min_conf = float(request.args.get("min_confidence", 0.65))
        market_filter = request.args.get("market")

        data = load_data()
        scan_result = data.get("scan_result", {})
        analyzed = scan_result.get("analyzed_matches", [])

        if not analyzed:
            return jsonify({
                "success": True,
                "message": "No analyzed matches available for backtesting",
                "summaries": {}
            })

        engine = BacktestingEngine()

        # STEP 6: Use run_from_analyzed_matches for richer breakdown
        # (by_volatility, by_profile, drawdown)
        summaries_raw = engine.run_from_analyzed_matches(
            analyzed_matches=analyzed,
            min_confidence=min_conf,
        )

        # Fallback: build records from match_history if no results
        if not summaries_raw:
            all_records = []
            for item in analyzed:
                match_data = item.get("match_data", {})
                analysis   = item.get("analysis", {}) or {}
                league  = match_data.get("competition", match_data.get("league", "Unknown"))
                country = match_data.get("country", "Unknown")
                history = analysis.get("match_history", [])
                if history:
                    records = engine.build_records_from_history(history, league=league, country=country)
                    all_records.extend(records)
            if not all_records:
                return jsonify({
                    "success": True,
                    "message": "Insufficient historical data for backtesting",
                    "total_records": 0,
                    "summaries": {}
                })
            summaries_raw = engine.run(all_records, min_confidence=min_conf)

        total_records = sum(s.total_bets for s in summaries_raw.values())

        # Filter by market if requested
        if market_filter:
            summaries_raw = {k: v for k, v in summaries_raw.items() if market_filter.upper() in k}

        summaries = {k: v.to_dict() for k, v in summaries_raw.items()}

        # Sort by ROI descending for compact view
        sorted_markets = sorted(summaries.items(), key=lambda x: -x[1].get("simulated_roi", 0))

        return jsonify({
            "success": True,
            "total_records": total_records,
            "total_markets": len(summaries),
            "min_confidence": min_conf,
            "summaries": dict(sorted_markets),
            "text_report": engine.report_text(summaries_raw)
        })

    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/diagnostics', methods=['GET', 'OPTIONS'])
def get_diagnostics():
    """
    Phase 12 — Full system diagnostics (unified).
    Returns all counters, odds API status, quota, fixture scan stats,
    bettable universe counts, and EV opportunity totals.
    Does NOT trigger a new scan.
    """
    try:
        from app.config.data_source_config import DataSourceConfig

        cfg = DataSourceConfig()
        # Read from cache only — NEVER trigger a new scan
        cached_data = cache.get("data") or {}
        scan_result = cached_data.get("scan_result", {}) or {}
        manager = cached_data.get("manager")

        # Count all match categories
        analyzed = scan_result.get("analyzed_matches", []) or []
        remaining = scan_result.get("remaining_matches", []) or []
        all_matches = analyzed + remaining

        total_upcoming = sum(
            1 for m in all_matches
            if m.get("match_data", {}).get("is_upcoming", False)
        )
        total_live = sum(
            1 for m in all_matches
            if m.get("match_data", {}).get("is_live", False)
        )
        total_finished = sum(
            1 for m in all_matches
            if m.get("match_data", {}).get("is_finished", False)
        )

        # EV counters from analyzed matches
        total_ev_detected = 0
        total_watchlist = 0
        s_tier = 0
        a_tier = 0

        for item in analyzed:
            a = item.get("analysis", {}) or {}
            tl = a.get("tier_level", "")
            if tl == "S_TIER":
                s_tier += 1
            elif tl == "A_TIER":
                a_tier += 1
            elif tl == "WATCHLIST":
                total_watchlist += 1
            ev_opps = a.get("ev_opportunities", []) or []
            if ev_opps:
                total_ev_detected += 1

        # Odds provider diagnostics
        odds_diag = {}
        if manager and hasattr(manager, '_odds_provider') and manager._odds_provider:
            op = manager._odds_provider
            if hasattr(op, 'get_diagnostics'):
                odds_diag = op.get_diagnostics()
        if not odds_diag:
            odds_diag = {
                "odds_api_key_present": cfg.odds_key_present,
                "odds_api_status": cfg.odds_status,
                "odds_events_found": 0,
                "sports_loaded": 0,
                "mapping_success_count": 0,
                "mapping_failed_count": 0,
                "bookmakers_available": [],
                "markets_available": [],
                "api_quota_remaining": None,
            }

        # Bettable universe counts from scan cache
        bettable_count  = 0
        limited_count   = 0
        research_count  = 0
        fixtures_with_odds = 0
        for m in all_matches:
            if not isinstance(m, dict):
                continue
            _an = m.get("analysis") or {}
            _ac = _an.get("market_access", "RESEARCH_ONLY")
            if _ac == "BETTABLE":
                bettable_count += 1
            elif _ac == "LIMITED_BETTABLE":
                limited_count += 1
            else:
                research_count += 1
            if bool(_an.get("odds_count", 0) or _an.get("matched_odds")):
                fixtures_with_odds += 1

        total_scan = len(all_matches)
        # odds_coverage: prefer live provider value, fall back to computed
        _raw_cov = odds_diag.get("coverage_apifootball", 0.0) or odds_diag.get("coverage_oddsapi", 0.0)
        odds_coverage_pct = _raw_cov if _raw_cov else (
            round(fixtures_with_odds / total_scan * 100, 1) if total_scan else 0.0
        )
        ev_eligible_fixtures = fixtures_with_odds  # all fixtures with odds are EV-eligible

        # Cache info
        cache_age = None
        if cache.get("timestamp"):
            cache_age = round((datetime.now() - cache["timestamp"]).total_seconds(), 1)

        return jsonify({
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # Data source
            "data_source": cfg.to_dict(),
            # Odds API provider details (Phase 5)
            **odds_diag,
            # Fixture scan
            "total_fixtures_scanned": total_scan,
            "total_upcoming": total_upcoming,
            "total_live": total_live,
            "total_finished": total_finished,
            "total_analyzed": len(analyzed),
            # EV / Tiers
            "total_ev_detected": total_ev_detected,
            "total_s_tier": s_tier,
            "total_a_tier": a_tier,
            "total_watchlist": total_watchlist,
            # Bettable universe (top-level aliases — used by Lovable dashboard)
            "fixtures_today":        total_scan,
            "fixtures_with_odds":    fixtures_with_odds,
            "ev_eligible_fixtures":  ev_eligible_fixtures,
            "odds_coverage":         odds_coverage_pct,
            "bettable_count":        bettable_count,
            "limited_count":         limited_count,
            "research_count":        research_count,
            # ev_opportunities is per-match; total here for KPI cards
            "ev_opportunities":      total_ev_detected,
            # Cache
            "cache_age_seconds": cache_age,
        })

    except Exception as e:
        logger.error(f"[DIAGNOSTICS] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ─── Phase 8 — Performance + Prediction History API ─────────────────────────

@app.route("/api/performance/summary")
def api_performance_summary():
    try:
        from app.database.supabase_repository import _parse_reset_at
        days        = int(request.args.get("days", 30))
        _auto_sr    = "1" if os.environ.get("TRACKING_RESET_AT", "").strip() else "0"
        since_reset = request.args.get("since_reset", _auto_sr).lower() in ("true", "1", "yes")
        since_date  = _parse_reset_at() if since_reset else request.args.get("since_date", "")
        repo = _get_repo()
        cfg  = _get_sb_cfg()
        return jsonify({
            "success":    True,
            **cfg.to_dict(),
            "tracking_reset_at":    since_date or None,
            "report_reset_filter":  bool(since_date),
            "performance": repo.get_performance_summary(days=days, since_date=since_date),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/performance/by-league")
def api_performance_by_league():
    try:
        from app.database.supabase_repository import _parse_reset_at
        league      = request.args.get("league", "")
        limit       = int(request.args.get("limit", 50))
        _auto_sr    = "1" if os.environ.get("TRACKING_RESET_AT", "").strip() else "0"
        since_reset = request.args.get("since_reset", _auto_sr).lower() in ("true", "1", "yes")
        since_date  = _parse_reset_at() if since_reset else request.args.get("since_date", "")
        repo        = _get_repo()
        return jsonify({
            "success":   True,
            "is_ready":  repo.supabase_connected,
            "since_date": since_date or None,
            "leagues":   repo.get_league_profitability(league=league, limit=limit, since_date=since_date),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/performance/by-market")
def api_performance_by_market():
    try:
        from app.database.supabase_repository import _parse_reset_at
        _auto_sr    = "1" if os.environ.get("TRACKING_RESET_AT", "").strip() else "0"
        since_reset = request.args.get("since_reset", _auto_sr).lower() in ("true", "1", "yes")
        since_date  = _parse_reset_at() if since_reset else request.args.get("since_date", "")
        repo        = _get_repo()
        return jsonify({
            "success":   True,
            "is_ready":  repo.supabase_connected,
            "since_date": since_date or None,
            "markets":   repo.get_market_performance(since_date=since_date),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/performance/by-tier")
def api_performance_by_tier():
    try:
        from app.database.supabase_repository import _parse_reset_at
        _auto_sr    = "1" if os.environ.get("TRACKING_RESET_AT", "").strip() else "0"
        since_reset = request.args.get("since_reset", _auto_sr).lower() in ("true", "1", "yes")
        since_date  = _parse_reset_at() if since_reset else request.args.get("since_date", "")
        repo        = _get_repo()
        return jsonify({
            "success":   True,
            "is_ready":  repo.supabase_connected,
            "since_date": since_date or None,
            "tiers":     repo.get_tier_performance(since_date=since_date),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/predictions/history")
def api_predictions_history():
    try:
        from app.database.supabase_repository import _parse_reset_at
        limit       = int(request.args.get("limit", 100))
        status      = request.args.get("status", "")
        _auto_sr    = "1" if os.environ.get("TRACKING_RESET_AT", "").strip() else "0"
        since_reset = request.args.get("since_reset", _auto_sr).lower() in ("true", "1", "yes")
        since_date  = _parse_reset_at() if since_reset else request.args.get("since_date", "")
        repo        = _get_repo()
        return jsonify({
            "success":     True,
            "is_ready":    repo.supabase_connected,
            "since_date":  since_date or None,
            "predictions": repo.get_prediction_history(limit=limit, status=status, since_date=since_date),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/predictions/pending")
def api_predictions_pending():
    try:
        from app.database.supabase_repository import _parse_reset_at
        
        # Parse POST_RESET filtering parameters
        tracking_reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()
        _auto_sr    = "1" if tracking_reset_at else "0"
        since_reset = request.args.get("since_reset", _auto_sr).lower() in ("true", "1", "yes")
        since_date  = None
        
        if since_reset and tracking_reset_at:
            since_date = _parse_reset_at()
        elif not since_reset:
            # Only use explicit since_date when since_reset is false
            explicit_since_date = request.args.get("since_date", "").strip()
            if explicit_since_date:
                since_date = explicit_since_date
        
        repo = _get_repo()
        preds = repo.get_pending_predictions(limit=200, since_date=since_date)
        
        return jsonify({
            "success":     True,
            "is_ready":    repo.supabase_connected,
            "since_date":  since_date or None,
            "post_reset_filter": bool(since_date),
            "count":       len(preds),
            "pending":     preds,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ─── Phases 9+10 — Pipeline trigger endpoints ────────────────────────────────

@app.route("/api/pipeline/refresh", methods=["POST"])
def api_pipeline_refresh():
    """Phase 9: Trigger a full refresh (scan + persist). Non-blocking response."""
    try:
        from app.pipelines.refresh_pipeline import RefreshPipeline
        data = cache.get("data")
        if not data:
            return jsonify({"success": False, "error": "No scan data in cache yet"}), 400
        scanner = data.get("scanner")
        repo    = _get_repo()
        pipeline = RefreshPipeline(scanner=scanner, repository=repo)
        result   = pipeline.run()
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error(f"[API] /api/pipeline/refresh: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/pipeline/settle", methods=["POST"])
def api_pipeline_settle():
    """Phase 10: Trigger settlement for all pending predictions."""
    try:
        from app.pipelines.settlement_pipeline import SettlementPipeline
        data    = cache.get("data")
        provider = data.get("manager") if data else None
        repo    = _get_repo()
        pipeline = SettlementPipeline(repository=repo, provider=provider)
        result   = pipeline.run()
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error(f"[API] /api/pipeline/settle: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ─── Phase 6 — Error Analysis API ───────────────────────────────────────────

@app.route("/api/error-analysis")
def api_error_analysis():
    """Phase 1-3: Full error analysis report — failure reasons, FP leagues, dangerous markets."""
    try:
        eae = _get_eae()
        return jsonify({
            "success":  True,
            **eae.get_error_analysis_report(),
        })
    except Exception as e:
        logger.error(f"[API] /api/error-analysis: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/false-positives")
def api_false_positives():
    """Phase 2: False positive pattern database, filterable by league/market."""
    try:
        league = request.args.get("league", "")
        market = request.args.get("market", "")
        min_occ = int(request.args.get("min_occurrences", 1))
        eae = _get_eae()
        patterns = eae.get_false_positive_table(league=league, market=market)
        patterns = [p for p in patterns if p["occurrence_count"] >= min_occ]
        return jsonify({
            "success":          True,
            "is_ready":         eae.is_ready,
            "total_patterns":   len(patterns),
            "patterns":         patterns,
            "summary":          eae.summary(),
        })
    except Exception as e:
        logger.error(f"[API] /api/false-positives: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/risk-patterns")
def api_risk_patterns():
    """Phase 3+4: Top failure reasons, dangerous leagues, dangerous markets, penalties."""
    try:
        top = int(request.args.get("top", 10))
        eae = _get_eae()
        return jsonify({
            "success":               True,
            "is_ready":              eae.is_ready,
            "top_failure_reasons":   eae.top_failure_reasons(top),
            "top_fp_leagues":        eae.top_false_positive_leagues(top),
            "top_dangerous_markets": eae.top_dangerous_markets(top),
            "all_patterns":          eae.get_all_patterns(min_occurrences=2),
        })
    except Exception as e:
        logger.error(f"[API] /api/risk-patterns: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ─── Phase 7 — League Specialization API ─────────────────────────────────────

@app.route("/api/league-profitability")
def api_league_profitability():
    """Phase 1+2: Full profitability matrix + league rankings."""
    try:
        min_s = int(request.args.get("min_sample", 3))
        lse = _get_lse()
        return jsonify({
            "success":       True,
            "is_ready":      lse.is_ready,
            "summary":       lse.summary(),
            "matrix":        lse.get_profitability_matrix(min_sample=min_s),
            "league_rankings": lse.get_league_rankings(min_sample=min_s),
        })
    except Exception as e:
        logger.error(f"[API] /api/league-profitability: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/best-markets")
def api_best_markets():
    """Phase 2+3: Best-performing markets across all leagues."""
    try:
        top = int(request.args.get("top", 10))
        lse = _get_lse()
        rankings = lse.get_league_rankings()
        best_per_league = [
            {"league": r["league"], "country": r["country"],
             "best_markets": r["best_markets"], "overall_roi": r["overall_roi"]}
            for r in rankings if r["best_markets"]
        ]
        return jsonify({
            "success":          True,
            "is_ready":         lse.is_ready,
            "best_markets_global": lse.get_best_markets(top_n=top),
            "best_per_league":  best_per_league[:20],
        })
    except Exception as e:
        logger.error(f"[API] /api/best-markets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/worst-markets")
def api_worst_markets():
    """Phase 2+5: Worst-performing markets and danger report."""
    try:
        top = int(request.args.get("top", 10))
        lse = _get_lse()
        rankings = lse.get_league_rankings()
        worst_per_league = [
            {"league": r["league"], "country": r["country"],
             "worst_markets": r["worst_markets"], "overall_roi": r["overall_roi"]}
            for r in rankings if r["worst_markets"]
        ]
        return jsonify({
            "success":           True,
            "is_ready":          lse.is_ready,
            "worst_markets_global": lse.get_worst_markets(top_n=top),
            "worst_per_league":  worst_per_league[:20],
            "danger_report":     lse.get_danger_report(),
        })
    except Exception as e:
        logger.error(f"[API] /api/worst-markets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/bettable-universe", methods=["GET", "OPTIONS"])
def api_bettable_universe():
    """Bettable Universe — coverage breakdown and prioritised league lists."""
    try:
        from collections import defaultdict
        from app.services.universe.bettable_classifier import (
            BETTABLE_COUNTRIES, RESEARCH_ONLY_COUNTRIES,
        )

        data = load_data()
        scan_result = data.get("scan_result") or {}
        all_matches = (
            scan_result.get("analyzed_matches", [])
            + scan_result.get("remaining_matches", [])
        )

        access_counts  = defaultdict(int)
        league_stats   = defaultdict(lambda: {"count": 0, "bettable": 0, "has_odds": 0,
                                               "prio_sum": 0, "coverage_sum": 0})
        country_stats  = defaultdict(lambda: {"count": 0, "bettable": 0, "has_odds": 0})
        bettable_rows  = []
        research_rows  = []

        for m in all_matches:
            if not isinstance(m, dict):
                continue
            md  = m.get("match_data", {})
            an  = m.get("analysis") or {}
            access = an.get("market_access", "RESEARCH_ONLY")
            prio   = an.get("bettable_priority_score", 0)
            cov    = an.get("odds_coverage_score", 0)
            has_o  = bool(an.get("odds_count", 0) or an.get("matched_odds"))
            league  = md.get("competition") or md.get("league", "")
            country = md.get("country", "")

            access_counts[access] += 1
            ls = league_stats[league]
            ls["count"] += 1
            ls["bettable"] += 1 if access == "BETTABLE" else 0
            ls["has_odds"] += 1 if has_o else 0
            ls["prio_sum"] += prio
            ls["coverage_sum"] += cov

            cs = country_stats[country]
            cs["count"] += 1
            cs["bettable"] += 1 if access == "BETTABLE" else 0
            cs["has_odds"] += 1 if has_o else 0

            row = {
                "fixture_id":             md.get("match_id"),
                "home_team":              md.get("home_team"),
                "away_team":              md.get("away_team"),
                "league":                 league,
                "country":                country,
                "kickoff_time":           md.get("time_display"),
                "market_access":          access,
                "bettable_priority_score": prio,
                "odds_coverage_score":    cov,
                "market_liquidity_score": an.get("market_liquidity_score", 0),
                "bettable_tier":          an.get("bettable_tier"),
                "best_market":            an.get("best_market"),
                "market_regime":          an.get("market_regime"),
                "statistical_tier":       an.get("statistical_tier"),
                "has_odds":               has_o,
            }
            if access == "BETTABLE":
                bettable_rows.append(row)
            else:
                research_rows.append(row)

        # League summary
        league_summary = sorted(
            [
                {
                    "league":         lg,
                    "matches":        s["count"],
                    "bettable":       s["bettable"],
                    "has_odds":       s["has_odds"],
                    "odds_pct":       round(s["has_odds"] / s["count"] * 100, 1) if s["count"] else 0,
                    "avg_priority":   round(s["prio_sum"] / s["count"], 1) if s["count"] else 0,
                    "avg_coverage":   round(s["coverage_sum"] / s["count"], 1) if s["count"] else 0,
                }
                for lg, s in league_stats.items()
            ],
            key=lambda x: (-x["has_odds"], -x["avg_priority"]),
        )

        # Country summary
        country_summary = sorted(
            [
                {
                    "country":    c,
                    "matches":    s["count"],
                    "bettable":   s["bettable"],
                    "has_odds":   s["has_odds"],
                    "odds_pct":   round(s["has_odds"] / s["count"] * 100, 1) if s["count"] else 0,
                }
                for c, s in country_stats.items()
            ],
            key=lambda x: (-x["has_odds"], -x["matches"]),
        )

        total = sum(access_counts.values()) or 1
        # top-level KPI aliases for Lovable dashboard direct binding
        _bettable_n  = access_counts.get("BETTABLE", 0)
        _limited_n   = access_counts.get("LIMITED_BETTABLE", 0)
        _research_n  = access_counts.get("RESEARCH_ONLY", 0)
        _total_n     = total
        _odds_pct    = round(sum(s["has_odds"] for s in league_stats.values()) / _total_n * 100, 1) if _total_n else 0.0
        return jsonify({
            "success":           True,
            "timestamp":         datetime.now(timezone.utc).isoformat(),
            # Top-level KPI aliases (Lovable direct binding)
            "total_matches":     _total_n,
            "bettable_count":    _bettable_n,
            "limited_count":     _limited_n,
            "research_count":    _research_n,
            "odds_coverage":     _odds_pct,
            # Detailed breakdown
            "universe_breakdown": {
                k: {"count": v, "pct": round(v / total * 100, 1)}
                for k, v in access_counts.items()
            },
            "bettable_matches":  sorted(bettable_rows, key=lambda x: -x["bettable_priority_score"])[:50],
            "research_matches":  len(research_rows),
            "top_leagues_with_odds":    [l for l in league_summary if l["has_odds"] > 0][:20],
            "top_leagues_without_odds": [l for l in league_summary if l["has_odds"] == 0][:20],
            "country_coverage":  country_summary[:30],
            "known_bettable_countries": sorted(BETTABLE_COUNTRIES),
            "known_research_countries": sorted(RESEARCH_ONLY_COUNTRIES),
        })
    except Exception as e:
        logger.error(f"[API] /api/bettable-universe: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/edge-discovery")
def api_edge_discovery():
    """Phase 3+5: Full edge discovery report + danger lists."""
    try:
        lse = _get_lse()
        return jsonify({
            "success":        True,
            "is_ready":       lse.is_ready,
            "summary":        lse.summary(),
            "edge_discovery": lse.get_edge_discovery(),
            "danger_report":  lse.get_danger_report(),
        })
    except Exception as e:
        logger.error(f"[API] /api/edge-discovery: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ─── Phase 5 — Odds Provider Diagnostics (dedicated route) ──────────────────

@app.route("/api/diagnostics/providers")
def api_diagnostics():
    """
    Phase 5 — Odds provider diagnostics (detailed).
    Shows primary/secondary provider, coverage stats, key status.
    Use /api/diagnostics for the unified dashboard view.
    """
    try:
        from app.config.data_source_config import DataSourceConfig
        cfg = DataSourceConfig()

        # Get live diagnostics from the OddsProviderManager if available
        odds_diag: dict = {}
        try:
            mgr = cfg.get_odds_provider()
            odds_diag = mgr.get_diagnostics()
        except Exception as exc:
            odds_diag = {"error": str(exc)}

        # Supabase status
        sb_status = "UNKNOWN"
        try:
            sb_status = _sb_cfg.supabase_status
        except Exception:
            pass

        return jsonify({
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # Phase 5 required fields
            "odds_provider_primary":   odds_diag.get("odds_provider_primary",   "API_FOOTBALL"),
            "odds_provider_secondary": odds_diag.get("odds_provider_secondary", "ODDS_API"),
            "odds_provider_status":    odds_diag.get("odds_provider_status",    cfg.odds_status),
            "coverage_apifootball":    odds_diag.get("coverage_apifootball",    0.0),
            "coverage_oddsapi":        odds_diag.get("coverage_oddsapi",        0.0),
            "matched_odds_apifootball": odds_diag.get("matched_odds_apifootball", 0),
            "matched_odds_oddsapi":     odds_diag.get("matched_odds_oddsapi",     0),
            # Key presence (never expose raw keys)
            "api_football_key_present": bool(cfg.apifootball_odds_key),
            "odds_api_key_present":     bool(cfg.odds_api_key),
            # Supabase
            "supabase_status": sb_status,
            # Full provider details
            "provider_details": odds_diag,
            # Config summary
            "config": {
                "odds_provider_config": cfg.odds_provider,
                "odds_status":          cfg.odds_status,
                "source_label":         cfg.source_label,
            },
            # Phase 2 — ODDS_FIRST_MODE diagnostics (populated after a scan)
            "odds_first_mode": {
                "mode":              "ODDS_FIRST",
                "min_matches_odds":  4,
                "min_matches_normal": 5,
                "ev_disabled_markets": [
                    "HOME_OVER_0_5", "AWAY_OVER_0_5",
                    "HT_OVER_1_0",
                    "SECOND_HALF_OVER_0_5", "SECOND_HALF_OVER_1_5",
                ],
            },
        })
    except Exception as e:
        logger.error(f"[API] /api/diagnostics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ─── Shadow Lab API ─────────────────────────────────────────────────────────────

@app.route("/api/shadow-lab", methods=["GET", "OPTIONS"])
def api_shadow_lab():
    """
    Shadow Lab - Comprehensive shadow strategy audit endpoint.
    
    READ ONLY - No database writes - No migrations - No production logic changes.
    
    Returns shadow strategy comparison, market scoreboard, missed opportunities,
    today's comparison, and recent settled picks.
    """
    try:
        from collections import defaultdict
        
        # Get TRACKING_RESET_AT
        reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()
        
        # Fetch POST_RESET predictions
        if reset_at:
            if "T" in reset_at:
                q = _repo._client.table("predictions").select(
                    "id, market, status, selection_mode, bookmaker_odd, "
                    "ev_percentage, created_at, prediction_date, "
                    "home_team, away_team, league, fixture_id, "
                    "offensive_profile, defensive_profile, market_generation_stats, "
                    "recommended_market_direction, best_over_market, best_under_market, "
                    "market_regime, confidence_score, volatility_score, chaos_score, "
                    "event_context, country, kickoff_time"
                ).gte("created_at", reset_at)
            else:
                q = _repo._client.table("predictions").select(
                    "id, market, status, selection_mode, bookmaker_odd, "
                    "ev_percentage, created_at, prediction_date, "
                    "home_team, away_team, league, fixture_id, "
                    "offensive_profile, defensive_profile, market_generation_stats, "
                    "recommended_market_direction, best_over_market, best_under_market, "
                    "market_regime, confidence_score, volatility_score, chaos_score, "
                    "event_context, country, kickoff_time"
                ).gte("prediction_date", reset_at)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            q = _repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd, "
                "ev_percentage, created_at, prediction_date, "
                "home_team, away_team, league, fixture_id, "
                "offensive_profile, defensive_profile, market_generation_stats, "
                "recommended_market_direction, best_over_market, best_under_market, "
                "market_regime, confidence_score, volatility_score, chaos_score, "
                "event_context, country, kickoff_time"
            ).gte("prediction_date", cutoff)
        
        rows = q.execute().data or []
        
        # Fetch fixtures for score data (include actual scores for backtesting)
        try:
            if reset_at:
                if "T" in reset_at:
                    fq = _repo._client.table("fixtures").select(
                        "id, fixture_id, home_team, away_team, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status"
                    ).gte("created_at", reset_at)
                else:
                    fq = _repo._client.table("fixtures").select(
                        "id, fixture_id, home_team, away_team, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status"
                    ).gte("kickoff_time", reset_at)
            else:
                from datetime import date, timedelta
                cutoff = (date.today() - timedelta(days=30)).isoformat()
                fq = _repo._client.table("fixtures").select(
                    "id, fixture_id, home_team, away_team, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status"
                ).gte("kickoff_time", cutoff)
            
            fixtures = fq.execute().data or []
        except Exception:
            fixtures = []
        
        # Use fixture_id (API ID) for lookup since predictions reference it
        fixture_lookup = {f["fixture_id"]: f for f in fixtures if f.get("fixture_id")}
        
        # ========================================================================
        # SHADOW PORTFOLIO GENERATION
        # ========================================================================
        # Generate independent shadow picks from profile data
        # These picks participate in ROI calculations separately from BetIQ
        
        shadow_predictions = []
        
        # Helper to safely get nested profile values
        # Note: profiles are stored as JSON strings in the database
        import json
        def get_profile_value(profile, key, default=0):
            if isinstance(profile, str):
                try:
                    profile = json.loads(profile)
                except:
                    return default
            if isinstance(profile, dict):
                return profile.get(key, default)
            return default
        
        # Generate shadow picks from all predictions (both pending and settled)
        # IMPORTANT: Only generate from predictions created BEFORE kickoff to avoid lookahead bias
        for pred in rows:
            fixture_id = pred.get("fixture_id", "")
            home_team = pred.get("home_team", "")
            away_team = pred.get("away_team", "")
            league = pred.get("league", "")
            country = pred.get("country", "")
            kickoff_time = pred.get("kickoff_time", pred.get("prediction_date", ""))
            created_at = pred.get("created_at", "")
            
            # Skip if no kickoff time or created_at
            if not kickoff_time or not created_at:
                continue
            
            # Skip if created after kickoff (lookahead bias prevention)
            from datetime import datetime
            try:
                gen_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                kick_time = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))
                if gen_time > kick_time:
                    continue  # Skip this prediction - lookahead bias
            except Exception:
                continue  # Skip if timestamp parsing fails
            
            # Get profile data
            offensive_profile = pred.get("offensive_profile") or {}
            defensive_profile = pred.get("defensive_profile") or {}
            market_regime = pred.get("market_regime", "")
            volatility_score = pred.get("volatility_score", 0) or 0
            chaos_score = pred.get("chaos_score", 0) or 0
            recommended_direction = pred.get("recommended_market_direction", "")
            
            # Get profile stats
            btts_rate = get_profile_value(offensive_profile, "btts_rate", 0)
            over_2_5_rate = get_profile_value(offensive_profile, "over_2_5_rate", 0)
            under_1_5_rate = get_profile_value(defensive_profile, "under_1_5_rate", 0)
            early_goal_rate = get_profile_value(offensive_profile, "early_goal_rate", 0)
            explosive_pairing_score = get_profile_value(offensive_profile, "explosive_pairing_score", 0)
            away_btts_rate = get_profile_value(offensive_profile, "away_btts_rate", 0)
            
            # ====================================================================
            # SHADOW_BTTS GENERATION
            # ====================================================================
            
            # BTTS_YES
            btts_yes_confidence = 0
            btts_yes_reason = ""
            
            if btts_rate >= 55 and over_2_5_rate >= 55:
                btts_yes_confidence = 75
                btts_yes_reason = f"High BTTS ({btts_rate}%) and Over 2.5 ({over_2_5_rate}%)"
            elif market_regime in ("HIGH_TEMPO", "CHAOTIC", "OPEN", "LATE_GOAL_LEAGUE"):
                btts_yes_confidence = 70
                btts_yes_reason = f"Market regime: {market_regime}"
            elif volatility_score >= 60 and chaos_score >= 50:
                btts_yes_confidence = 65
                btts_yes_reason = f"High volatility ({volatility_score}) and chaos ({chaos_score})"
            
            if btts_yes_confidence >= 65:
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "SHADOW_BTTS",
                    "market": "BTTS_YES",
                    "confidence": btts_yes_confidence,
                    "reason": btts_yes_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,  # Will be estimated or fetched later
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # BTTS_NO
            btts_no_confidence = 0
            btts_no_reason = ""
            
            if btts_rate <= 35 and under_1_5_rate >= 55:
                btts_no_confidence = 75
                btts_no_reason = f"Low BTTS ({btts_rate}%) and High Under 1.5 ({under_1_5_rate}%)"
            elif market_regime in ("LOW_TEMPO", "DEFENSIVE"):
                btts_no_confidence = 70
                btts_no_reason = f"Market regime: {market_regime}"
            elif recommended_direction == "UNDER":
                btts_no_confidence = 65
                btts_no_reason = "Recommended direction: UNDER"
            
            if btts_no_confidence >= 65:
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "SHADOW_BTTS",
                    "market": "BTTS_NO",
                    "confidence": btts_no_confidence,
                    "reason": btts_no_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # ====================================================================
            # SHADOW_TEAM_GOALS GENERATION
            # ====================================================================
            
            # HOME_TEAM_OVER_0_5
            if early_goal_rate >= 60 or (over_2_5_rate >= 50 and btts_rate >= 50):
                ho05_confidence = 75 if early_goal_rate >= 60 else 70
                ho05_reason = f"Early goal rate: {early_goal_rate}%" if early_goal_rate >= 60 else f"Over 2.5 rate: {over_2_5_rate}%"
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "SHADOW_TEAM_GOALS",
                    "market": "HOME_TEAM_OVER_0_5",
                    "confidence": ho05_confidence,
                    "reason": ho05_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # HOME_TEAM_OVER_1_5
            if early_goal_rate >= 75 and over_2_5_rate >= 60:
                ho15_confidence = 75
                ho15_reason = f"Early goal rate: {early_goal_rate}%, Over 2.5 rate: {over_2_5_rate}%"
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "SHADOW_TEAM_GOALS",
                    "market": "HOME_TEAM_OVER_1_5",
                    "confidence": ho15_confidence,
                    "reason": ho15_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # AWAY_TEAM_OVER_0_5
            if away_btts_rate >= 50 or (btts_rate >= 55 and over_2_5_rate >= 50):
                ao05_confidence = 70
                ao05_reason = f"Away BTTS rate: {away_btts_rate}%" if away_btts_rate >= 50 else f"High BTTS and Over 2.5"
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "SHADOW_TEAM_GOALS",
                    "market": "AWAY_TEAM_OVER_0_5",
                    "confidence": ao05_confidence,
                    "reason": ao05_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # AWAY_TEAM_OVER_1_5
            if away_btts_rate >= 65 and over_2_5_rate >= 65:
                ao15_confidence = 75
                ao15_reason = f"Away BTTS rate: {away_btts_rate}%, Over 2.5 rate: {over_2_5_rate}%"
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "SHADOW_TEAM_GOALS",
                    "market": "AWAY_TEAM_OVER_1_5",
                    "confidence": ao15_confidence,
                    "reason": ao15_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # ====================================================================
            # TEAM_GOALS_CONSERVATIVE GENERATION
            # ====================================================================
            # More selective version with stricter thresholds
            
            # HOME_TEAM_OVER_0_5 (Conservative)
            if early_goal_rate >= 70 and over_2_5_rate >= 60 and market_regime in ("HIGH_TEMPO", "CHAOTIC", "HIGH_TEMPO_OVER", "SECOND_HALF_CHAOS"):
                ho05_conf = 80
                ho05_reason = f"Conservative: Early goal {early_goal_rate}%, Over 2.5 {over_2_5_rate}%, Regime: {market_regime}"
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "TEAM_GOALS_CONSERVATIVE",
                    "market": "HOME_TEAM_OVER_0_5",
                    "confidence": ho05_conf,
                    "reason": ho05_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # HOME_TEAM_OVER_1_5 (Conservative)
            if early_goal_rate >= 80 and over_2_5_rate >= 70 and explosive_pairing_score >= 65:
                ho15_conf = 85
                ho15_reason = f"Conservative: Early goal {early_goal_rate}%, Over 2.5 {over_2_5_rate}%, Explosive {explosive_pairing_score}%"
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "TEAM_GOALS_CONSERVATIVE",
                    "market": "HOME_TEAM_OVER_1_5",
                    "confidence": ho15_conf,
                    "reason": ho15_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # AWAY_TEAM_OVER_0_5 (Conservative)
            if away_btts_rate >= 60 and btts_rate >= 60:
                ao05_conf = 75
                ao05_reason = f"Conservative: Away BTTS {away_btts_rate}%, BTTS {btts_rate}%"
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "TEAM_GOALS_CONSERVATIVE",
                    "market": "AWAY_TEAM_OVER_0_5",
                    "confidence": ao05_conf,
                    "reason": ao05_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
            
            # AWAY_TEAM_OVER_1_5 (Conservative)
            if away_btts_rate >= 70 and over_2_5_rate >= 70:
                ao15_conf = 80
                ao15_reason = f"Conservative: Away BTTS {away_btts_rate}%, Over 2.5 {over_2_5_rate}%"
                shadow_predictions.append({
                    "fixture_id": fixture_id,
                    "strategy": "TEAM_GOALS_CONSERVATIVE",
                    "market": "AWAY_TEAM_OVER_1_5",
                    "confidence": ao15_conf,
                    "reason": ao15_reason,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "created_at": created_at,
                    "bookmaker_odd": None,
                    "simulated_result": None,
                    "simulated_profit_loss": None
                })
        
        # ========================================================================
        # SETTLE SHADOW PREDICTIONS
        # ========================================================================
        # Use actual fixture scores to determine simulated results
        
        for sp in shadow_predictions:
            fixture_id = sp.get("fixture_id")
            fixture = fixture_lookup.get(fixture_id)
            
            if not fixture:
                continue
            
            home_score = fixture.get("home_score")
            away_score = fixture.get("away_score")
            
            if home_score is None or away_score is None:
                continue
            
            market = sp.get("market")
            result = None
            
            # Determine result based on actual scores
            if market == "BTTS_YES":
                result = "WON" if home_score > 0 and away_score > 0 else "LOST"
            elif market == "BTTS_NO":
                result = "WON" if home_score == 0 or away_score == 0 else "LOST"
            elif market == "HOME_TEAM_OVER_0_5":
                result = "WON" if home_score >= 1 else "LOST"
            elif market == "HOME_TEAM_OVER_1_5":
                result = "WON" if home_score >= 2 else "LOST"
            elif market == "AWAY_TEAM_OVER_0_5":
                result = "WON" if away_score >= 1 else "LOST"
            elif market == "AWAY_TEAM_OVER_1_5":
                result = "WON" if away_score >= 2 else "LOST"
            
            sp["simulated_result"] = result
            
            # Simulate P/L using estimated odds (simplified: assume 1.8 for over, 1.9 for BTTS)
            if result == "WON":
                if "BTTS" in market:
                    sp["simulated_profit_loss"] = 0.9  # BTTS odds ~1.9
                else:
                    sp["simulated_profit_loss"] = 0.8  # Over odds ~1.8
            elif result == "LOST":
                sp["simulated_profit_loss"] = -1.0
            else:
                sp["simulated_profit_loss"] = 0.0
        
        # Backtest BTTS and Team Goals from settled predictions
        # Reconstruct ex-post accuracy using actual scores
        shadow_backtest = {
            "BTTS_YES": {"sample": 0, "wins": 0},
            "BTTS_NO": {"sample": 0, "wins": 0},
            "HOME_TEAM_OVER_0_5": {"sample": 0, "wins": 0},
            "AWAY_TEAM_OVER_0_5": {"sample": 0, "wins": 0},
            "HOME_TEAM_OVER_1_5": {"sample": 0, "wins": 0},
            "AWAY_TEAM_OVER_1_5": {"sample": 0, "wins": 0}
        }
        
        settled_predictions = [r for r in rows if r.get("status") in ("WON", "LOST")]
        
        for pred in settled_predictions:
            fixture_id = pred.get("fixture_id")
            fixture = fixture_lookup.get(fixture_id)
            
            if not fixture:
                continue
            
            home_score = fixture.get("home_score")
            away_score = fixture.get("away_score")
            
            if home_score is None or away_score is None:
                continue
            
            total_goals = home_score + away_score
            
            # BTTS_YES: both teams score
            shadow_backtest["BTTS_YES"]["sample"] += 1
            if home_score > 0 and away_score > 0:
                shadow_backtest["BTTS_YES"]["wins"] += 1
            
            # BTTS_NO: at least one team doesn't score
            shadow_backtest["BTTS_NO"]["sample"] += 1
            if home_score == 0 or away_score == 0:
                shadow_backtest["BTTS_NO"]["wins"] += 1
            
            # HOME_TEAM_OVER_0_5
            shadow_backtest["HOME_TEAM_OVER_0_5"]["sample"] += 1
            if home_score >= 1:
                shadow_backtest["HOME_TEAM_OVER_0_5"]["wins"] += 1
            
            # AWAY_TEAM_OVER_0_5
            shadow_backtest["AWAY_TEAM_OVER_0_5"]["sample"] += 1
            if away_score >= 1:
                shadow_backtest["AWAY_TEAM_OVER_0_5"]["wins"] += 1
            
            # HOME_TEAM_OVER_1_5
            shadow_backtest["HOME_TEAM_OVER_1_5"]["sample"] += 1
            if home_score >= 2:
                shadow_backtest["HOME_TEAM_OVER_1_5"]["wins"] += 1
            
            # AWAY_TEAM_OVER_1_5
            shadow_backtest["AWAY_TEAM_OVER_1_5"]["sample"] += 1
            if away_score >= 2:
                shadow_backtest["AWAY_TEAM_OVER_1_5"]["wins"] += 1
        
        # Fetch active fixtures (upcoming matches) for missed opportunities
        try:
            from datetime import date, timedelta
            today = date.today()
            tomorrow = (today + timedelta(days=1)).isoformat()
            
            active_fq = _repo._client.table("fixtures").select(
                "id, home_team, away_team, league, kickoff_time"
            ).gte("kickoff_time", today).lte("kickoff_time", tomorrow)
            
            active_fixtures = active_fq.execute().data or []
        except Exception:
            active_fixtures = []
        
        REAL_ODDS_THRESHOLD = 1.1
        
        def compute_pl(status, odd):
            """Compute P/L manually: WIN: odd - 1, LOSS: -1, VOID: 0"""
            if status == "WON":
                return odd - 1
            elif status == "LOST":
                return -1.0
            else:
                return 0.0
        
        def compute_strategy(filtered_rows):
            """Compute strategy metrics."""
            with_odds = [r for r in filtered_rows if r.get("bookmaker_odd")]
            settled = [r for r in with_odds if r.get("status") in ("WON", "LOST")]
            wins = [r for r in settled if r.get("status") == "WON"]
            losses = [r for r in settled if r.get("status") == "LOST"]
            
            accuracy = len(wins) / len(settled) * 100 if settled else 0
            profit = sum(compute_pl(r.get("status"), r.get("bookmaker_odd")) for r in settled)
            roi = profit / len(settled) * 100 if settled else 0
            
            return {
                "total": len(filtered_rows),
                "settled": len(settled),
                "wins": len(wins),
                "losses": len(losses),
                "accuracy": round(accuracy, 1),
                "profit": round(profit, 2),
                "roi": round(roi, 1)
            }
        
        def compute_shadow_strategy(shadow_filtered, strategy_name):
            """Compute shadow strategy metrics from shadow_predictions."""
            settled = [r for r in shadow_filtered if r.get("simulated_result") in ("WON", "LOST")]
            wins = [r for r in settled if r.get("simulated_result") == "WON"]
            losses = [r for r in settled if r.get("simulated_result") == "LOST"]
            
            accuracy = len(wins) / len(settled) * 100 if settled else 0
            profit = sum(r.get("simulated_profit_loss", 0) for r in settled)
            roi = profit / len(settled) * 100 if settled else 0
            
            return {
                "total": len(shadow_filtered),
                "settled": len(settled),
                "wins": len(wins),
                "losses": len(losses),
                "accuracy": round(accuracy, 1),
                "profit": round(profit, 2),
                "roi": round(roi, 1)
            }
        
        # Define strategy filters
        strategies = {
            "BETIQ_LIVE_SAFE": lambda r: r.get("selection_mode") in ("LIVE_SAFE", "LIVE"),
            "ALL_REAL_ODDS": lambda r: r.get("bookmaker_odd") and r.get("bookmaker_odd") >= REAL_ODDS_THRESHOLD,
            "NO_TOXIC_MARKETS": lambda r: r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5"),
            "PREFERRED_MARKETS": lambda r: r.get("market") in ("HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5"),
            "POSITIVE_TIERS": lambda r: False,  # Disabled - tier field not available
            "ODDS_CAP_5": lambda r: r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 5.0,
            "ODDS_CAP_3": lambda r: r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 3.0,
            "EV_0_TO_10": lambda r: r.get("ev_percentage") is not None and 0 <= r.get("ev_percentage") <= 10,
            "EV_0_TO_30": lambda r: r.get("ev_percentage") is not None and 0 <= r.get("ev_percentage") <= 30,
            "SHADOW_MARKET_V1": lambda r: (
                r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 5.0
                and r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
                and (r.get("ev_percentage") or 0) <= 35
                and r.get("market") in ("HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5")
            ),
            "SHADOW_BTTS": lambda r: r.get("market") in ("BTTS_YES", "BTTS_NO"),
            "SHADOW_TEAM_GOALS": lambda r: r.get("market") in (
                "HOME_TEAM_OVER_0_5", "AWAY_TEAM_OVER_0_5",
                "HOME_TEAM_OVER_1_5", "AWAY_TEAM_OVER_1_5"
            ),
            "TEAM_GOALS_CONSERVATIVE": lambda r: r.get("market") in (
                "HOME_TEAM_OVER_0_5", "AWAY_TEAM_OVER_0_5",
                "HOME_TEAM_OVER_1_5", "AWAY_TEAM_OVER_1_5"
            ),
            "NO_EXTREME_UNDERS": lambda r: (
                r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
                and not (("_UNDER_" in r.get("market", "") or r.get("market", "").startswith("UNDER")) and r.get("bookmaker_odd") and r.get("bookmaker_odd") > 4.0)
            )
        }
        
        # Compute all strategies
        leaderboard = []
        for name, filter_fn in strategies.items():
            # For shadow strategies, use shadow_predictions instead of rows
            if name in ("SHADOW_BTTS", "SHADOW_TEAM_GOALS", "TEAM_GOALS_CONSERVATIVE"):
                shadow_filtered = [r for r in shadow_predictions if r.get("strategy") == name]
                metrics = compute_shadow_strategy(shadow_filtered, name)
            else:
                filtered = [r for r in rows if filter_fn(r)]
                metrics = compute_strategy(filtered)
            leaderboard.append({
                "strategy": name,
                **metrics
            })
        
        # Sort leaderboard by ROI
        leaderboard.sort(key=lambda x: x["roi"], reverse=True)
        
        # Extract live_safe and shadow strategies
        live_safe = next((s for s in leaderboard if s["strategy"] == "BETIQ_LIVE_SAFE"), {
            "strategy": "BETIQ_LIVE_SAFE",
            "total": 0, "settled": 0, "wins": 0, "losses": 0,
            "accuracy": 0, "profit": 0, "roi": 0
        })
        
        shadow_market_v1 = next((s for s in leaderboard if s["strategy"] == "SHADOW_MARKET_V1"), {
            "strategy": "SHADOW_MARKET_V1",
            "total": 0, "settled": 0, "wins": 0, "losses": 0,
            "accuracy": 0, "profit": 0, "roi": 0
        })
        
        shadow_btts = next((s for s in leaderboard if s["strategy"] == "SHADOW_BTTS"), {
            "strategy": "SHADOW_BTTS",
            "total": 0, "settled": 0, "wins": 0, "losses": 0,
            "accuracy": 0, "profit": 0, "roi": 0
        })
        
        shadow_team_goals = next((s for s in leaderboard if s["strategy"] == "SHADOW_TEAM_GOALS"), {
            "strategy": "SHADOW_TEAM_GOALS",
            "total": 0, "settled": 0, "wins": 0, "losses": 0,
            "accuracy": 0, "profit": 0, "roi": 0
        })
        
        team_goals_conservative = next((s for s in leaderboard if s["strategy"] == "TEAM_GOALS_CONSERVATIVE"), {
            "strategy": "TEAM_GOALS_CONSERVATIVE",
            "total": 0, "settled": 0, "wins": 0, "losses": 0,
            "accuracy": 0, "profit": 0, "roi": 0
        })
        
        no_extreme_unders = next((s for s in leaderboard if s["strategy"] == "NO_EXTREME_UNDERS"), {
            "strategy": "NO_EXTREME_UNDERS",
            "total": 0, "settled": 0, "wins": 0, "losses": 0,
            "accuracy": 0, "profit": 0, "roi": 0
        })
        
        # Market scoreboard
        market_data = defaultdict(lambda: {
            "settled": 0, "wins": 0, "total_odd": 0.0, "with_odd_count": 0, "profit": 0.0
        })
        
        for r in rows:
            market = r.get("market") or "UNKNOWN"
            if r.get("bookmaker_odd") and r.get("bookmaker_odd") >= REAL_ODDS_THRESHOLD:
                if r.get("status") in ("WON", "LOST"):
                    market_data[market]["settled"] += 1
                    if r.get("status") == "WON":
                        market_data[market]["wins"] += 1
                    market_data[market]["total_odd"] += r.get("bookmaker_odd")
                    market_data[market]["with_odd_count"] += 1
                    market_data[market]["profit"] += compute_pl(r.get("status"), r.get("bookmaker_odd"))
        
        market_scoreboard = []
        for market, d in market_data.items():
            if d["settled"] == 0:
                continue
            accuracy = d["wins"] / d["settled"] * 100
            avg_odd = d["total_odd"] / d["with_odd_count"]
            roi = d["profit"] / d["with_odd_count"] * 100
            market_scoreboard.append({
                "market": market,
                "settled": d["settled"],
                "wins": d["wins"],
                "accuracy": round(accuracy, 1),
                "avg_odd": round(avg_odd, 2),
                "profit": round(d["profit"], 2),
                "roi": round(roi, 1)
            })
        
        market_scoreboard.sort(key=lambda x: x["roi"], reverse=True)
        
        # Missed opportunities - include shadow backtest data
        missed_opportunities = []
        
        # Add BTTS and Team Goals backtest results (always include if sample > 0)
        for market, stats in shadow_backtest.items():
            if stats["sample"] > 0:
                accuracy = stats["wins"] / stats["sample"] * 100
                missed_opportunities.append({
                    "market": market,
                    "sample": stats["sample"],
                    "wins": stats["wins"],
                    "accuracy": round(accuracy, 1),
                    "generated_by_betiq": False,
                    "source": "shadow_backtest"
                })
        
        # Add other missed markets (existing logic)
        missed_markets = [
            "HOME_TEAM_TO_SCORE", "AWAY_TEAM_TO_SCORE",
            "FIRST_HALF_GOAL",
            "DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "DOUBLE_CHANCE_12",
            "DRAW_NO_BET_HOME", "DRAW_NO_BET_AWAY"
        ]
        
        generated_markets = set(market_data.keys())
        
        if fixtures:
            for market in missed_markets:
                if market in generated_markets:
                    continue
                
                settled = 0
                wins = 0
                
                for fixture in fixtures:
                    home_score = fixture.get("home_score")
                    away_score = fixture.get("away_score")
                    ht_home_score = fixture.get("ht_home_score")
                    ht_away_score = fixture.get("ht_away_score")
                    
                    if home_score is None or away_score is None:
                        continue
                    
                    ft_total = home_score + away_score
                    ht_total = (ht_home_score or 0) + (ht_away_score or 0)
                    
                    result = None
                    if market == "BTTS_YES":
                        result = "WON" if home_score > 0 and away_score > 0 else "LOST"
                    elif market == "BTTS_NO":
                        result = "WON" if home_score == 0 or away_score == 0 else "LOST"
                    elif market == "HOME_TEAM_TO_SCORE":
                        result = "WON" if home_score > 0 else "LOST"
                    elif market == "AWAY_TEAM_TO_SCORE":
                        result = "WON" if away_score > 0 else "LOST"
                    elif market == "FIRST_HALF_GOAL":
                        result = "WON" if ht_total > 0 else "LOST"
                    elif market == "DOUBLE_CHANCE_1X":
                        result = "WON" if home_score >= away_score else "LOST"
                    elif market == "DOUBLE_CHANCE_X2":
                        result = "WON" if away_score >= home_score else "LOST"
                    elif market == "DOUBLE_CHANCE_12":
                        result = "WON" if home_score != away_score else "LOST"
                    elif market == "DRAW_NO_BET_HOME":
                        result = "WON" if home_score > away_score else "LOST"
                    elif market == "DRAW_NO_BET_AWAY":
                        result = "WON" if away_score > home_score else "LOST"
                    
                    if result:
                        settled += 1
                        if result == "WON":
                            wins += 1
                
                if settled > 0:
                    accuracy = wins / settled * 100
                    missed_opportunities.append({
                        "market": market,
                        "sample": settled,
                        "wins": wins,
                        "accuracy": round(accuracy, 1),
                        "generated_by_betiq": False
                    })
        
        # Today's comparison
        today = datetime.now(timezone.utc).date().isoformat()
        today_predictions = [r for r in rows if r.get("prediction_date", "").startswith(today)]
        
        today_comparison = []
        for r in today_predictions:
            # Determine shadow decision
            shadow_decision = "SKIP"
            shadow_reason = ""
            
            if (r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 5.0
                and r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
                and (r.get("ev_percentage") or 0) <= 35
                and r.get("market") in ("HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5")):
                shadow_decision = "TAKE"
                shadow_reason = "SHADOW_MARKET_V1 criteria met"
            
            # Determine betiq decision
            betiq_decision = "TAKE" if r.get("selection_mode") in ("LIVE_SAFE", "LIVE") else "SKIP"
            
            today_comparison.append({
                "fixture_id": r.get("fixture_id", ""),
                "home_team": r.get("home_team", ""),
                "away_team": r.get("away_team", ""),
                "league": r.get("league", ""),
                "kickoff_time": r.get("kickoff_time", ""),
                "betiq_decision": betiq_decision,
                "betiq_market": r.get("market", ""),
                "shadow_decision": shadow_decision,
                "shadow_reason": shadow_reason,
                "selection_mode": r.get("selection_mode", ""),
                "market": r.get("market", ""),
                "bookmaker_odd": r.get("bookmaker_odd") or 0,
                "status": r.get("status", "")
            })
        
        # Recent settled
        settled_rows = [r for r in rows if r.get("status") in ("WON", "LOST")]
        settled_rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        recent_settled = []
        for r in settled_rows[:20]:
            betiq_taken = r.get("selection_mode") in ("LIVE_SAFE", "LIVE")
            
            # Determine if shadow would have taken it
            shadow_taken = (
                r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 5.0
                and r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
                and (r.get("ev_percentage") or 0) <= 35
                and r.get("market") in ("HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5")
            )
            
            profit = compute_pl(r.get("status"), r.get("bookmaker_odd")) if r.get("bookmaker_odd") else 0
            
            recent_settled.append({
                "prediction_id": r.get("id", ""),
                "date": r.get("created_at", ""),
                "home_team": r.get("home_team", ""),
                "away_team": r.get("away_team", ""),
                "market": r.get("market", ""),
                "odd": r.get("bookmaker_odd") or 0,
                "result": r.get("status", ""),
                "betiq_taken": betiq_taken,
                "shadow_taken": shadow_taken,
                "profit": round(profit, 2)
            })
        
        # MISSED_SHADOW_OPPORTUNITIES
        # Evaluate markets not currently generated by BetIQ using pending predictions with profile data
        missed_shadow_opportunities = []
        
        # Use pending predictions as source
        pending_predictions = [r for r in rows if r.get("status") == "PENDING"]
        
        # Get markets BetIQ has generated
        generated_markets = set(r.get("market") for r in rows if r.get("market"))
        
        # Helper to safely get nested profile values
        # Note: profiles are stored as JSON strings in the database
        import json
        def get_profile_value(profile, key, default=0):
            if isinstance(profile, str):
                try:
                    profile = json.loads(profile)
                except:
                    return default
            if isinstance(profile, dict):
                return profile.get(key, default)
            return default
        
        for pred in pending_predictions:
            fixture_id = pred.get("fixture_id", "")
            home_team = pred.get("home_team", "")
            away_team = pred.get("away_team", "")
            league = pred.get("league", "")
            country = pred.get("country", "")
            kickoff_time = pred.get("kickoff_time", pred.get("prediction_date", ""))
            match = f"{home_team} vs {away_team}"
            
            # Get profile data
            offensive_profile = pred.get("offensive_profile") or {}
            defensive_profile = pred.get("defensive_profile") or {}
            market_regime = pred.get("market_regime", "")
            volatility_score = pred.get("volatility_score", 0) or 0
            chaos_score = pred.get("chaos_score", 0) or 0
            recommended_direction = pred.get("recommended_market_direction", "")
            
            # BTTS_YES scoring
            btts_yes_confidence = 0
            btts_yes_reason = ""
            
            btts_rate = get_profile_value(offensive_profile, "btts_rate", 0)
            over_2_5_rate = get_profile_value(offensive_profile, "over_2_5_rate", 0)
            
            if btts_rate >= 55:
                btts_yes_confidence = 70
                btts_yes_reason = f"High BTTS rate ({btts_rate}%)"
            elif over_2_5_rate >= 55:
                btts_yes_confidence = 65
                btts_yes_reason = f"High Over 2.5 rate ({over_2_5_rate}%)"
            elif market_regime in ("HIGH_TEMPO", "LATE_GOAL_LEAGUE", "CHAOTIC", "OPEN"):
                btts_yes_confidence = 60
                btts_yes_reason = f"Market regime: {market_regime}"
            elif volatility_score >= 60 and chaos_score >= 50:
                btts_yes_confidence = 60
                btts_yes_reason = f"High volatility ({volatility_score}) and chaos ({chaos_score})"
            
            if btts_yes_confidence >= 60 and "BTTS_YES" not in generated_markets:
                missed_shadow_opportunities.append({
                    "fixture_id": fixture_id,
                    "match": match,
                    "market": "BTTS_YES",
                    "strategy": "SHADOW_BTTS",
                    "confidence": btts_yes_confidence,
                    "reason": btts_yes_reason,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "source": "prediction_profile"
                })
            
            # BTTS_NO scoring
            btts_no_confidence = 0
            btts_no_reason = ""
            
            under_1_5_rate = get_profile_value(defensive_profile, "under_1_5_rate", 0)
            
            if under_1_5_rate >= 55:
                btts_no_confidence = 70
                btts_no_reason = f"High Under 1.5 rate ({under_1_5_rate}%)"
            elif btts_rate <= 35:
                btts_no_confidence = 65
                btts_no_reason = f"Low BTTS rate ({btts_rate}%)"
            elif recommended_direction == "UNDER":
                btts_no_confidence = 60
                btts_no_reason = "Recommended direction: UNDER"
            elif market_regime in ("LOW_TEMPO", "DEFENSIVE"):
                btts_no_confidence = 60
                btts_no_reason = f"Market regime: {market_regime}"
            
            if btts_no_confidence >= 60 and "BTTS_NO" not in generated_markets:
                missed_shadow_opportunities.append({
                    "fixture_id": fixture_id,
                    "match": match,
                    "market": "BTTS_NO",
                    "strategy": "SHADOW_BTTS",
                    "confidence": btts_no_confidence,
                    "reason": btts_no_reason,
                    "league": league,
                    "country": country,
                    "kickoff_time": kickoff_time,
                    "source": "prediction_profile"
                })
            
            # Team Goals scoring
            early_goal_rate = get_profile_value(offensive_profile, "early_goal_rate", 0)
            explosive_pairing_score = get_profile_value(offensive_profile, "explosive_pairing_score", 0)
            
            # HOME_TEAM_OVER_0_5
            if early_goal_rate >= 55 or over_2_5_rate >= 50:
                ho05_confidence = 70 if early_goal_rate >= 55 else 65
                ho05_reason = f"Early goal rate: {early_goal_rate}%" if early_goal_rate >= 55 else f"Over 2.5 rate: {over_2_5_rate}%"
                if "HOME_TEAM_OVER_0_5" not in generated_markets:
                    missed_shadow_opportunities.append({
                        "fixture_id": fixture_id,
                        "match": match,
                        "market": "HOME_TEAM_OVER_0_5",
                        "strategy": "SHADOW_TEAM_GOALS",
                        "confidence": ho05_confidence,
                        "reason": ho05_reason,
                        "league": league,
                        "country": country,
                        "kickoff_time": kickoff_time,
                        "source": "prediction_profile"
                    })
            
            # HOME_TEAM_OVER_1_5
            if explosive_pairing_score >= 60 or over_2_5_rate >= 65:
                ho15_confidence = 70 if explosive_pairing_score >= 60 else 65
                ho15_reason = f"Explosive pairing: {explosive_pairing_score}" if explosive_pairing_score >= 60 else f"High Over 2.5 rate: {over_2_5_rate}%"
                if "HOME_TEAM_OVER_1_5" not in generated_markets:
                    missed_shadow_opportunities.append({
                        "fixture_id": fixture_id,
                        "match": match,
                        "market": "HOME_TEAM_OVER_1_5",
                        "strategy": "SHADOW_TEAM_GOALS",
                        "confidence": ho15_confidence,
                        "reason": ho15_reason,
                        "league": league,
                        "country": country,
                        "kickoff_time": kickoff_time,
                        "source": "prediction_profile"
                    })
            
            # AWAY_TEAM_OVER_0_5
            if early_goal_rate >= 50 or over_2_5_rate >= 45:
                ao05_confidence = 65
                ao05_reason = "Using match-level offensive profile proxy (team-specific unavailable)"
                if "AWAY_TEAM_OVER_0_5" not in generated_markets:
                    missed_shadow_opportunities.append({
                        "fixture_id": fixture_id,
                        "match": match,
                        "market": "AWAY_TEAM_OVER_0_5",
                        "strategy": "SHADOW_TEAM_GOALS",
                        "confidence": ao05_confidence,
                        "reason": ao05_reason,
                        "league": league,
                        "country": country,
                        "kickoff_time": kickoff_time,
                        "source": "prediction_profile"
                    })
            
            # AWAY_TEAM_OVER_1_5
            if explosive_pairing_score >= 55 or over_2_5_rate >= 60:
                ao15_confidence = 60
                ao15_reason = "Using match-level offensive profile proxy (team-specific unavailable)"
                if "AWAY_TEAM_OVER_1_5" not in generated_markets:
                    missed_shadow_opportunities.append({
                        "fixture_id": fixture_id,
                        "match": match,
                        "market": "AWAY_TEAM_OVER_1_5",
                        "strategy": "SHADOW_TEAM_GOALS",
                        "confidence": ao15_confidence,
                        "reason": ao15_reason,
                        "league": league,
                        "country": country,
                        "kickoff_time": kickoff_time,
                        "source": "prediction_profile"
                    })
        
        # Sort by confidence
        missed_shadow_opportunities.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Summary
        total_predictions = len(rows)
        settled_predictions = len([r for r in rows if r.get("status") in ("WON", "LOST")])
        real_odds_predictions = len([r for r in rows if r.get("bookmaker_odd") and r.get("bookmaker_odd") >= REAL_ODDS_THRESHOLD])
        
        return jsonify({
            "success": True,
            "tracking_reset_at": reset_at,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            
            "summary": {
                "total_predictions": total_predictions,
                "settled_predictions": settled_predictions,
                "real_odds_predictions": real_odds_predictions
            },
            
            "live_safe": live_safe,
            "shadow_market_v1": shadow_market_v1,
            "shadow_btts": shadow_btts,
            "shadow_team_goals": shadow_team_goals,
            "team_goals_conservative": team_goals_conservative,
            "no_extreme_unders": no_extreme_unders,
            "leaderboard": leaderboard,
            "market_scoreboard": market_scoreboard,
            "missed_opportunities": missed_opportunities,
            "missed_shadow_opportunities": missed_shadow_opportunities,
            "today_comparison": today_comparison,
            "recent_settled": recent_settled,
            
            # Shadow portfolio - simulated picks with ROI participation
            "shadow_portfolio": shadow_predictions
        })
        
    except Exception as e:
        logger.error(f"[API] /api/shadow-lab: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print(" DASHBOARD FLASK")
    print("="*60)
    print("\nDashboard URL: http://localhost:5000")
    print("\nAppuyez sur Ctrl+C pour arrêter\n")

    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
