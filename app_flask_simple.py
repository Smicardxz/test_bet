"""
Version Flask SIMPLE avec données de démonstration
Pour tester votre dashboard Lovable avec compétitions inférieures
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Données de démonstration avec compétitions inférieures/obscures
DEMO_DATA = {
    "matches": [
        {
            "match_id": "demo_1",
            "home_team": "Queensland Lions",
            "away_team": "Brisbane Strikers",
            "league": "Queensland Premier League",
            "country": "Australia",
            "match_date": "2026-05-29",
            "kickoff_time": "14:00",
            "status": "UPCOMING",
            "intelligence_score": 85.5,
            "pattern_rarity_score": 78.2,
            "stability_score": 82.1,
            "market_edge_score": 15.3,
            "scoring_profile": "LOW_SCORING",
            "tempo_profile": "SLOW_START_PROFILE",
            "specific_profiles": ["EXTREME_UNDER_PROFILE", "HT_UNDER_PROFILE"],
            "why_interesting": "High intelligence score with rare slow-start pattern",
            "data_quality_score": 0.85,
            "analyzed": True,
            "final_score": 85.5,
            "confidence_score": 82.1,
            "market_type": "UNDER_2_5",
            "bookmaker_odds": 2.10,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_2",
            "home_team": "Negelle Arsi",
            "away_team": "Jimma Aba Jifar",
            "league": "Ethiopia Premier League",
            "country": "Ethiopia",
            "match_date": "2026-05-29",
            "kickoff_time": "16:00",
            "status": "UPCOMING",
            "intelligence_score": 92.3,
            "pattern_rarity_score": 88.7,
            "stability_score": 79.5,
            "market_edge_score": 22.8,
            "scoring_profile": "EXTREME_UNDER",
            "tempo_profile": "LOW_TEMPO",
            "specific_profiles": ["EXTREME_UNDER_PROFILE", "NO_BTTS_PROFILE"],
            "why_interesting": "Extreme under profile with high market edge",
            "data_quality_score": 0.78,
            "analyzed": True,
            "final_score": 92.3,
            "confidence_score": 79.5,
            "market_type": "UNDER_3_5",
            "bookmaker_odds": 1.85,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_3",
            "home_team": "Kyrgyzstan U23",
            "away_team": "Tajikistan U23",
            "league": "Kyrgyzstan Premier League",
            "country": "Kyrgyzstan",
            "match_date": "2026-05-29",
            "kickoff_time": "18:00",
            "status": "UPCOMING",
            "intelligence_score": 76.8,
            "pattern_rarity_score": 82.4,
            "stability_score": 71.2,
            "market_edge_score": 18.9,
            "scoring_profile": "BALANCED_SCORING",
            "tempo_profile": "MEDIUM_TEMPO",
            "specific_profiles": ["BTTS_PROFILE", "VOLATILE_MATCH"],
            "why_interesting": "BTTS tendency with volatile match pattern",
            "data_quality_score": 0.72,
            "analyzed": True,
            "final_score": 76.8,
            "confidence_score": 71.2,
            "market_type": "BTTS_YES",
            "bookmaker_odds": 2.25,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_4",
            "home_team": "Sunderland",
            "away_team": "Preston North End",
            "league": "Championship",
            "country": "England",
            "match_date": "2026-05-29",
            "kickoff_time": "20:00",
            "status": "UPCOMING",
            "intelligence_score": 88.1,
            "pattern_rarity_score": 75.3,
            "stability_score": 85.7,
            "market_edge_score": 12.4,
            "scoring_profile": "LOW_SCORING",
            "tempo_profile": "SLOW_START_PROFILE",
            "specific_profiles": ["HT_UNDER_PROFILE", "SECOND_HALF_EXPLOSION"],
            "why_interesting": "Championship match with second half explosion pattern",
            "data_quality_score": 0.91,
            "analyzed": True,
            "final_score": 88.1,
            "confidence_score": 85.7,
            "market_type": "HT_UNDER_1_5",
            "bookmaker_odds": 1.95,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_5",
            "home_team": "FC Seoul B",
            "away_team": "Incheon United B",
            "league": "K2 League",
            "country": "South Korea",
            "match_date": "2026-05-29",
            "kickoff_time": "12:00",
            "status": "UPCOMING",
            "intelligence_score": 81.4,
            "pattern_rarity_score": 79.8,
            "stability_score": 83.2,
            "market_edge_score": 19.7,
            "scoring_profile": "HIGH_SCORING",
            "tempo_profile": "HIGH_TEMPO",
            "specific_profiles": ["OVER_ACCELERATION", "BTTS_PROFILE"],
            "why_interesting": "K2 League with high tempo and BTTS profile",
            "data_quality_score": 0.68,
            "analyzed": True,
            "final_score": 81.4,
            "confidence_score": 83.2,
            "market_type": "OVER_2_5",
            "bookmaker_odds": 2.15,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_6",
            "home_team": "PSM Makassar",
            "away_team": "Persija Jakarta",
            "league": "Indonesia Liga 1",
            "country": "Indonesia",
            "match_date": "2026-05-29",
            "kickoff_time": "13:30",
            "status": "UPCOMING",
            "intelligence_score": 73.9,
            "pattern_rarity_score": 85.1,
            "stability_score": 69.4,
            "market_edge_score": 25.2,
            "scoring_profile": "BALANCED_SCORING",
            "tempo_profile": "MEDIUM_TEMPO",
            "specific_profiles":["VOLATILE_MATCH", "ASYMMETRIC_SCORING"],
            "why_interesting": "Indonesian league with volatile asymmetric scoring",
            "data_quality_score": 0.65,
            "analyzed": True,
            "final_score": 73.9,
            "confidence_score": 69.4,
            "market_type": "BOTH_TEAMS_TO_SCORE",
            "bookmaker_odds": 2.05,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_7",
            "home_team": "Dundee United",
            "away_team": "Dundee FC",
            "league": "Scottish Championship",
            "country": "Scotland",
            "match_date": "2026-05-29",
            "kickoff_time": "15:00",
            "status": "UPCOMING",
            "intelligence_score": 86.7,
            "pattern_rarity_score": 77.9,
            "stability_score": 88.3,
            "market_edge_score": 14.8,
            "scoring_profile": "LOW_SCORING",
            "tempo_profile": "LOW_TEMPO",
            "specific_profiles": ["EXTREME_UNDER_PROFILE", "CLEAN_SHEET_SPECIALIST"],
            "why_interesting": "Scottish Championship derby with extreme under pattern",
            "data_quality_score": 0.87,
            "analyzed": True,
            "final_score": 86.7,
            "confidence_score": 88.3,
            "market_type": "UNDER_2_5",
            "bookmaker_odds": 1.90,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_8",
            "home_team": "Bolivar B",
            "away_team": "Always Ready B",
            "league": "Bolivia National B",
            "country": "Bolivia",
            "match_date": "2026-05-29",
            "kickoff_time": "19:00",
            "status": "UPCOMING",
            "intelligence_score": 79.2,
            "pattern_rarity_score": 83.6,
            "stability_score": 74.8,
            "market_edge_score": 21.3,
            "scoring_profile": "BALANCED_SCORING",
            "tempo_profile": "MEDIUM_TEMPO",
            "specific_profiles": ["BTTS_PROFILE", "LATE_GOAL_PROFILE"],
            "why_interesting": "Bolivia B league with BTTS and late goal patterns",
            "data_quality_score": 0.61,
            "analyzed": True,
            "final_score": 79.2,
            "confidence_score": 74.8,
            "market_type": "BTTS_YES",
            "bookmaker_odds": 2.30,
            "bookmaker": "Demo Bookmaker"
        }
    ]
}

# Routes pour Lovable
@app.route('/')
def index():
    return render_template('dashboard_intelligence.html')


@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "FLASK_SIMPLE_DEMO_v1.0"
    })


@app.route('/api/dashboard/summary', methods=['GET', 'OPTIONS'])
def dashboard_summary():
    """Summary avec compétitions inférieures/obscures"""
    try:
        matches = DEMO_DATA["matches"]
        
        total = len(matches)
        analyzed = sum(1 for m in matches if m["analyzed"])
        awaiting = total - analyzed
        live = sum(1 for m in matches if m["status"] == "LIVE")
        finished = sum(1 for m in matches if m["status"] == "FINISHED")
        opportunities = sum(1 for m in matches if m.get("intelligence_score", 0) >= 80)
        
        # Calculer les ligues inférieures
        lower_leagues = [
            "Championship", "Ligue 2", "2. Bundesliga", "Serie B", "LaLiga2",
            "League One", "League Two", "National League", "Scottish Championship",
            "J3", "K2", "China FA", "Vietnam", "Indonesia", "Ethiopia", "Sudan",
            "Queensland Premier League", "Bolivia National B", "Kyrgyzstan Premier League"
        ]
        
        lower_div_matches = [
            m for m in matches 
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
            "opportunities_count": opportunities,
            "data_source": "demo_global_intelligence",
            "last_refresh": datetime.utcnow().isoformat(),
            "lower_division_matches": len(lower_div_matches),
            "obscure_competitions": len(set(m.get("league", "") for m in lower_div_matches)),
            "global_intelligence_avg": sum(m.get("intelligence_score", 0) for m in matches) / len(matches),
            "high_intelligence": len([m for m in matches if m.get("intelligence_score", 0) >= 80]),
            "market_edges": len([m for m in matches if m.get("market_edge_score", 0) > 0]),
            "rare_patterns": len([m for m in matches if m.get("pattern_rarity_score", 0) >= 70]),
            "stable_patterns": len([m for m in matches if m.get("stability_score", 0) >= 70]),
            "competitions_covered": len(set(m.get("league", "") for m in matches)),
            "countries_covered": len(set(m.get("country", "") for m in matches))
        })
        
    except Exception as e:
        logger.error(f"Error in dashboard summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/matches', methods=['GET', 'OPTIONS'])
def get_matches():
    """Matches avec filtres pour Lovable"""
    try:
        matches = DEMO_DATA["matches"]
        
        # Paramètres
        limit = int(request.args.get('limit', 50))
        min_intelligence = float(request.args.get('min_intelligence', 0))
        
        # Filtrer
        filtered = [m for m in matches if m.get("intelligence_score", 0) >= min_intelligence]
        
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
        matches = DEMO_DATA["matches"]
        
        # Stats par pays
        countries = {}
        for match in matches:
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
    return jsonify({
        "success": True,
        "message": "Demo data - no refresh needed",
        "timestamp": datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    logger.info("Starting Flask SIMPLE DEMO with lower/obscure competitions...")
    app.run(debug=True, host='0.0.0.0', port=5003)
