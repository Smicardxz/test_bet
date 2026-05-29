"""
Match Analysis Loader
On-demand analysis for selected matches
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.providers.base_provider import BaseDataProvider

logger = logging.getLogger(__name__)


class MatchAnalysisLoader:
    """
    Loads detailed analysis for a single match on-demand
    
    Fetches:
    - Team history
    - H2H data
    - Statistical analysis
    - Anomaly detection
    
    Only when requested by user
    """
    
    def __init__(self, provider: BaseDataProvider, is_real_data: bool = False):
        """Initialize analysis loader"""
        self.provider = provider
        self.is_real_data = is_real_data
        
        # Track API usage
        self.api_requests_count = 0
        
        logger.info("MatchAnalysisLoader initialized")
    
    def analyze_match(
        self,
        match_id: str,
        home_team_id: str,
        away_team_id: str,
        market_type: str = "HT Under"
    ) -> Dict[str, Any]:
        """
        Analyze a single match in detail
        
        Args:
            match_id: Match ID
            home_team_id: Home team ID
            away_team_id: Away team ID
            market_type: Market to analyze
            
        Returns:
            Complete analysis dict
        """
        start_time = datetime.now()
        self.api_requests_count = 0
        
        logger.info(f"Starting analysis for match {match_id}")
        
        result = {
            "success": False,
            "match_id": match_id,
            "error": None,
            "analysis": None,
            "api_requests_used": 0,
            "analysis_duration_seconds": 0
        }
        
        try:
            # Step 1: Fetch home team history (1 API request)
            logger.info("Fetching home team history...")
            home_response = self.provider.get_team_recent_matches(home_team_id, limit=10)
            self.api_requests_count += 1
            
            if not home_response.success:
                result["error"] = f"Failed to fetch home team history: {home_response.error}"
                result["api_requests_used"] = self.api_requests_count
                return result
            
            home_history = home_response.data
            
            # Step 2: Fetch away team history (1 API request)
            logger.info("Fetching away team history...")
            away_response = self.provider.get_team_recent_matches(away_team_id, limit=10)
            self.api_requests_count += 1
            
            if not away_response.success:
                result["error"] = f"Failed to fetch away team history: {away_response.error}"
                result["api_requests_used"] = self.api_requests_count
                return result
            
            away_history = away_response.data
            
            # Step 3: Fetch H2H (1 API request)
            logger.info("Fetching H2H...")
            h2h_response = self.provider.get_head_to_head(home_team_id, away_team_id, limit=10)
            self.api_requests_count += 1
            
            h2h_matches = h2h_response.data if h2h_response.success else []
            
            # Step 4: Calculate statistics (no API calls)
            logger.info("Computing statistics...")
            stats = self._compute_statistics(
                home_history,
                away_history,
                h2h_matches,
                market_type
            )
            
            # Step 5: Run anomaly detection (no API calls)
            logger.info("Running anomaly detection...")
            anomaly = self._detect_anomaly(stats, market_type)
            
            # Build result
            duration = (datetime.now() - start_time).total_seconds()
            
            result.update({
                "success": True,
                "analysis": {
                    "home_history": self._summarize_history(home_history),
                    "away_history": self._summarize_history(away_history),
                    "h2h": self._summarize_h2h(h2h_matches),
                    "statistics": stats,
                    "anomaly": anomaly,
                    "market_type": market_type
                },
                "api_requests_used": self.api_requests_count,
                "analysis_duration_seconds": duration,
                "analyzed_at": datetime.now().isoformat()
            })
            
            logger.info(f"Analysis complete in {duration:.2f}s using {self.api_requests_count} API requests")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            result["error"] = str(e)
            result["api_requests_used"] = self.api_requests_count
        
        return result
    
    def _compute_statistics(
        self,
        home_history: list,
        away_history: list,
        h2h_matches: list,
        market_type: str
    ) -> Dict[str, Any]:
        """Compute statistical metrics"""
        
        # Extract goals from history
        def extract_goals(matches, is_home: bool):
            goals = []
            for match in matches:
                if match.score_fulltime:
                    if is_home:
                        goals.append(match.score_fulltime.home)
                    else:
                        goals.append(match.score_fulltime.away)
            return goals
        
        home_goals_scored = extract_goals(home_history, True)
        away_goals_conceded = extract_goals(away_history, False)
        
        return {
            "home_avg_goals": sum(home_goals_scored) / len(home_goals_scored) if home_goals_scored else 0,
            "away_avg_goals_conceded": sum(away_goals_conceded) / len(away_goals_conceded) if away_goals_conceded else 0,
            "home_sample_size": len(home_goals_scored),
            "away_sample_size": len(away_goals_conceded),
            "h2h_count": len(h2h_matches),
            "data_quality": min(len(home_history), len(away_history)) / 10.0
        }
    
    def _detect_anomaly(self, stats: Dict[str, Any], market_type: str) -> Dict[str, Any]:
        """Run anomaly detection"""
        
        # Simple anomaly detection
        confidence = 0.0
        
        if stats["data_quality"] > 0.5:
            # Check if under pattern
            if market_type == "HT Under":
                avg_total = stats["home_avg_goals"] + stats["away_avg_goals_conceded"]
                if avg_total < 1.0:
                    confidence = 0.7
                elif avg_total < 1.5:
                    confidence = 0.5
        
        return {
            "detected": confidence > 0.5,
            "confidence": confidence,
            "score": confidence * 100,
            "explanation": f"Based on {stats['home_sample_size']} home matches and {stats['away_sample_size']} away matches"
        }
    
    def _summarize_history(self, matches: list) -> Dict[str, Any]:
        """Summarize match history"""
        if not matches:
            return {"count": 0, "available": False}
        
        return {
            "count": len(matches),
            "available": True,
            "recent_results": [
                {
                    "opponent": m.away_team.name if hasattr(m, 'away_team') else "Unknown",
                    "score": f"{m.score_fulltime.home}-{m.score_fulltime.away}" if m.score_fulltime else "N/A"
                }
                for m in matches[:5]
            ]
        }
    
    def _summarize_h2h(self, matches: list) -> Dict[str, Any]:
        """Summarize H2H"""
        if not matches:
            return {"count": 0, "available": False}
        
        return {
            "count": len(matches),
            "available": True
        }
    
    def estimate_cost(self) -> int:
        """Estimate API requests needed for analysis"""
        return 3  # home history + away history + h2h
