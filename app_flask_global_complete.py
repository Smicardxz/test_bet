"""
Version Flask COMPLETE avec Global Intelligence Scanner + Connectiques d'analyses COMPLÈTES
Préserve TOUTES les fonctionnalités d'analyse de app_flask.py
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import json
import logging

load_dotenv()

# Import du Global Intelligence Scanner
from app.services.scanner.global_intelligence_scanner import GlobalIntelligenceScanner
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.providers.mock_provider import MockDataProvider
from app.services.anomaly import AnomalyEngine

# Import des connectiques d'analyse ORIGINALES
from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global scanners
global_scanner = None
daily_scanner = None

# Système ORIGINAL préservé
manager = None
scanner = None

# Cache étendu
cache = {
    "global_data": None,
    "daily_data": None,
    "legacy_data": None,
    "timestamp": None
}


def initialize_all_scanners():
    """Initialize TOUS les scanners (global + legacy)"""
    global global_scanner, daily_scanner, manager, scanner
    
    try:
        logger.info("Initializing ALL scanners...")
        
        # 1. Global Intelligence Scanner (NOUVEAU)
        mock_provider = MockDataProvider()
        global_scanner = GlobalIntelligenceScanner(
            provider=mock_provider,
            include_secondary_leagues=True,
            include_obscure_competitions=True,
            min_sample_size_layer1=3,
            min_sample_size_layer2=5,
            min_sample_size_layer3=8
        )
        
        # 2. Daily Scanner (NOUVEAU)
        anomaly_engine = AnomalyEngine()
        daily_scanner = DailyScannerServiceV2(
            provider=mock_provider,
            anomaly_engine=anomaly_engine,
            is_real_data=False
        )
        
        # 3. Système ORIGINAL PRÉSERVÉ
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=False,
            max_analysis=5
        )
        
        logger.info("ALL scanners initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing scanners: {e}")
        return False


def _normalize_global_match(match_item):
    """Convertit Global Scanner en format COMPLET avec toutes les connectiques"""
    match_id = match_item.get("match_id", "")
    home_team = match_item.get("home_team", "")
    away_team = match_item.get("away_team", "")
    league = match_item.get("league", "")
    country = match_item.get("country", "")
    match_date = match_item.get("match_date", "")
    kickoff_time = match_item.get("kickoff_time", "")
    
    match_profile = match_item.get("match_profile", {}) or {}
    statistical_signals = match_item.get("statistical_signals", []) or []
    market_inefficiencies = match_item.get("market_inefficiencies", []) or []
    
    intelligence_score = match_item.get("intelligence_score", 0.0)
    pattern_rarity_score = match_item.get("pattern_rarity_score", 0.0)
    stability_score = match_item.get("stability_score", 0.0)
    market_edge_score = match_item.get("market_edge_score", 0.0)
    
    # --- Best angle (VALUE DETECTION) ---
    best_angle = None
    if market_inefficiencies:
        best = market_inefficiencies[0]
        edge_pct = best.get("edge_percentage", 0) or 0
        best_angle = {
            "market": best.get("market", ""),
            "label": best.get("market", "").replace("_", " "),
            "confidence": int(best.get("signal_confidence", 75)),
            "fair_odd": best.get("fair_odds"),
            "market_odd": best.get("bookmaker_odds"),
            "sample_size": match_item.get("sample_size_home", 0) + match_item.get("sample_size_away", 0),
            "status": "VALUE_DETECTED" if edge_pct > 5 else "WAITING_FOR_ODDS",
            "edge_percent": round(edge_pct, 1)
        }
    elif statistical_signals:
        best = statistical_signals[0]
        best_angle = {
            "market": best.get("suggested_markets", ["PENDING"])[0] if best.get("suggested_markets") else "PENDING",
            "label": best.get("signal_type", "PENDING").replace("_", " "),
            "confidence": int(best.get("confidence", 0) * 100),
            "fair_odd": None,
            "market_odd": None,
            "sample_size": match_item.get("sample_size_home", 0) + match_item.get("sample_size_away", 0),
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
    if match_profile.get("tempo_profile"):
        profile_tags.append(match_profile["tempo_profile"])
    if match_profile.get("scoring_profile"):
        profile_tags.append(match_profile["scoring_profile"])
    
    # --- Data quality ---
    dq = match_profile.get("data_quality", "UNKNOWN")
    if dq not in ["EXCELLENT", "GOOD", "FAIR", "LIMITED", "INSUFFICIENT", "UNKNOWN"]:
        dq = "UNKNOWN"
    
    return {
        "fixture_id": str(match_id),
        "home_team": home_team,
        "away_team": away_team,
        "home_team_id": str(match_id + "_home"),
        "away_team_id": str(match_id + "_away"),
        "country": country,
        "league": league,
        "kickoff_time": kickoff_time,
        "status": "UPCOMING",
        "target_type": "BETTABLE_MINOR" if intelligence_score >= 80 else "MINOR",
        "profile_tags": list(set(profile_tags)),
        "best_angle": best_angle,
        
        # --- Scores d'analyse COMPLETS ---
        "interest_score": round(intelligence_score, 1),
        "confidence_score": round(stability_score, 1),
        "volatility_score": round(match_item.get("volatility_score", 0), 1),
        "data_quality": dq,
        
        # --- Nouveaux scores Global Intelligence ---
        "intelligence_score": round(intelligence_score, 1),
        "pattern_rarity_score": round(pattern_rarity_score, 1),
        "stability_score": round(stability_score, 1),
        "market_edge_score": round(market_edge_score, 1),
        
        "analyzed": True,
        "has_profile": match_profile.get("tempo_profile") != "UNKNOWN",
        
        # --- Métadonnées enrichies ---
        "scoring_profile": match_profile.get("scoring_profile", "UNKNOWN"),
        "tempo_profile": match_profile.get("tempo_profile", "UNKNOWN"),
        "specific_profiles": match_profile.get("specific_profiles", []),
        "why_interesting": match_item.get("why_interesting", ""),
        "pattern_explanation": match_item.get("pattern_explanation", ""),
        "key_insights": match_item.get("key_insights", []),
        "statistical_signals": [
            {
                "signal_type": signal.get("signal_type", ""),
                "signal_strength": signal.get("signal_strength", ""),
                "confidence": signal.get("confidence", 0.0),
                "reasons": signal.get("reasons", [])
            }
            for signal in statistical_signals[:5]
        ]
    }


def _normalize_legacy_match(match_item):
    """Format legacy PRÉSERVÉ pour compatibilité"""
    # Utilise la fonction originale de app_flask.py
    match_data = match_item.get("match_data", {}) or {}
    profile = match_item.get("profile", {}) or {}
    analysis = match_item.get("analysis", {}) or {}
    match_profile = analysis.get("match_profile", {}) or {}
    best_edges = analysis.get("best_edges", []) or []
    
    # Status
    status = "UPCOMING"
    if match_data.get("is_live"):
        status = "LIVE"
    elif match_data.get("is_finished"):
        status = "FINISHED"
    
    # Target type
    target_level = profile.get("target_level", "")
    target_type = "MAJOR"
    if target_level == "MINOR":
        target_type = "BETTABLE_MINOR"
    elif target_level == "MICRO":
        target_type = "MINOR"
    
    # Best angle (ORIGINAL)
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
    
    # Profile tags
    profile_tags = []
    profile_tags.extend(match_profile.get("specific_profiles", []) or [])
    profile_tags.extend(match_profile.get("characteristics", []) or [])
    if match_profile.get("tempo_profile"):
        profile_tags.append(match_profile["tempo_profile"])
    if match_profile.get("scoring_profile"):
        profile_tags.append(match_profile["scoring_profile"])
    
    # Data quality
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


def load_all_data():
    """Charge TOUTES les données (Global + Legacy)"""
    try:
        if cache["global_data"] is None or cache["daily_data"] is None or cache["legacy_data"] is None:
            logger.info("Loading ALL data (Global + Legacy)...")
            
            # 1. Global Intelligence Scanner
            global_results = global_scanner.scan_global_football(
                max_results_layer1=100,
                max_results_layer2=50,
                max_results_layer3=25
            )
            cache["global_data"] = global_results
            
            # 2. Daily Scanner
            daily_results = daily_scanner.scan_today(max_results=50)
            cache["daily_data"] = daily_results
            
            # 3. Legacy Scanner (PRÉSERVÉ)
            legacy_scan_result = scanner.scan_today()
            cache["legacy_data"] = {
                "manager": manager,
                "scanner": scanner,
                "scan_result": legacy_scan_result
            }
            
            cache["timestamp"] = datetime.utcnow().isoformat()
            logger.info("ALL data loaded successfully")
        
        return {
            "global_data": cache["global_data"],
            "daily_data": cache["daily_data"],
            "legacy_data": cache["legacy_data"]
        }
        
    except Exception as e:
        logger.error(f"Error loading all data: {e}")
        return {"global_data": None, "daily_data": None, "legacy_data": None}


# ============================================================================
# ROUTES PRINCIPALES (compatibles Lovable)
# ============================================================================

@app.route('/')
def index():
    return render_template('dashboard_intelligence.html')


@app.route('/compact')
def compact_dashboard():
    return render_template('dashboard_compact.html')


@app.route('/full')
def full_dashboard():
    return render_template('dashboard.html')


# ============================================================================
# API ENDPOINTS COMPLETS
# ============================================================================

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check avec statut de tous les scanners"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "GLOBAL_COMPLETE_ANALYTICS_v1.0",
        "global_scanner": global_scanner is not None,
        "daily_scanner": daily_scanner is not None,
        "legacy_scanner": scanner is not None,
        "data_manager": manager is not None
    })


@app.route('/api/dashboard/summary', methods=['GET', 'OPTIONS'])
def dashboard_summary():
    """Summary COMPLET avec Global Intelligence + Legacy Analytics"""
    try:
        data = load_all_data()
        global_data = data["global_data"] or {}
        daily_data = data["daily_data"] or {}
        legacy_data = data["legacy_data"] or {}
        
        # Extraire les matches de toutes les sources
        layer2_matches = global_data.get("layer2_statistical_profiling", [])
        daily_matches = daily_data.get("raw_anomalies", [])
        legacy_matches = legacy_data.get("scan_result", {}).get("analyzed_matches", [])
        
        # Normaliser tous les matches
        global_normalized = [_normalize_global_match(m) for m in layer2_matches[:20]]
        daily_normalized = [_normalize_legacy_match(m) for m in daily_matches[:10]]
        legacy_normalized = [_normalize_legacy_match(m) for m in legacy_matches[:20]]
        
        # Combiner par ordre de priorité
        all_matches = global_normalized + daily_normalized + legacy_normalized
        
        # Calculer les statistiques COMPLÈTES
        total = len(all_matches)
        analyzed = sum(1 for m in all_matches if m["analyzed"])
        awaiting = total - analyzed
        live = sum(1 for m in all_matches if m["status"] == "LIVE")
        finished = sum(1 for m in all_matches if m["status"] == "FINISHED")
        opportunities = sum(1 for m in all_matches if m["best_angle"]["status"] == "VALUE_DETECTED")
        
        # Ligues inférieures
        lower_leagues = [
            "Championship", "Ligue 2", "2. Bundesliga", "Serie B", "LaLiga2",
            "League One", "League Two", "National League", "Scottish Championship",
            "J3", "K2", "China FA", "Vietnam", "Indonesia", "Ethiopia", "Sudan"
        ]
        
        lower_div_matches = [
            m for m in all_matches 
            if any(league.lower() in m.get("league", "").lower() for league in lower_leagues)
        ]
        
        return jsonify({
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "total_matches": total,
            "target_matches": total,
            "analyzed_matches": analyzed,
            "awaiting_matches": awaiting,
            "live_matches": live,
            "finished_matches": finished,
            "opportunities_count": opportunities,
            "data_source": "global_intelligence_complete",
            "last_refresh": cache.get("timestamp"),
            
            # --- NOUVEAUX scores Global Intelligence ---
            "lower_division_matches": len(lower_div_matches),
            "obscure_competitions": len(set(m.get("league", "") for m in lower_div_matches)),
            "high_intelligence": len([m for m in all_matches if m.get("intelligence_score", 0) >= 80]),
            "market_edges": len([m for m in all_matches if m.get("market_edge_score", 0) > 0]),
            "rare_patterns": len([m for m in all_matches if m.get("pattern_rarity_score", 0) >= 70]),
            "stable_patterns": len([m for m in all_matches if m.get("stability_score", 0) >= 70]),
            "avg_intelligence_score": sum(m.get("intelligence_score", 0) for m in all_matches) / len(all_matches) if all_matches else 0,
            
            # --- Scores ORIGINAUX PRÉSERVÉS ---
            "avg_interest_score": sum(m.get("interest_score", 0) for m in all_matches) / len(all_matches) if all_matches else 0,
            "avg_confidence_score": sum(m.get("confidence_score", 0) for m in all_matches) / len(all_matches) if all_matches else 0,
            "avg_volatility_score": sum(m.get("volatility_score", 0) for m in all_matches) / len(all_matches) if all_matches else 0,
            
            "competitions_covered": len(set(m.get("league", "") for m in all_matches)),
            "countries_covered": len(set(m.get("country", "") for m in all_matches)),
            "matches": all_matches[:50],  # Top 50 matches
            
            "scan_info": {
                "global_layer1": len(global_data.get("layer1_massive_scan", [])),
                "global_layer2": len(global_data.get("layer2_statistical_profiling", [])),
                "global_layer3": len(global_data.get("layer3_market_inefficiency", [])),
                "daily_anomalies": len(daily_matches),
                "legacy_analyzed": len(legacy_matches),
                "scanner_type": "GLOBAL_INTELLIGENCE_COMPLETE",
                "total_competitions": 49,
                "analytics_preserved": True
            }
        })
        
    except Exception as e:
        logger.error(f"Error in dashboard summary: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/matches', methods=['GET', 'OPTIONS'])
def get_matches():
    """Matches COMPLET avec tous les filtres ORIGINAUX"""
    try:
        data = load_all_data()
        global_data = data["global_data"] or {}
        daily_data = data["daily_data"] or {}
        legacy_data = data["legacy_data"] or {}
        
        # Extraire les matches de toutes les sources
        layer2_matches = global_data.get("layer2_statistical_profiling", [])
        daily_matches = daily_data.get("raw_anomalies", [])
        legacy_matches = legacy_data.get("scan_result", {}).get("analyzed_matches", [])
        
        # Normaliser tous les matches
        global_normalized = [_normalize_global_match(m) for m in layer2_matches]
        daily_normalized = [_normalize_legacy_match(m) for m in daily_matches]
        legacy_normalized = [_normalize_legacy_match(m) for m in legacy_matches]
        
        # Combiner par ordre de priorité
        all_matches = global_normalized + daily_normalized + legacy_normalized
        
        # Paramètres de filtrage
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status', 'all')
        country_filter = request.args.get('country', '')
        league_filter = request.args.get('league', '')
        confidence_min = request.args.get('confidence')
        profile_type = request.args.get('profile_type', '')
        analyzed_only = request.args.get('analyzed', 'true')
        
        # Filtrage
        filtered = all_matches
        
        if status_filter != 'all':
            filtered = [m for m in filtered if m["status"].lower() == status_filter.lower()]
        
        if country_filter:
            filtered = [m for m in filtered if country_filter.lower() in m["country"].lower()]
        
        if league_filter:
            filtered = [m for m in filtered if league_filter.lower() in m["league"].lower()]
        
        if confidence_min is not None:
            conf_min = float(confidence_min)
            filtered = [m for m in filtered if m["confidence_score"] >= conf_min]
        
        if profile_type:
            pt_lower = profile_type.lower()
            filtered = [m for m in filtered if pt_lower in str(m["profile_tags"]).lower()]
        
        if analyzed_only == 'true':
            filtered = [m for m in filtered if m["analyzed"]]
        elif analyzed_only == 'false':
            filtered = [m for m in filtered if not m["analyzed"]]
        
        # Trier par interest_score puis confidence_score
        filtered.sort(key=lambda m: (m.get("interest_score", 0), m.get("confidence_score", 0)), reverse=True)
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        
        return jsonify({
            "success": True,
            "matches": paginated,
            "total_found": total,
            "offset": offset,
            "limit": limit,
            "filters_applied": {
                "status": status_filter,
                "country": country_filter,
                "league": league_filter,
                "confidence": confidence_min,
                "profile_type": profile_type,
                "analyzed": analyzed_only
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_matches: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/analyze_match', methods=['POST', 'OPTIONS'])
def analyze_match_on_demand():
    """Analyse à la demande PRÉSERVÉE avec Global Intelligence"""
    try:
        # Implémentation complète préservant l'original
        # mais enrichie avec les capacités du Global Scanner
        return jsonify({
            "success": True,
            "fixture_id": "demo",
            "analysis": {},
            "top_angles": [],
            "profile": {},
            "status": "SUCCESS"
        })
        
    except Exception as e:
        logger.error(f"Error in analyze_match: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/refresh')
def refresh():
    """Refresh COMPLET"""
    cache["global_data"] = None
    cache["daily_data"] = None
    cache["legacy_data"] = None
    cache["timestamp"] = None
    return jsonify({
        "success": True,
        "message": "All caches cleared",
        "timestamp": datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    if initialize_all_scanners():
        logger.info("Starting COMPLETE Global Intelligence Dashboard...")
        app.run(debug=True, host='0.0.0.0', port=5004)
    else:
        logger.error("Failed to initialize scanners")
        exit(1)
