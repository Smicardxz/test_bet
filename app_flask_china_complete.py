"""
Version Flask COMPLETE avec Chine et TOUTES les compétitions inférieures/obscures
Pour votre dashboard Lovable avec le pipeline modifié
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Données COMPLÈTES avec Chine et toutes les ligues inférieures/obscures
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
            "specific_profiles":["BTTS_PROFILE", "LATE_GOAL_PROFILE"],
            "why_interesting": "Bolivia B league with BTTS and late goal patterns",
            "data_quality_score": 0.61,
            "analyzed": True,
            "final_score": 79.2,
            "confidence_score": 74.8,
            "market_type": "BTTS_YES",
            "bookmaker_odds": 2.30,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_9",
            "home_team": "Shanghai Port",
            "away_team": "Beijing Guoan",
            "league": "Chinese Super League",
            "country": "China",
            "match_date": "2026-05-29",
            "kickoff_time": "13:00",
            "status": "UPCOMING",
            "intelligence_score": 87.4,
            "pattern_rarity_score": 81.9,
            "stability_score": 85.2,
            "market_edge_score": 18.6,
            "scoring_profile": "HIGH_SCORING",
            "tempo_profile": "HIGH_TEMPO",
            "specific_profiles": ["OVER_ACCELERATION", "BTTS_PROFILE"],
            "why_interesting": "Chinese Super League with high tempo and over acceleration",
            "data_quality_score": 0.89,
            "analyzed": True,
            "final_score": 87.4,
            "confidence_score": 85.2,
            "market_type": "OVER_2_5",
            "bookmaker_odds": 2.05,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_10",
            "home_team": "Nanjing City",
            "away_team": "Sichuan Jiuniu",
            "league": "China League One",
            "country": "China",
            "match_date": "2026-05-29",
            "kickoff_time": "14:30",
            "status": "UPCOMING",
            "intelligence_score": 83.1,
            "pattern_rarity_score": 86.3,
            "stability_score": 78.7,
            "market_edge_score": 24.1,
            "scoring_profile": "BALANCED_SCORING",
            "tempo_profile": "MEDIUM_TEMPO",
            "specific_profiles": ["VOLATILE_MATCH", "ASYMMETRIC_SCORING"],
            "why_interesting": "China League One with volatile asymmetric scoring patterns",
            "data_quality_score": 0.73,
            "analyzed": True,
            "final_score": 83.1,
            "confidence_score": 78.7,
            "market_type": "BTTS_YES",
            "bookmaker_odds": 2.25,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_11",
            "home_team": "Qingdao Red Lions",
            "away_team": "Dongguan United",
            "league": "China League Two",
            "country": "China",
            "match_date": "2026-05-29",
            "kickoff_time": "16:00",
            "status": "UPCOMING",
            "intelligence_score": 91.8,
            "pattern_rarity_score": 89.4,
            "stability_score": 84.6,
            "market_edge_score": 27.3,
            "scoring_profile": "EXTREME_UNDER",
            "tempo_profile": "LOW_TEMPO",
            "specific_profiles": ["EXTREME_UNDER_PROFILE", "HT_UNDER_PROFILE"],
            "why_interesting": "China League Two with extreme under pattern and high market edge",
            "data_quality_score": 0.67,
            "analyzed": True,
            "final_score": 91.8,
            "confidence_score": 84.6,
            "market_type": "UNDER_2_5",
            "bookmaker_odds": 1.95,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_12",
            "home_team": "Al-Merrikh SC",
            "away_team": "Al-Hilal SC Omdurman",
            "league": "Sudan Premier League",
            "country": "Sudan",
            "match_date": "2026-05-29",
            "kickoff_time": "17:00",
            "status": "UPCOMING",
            "intelligence_score": 84.6,
            "pattern_rarity_score": 80.7,
            "stability_score": 81.3,
            "market_edge_score": 16.9,
            "scoring_profile": "LOW_SCORING",
            "tempo_profile": "MEDIUM_TEMPO",
            "specific_profiles": ["HT_UNDER_PROFILE", "DEAD_FIRST_HALF"],
            "why_interesting": "Sudan Premier League with first half dead pattern",
            "data_quality_score": 0.59,
            "analyzed": True,
            "final_score": 84.6,
            "confidence_score": 81.3,
            "market_type": "UNDER_2_5",
            "bookmaker_odds": 2.00,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_13",
            "home_team": "Vikingur Reykjavik",
            "away_team": "Breidablik",
            "league": "Iceland Premier League",
            "country": "Iceland",
            "match_date": "2026-05-29",
            "kickoff_time": "19:30",
            "status": "UPCOMING",
            "intelligence_score": 77.3,
            "pattern_rarity_score": 84.2,
            "stability_score": 72.8,
            "market_edge_score": 20.4,
            "scoring_profile": "BALANCED_SCORING",
            "tempo_profile": "MEDIUM_TEMPO",
            "specific_profiles": ["BTTS_PROFILE", "LATE_GOAL_PROFILE"],
            "why_interesting": "Iceland Premier League with BTTS and late goal tendencies",
            "data_quality_score": 0.71,
            "analyzed": True,
            "final_score": 77.3,
            "confidence_score": 72.8,
            "market_type": "BTTS_YES",
            "bookmaker_odds": 2.15,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_14",
            "home_team": "HJK Helsinki B",
            "away_team": "IFK Mariehamn B",
            "league": "Finland Ykkonen",
            "country": "Finland",
            "match_date": "2026-05-29",
            "kickoff_time": "18:00",
            "status": "UPCOMING",
            "intelligence_score": 80.9,
            "pattern_rarity_score": 87.1,
            "stability_score": 76.4,
            "market_edge_score": 22.7,
            "scoring_profile": "LOW_SCORING",
            "tempo_profile": "SLOW_START_PROFILE",
            "specific_profiles": ["EXTREME_UNDER_PROFILE", "CLEAN_SHEET_SPECIALIST"],
            "why_interesting": "Finland Ykkonen with extreme under and clean sheet patterns",
            "data_quality_score": 0.64,
            "analyzed": True,
            "final_score": 80.9,
            "confidence_score": 76.4,
            "market_type": "UNDER_2_5",
            "bookmaker_odds": 1.90,
            "bookmaker": "Demo Bookmaker"
        },
        {
            "match_id": "demo_15",
            "home_team": "Colombia B Team",
            "away_team": "Bolivar B Team",
            "league": "Colombia B League",
            "country": "Colombia",
            "match_date": "2026-05-29",
            "kickoff_time": "21:00",
            "status": "UPCOMING",
            "intelligence_score": 82.7,
            "pattern_rarity_score": 79.5,
            "stability_score": 80.1,
            "market_edge_score": 17.8,
            "scoring_profile": "BALANCED_SCORING",
            "tempo_profile": "MEDIUM_TEMPO",
            "specific_profiles": ["BTTS_PROFILE", "VOLATILE_MATCH"],
            "why_interesting": "Colombia B League with volatile BTTS patterns",
            "data_quality_score": 0.58,
            "analyzed": True,
            "final_score": 82.7,
            "confidence_score": 80.1,
            "market_type": "BTTS_YES",
            "bookmaker_odds": 2.20,
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
        "version": "FLASK_CHINA_COMPLETE_v1.0"
    })


@app.route('/api/dashboard/summary', methods=['GET', 'OPTIONS'])
def dashboard_summary():
    """Summary avec TOUTES les compétitions dont la Chine"""
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
            "J3", "K2", "China League One", "China League Two", "Vietnam", "Indonesia", 
            "Ethiopia", "Sudan", "Queensland Premier League", "Bolivia National B", 
            "Kyrgyzstan Premier League", "Iceland Premier League", "Finland Ykkonen",
            "Colombia B League"
        ]
        
        lower_div_matches = [
            m for m in matches 
            if any(league.lower() in m.get("league", "").lower() for league in lower_leagues)
        ]
        
        # Calculer les pays avec le plus de matches
        country_counts = {}
        for match in matches:
            country = match.get("country", "Unknown")
            country_counts[country] = country_counts.get(country, 0) + 1
        
        hot_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return jsonify({
            "success": True,
            "total_matches": total,
            "target_matches": total,
            "analyzed_matches": analyzed,
            "awaiting_matches": awaiting,
            "live_matches": live,
            "finished_matches": finished,
            "opportunities_count": opportunities,
            "data_source": "china_global_intelligence_complete",
            "last_refresh": datetime.utcnow().isoformat(),
            "lower_division_matches": len(lower_div_matches),
            "obscure_competitions": len(set(m.get("league", "") for m in lower_div_matches)),
            "global_intelligence_avg": sum(m.get("intelligence_score", 0) for m in matches) / len(matches),
            "high_intelligence": len([m for m in matches if m.get("intelligence_score", 0) >= 80]),
            "market_edges": len([m for m in matches if m.get("market_edge_score", 0) > 0]),
            "rare_patterns": len([m for m in matches if m.get("pattern_rarity_score", 0) >= 70]),
            "stable_patterns": len([m for m in matches if m.get("stability_score", 0) >= 70]),
            "competitions_covered": len(set(m.get("league", "") for m in matches)),
            "countries_covered": len(set(m.get("country", "") for m in matches)),
            "hot_countries": [{"country": c, "matches": m} for c, m in hot_countries]
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
        country = request.args.get('country', '')
        league = request.args.get('league', '')
        
        # Filtrer
        filtered = [m for m in matches if m.get("intelligence_score", 0) >= min_intelligence]
        
        if country:
            filtered = [m for m in filtered if country.lower() in m.get("country", "").lower()]
        
        if league:
            filtered = [m for m in filtered if league.lower() in m.get("league", "").lower()]
        
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
    """Coverage des ligues (y compris Chine et inférieures)"""
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
        "message": "China Complete data - no refresh needed",
        "timestamp": datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    logger.info("Starting Flask COMPLETE with China and ALL lower/obscure competitions...")
    app.run(debug=True, host='0.0.0.0', port=5005)
