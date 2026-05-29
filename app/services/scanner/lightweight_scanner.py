"""
Lightweight Match Scanner
Fast loading without deep analysis
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from app.providers.base_provider import BaseDataProvider
from app.services.targeting import LeagueTargetingService, TargetMode

logger = logging.getLogger(__name__)


class LightweightMatchScanner:
    """
    Lightweight scanner for fast dashboard loading
    
    Only fetches:
    - Today's matches
    - Basic metadata
    - League targeting
    
    Does NOT fetch:
    - Team history
    - H2H data
    - Statistical analysis
    - Odds details
    """
    
    def __init__(self, provider: BaseDataProvider, is_real_data: bool = False):
        """Initialize lightweight scanner"""
        self.provider = provider
        self.is_real_data = is_real_data
        self.targeting = LeagueTargetingService(TargetMode.ALL_MINOR)
        
        logger.info(f"LightweightMatchScanner initialized (real_data={is_real_data})")
    
    def scan_today(self) -> Dict[str, Any]:
        """
        Scan today's matches - FAST
        
        Returns:
            Dict with matches and metadata
        """
        start_time = datetime.now()
        
        logger.info("Starting lightweight scan...")
        
        # Fetch today's matches (1 API request)
        response = self.provider.get_today_matches()
        
        if not response.success:
            logger.error(f"Failed to fetch matches: {response.error}")
            return {
                "success": False,
                "error": response.error,
                "matches": [],
                "api_requests_used": 1
            }
        
        matches = response.data
        logger.info(f"Fetched {len(matches)} matches")
        
        # Enrich with targeting info (no API calls)
        enriched_matches = []
        
        for match in matches:
            # Analyze league
            profile = self.targeting.analyze_competition(
                match.competition.name,
                match.competition.country
            )
            
            # Create lightweight match object
            enriched_match = {
                "match_id": match.id,
                "home_team": match.home_team.name,
                "away_team": match.away_team.name,
                "competition": match.competition.name,
                "country": match.competition.country,
                "kickoff_time": match.match_date.isoformat(),
                "status": match.status.value,
                
                # League targeting
                "target_score": profile.target_score,
                "is_lower_league": profile.is_lower_league,
                "is_obscure": profile.is_obscure,
                "is_women": profile.is_women,
                "is_youth": profile.is_youth,
                "is_reserve": profile.is_reserve,
                "is_major_league": profile.is_major_league,
                "reason_tags": profile.reason_tags,
                
                # Metadata
                "data_source": "REAL" if self.is_real_data else "MOCK",
                "provider": self.provider.config.name,
                
                # Analysis status
                "analyzed": False,
                "analysis_available": False
            }
            
            enriched_matches.append(enriched_match)
        
        # Filter target matches
        target_matches = [
            m for m in enriched_matches
            if self.targeting.should_include_from_dict(m)
        ]
        
        # Sort by target score
        target_matches.sort(key=lambda x: x["target_score"], reverse=True)
        
        # Calculate stats
        duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            "success": True,
            "error": None,
            
            # Matches
            "all_matches": enriched_matches,
            "target_matches": target_matches,
            
            # Stats
            "total_matches": len(matches),
            "target_count": len(target_matches),
            "countries": len(set(m["country"] for m in enriched_matches)),
            "competitions": len(set(m["competition"] for m in enriched_matches)),
            
            # Categories
            "women_count": sum(1 for m in target_matches if m["is_women"]),
            "youth_count": sum(1 for m in target_matches if m["is_youth"]),
            "reserve_count": sum(1 for m in target_matches if m["is_reserve"]),
            "lower_division_count": sum(1 for m in target_matches if m["is_lower_league"]),
            "obscure_count": sum(1 for m in target_matches if m["is_obscure"]),
            
            # Performance
            "scan_duration_seconds": duration,
            "api_requests_used": 1,  # Only get_today_matches()
            
            # Metadata
            "scan_timestamp": datetime.now().isoformat(),
            "data_source": "REAL" if self.is_real_data else "MOCK",
            "provider": self.provider.config.name
        }
        
        logger.info(f"Lightweight scan complete in {duration:.2f}s")
        logger.info(f"Found {len(target_matches)} target matches out of {len(matches)} total")
        
        return result
    
    def _should_include_from_dict(self, match_dict: Dict[str, Any]) -> bool:
        """Check if match should be included based on targeting"""
        # Create minimal profile
        class MinimalProfile:
            def __init__(self, d):
                self.target_score = d["target_score"]
                self.is_major_league = d["is_major_league"]
                self.is_women = d["is_women"]
                self.is_youth = d["is_youth"]
                self.is_reserve = d["is_reserve"]
                self.is_lower_league = d["is_lower_league"]
                self.is_obscure = d["is_obscure"]
        
        profile = MinimalProfile(match_dict)
        return self.targeting.should_include(profile)


# Helper for targeting service
def should_include_from_dict(targeting_service, match_dict: Dict[str, Any]) -> bool:
    """Helper to check targeting from dict"""
    class MinimalProfile:
        def __init__(self, d):
            self.target_score = d["target_score"]
            self.is_major_league = d["is_major_league"]
            self.is_women = d["is_women"]
            self.is_youth = d["is_youth"]
            self.is_reserve = d["is_reserve"]
            self.is_lower_league = d["is_lower_league"]
            self.is_obscure = d["is_obscure"]
    
    profile = MinimalProfile(match_dict)
    return targeting_service.should_include(profile)


# Monkey patch targeting service
LeagueTargetingService.should_include_from_dict = should_include_from_dict
