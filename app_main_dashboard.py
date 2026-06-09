"""
Main Dashboard - Integration du Global Intelligence Scanner avec Lovable

Ce fichier remplace app_flask.py pour utiliser le nouveau GLOBAL FOOTBALL INTELLIGENCE SCANNER
tout en gardant la compatibilité avec votre dashboard Lovable existant
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

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global scanners
global_scanner = None
daily_scanner = None
cache = {
    "global_data": None,
    "daily_data": None,
    "timestamp": None
}


def initialize_scanners():
    """Initialize les scanners globaux"""
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
        logger.error(f"Error initializing scanners: {e}")
        return False


def _normalize_global_match(match_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforme un match du Global Scanner en format compatible Lovable
    """
    # Extraire les données du Global Scan Result
    match_id = match_item.get("match_id", "")
    home_team = match_item.get("home_team", "")
    away_team = match_item.get("away_team", "")
    league = match_item.get("league", "")
    country = match_item.get("country", "")
    match_date = match_item.get("match_date", "")
    kickoff_time = match_item.get("kickoff_time", "")
    
    # Extraire les profils et signaux
    match_profile = match_item.get("match_profile", {}) or {}
    statistical_signals = match_item.get("statistical_signals", []) or []
    pattern_detection = match_item.get("pattern_detection", {}) or {}
    market_inefficiencies = match_item.get("market_inefficiencies", []) or []
    
    # Scores d'intelligence
    intelligence_score = match_item.get("intelligence_score", 0.0)
    pattern_rarity_score = match_item.get("pattern_rarity_score", 0.0)
    stability_score = match_item.get("stability_score", 0.0)
    market_edge_score = match_item.get("market_edge_score", 0.0)
    
    # Construire le format Lovable-compatible
    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "league": league,
        "country": country,
        "match_date": match_date,
        "kickoff_time": kickoff_time,
        "status": "UPCOMING",  # Tous les matches sont upcoming dans le scanner
        
        # Intelligence scores (nouveaux)
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
            for signal in statistical_signals[:5]  # Top 5 signaux
        ],
        
        # Pattern detection
        "dominant_patterns": pattern_detection.get("dominant_patterns", []),
        "pattern_score": pattern_detection.get("pattern_score", 0.0),
        
        # Market inefficiencies
        "market_inefficiencies": market_inefficiencies,
        
        # Explanations
        "why_interesting": match_item.get("why_interesting", ""),
        "pattern_explanation": match_item.get("pattern_explanation", ""),
        "key_insights": match_item.get("key_insights", []),
        
        # Metadata
        "data_quality_score": match_item.get("data_quality_score", 0.0),
        "sample_size_home": match_item.get("sample_size_home", 0),
        "sample_size_away": match_item.get("sample_size_away", 0),
        "provider": match_item.get("provider", ""),
        "scan_timestamp": match_item.get("scan_timestamp", "")
    }


def _normalize_daily_match(match_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforme un match du Daily Scanner en format compatible Lovable
    """
    # Format existant pour compatibilité
    match_data = match_item.get("match_data", {}) or {}
    profile = match_item.get("profile", {}) or {}
    analysis = match_item.get("analysis", {}) or {}
    
    return {
        "match_id": match_item.get("match_id", ""),
        "home_team": match_data.get("home_team", ""),
        "away_team": match_data.get("away_team", ""),
        "league": match_data.get("league", ""),
        "country": match_data.get("country", ""),
        "match_date": match_data.get("match_date", ""),
        "kickoff_time": match_data.get("kickoff_time", ""),
        "status": "UPCOMING",
        
        # Scores traditionnels
        "anomaly_score": match_item.get("final_score", 0.0),
        "confidence": match_item.get("confidence_score", 0.0),
        
        # Market info
        "market_type": match_item.get("market_type", ""),
        "bookmaker_odds": match_item.get("bookmaker_odds"),
        "bookmaker": match_item.get("bookmaker", ""),
        
        # Data quality
        "data_quality_score": match_item.get("data_quality_score", 0.0),
        "sample_size_home": match_item.get("home_sample_size", 0),
        "sample_size_away": match_item.get("away_sample_size", 0),
        
        # Legacy compatibility
        "intelligence_score": match_item.get("final_score", 0.0),
        "pattern_rarity_score": 0.0,
        "stability_score": match_item.get("data_quality_score", 0.0),
        "market_edge_score": 0.0,
        
        "scoring_profile": "UNKNOWN",
        "tempo_profile": "UNKNOWN",
        "specific_profiles": [],
        "characteristics": [],
        "statistical_signals": [],
        "dominant_patterns": [],
        "pattern_score": 0.0,
        "market_inefficiencies": [],
        "why_interesting": f"Anomaly score: {match_item.get('final_score', 0.0):.1f}",
        "pattern_explanation": match_item.get("market_type", ""),
        "key_insights": [f"Market: {match_item.get('market_type', '')}"],
        
        "provider": match_item.get("provider", ""),
        "scan_timestamp": match_item.get("scan_timestamp", "")
    }


# ============================================================================
# ROUTES PRINCIPALES (compatibles Lovable)
# ============================================================================

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


# ============================================================================
# API ENDPOINTS POUR LOVABLE
# ============================================================================

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "GLOBAL_DASHBOARD_INTEGRATION_v1.0",
        "scanners_initialized": global_scanner is not None and daily_scanner is not None
    })


@app.route('/api/dashboard/summary', methods=['GET', 'OPTIONS'])
def dashboard_summary():
    """
    Clean dashboard summary pour Lovable avec Global Intelligence Scanner
    """
    try:
        # S'assurer que les scanners sont initialisés
        if not global_scanner or not daily_scanner:
            initialize_scanners()
        
        # Refresh cache si nécessaire
        if not cache["global_data"] or not cache["daily_data"]:
            refresh_data()
        
        global_data = cache["global_data"] or {}
        daily_data = cache["daily_data"] or {}
        
        # Combiner les données
        layer2_matches = global_data.get("layer2_statistical_profiling", [])
        daily_matches = daily_data.get("raw_anomalies", [])
        
        # Normaliser les matches
        global_matches_normalized = [_normalize_global_match(m) for m in layer2_matches[:20]]
        daily_matches_normalized = [_normalize_daily_match(m) for m in daily_matches[:10]]
        
        # Combiner pour le dashboard
        all_matches = global_matches_normalized + daily_matches_normalized
        
        # Calculer les statistiques
        summary = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "total_matches": len(all_matches),
            "high_intelligence": len([m for m in all_matches if m.get("intelligence_score", 0) >= 80]),
            "market_edges": len([m for m in all_matches if m.get("market_edge_score", 0) > 0]),
            "rare_patterns": len([m for m in all_matches if m.get("pattern_rarity_score", 0) >= 70]),
            "stable_patterns": len([m for m in all_matches if m.get("stability_score", 0) >= 70]),
            "avg_intelligence_score": sum(m.get("intelligence_score", 0) for m in all_matches) / len(all_matches) if all_matches else 0,
            "competitions_covered": len(set(m.get("league", "") for m in all_matches)),
            "countries_covered": len(set(m.get("country", "") for m in all_matches)),
            "matches": all_matches[:30],  # Top 30 matches
            "scan_info": {
                "global_layer1": len(global_data.get("layer1_massive_scan", [])),
                "global_layer2": len(global_data.get("layer2_statistical_profiling", [])),
                "global_layer3": len(global_data.get("layer3_market_inefficiency", [])),
                "daily_anomalies": len(daily_matches),
                "scanner_type": "GLOBAL_INTELLIGENCE_INTEGRATED"
            }
        }
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error in dashboard summary: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/matches', methods=['GET', 'OPTIONS'])
def get_matches():
    """
    Clean match list endpoint avec filtres pour Lovable
    """
    try:
        # Paramètres
        limit = int(request.args.get('limit', 50))
        min_intelligence = float(request.args.get('min_intelligence', 0))
        has_market_edge = request.args.get('has_market_edge', 'false').lower() == 'true'
        competition = request.args.get('competition', '')
        
        # S'assurer que les scanners sont initialisés
        if not global_scanner or not daily_scanner:
            initialize_scanners()
        
        # Refresh cache si nécessaire
        if not cache["global_data"] or not cache["daily_data"]:
            refresh_data()
        
        global_data = cache["global_data"] or {}
        daily_data = cache["daily_data"] or {}
        
        # Combiner les matches
        layer2_matches = global_data.get("layer2_statistical_profiling", [])
        daily_matches = daily_data.get("raw_anomalies", [])
        
        # Normaliser
        global_matches = [_normalize_global_match(m) for m in layer2_matches]
        daily_matches = [_normalize_daily_match(m) for m in daily_matches]
        all_matches = global_matches + daily_matches
        
        # Filtrer
        filtered_matches = []
        for match in all_matches:
            # Intelligence filter
            if match.get("intelligence_score", 0) < min_intelligence:
                continue
            
            # Market edge filter
            if has_market_edge and match.get("market_edge_score", 0) <= 0:
                continue
            
            # Competition filter
            if competition and competition.lower() not in match.get("league", "").lower():
                continue
            
            filtered_matches.append(match)
        
        # Trier par intelligence score
        filtered_matches.sort(key=lambda x: x.get("intelligence_score", 0), reverse=True)
        
        return jsonify({
            "success": True,
            "matches": filtered_matches[:limit],
            "total_found": len(filtered_matches),
            "filters_applied": {
                "min_intelligence": min_intelligence,
                "has_market_edge": has_market_edge,
                "competition": competition
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_matches: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/leagues/coverage', methods=['GET', 'OPTIONS'])
def leagues_coverage():
    """
    Returns coverage stats per country and league
    """
    try:
        # S'assurer que les scanners sont initialisés
        if not global_scanner or not daily_scanner:
            initialize_scanners()
        
        # Refresh cache si nécessaire
        if not cache["global_data"] or not cache["daily_data"]:
            refresh_data()
        
        global_data = cache["global_data"] or {}
        daily_data = cache["daily_data"] or {}
        
        # Extraire les leagues des données
        layer1_matches = global_data.get("layer1_massive_scan", [])
        layer2_matches = global_data.get("layer2_statistical_profiling", [])
        daily_matches = daily_data.get("raw_anomalies", [])
        
        # Combiner tous les matches
        all_matches = layer1_matches + layer2_matches + daily_matches
        
        # Calculer les statistiques par pays/league
        coverage = {}
        for match in all_matches:
            country = match.get("country", "Unknown")
            league = match.get("league", "Unknown")
            
            if country not in coverage:
                coverage[country] = {
                    "country": country,
                    "leagues": {},
                    "total_matches": 0
                }
            
            if league not in coverage[country]["leagues"]:
                coverage[country]["leagues"][league] = 0
            
            coverage[country]["leagues"][league] += 1
            coverage[country]["total_matches"] += 1
        
        # Convertir en liste
        coverage_list = list(coverage.values())
        
        # Trier par nombre de matches
        coverage_list.sort(key=lambda x: x["total_matches"], reverse=True)
        
        return jsonify({
            "success": True,
            "coverage": coverage_list,
            "total_countries": len(coverage_list),
            "total_leagues": sum(len(country["leagues"]) for country in coverage_list),
            "total_matches": len(all_matches)
        })
        
    except Exception as e:
        logger.error(f"Error in leagues coverage: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# ENDPOINTS DE CONTROLE
# ============================================================================

@app.route('/api/refresh')
def refresh():
    """Force le rechargement des données"""
    cache["global_data"] = None
    cache["daily_data"] = None
    cache["timestamp"] = None
    return jsonify({
        "success": True,
        "message": "Cache cleared, data will be refreshed on next request",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/global-scan', methods=['GET'])
def global_scan_endpoint():
    """Endpoint direct pour le Global Intelligence Scanner"""
    try:
        if not global_scanner:
            initialize_scanners()
        
        results = global_scanner.scan_global_football(
            max_results_layer1=100,
            max_results_layer2=50,
            max_results_layer3=25
        )
        
        return jsonify({
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error in global scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/daily-scan', methods=['GET'])
def daily_scan_endpoint():
    """Endpoint direct pour le Daily Scanner"""
    try:
        if not daily_scanner:
            initialize_scanners()
        
        results = daily_scanner.scan_today(max_results=50)
        
        return jsonify({
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error in daily scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def refresh_data():
    """Refresh les données des scanners"""
    global cache
    
    try:
        logger.info("Refreshing scanner data...")
        
        # Scanner global
        if global_scanner:
            global_results = global_scanner.scan_global_football(
                max_results_layer1=100,
                max_results_layer2=50,
                max_results_layer3=25
            )
            cache["global_data"] = global_results
        
        # Scanner daily
        if daily_scanner:
            daily_results = daily_scanner.scan_today(max_results=50)
            cache["daily_data"] = daily_results
        
        cache["timestamp"] = datetime.utcnow().isoformat()
        
        logger.info("Data refreshed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        return False


if __name__ == '__main__':
    # Initialize scanners
    if initialize_scanners():
        logger.info("Starting Global Dashboard Integration...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        logger.error("Failed to initialize scanners")
        exit(1)
