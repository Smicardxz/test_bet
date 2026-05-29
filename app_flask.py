"""
Flask Dashboard - Alternative à Streamlit
Compatible avec toutes versions Python
"""

from flask import Flask, render_template, jsonify
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import json
import logging

load_dotenv()

from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache global pour éviter de recharger à chaque requête
cache = {
    "data": None,
    "timestamp": None
}

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


@app.route('/api/refresh')
def refresh():
    """Force le rechargement des données"""
    cache["data"] = None
    cache["timestamp"] = None
    return jsonify({"success": True, "message": "Cache cleared"})


@app.route('/api/analyze_match', methods=['POST'])
def analyze_match_on_demand():
    """
    Analyze a specific match on demand with REAL data
    
    Expects JSON:
    {
        "fixture_id": "...",
        "home_team_id": "...",
        "away_team_id": "...",
        "home_team_name": "...",
        "away_team_name": "..."
    }
    
    Returns:
    {
        "success": true/false,
        "analysis_status": "ANALYZED|DATA_INSUFFICIENT|ERROR",
        "data_origin": "REAL",
        "home_history_count": 0,
        "away_history_count": 0,
        ...
    }
    """
    try:
        from flask import request
        from app.services.data.match_data_loader import MatchDataLoader
        from app.services.analysis.league_profile_engine import LeagueProfile
        
        # Get request data
        req_data = request.get_json()
        fixture_id = req_data.get('fixture_id')
        home_team_id = req_data.get('home_team_id')
        away_team_id = req_data.get('away_team_id')
        home_team_name = req_data.get('home_team_name', '')
        away_team_name = req_data.get('away_team_name', '')
        
        logger.info(f"[ANALYZE] fixture_id={fixture_id}")
        logger.info(f"[ANALYZE] home_team_id={home_team_id}, away_team_id={away_team_id}")
        
        if not all([fixture_id, home_team_id, away_team_id]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: fixture_id, home_team_id, away_team_id"
            }), 400
        
        # Get provider
        data = load_data()
        manager = data["manager"]
        provider = manager.provider
        
        logger.info(f"[ANALYZE] Loading match data...")
        
        # Load REAL historical data
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
        
        logger.info(f"[ANALYZE] home_history_count={bundle.home_history_count}")
        logger.info(f"[ANALYZE] away_history_count={bundle.away_history_count}")
        logger.info(f"[ANALYZE] h2h_count={bundle.h2h_count}")
        logger.info(f"[ANALYZE] history_status={bundle.history_status}")
        
        # Check data quality
        if bundle.history_status == "MISSING":
            return jsonify({
                "success": True,
                "analysis_status": "DATA_INSUFFICIENT",
                "reason": "NO_HISTORY_AVAILABLE",
                "data_origin": "REAL",
                "home_history_count": 0,
                "away_history_count": 0,
                "h2h_count": 0,
                "errors": bundle.errors,
                "warnings": bundle.warnings
            })
        
        if bundle.history_status == "INSUFFICIENT":
            return jsonify({
                "success": True,
                "analysis_status": "DATA_INSUFFICIENT",
                "reason": "INSUFFICIENT_SAMPLE_SIZE",
                "sample_size": bundle.home_history_count + bundle.away_history_count,
                "data_origin": "REAL",
                "home_history_count": bundle.home_history_count,
                "away_history_count": bundle.away_history_count,
                "h2h_count": bundle.h2h_count,
                "errors": bundle.errors,
                "warnings": bundle.warnings
            })
        
        # Get scanner
        scanner = data["scanner"]
        
        # Create a simple profile
        profile = LeagueProfile(
            league_name=req_data.get('league_name', 'Unknown'),
            country=req_data.get('country', 'Unknown')
        )
        
        # Create a mock match object
        class MockMatch:
            def __init__(self, fixture_id, home_id, away_id, home_name, away_name):
                self.match_id = fixture_id
                self.home_team = type('obj', (object,), {'id': home_id, 'name': home_name})()
                self.away_team = type('obj', (object,), {'id': away_id, 'name': away_name})()
                self.match_date = None
        
        mock_match = MockMatch(fixture_id, home_team_id, away_team_id, home_team_name, away_team_name)
        
        # Analyze
        logger.info(f"[ANALYZE] Running analysis...")
        analysis = scanner._analyze_match(mock_match, profile)
        
        if not analysis:
            return jsonify({
                "success": False,
                "error": "Analysis returned None"
            }), 500
        
        status = analysis.get("status", "OK")
        logger.info(f"[ANALYZE] status={status}")
        
        if status == "DATA_INSUFFICIENT":
            return jsonify({
                "success": True,
                "analysis_status": "DATA_INSUFFICIENT",
                "reason": analysis.get("reason"),
                "data_origin": analysis.get("data_origin", "REAL"),
                "home_history_count": analysis.get("home_history_count", 0),
                "away_history_count": analysis.get("away_history_count", 0),
                "errors": analysis.get("errors", []),
                "warnings": analysis.get("warnings", [])
            })
        
        if status == "ANALYZABLE_NO_ODDS":
            # Match analyzed successfully without odds
            debug = analysis.get("debug", {})
            ht_analysis = analysis.get("ht_analysis", {})
            ft_analysis = analysis.get("ft_analysis", {})
            
            logger.info(f"[ANALYZE] ht_rows={len(ht_analysis.get('table', []))}")
            logger.info(f"[ANALYZE] ft_rows={len(ft_analysis.get('table', []))}")
            logger.info(f"[ANALYZE] signals={len(analysis.get('signals', []))}")
            
            return jsonify({
                "success": True,
                "analysis_status": "ANALYZABLE_NO_ODDS",
                "data_origin": debug.get("data_origin", "REAL"),
                "mock_usage": debug.get("mock_usage", False),
                "home_history_count": debug.get("home_history_count", 0),
                "away_history_count": debug.get("away_history_count", 0),
                "h2h_count": debug.get("h2h_count", 0),
                "h2h_missing": debug.get("h2h_missing", False),
                "ht_data_available": debug.get("ht_data_available", False),
                "ft_data_available": debug.get("ft_data_available", False),
                "ht_analysis": ht_analysis,
                "ft_analysis": ft_analysis,
                "signals": analysis.get("signals", []),
                "match_history": analysis.get("match_history", []),
                "historical_summary": analysis.get("historical_summary", {}),
                "line_breach": analysis.get("line_breach", {}),
                "errors": debug.get("errors", []),
                "warnings": debug.get("warnings", [])
            })
        
        # Extract results
        debug = analysis.get("debug", {})
        ht_analysis = analysis.get("ht_analysis", {})
        ft_analysis = analysis.get("ft_analysis", {})
        
        logger.info(f"[ANALYZE] ht_rows={len(ht_analysis.get('table', []))}")
        logger.info(f"[ANALYZE] ft_rows={len(ft_analysis.get('table', []))}")
        
        return jsonify({
            "success": True,
            "analysis_status": "ANALYZED",
            "data_origin": debug.get("data_origin", "REAL"),
            "mock_usage": debug.get("mock_usage", False),
            "home_history_count": debug.get("home_history_count", 0),
            "away_history_count": debug.get("away_history_count", 0),
            "h2h_count": debug.get("h2h_count", 0),
            "ht_data_available": debug.get("ht_data_available", False),
            "ft_data_available": debug.get("ft_data_available", False),
            "ht_analysis": ht_analysis,
            "ft_analysis": ft_analysis,
            "signals": analysis.get("signals", []),
            "match_history": analysis.get("match_history", []),
            "errors": debug.get("errors", []),
            "warnings": debug.get("warnings", [])
        })
        
    except Exception as e:
        logger.error(f"[ANALYZE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
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


if __name__ == '__main__':
    print("\n" + "="*60)
    print(" DASHBOARD FLASK")
    print("="*60)
    print("\nDashboard URL: http://localhost:5000")
    print("\nAppuyez sur Ctrl+C pour arrêter\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
