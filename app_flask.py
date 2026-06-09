"""
Flask Dashboard - Alternative à Streamlit
Compatible avec toutes versions Python
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import json
import logging

load_dotenv()

# Import du nouveau Global Intelligence Scanner
from app.services.scanner.global_intelligence_scanner import GlobalIntelligenceScanner
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.providers.mock_provider import MockDataProvider
from app.services.anomaly import AnomalyEngine

# Legacy imports (gardés pour compatibilité)
from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global scanners pour le nouveau système
global_scanner = None
daily_scanner = None

# Cache global pour éviter de recharger à chaque requête
cache = {
    "global_data": None,
    "daily_data": None,
    "legacy_data": None,
    "timestamp": None
}


def initialize_global_scanners():
    """Initialize les nouveaux scanners globaux"""
    global global_scanner, daily_scanner
    
    try:
        # Initialize providers
        mock_provider = MockDataProvider()
        
        # Initialize Global Intelligence Scanner
        global_scanner = GlobalIntelligenceScanner(
            provider=mock_provider,
            include_secondary_leagues=True,
            include_obscure_competitions=True,
            min_sample_size_layer1=3,
            min_sample_size_layer2=5,
            min_sample_size_layer3=8
        )
        
        # Initialize Daily Scanner
        anomaly_engine = AnomalyEngine()
        daily_scanner = DailyScannerServiceV2(
            provider=mock_provider,
            anomaly_engine=anomaly_engine,
            is_real_data=False
        )
        
        logger.info("Global scanners initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing global scanners: {e}")
        return False


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
        "profile_tags": list(set(profile_tags)),
        "best_angle": best_angle,
        "interest_score": round(match_profile.get("interest_score", 0), 1),
        "confidence_score": round(match_profile.get("confidence_score", 0), 1),
        "volatility_score": round(match_profile.get("volatility_score", 0), 1),
        "data_quality": dq,
        "analyzed": bool(analysis),
        "has_profile": bool(match_profile) and match_profile.get("tempo_profile") != "UNKNOWN"
    }


def _get_all_matches_from_cache():
    """Récupère tous les matchs (analysés + non analysés) depuis le cache."""
    data = load_data()
    if not data or data.get("manager") is None:
        return []
    scan_result = data.get("scan_result", {})
    analyzed = scan_result.get("analyzed_matches", []) or []
    remaining = scan_result.get("remaining_matches", []) or []
    return analyzed + remaining

def load_data():
    """Charge les données (avec cache de 15 minutes)"""
    now = datetime.now()
    
    # Si cache existe et < 30 secondes, retourner cache (DEV MODE)
    if cache["data"] and cache["timestamp"]:
        age = (now - cache["timestamp"]).total_seconds()
        if age < 30:  # 30 secondes (mode développement - mettre 900 en prod)
            logger.info(f"[CACHE] Using cached data (age: {age:.0f}s)")
            return cache["data"]
    
    logger.info("[CACHE] Cache expired or empty, loading fresh data...")
    
    # Charger nouvelles données
    try:
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=False,
            max_analysis=5  # REDUCED: Only analyze top 5 to avoid timeout
        )
        
        scan_result = scanner.scan_today()
        
        data = {
            "manager": manager,
            "scanner": scanner,  # Store scanner for analyze endpoint
            "scan_result": scan_result,
            "timestamp": now
        }
        
        # Mettre en cache
        cache["data"] = data
        cache["timestamp"] = now
        
        return data
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        
        # Return minimal data structure to avoid crashes
        return {
            "manager": None,
            "scanner": None,
            "scan_result": {
                "success": False,
                "error": str(e),
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
                "total_matches": scan_result.get("total_matches", 0),
                "target_count": scan_result.get("target_count", 0),
                "analyzed_count": scan_result.get("analyzed_count", 0),
                "scan_duration": scan_result.get("scan_duration_seconds", 0)
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
            
            match_info = {
                "match_id": match_data.get("match_id", ""),
                "home_team": match_data.get("home_team", ""),
                "away_team": match_data.get("away_team", ""),
                "home_team_id": match_data.get("home_team_id", ""),
                "away_team_id": match_data.get("away_team_id", ""),
                "country": country,
                "competition": match_data.get("competition", ""),
                "kickoff_time": match_data.get("time_display", "TBD"),
                "status": match_data.get("badge_text", "⏰ UPCOMING"),
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
                "analysis_status": analysis_status,
                "not_analyzed_reason": not_analyzed_reason
            }
            
            # Ajouter HT/FT analysis et historique (si match analysé)
            if analysis:
                match_info["ht_analysis"] = analysis.get("ht_analysis", {})
                match_info["ft_analysis"] = analysis.get("ft_analysis", {})
                match_info["match_history"] = analysis.get("match_history", [])
                match_info["match_profile"] = analysis.get("match_profile", {})  # DISCOVERY ENGINE
                match_info["best_edges"] = analysis.get("best_edges", [])  # VALUE LAYER
                match_info["edge_detection"] = analysis.get("edge_detection", {})  # Full edge results
                
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
            elif match_info["not_analyzed_reason"] == "awaiting_user_action":
                response["diagnostic"]["awaiting_user_action"] += 1
            elif match_info["not_analyzed_reason"] == "finished_match":
                response["diagnostic"]["finished_matches"] += 1
            elif match_info["not_analyzed_reason"] == "live_match":
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
    if cache["data"] and cache["data"].get("manager"):
        is_real = getattr(cache["data"]["manager"], "is_real_data", False)

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0-lovable",
        "data_source": "api_football" if is_real else "unknown",
        "cache_age_seconds": round(cache_age, 1) if cache_age is not None else None,
        "cache_active": cache_age is not None and cache_age < 30,
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


# ============================================================================
# LEGACY / INTERNAL ENDPOINTS (kept for existing dashboard)
# ============================================================================

@app.route('/api/refresh')
def refresh():
    """Force le rechargement des données"""
    cache["data"] = None
    cache["timestamp"] = None
    return jsonify({"success": True, "message": "Cache cleared"})


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
    Analyze a specific match on demand with REAL data.
    Returns a STABLE schema regardless of data quality.
    """
    try:
        from flask import request
        from app.services.data.match_data_loader import MatchDataLoader
        from app.services.analysis.league_profile_engine import LeagueProfile

        req_data = request.get_json() or {}
        fixture_id = req_data.get('fixture_id')
        home_team_id = req_data.get('home_team_id')
        away_team_id = req_data.get('away_team_id')
        home_team_name = req_data.get('home_team_name', '')
        away_team_name = req_data.get('away_team_name', '')

        logger.info(f"[ANALYZE] fixture_id={fixture_id}")

        if not all([fixture_id, home_team_id, away_team_id]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: fixture_id, home_team_id, away_team_id"
            }), 400

        data = load_data()
        manager = data["manager"]
        if not manager:
            return jsonify(_build_analyze_response(fixture_id, status="ERROR", errors=["Data manager not available"]))

        provider = manager.provider
        loader = MatchDataLoader(provider)
        bundle = loader.load_match_data(
            fixture_id=fixture_id,
            home_team_id=int(home_team_id),
            away_team_id=int(away_team_id),
            home_team_name=home_team_name,
            away_team_name=away_team_name,
            match_date=None,
            history_limit=10
        )

        # Data insufficient -> return stable schema with status
        if bundle.history_status in ("MISSING", "INSUFFICIENT"):
            reason = "NO_HISTORY_AVAILABLE" if bundle.history_status == "MISSING" else "INSUFFICIENT_SAMPLE_SIZE"
            return jsonify(_build_analyze_response(
                fixture_id,
                bundle=bundle,
                status="DATA_INSUFFICIENT",
                errors=[reason] + (bundle.errors or [])
            ))

        scanner = data["scanner"]
        profile = LeagueProfile(
            league_name=req_data.get('league_name', 'Unknown'),
            country=req_data.get('country', 'Unknown')
        )

        class MockMatch:
            def __init__(self, fid, hid, aid, hname, aname):
                self.match_id = fid
                self.home_team = type('obj', (object,), {'id': hid, 'name': hname})()
                self.away_team = type('obj', (object,), {'id': aid, 'name': aname})()
                self.match_date = None

        mock_match = MockMatch(fixture_id, home_team_id, away_team_id, home_team_name, away_team_name)
        analysis = scanner._analyze_match(mock_match, profile)

        if not analysis:
            return jsonify(_build_analyze_response(fixture_id, status="ERROR", errors=["Analysis returned None"]))

        raw_status = analysis.get("status", "OK")
        if raw_status == "DATA_INSUFFICIENT":
            return jsonify(_build_analyze_response(
                fixture_id,
                analysis=analysis,
                status="DATA_INSUFFICIENT",
                errors=[analysis.get("reason", "")] or []
            ))

        # Normal case: analyzed with or without odds
        return jsonify(_build_analyze_response(
            fixture_id,
            analysis=analysis,
            status="ANALYZABLE_NO_ODDS" if raw_status == "ANALYZABLE_NO_ODDS" else "ANALYZED"
        ))

    except Exception as e:
        logger.error(f"[ANALYZE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(_build_analyze_response(
            req_data.get('fixture_id', 'unknown') if 'req_data' in dir() else 'unknown',
            status="ERROR",
            errors=[str(e)]
        ))


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


if __name__ == '__main__':
    print("\n" + "="*60)
    print(" DASHBOARD FLASK")
    print("="*60)
    print("\nDashboard URL: http://localhost:5000")
    print("\nAppuyez sur Ctrl+C pour arrêter\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
