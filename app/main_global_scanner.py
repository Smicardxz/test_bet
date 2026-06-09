"""
Main Global Football Intelligence Scanner API

Nouveau endpoint pour le GLOBAL FOOTBALL INTELLIGENCE SCANNER
Remplace l'approche restrictive par du scanning massif et intelligent
"""

from flask import Flask, jsonify, request
from datetime import datetime
import logging
from typing import Dict, Any

from app.providers.mock_provider import MockDataProvider
from app.providers.sofascore_provider import SofaScoreProvider
from app.services.scanner.global_intelligence_scanner import GlobalIntelligenceScanner
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.services.anomaly import AnomalyEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global scanner instances
global_scanner = None
daily_scanner = None


def initialize_scanners():
    """Initialize scanner instances"""
    global global_scanner, daily_scanner
    
    try:
        # Initialize providers
        mock_provider = MockDataProvider()
        sofascore_provider = SofaScoreProvider()
        
        # Initialize Global Intelligence Scanner
        global_scanner = GlobalIntelligenceScanner(
            provider=mock_provider,
            include_secondary_leagues=True,
            include_obscure_competitions=True,
            min_sample_size_layer1=3,  # Very inclusive
            min_sample_size_layer2=5,  # Moderate
            min_sample_size_layer3=8   # Standard
        )
        
        # Initialize Daily Scanner (relaxed thresholds)
        anomaly_engine = AnomalyEngine()
        daily_scanner = DailyScannerServiceV2(
            provider=mock_provider,
            anomaly_engine=anomaly_engine,
            is_real_data=False
        )
        
        logger.info("Global scanners initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing scanners: {e}")
        raise


@app.route('/api/global-scan', methods=['GET'])
def global_scan():
    """
    GLOBAL FOOTBALL INTELLIGENCE SCAN
    
    Endpoint principal pour le scanning massif et intelligent
    Architecture LAYER 1-2-3
    """
    
    try:
        # Get parameters
        date_param = request.args.get('date')
        max_layer1 = int(request.args.get('max_layer1', 200))
        max_layer2 = int(request.args.get('max_layer2', 100))
        max_layer3 = int(request.args.get('max_layer3', 50))
        
        # Parse date
        scan_date = None
        if date_param:
            try:
                scan_date = datetime.fromisoformat(date_param)
            except ValueError:
                return jsonify({"error": "Invalid date format. Use ISO format."}), 400
        
        # Ensure scanners are initialized
        if not global_scanner:
            initialize_scanners()
        
        # Run global scan
        logger.info(f"Starting GLOBAL FOOTBALL INTELLIGENCE SCAN")
        results = global_scanner.scan_global_football(
            date=scan_date,
            max_results_layer1=max_layer1,
            max_results_layer2=max_layer2,
            max_results_layer3=max_layer3
        )
        
        # Add success info
        results["success"] = True
        results["timestamp"] = datetime.utcnow().isoformat()
        results["scan_type"] = "GLOBAL_INTELLIGENCE_LAYERS_1_2_3"
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in global scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/daily-scan', methods=['GET'])
def daily_scan():
    """
    Daily Scan (relaxed thresholds)
    
    Version améliorée du scanner quotidien avec seuils relaxés
    """
    
    try:
        # Get parameters
        max_results = int(request.args.get('max_results', 100))
        competitions = request.args.getlist('competitions')
        
        # Ensure scanner is initialized
        if not daily_scanner:
            initialize_scanners()
        
        # Run daily scan
        logger.info(f"Starting DAILY SCAN (relaxed thresholds)")
        results = daily_scanner.scan_today(
            competition_ids=competitions if competitions else None,
            max_results=max_results
        )
        
        # Add success info
        results["success"] = True
        results["timestamp"] = datetime.utcnow().isoformat()
        results["scan_type"] = "DAILY_RELAXED_THRESHOLD"
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in daily scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/compare-scanners', methods=['GET'])
def compare_scanners():
    """
    Compare Global Scanner vs Daily Scanner
    
    Montre la différence entre l'approche massive et l'approche restrictive
    """
    
    try:
        # Ensure scanners are initialized
        if not global_scanner or not daily_scanner:
            initialize_scanners()
        
        # Run both scans
        logger.info("Running COMPARISON: Global vs Daily")
        
        # Global scan
        global_results = global_scanner.scan_global_football(
            max_results_layer1=100,
            max_results_layer2=50,
            max_results_layer3=25
        )
        
        # Daily scan
        daily_results = daily_scanner.scan_today(max_results=50)
        
        # Comparison analysis
        comparison = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "scan_comparison": {
                "global_scanner": {
                    "layer1_matches": len(global_results["layer1_massive_scan"]),
                    "layer2_profiles": len(global_results["layer2_statistical_profiling"]),
                    "layer3_market_edges": len(global_results["layer3_market_inefficiency"]),
                    "total_signals": sum(len(r.get("statistical_signals", [])) for r in global_results["layer2_statistical_profiling"]),
                    "avg_intelligence_score": global_results["summary"]["layer2_summary"]["avg_intelligence_score"],
                    "competitions_covered": global_results["summary"]["layer1_summary"]["competitions_covered"],
                    "countries_covered": global_results["summary"]["layer1_summary"]["countries_covered"]
                },
                "daily_scanner": {
                    "total_anomalies": len(daily_results["raw_anomalies"]),
                    "single_bets": len(daily_results["single_bets"]),
                    "combinations": len(daily_results["combinations"]),
                    "avg_anomaly_score": daily_results.get("scan_statistics", {}).get("avg_anomaly_score", 0),
                    "matches_fetched": daily_results.get("source_status", {}).get("matches_found", 0)
                }
            },
            "key_differences": [
                f"Global scanner covers {global_results['summary']['layer1_summary']['competitions_covered']} competitions vs focused approach",
                f"Global scanner detects {sum(len(r.get('statistical_signals', [])) for r in global_results['layer2_statistical_profiling'])} diverse signals vs {len(daily_results['raw_anomalies'])} focused anomalies",
                f"Global scanner intelligence score: {global_results['summary']['layer2_summary']['avg_intelligence_score']:.1f} vs Daily scanner anomaly score",
                "Global scanner includes secondary leagues, women, youth, reserves",
                "Daily scanner focuses on EXTREME_UNDER patterns only"
            ],
            "recommendation": "Use Global Scanner for intelligence gathering, Daily Scanner for specific betting opportunities"
        }
        
        return jsonify(comparison)
        
    except Exception as e:
        logger.error(f"Error in scanner comparison: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/available-competitions', methods=['GET'])
def get_competitions():
    """
    Get list of available competitions for global scanning
    
    Montre toutes les compétitions incluses dans le scanning massif
    """
    
    try:
        if not global_scanner:
            initialize_scanners()
        
        competitions = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "global_competitions": {
                "major_europe": [
                    {"id": "CL", "name": "Champions League", "type": "major"},
                    {"id": "EL", "name": "Europa League", "type": "major"},
                    {"id": "ECL", "name": "Conference League", "type": "major"},
                    {"id": "PL", "name": "Premier League", "type": "major"},
                    {"id": "L1", "name": "Ligue 1", "type": "major"},
                    {"id": "BL", "name": "Bundesliga", "type": "major"},
                    {"id": "SA", "name": "Serie A", "type": "major"},
                    {"id": "LIGA", "name": "La Liga", "type": "major"}
                ],
                "second_divisions": [
                    {"id": "CH", "name": "Championship", "type": "second_division"},
                    {"id": "L2", "name": "Ligue 2", "type": "second_division"},
                    {"id": "2BL", "name": "2. Bundesliga", "type": "second_division"},
                    {"id": "SB", "name": "Serie B", "type": "second_division"},
                    {"id": "LIGA2", "name": "LaLiga2", "type": "second_division"}
                ],
                "lower_divisions": [
                    {"id": "L1C", "name": "League One Conference", "type": "lower_division"},
                    {"id": "L2C", "name": "League Two Conference", "type": "lower_division"},
                    {"id": "3L", "name": "Third League", "type": "lower_division"},
                    {"id": "NLD", "name": "National League", "type": "lower_division"},
                    {"id": "SCD", "name": "Scottish Championship", "type": "lower_division"}
                ],
                "reserve_leagues": [
                    {"id": "PLR", "name": "Premier League Reserve", "type": "reserve"},
                    {"id": "L1R", "name": "Ligue 1 Reserve", "type": "reserve"},
                    {"id": "BLR", "name": "Bundesliga Reserve", "type": "reserve"},
                    {"id": "SAR", "name": "Serie A Reserve", "type": "reserve"}
                ],
                "women_leagues": [
                    {"id": "WSL", "name": "Women's Super League", "type": "women"},
                    {"id": "D1F", "name": "Division 1 Féminine", "type": "women"},
                    {"id": "FBL", "name": "Frauen Bundesliga", "type": "women"},
                    {"id": "SFW", "name": "Serie A Women", "type": "women"}
                ],
                "youth_leagues": [
                    {"id": "U19CL", "name": "UEFA Youth League", "type": "youth"},
                    {"id": "U19EL", "name": "UEFA Youth Elite", "type": "youth"}
                ],
                "asia_obscure": [
                    {"id": "J3", "name": "Japan J3 League", "type": "obscure"},
                    {"id": "K2", "name": "Korea K2 League", "type": "obscure"},
                    {"id": "CFA", "name": "China FA League", "type": "obscure"},
                    {"id": "VLEAGUE", "name": "Vietnam V-League", "type": "obscure"},
                    {"id": "IL", "name": "Indonesia Liga", "type": "obscure"}
                ],
                "africa_obscure": [
                    {"id": "ETP", "name": "Ethiopia Premier League", "type": "obscure"},
                    {"id": "SPL", "name": "Sudan Premier League", "type": "obscure"},
                    {"id": "KYL", "name": "Kyrgyzstan Premier League", "type": "obscure"},
                    {"id": "ML", "name": "Mongolia League", "type": "obscure"}
                ],
                "americas_obscure": [
                    {"id": "CB", "name": "Colombia B", "type": "obscure"},
                    {"id": "BF", "name": "Bolivia League", "type": "obscure"},
                    {"id": "ISL", "name": "Iceland Lower League", "type": "obscure"},
                    {"id": "FIL", "name": "Finland Lower League", "type": "obscure"}
                ],
                "regional_cups": [
                    {"id": "FA_CUP", "name": "FA Cup", "type": "cup"},
                    {"id": "DFB_POKAL", "name": "DFB Pokal", "type": "cup"},
                    {"id": "COPA_DEL_REY", "name": "Copa del Rey", "type": "cup"},
                    {"id": "COUPE_DE_FRANCE", "name": "Coupe de France", "type": "cup"}
                ],
                "small_countries": [
                    {"id": "WELSH", "name": "Welsh Premier League", "type": "small"},
                    {"id": "SCOTTISH_CH", "name": "Scottish Championship", "type": "small"},
                    {"id": "IRISH_PREM", "name": "Irish Premier League", "type": "small"},
                    {"id": "NIFL", "name": "NIFL Premiership", "type": "small"}
                ]
            },
            "total_competitions": len(global_scanner.global_competitions),
            "coverage_types": {
                "major": 8,
                "second_division": 5,
                "lower_division": 5,
                "reserve": 4,
                "women": 4,
                "youth": 2,
                "asia_obscure": 5,
                "africa_obscure": 4,
                "americas_obscure": 4,
                "regional_cups": 4,
                "small_countries": 4
            }
        }
        
        return jsonify(competitions)
        
    except Exception as e:
        logger.error(f"Error getting competitions: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "GLOBAL_INTELLIGENCE_SCANNER_v1.0",
        "scanners_initialized": global_scanner is not None and daily_scanner is not None
    })


if __name__ == '__main__':
    initialize_scanners()
    app.run(debug=True, host='0.0.0.0', port=5001)
