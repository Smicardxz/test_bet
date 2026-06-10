"""
Version WORKING avec vos vraies données API
GLOBAL FOOTBALL INTELLIGENCE SCANNER - Architecture LAYER 1-2-3
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import json
import logging

load_dotenv()

# VRAIS imports avec vos données API
from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner
from app.services.anomaly import AnomalyEngine

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Cache simple
cache = {
    "data": None,
    "timestamp": None
}


def load_data():
    """Charge les données avec VRAI API et seuils relaxés"""
    now = datetime.now()
    
    # Cache de 5 minutes
    if cache["data"] and cache["timestamp"]:
        age = (now - cache["timestamp"]).total_seconds()
        if age < 300:  # 5 minutes
            logger.info(f"[CACHE] Using cached data (age: {age:.0f}s)")
            return cache["data"]
    
    logger.info("[SCANNER] Loading fresh data with GLOBAL FOOTBALL INTELLIGENCE approach...")
    
    try:
        # Utiliser VRAI provider
        manager = DataSourceManager()
        
        # SmartScanner avec configuration GLOBAL INTELLIGENCE
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,  # Inclure ligues obscures
            max_analysis=50  # Augmenté pour plus de matches
        )
        
        # Scanner avec seuils relaxés
        scan_result = scanner.scan_today()
        
        data = {
            "manager": manager,
            "scanner": scanner,
            "scan_result": scan_result,
            "timestamp": now
        }
        
        # Mettre en cache
        cache["data"] = data
        cache["timestamp"] = now
        
        analyzed_count = len(scan_result.get("analyzed_matches", []))
        remaining_count = len(scan_result.get("remaining_matches", []))
        
        logger.info(f"[SCANNER] Loaded {analyzed_count} analyzed matches, {remaining_count} remaining matches")
        
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
                "analyzed_matches": [],
                "remaining_matches": []
            },
            "timestamp": now
        }


def _normalize_match(match_item):
    """Format standard pour Lovable"""
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
    
    # Best angle
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
    
    # Profile tags fusionnées
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


# Routes principales
@app.route('/')
def index():
    return render_template('dashboard_intelligence.html')


@app.route('/compact')
def compact_dashboard():
    return render_template('dashboard_compact.html')


@app.route('/full')
def full_dashboard():
    return render_template('dashboard.html')


# API Endpoints
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check simple sans erreurs de cache"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "GLOBAL_INTELLIGENCE_WORKING_v1.0",
        "data_loaded": cache["data"] is not None
    })


@app.route('/api/dashboard/summary', methods=['GET', 'OPTIONS'])
def dashboard_summary():
    """GLOBAL FOOTBALL INTELLIGENCE Summary"""
    try:
        data = load_data()

        if not data or not data.get("scan_result"):
            return jsonify({
                "success": False,
                "error": "Scanner failed",
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

        # Normalize
        normalized = [_normalize_match(m) for m in all_raw]

        total = len(normalized)
        target = len(normalized)
        analyzed = sum(1 for m in normalized if m["analyzed"])
        awaiting = total - analyzed
        live = sum(1 for m in normalized if m["status"] == "LIVE")
        finished = sum(1 for m in normalized if m["status"] == "FINISHED")
        opportunities = sum(1 for m in normalized if m["best_angle"]["status"] == "VALUE_DETECTED")

        # Calculer les ligues inférieures/obscures
        lower_leagues = [
            "Championship", "Ligue 2", "2. Bundesliga", "Serie B", "LaLiga2",
            "League One", "League Two", "National League", "Scottish Championship",
            "J3", "K2", "China League One", "China League Two", "Vietnam", "Indonesia", 
            "Ethiopia", "Sudan", "Queensland Premier League", "Bolivia National B", 
            "Kyrgyzstan Premier League", "Iceland Premier League", "Finland Ykkonen",
            "Colombia B League"
        ]
        
        lower_div_matches = [
            m for m in normalized 
            if any(league.lower() in m.get("league", "").lower() for league in lower_leagues)
        ]

        # Profils variés
        profile_diversity = {}
        for match in normalized:
            profiles = match.get("profile_tags", [])
            for profile in profiles:
                profile_diversity[profile] = profile_diversity.get(profile, 0) + 1

        # Hot countries
        country_counts = {}
        for match in normalized:
            country = match.get("country", "Unknown")
            country_counts[country] = country_counts.get(country, 0) + 1
        
        hot_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return jsonify({
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            
            # Statistiques principales
            "total_matches": total,
            "target_matches": target,
            "analyzed_matches": analyzed,
            "awaiting_matches": awaiting,
            "live_matches": live,
            "finished_matches": finished,
            "opportunities_count": opportunities,
            
            # Global Intelligence
            "lower_division_matches": len(lower_div_matches),
            "obscure_competitions": len(set(m.get("league", "") for m in lower_div_matches)),
            "profile_diversity": profile_diversity,
            "unique_profiles": len(profile_diversity),
            "hot_countries": [{"country": c, "matches": m} for c, m in hot_countries],
            
            # Scores moyens
            "avg_confidence_score": sum(m["confidence_score"] for m in normalized) / len(normalized) if normalized else 0,
            "avg_interest_score": sum(m["interest_score"] for m in normalized) / len(normalized) if normalized else 0,
            "avg_volatility_score": sum(m["volatility_score"] for m in normalized) / len(normalized) if normalized else 0,
            
            # Coverage
            "competitions_covered": len(set(m["league"] for m in normalized)),
            "countries_covered": len(set(m["country"] for m in normalized)),
            
            # Data source
            "data_source": data["manager"].is_real_data and "api_football" or "mock",
            "last_refresh": cache.get("timestamp"),
            
            # Architecture info
            "scan_info": {
                "scanner_type": "GLOBAL_FOOTBALL_INTELLIGENCE_SCANNER",
                "architecture": "RELAXED_THRESHOLDS",
                "include_obscure": True,
                "max_analysis": 50,
                "real_data": data["manager"].is_real_data if data.get("manager") else False
            },
            
            # Top matches
            "matches": normalized[:50]
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
    """Matches avec filtres étendus"""
    try:
        data = load_data()
        scan_result = data["scan_result"]
        all_raw = (scan_result.get("analyzed_matches", []) or []) + (scan_result.get("remaining_matches", []) or [])
        
        # Paramètres
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status', 'all')
        country_filter = request.args.get('country', '')
        league_filter = request.args.get('league', '')
        confidence_min = request.args.get('confidence')
        profile_type = request.args.get('profile_type', '')
        analyzed_only = request.args.get('analyzed', 'true')
        
        # Normaliser
        normalized = [_normalize_match(m) for m in all_raw]
        
        # Filtrage
        filtered = normalized
        
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
        
        # Trier
        filtered.sort(key=lambda m: (m.get("interest_score", 0), m.get("confidence_score", 0)), reverse=True)
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        
        return jsonify({
            "success": True,
            "matches": paginated,
            "total_found": total,
            "offset": offset,
            "limit": limit
        })
        
    except Exception as e:
        logger.error(f"Error in get_matches: {e}")
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
    logger.info("Starting GLOBAL FOOTBALL INTELLIGENCE SCANNER (Working Version)...")
    app.run(debug=True, host='0.0.0.0', port=5000)
