"""
Version Flask avec Global Intelligence Scanner
Remplace app_flask.py pour avoir les compétitions inférieures
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime
import logging

# Import du Global Scanner
from app.services.scanner.global_intelligence_scanner import GlobalIntelligenceScanner
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.providers.mock_provider import MockDataProvider
from app.services.anomaly import AnomalyEngine

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize scanners
global_scanner = GlobalIntelligenceScanner(
    provider=MockDataProvider(),
    include_secondary_leagues=True,
    include_obscure_competitions=True
)

daily_scanner = DailyScannerServiceV2(
    provider=MockDataProvider(),
    anomaly_engine=AnomalyEngine(),
    is_real_data=False
)

# Cache
cache = {"data": None, "timestamp": None}


def _normalize_match(match_item):
    """Convertit en format Lovable"""
    if "match_profile" in match_item:  # Global Scanner format
        return {
            "match_id": match_item.get("match_id", ""),
            "home_team": match_item.get("home_team", ""),
            "away_team": match_item.get("away_team", ""),
            "league": match_item.get("league", ""),
            "country": match_item.get("country", ""),
            "match_date": match_item.get("match_date", ""),
            "kickoff_time": match_item.get("kickoff_time", ""),
            "status": "UPCOMING",
            "intelligence_score": match_item.get("intelligence_score", 0),
            "pattern_rarity_score": match_item.get("pattern_rarity_score", 0),
            "stability_score": match_item.get("stability_score", 0),
            "market_edge_score": match_item.get("market_edge_score", 0),
            "scoring_profile": match_item.get("match_profile", {}).get("scoring_profile", "UNKNOWN"),
            "specific_profiles": match_item.get("match_profile", {}).get("specific_profiles", []),
            "why_interesting": match_item.get("why_interesting", ""),
            "data_quality_score": match_item.get("data_quality_score", 0),
            "analyzed": True,
            "final_score": match_item.get("intelligence_score", 0),
            "confidence_score": match_item.get("stability_score", 0)
        }
    else:  # Daily Scanner format
        return {
            "match_id": match_item.get("match_id", ""),
            "home_team": match_item.get("home_team", ""),
            "away_team": match_item.get("away_team", ""),
            "league": match_item.get("league", ""),
            "country": match_item.get("country", ""),
            "match_date": match_item.get("match_date", ""),
            "kickoff_time": match_item.get("kickoff_time", ""),
            "status": "UPCOMING",
            "intelligence_score": match_item.get("final_score", 0),
            "pattern_rarity_score": 0,
            "stability_score": match_item.get("data_quality_score", 0),
            "market_edge_score": 0,
            "scoring_profile": "UNKNOWN",
            "specific_profiles": [],
            "why_interesting": f"Anomaly score: {match_item.get('final_score', 0):.1f}",
            "data_quality_score": match_item.get("data_quality_score", 0),
            "analyzed": True,
            "final_score": match_item.get("final_score", 0),
            "confidence_score": match_item.get("data_quality_score", 0)
        }


def load_data():
    """Charge les données avec Global Scanner"""
    try:
        if cache["data"] is None or cache["timestamp"] is None:
            logger.info("Loading GLOBAL INTELLIGENCE data...")
            
            # Global Scanner
            global_results = global_scanner.scan_global_football(
                max_results_layer1=50,
                max_results_layer2=30,
                max_results_layer3=20
            )
            
            # Daily Scanner
            daily_results = daily_scanner.scan_today(max_results=30)
            
            # Combiner
            layer2_matches = global_results.get("layer2_statistical_profiling", [])
            daily_matches = daily_results.get("raw_anomalies", [])
            
            all_matches = layer2_matches + daily_matches
            
            cache["data"] = {
                "scan_result": {
                    "analyzed_matches": all_matches,
                    "remaining_matches": []
                },
                "stats": {
                    "data_source": "global_intelligence_scanner",
                    "total_analyzed": len(all_matches),
                    "is_real_data": False
                }
            }
            cache["timestamp"] = datetime.utcnow().isoformat()
            logger.info(f"Loaded {len(all_matches)} matches successfully")
        
        return cache["data"]
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return {"manager": None}


# Routes pour Lovable
@app.route('/')
def index():
    return render_template('dashboard_intelligence.html')


@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "FLASK_GLOBAL_INTELLIGENCE_v1.0"
    })


@app.route('/api/dashboard/summary', methods=['GET', 'OPTIONS'])
def dashboard_summary():
    """Summary pour Lovable avec compétitions inférieures"""
    try:
        data = load_data()
        
        if data.get("manager") is None:
            return jsonify({
                "success": False,
                "error": "Data loading failed",
                "total_matches": 0,
                "analyzed_matches": 0,
                "awaiting_matches": 0,
                "live_matches": 0,
                "finished_matches": 0,
                "opportunities_count": 0,
                "data_source": "unknown",
                "last_refresh": None
            })
        
        scan_result = data["scan_result"]
        all_raw = scan_result.get("analyzed_matches", [])
        
        # Normalize
        normalized = [_normalize_match(m) for m in all_raw]
        
        total = len(normalized)
        analyzed = sum(1 for m in normalized if m["analyzed"])
        awaiting = total - analyzed
        live = sum(1 for m in normalized if m["status"] == "LIVE")
        finished = sum(1 for m in normalized if m["status"] == "FINISHED")
        
        # Calculer les ligues inférieures
        lower_leagues = [
            "Championship", "Ligue 2", "2. Bundesliga", "Serie B", "LaLiga2",
            "League One", "League Two", "National League", "J3", "K2",
            "China FA", "Vietnam", "Indonesia", "Ethiopia", "Sudan"
        ]
        
        lower_div_matches = [
            m for m in normalized 
            if any(league.lower() in m.get("league", "").lower() for league in lower_leagues)
        ]
        
        return jsonify({
            "success": True,
            "total_matches": total,
            "target_matches": total,
            "analyzed_matches": analyzed,
            "awaiting_matches": awaiting,
            "live_matches": live,
            "finished_matches": finished,
            "opportunities_count": sum(1 for m in normalized if m.get("intelligence_score", 0) >= 80),
            "data_source": "global_intelligence_scanner",
            "last_refresh": cache.get("timestamp"),
            "lower_division_matches": len(lower_div_matches),
            "obscure_competitions": len(set(m.get("league", "") for m in lower_div_matches)),
            "global_intelligence_avg": sum(m.get("intelligence_score", 0) for m in normalized) / len(normalized) if normalized else 0
        })
        
    except Exception as e:
        logger.error(f"Error in dashboard summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/matches', methods=['GET', 'OPTIONS'])
def get_matches():
    """Matches avec filtres pour Lovable"""
    try:
        data = load_data()
        scan_result = data["scan_result"]
        all_raw = scan_result.get("analyzed_matches", [])
        
        # Paramètres
        limit = int(request.args.get('limit', 50))
        min_intelligence = float(request.args.get('min_intelligence', 0))
        
        # Normaliser et filtrer
        normalized = [_normalize_match(m) for m in all_raw]
        filtered = [m for m in normalized if m.get("intelligence_score", 0) >= min_intelligence]
        
        # Trier
        filtered.sort(key=lambda x: x.get("intelligence_score", 0), reverse=True)
        
        return jsonify({
            "success": True,
            "matches": filtered[:limit],
            "total_found": len(filtered)
        })
        
    except Exception as e:
        logger.error(f"Error in get_matches: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/leagues/coverage', methods=['GET', 'OPTIONS'])
def leagues_coverage():
    """Coverage des ligues (y compris inférieures)"""
    try:
        data = load_data()
        scan_result = data["scan_result"]
        matches = scan_result.get("analyzed_matches", [])
        
        # Normaliser
        normalized = [_normalize_match(m) for m in matches]
        
        # Stats par pays
        countries = {}
        for match in normalized:
            country = match.get("country", "Unknown")
            league = match.get("league", "Unknown")
            
            if country not in countries:
                countries[country] = {"country": country, "leagues": {}, "total_matches": 0}
            
            if league not in countries[country]["leagues"]:
                countries[country]["leagues"][league] = 0
            
            countries[country]["leagues"][league] += 1
            countries[country]["total_matches"] += 1
        
        return jsonify({
            "success": True,
            "countries": list(countries.values()),
            "total_countries": len(countries),
            "total_leagues": sum(len(c["leagues"]) for c in countries.values())
        })
        
    except Exception as e:
        logger.error(f"Error in leagues coverage: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/refresh')
def refresh():
    """Refresh des données"""
    cache["data"] = None
    cache["timestamp"] = None
    return jsonify({
        "success": True,
        "message": "Cache cleared",
        "timestamp": datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    logger.info("Starting Flask with Global Intelligence Scanner...")
    app.run(debug=True, host='0.0.0.0', port=5002)
