"""
app/services/events/event_mode_tagger.py
========================================
Lightweight EVENT_MODE tagging for main tracking cycle.

Purpose:
- Tag existing predictions with event_context fields
- No duplicate API calls or scans
- Works with data already saved by refresh_predictions.py
- Feature flag controlled via EVENT_MODE_ENABLED

Usage:
    from app.services.events.event_mode_tagger import tag_event_mode
    
    result = tag_event_mode(repo, dry_run=False)
"""

import logging
from typing import Dict, Any, Optional
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def tag_event_mode(repo, dry_run: bool = False) -> Dict[str, Any]:
    """
    Lightweight EVENT_MODE tagging for existing predictions.
    
    This function:
    - Updates event_context, event_name, is_event_match, event_phase fields
    - Works only on existing predictions (no API calls)
    - Is idempotent and safe to run multiple times
    - Returns statistics for logging
    
    Args:
        repo: SupabaseRepository instance
        dry_run: If True, only report what would be updated
        
    Returns:
        Dict with tagging statistics
    """
    try:
        # Check if EVENT_MODE is enabled
        import os
        event_mode_enabled = os.getenv('EVENT_MODE_ENABLED', 'false').lower() == 'true'
        
        if not event_mode_enabled:
            logger.info("[EVENT_MODE] EVENT_MODE_ENABLED=false - skipping tagging")
            return {
                "event_mode_enabled": False,
                "event_tagged_predictions": 0,
                "event_matches_detected": 0,
                "domestic_matches": 0,
                "breakdown": {}
            }
        
        logger.info("[EVENT_MODE] Starting lightweight tagging...")
        
        # Get predictions without event_context or with default values
        cutoff_date = (date.today() - timedelta(days=30)).isoformat()
        
        query = repo._client.table("predictions").select(
            "id, fixture_id, home_team, away_team, league, country, prediction_date, "
            "event_context, event_name, is_event_match, event_phase"
        ).gte("prediction_date", cutoff_date)
        
        result = query.execute()
        predictions = result.data or []
        
        if not predictions:
            logger.info("[EVENT_MODE] No predictions found in last 30 days")
            return {
                "event_mode_enabled": True,
                "event_tagged_predictions": 0,
                "event_matches_detected": 0,
                "domestic_matches": 0,
                "breakdown": {}
            }
        
        # Tag each prediction
        tagged_count = 0
        event_matches = 0
        domestic_matches = 0
        breakdown = {}
        
        for pred in predictions:
            # Skip if already tagged with non-default values
            if (pred.get("event_context") and pred.get("event_context") != "DOMESTIC_LEAGUE" and 
                pred.get("is_event_match") is not None):
                continue
            
            # Determine event context based on league name
            league = pred.get("league", "")
            event_context = _determine_event_context(league)
            event_name = _determine_event_name(league, event_context)
            event_phase = _determine_event_phase(league, event_context)
            is_event_match = event_context != "DOMESTIC_LEAGUE"
            
            # Update breakdown
            if event_context not in breakdown:
                breakdown[event_context] = 0
            breakdown[event_context] += 1
            
            if is_event_match:
                event_matches += 1
            else:
                domestic_matches += 1
            
            # Update prediction if not dry_run
            if not dry_run:
                update_data = {
                    "event_context": event_context,
                    "event_name": event_name,
                    "is_event_match": is_event_match,
                    "event_phase": event_phase
                }
                
                repo._client.table("predictions").update(update_data).eq("id", pred["id"]).execute()
                tagged_count += 1
            else:
                tagged_count += 1  # Count for dry-run reporting
        
        # Calculate specific event type counts
        international_friendlies = breakdown.get("INTERNATIONAL_FRIENDLY", 0)
        world_cup_matches = breakdown.get("WORLD_CUP", 0)
        youth_tournaments = breakdown.get("YOUTH_TOURNAMENT", 0)
        
        logger.info(
            f"[EVENT_MODE] Tagging complete: "
            f"tagged={tagged_count}, events={event_matches}, domestic={domestic_matches}"
        )
        
        return {
            "event_mode_enabled": True,
            "event_tagged_predictions": tagged_count,
            "event_matches_detected": event_matches,
            "domestic_matches": domestic_matches,
            "international_friendlies": international_friendlies,
            "world_cup_matches": world_cup_matches,
            "youth_tournaments": youth_tournaments,
            "breakdown": breakdown
        }
        
    except Exception as e:
        logger.error(f"[EVENT_MODE] Tagging failed: {e}")
        return {
            "event_mode_enabled": False,
            "event_tagged_predictions": 0,
            "event_matches_detected": 0,
            "domestic_matches": 0,
            "breakdown": {},
            "error": str(e)
        }


def _determine_event_context(league: str) -> str:
    """Determine event context from league name."""
    if not league:
        return "DOMESTIC_LEAGUE"
    
    league_lower = league.lower()
    
    # World Cup
    if "world cup" in league_lower or "fifa world cup" in league_lower:
        return "WORLD_CUP"
    
    # Continental tournaments
    if any(tournament in league_lower for tournament in [
        "euro", "european championship", "copa america", "afcon", "africa cup",
        "asian cup", "gold cup", "nations league"
    ]):
        return "CONTINENTAL_TOURNAMENT"
    
    # Youth tournaments
    if any(youth in league_lower for youth in [
        "u20", "u21", "u19", "u17", "under-20", "under-21", "under-19",
        "under-17", "youth", "junior"
    ]):
        return "YOUTH_TOURNAMENT"
    
    # International friendlies
    if any(friendly in league_lower for friendly in [
        "friendly", "friendlies", "international friendly"
    ]):
        return "INTERNATIONAL_FRIENDLY"
    
    # Default to domestic
    return "DOMESTIC_LEAGUE"


def _determine_event_name(league: str, event_context: str) -> str:
    """Determine human-readable event name."""
    if not league:
        return "Unknown"
    
    league_lower = league.lower()
    
    # World Cup
    if "world cup" in league_lower or "fifa world cup" in league_lower:
        return "FIFA World Cup 2026"
    
    # Continental tournaments
    if "euro" in league_lower or "european championship" in league_lower:
        return "UEFA European Championship"
    if "copa america" in league_lower:
        return "Copa América"
    if "afcon" in league_lower or "africa cup" in league_lower:
        return "Africa Cup of Nations"
    if "asian cup" in league_lower:
        return "AFC Asian Cup"
    if "gold cup" in league_lower:
        return "CONCACAF Gold Cup"
    if "nations league" in league_lower:
        return "UEFA Nations League"
    
    # Friendlies
    if any(friendly in league_lower for friendly in [
        "friendly", "friendlies", "international friendly"
    ]):
        return "International Friendlies"
    
    # Youth tournaments - use original name
    if any(youth in league_lower for youth in [
        "u20", "u21", "u19", "u17", "under-20", "under-21", "under-19",
        "under-17", "youth", "junior"
    ]):
        return league
    
    # Default
    return league


def _determine_event_phase(league: str, event_context: str) -> str:
    """Determine event phase from league name."""
    if not league:
        return "unknown_phase"
    
    league_lower = league.lower()
    
    # Qualification phases
    if any(qual in league_lower for qual in [
        "qualification", "qualifier", "qualifying"
    ]):
        return "qualification"
    
    # Group stage
    if "group" in league_lower:
        return "group_stage"
    
    # Final phases
    if "final" in league_lower:
        return "final"
    if "semi" in league_lower:
        return "semi_final"
    if any(knockout in league_lower for knockout in [
        "knockout", "round of", "quarter"
    ]):
        return "knockout_round"
    
    # Friendlies
    if any(friendly in league_lower for friendly in [
        "friendly", "friendlies", "international friendly"
    ]):
        return "warmup"
    
    # Default
    return "unknown_phase"


def get_event_mode_status(repo) -> Dict[str, Any]:
    """
    Get current EVENT_MODE status from database.
    
    Returns statistics about event vs domestic predictions.
    """
    try:
        # Get recent predictions with event context
        cutoff_date = (date.today() - timedelta(days=30)).isoformat()
        
        query = repo._client.table("predictions").select(
            "event_context, is_event_match", count="exact"
        ).gte("prediction_date", cutoff_date)
        
        result = query.execute()
        predictions = result.data or []
        
        if not predictions:
            return {
                "total_predictions": 0,
                "event_predictions": 0,
                "domestic_predictions": 0,
                "event_percentage": 0.0,
                "breakdown": {}
            }
        
        # Calculate statistics
        total = len(predictions)
        event_count = len([p for p in predictions if p.get("is_event_match", False)])
        domestic_count = total - event_count
        
        # Breakdown by context
        breakdown = {}
        for p in predictions:
            ctx = p.get("event_context", "DOMESTIC_LEAGUE")
            if ctx not in breakdown:
                breakdown[ctx] = 0
            breakdown[ctx] += 1
        
        return {
            "total_predictions": total,
            "event_predictions": event_count,
            "domestic_predictions": domestic_count,
            "event_percentage": round(event_count * 100.0 / total, 1) if total > 0 else 0.0,
            "breakdown": breakdown
        }
        
    except Exception as e:
        logger.error(f"[EVENT_MODE] Status check failed: {e}")
        return {
            "total_predictions": 0,
            "event_predictions": 0,
            "domestic_predictions": 0,
            "event_percentage": 0.0,
            "breakdown": {},
            "error": str(e)
        }
