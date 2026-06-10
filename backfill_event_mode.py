#!/usr/bin/env python3
"""
backfill_event_mode.py
=======================
Manual audit/backfill tool for EVENT_MODE.

This tool:
- Does NOT run continuous scans
- Does NOT create duplicate predictions
- Only backfills event_context for existing rows
- Has --dry-run and --days options
- Is used for manual maintenance and auditing

NO DUPLICATE GUARANTEE:
- This tool NEVER inserts new predictions
- It ONLY updates existing prediction rows
- Uses .update() + .eq() pattern for existing rows
- No save_prediction, insert, or upsert operations
- Safe to run multiple times without creating duplicates

Usage:
    python backfill_event_mode.py --dry-run --days 30
    python backfill_event_mode.py --days 60
    python backfill_event_mode.py --event INTERNATIONAL_FRIENDLY
"""

import argparse
import logging
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill EVENT_MODE for existing predictions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)"
    )
    parser.add_argument(
        "--event",
        type=str,
        help="Filter by specific event context (e.g., WORLD_CUP, INTERNATIONAL_FRIENDLY)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed information about each prediction"
    )
    return parser.parse_args()


def backfill_event_mode(args):
    """Backfill EVENT_MODE for existing predictions."""
    print(f"\n{BOLD}🏆 EVENT MODE BACKFILL TOOL{RESET}")
    print(f"{'='*50}")
    
    try:
        # Import dependencies
        from app.database.supabase_config import get_supabase_config
        from app.database.supabase_repository import get_repository
        from app.services.events.event_mode_tagger import tag_event_mode
        
        # Check database connection
        cfg = get_supabase_config()
        if not cfg.supabase_connected:
            print(f"{RED}❌ Supabase not connected{RESET}")
            return False
        
        repo = get_repository()
        print(f"{GREEN}✅ Database connected{RESET}")
        
        # Show backfill parameters
        print(f"\n{CYAN}📋 Backfill parameters:{RESET}")
        print(f"  Dry run: {args.dry_run}")
        print(f"  Days: {args.days}")
        print(f"  Event filter: {args.event or 'All events'}")
        print(f"  Verbose: {args.verbose}")
        
        # Get existing predictions count
        cutoff_date = (date.today() - timedelta(days=args.days)).isoformat()
        
        base_query = repo._client.table("predictions").select(
            "id, fixture_id, home_team, away_team, league, country, prediction_date, "
            "event_context, event_name, is_event_match, event_phase"
        ).gte("prediction_date", cutoff_date)
        
        if args.event:
            base_query = base_query.eq("event_context", args.event)
        
        result = base_query.execute()
        predictions = result.data or []
        
        print(f"\n{CYAN}📊 Existing predictions:{RESET}")
        print(f"  Total predictions (last {args.days} days): {len(predictions)}")
        
        if args.event:
            print(f"  Filtered by event: {args.event}")
        
        # Count by current event context
        current_breakdown = {}
        for pred in predictions:
            ctx = pred.get("event_context", "DOMESTIC_LEAGUE")
            if ctx not in current_breakdown:
                current_breakdown[ctx] = 0
            current_breakdown[ctx] += 1
        
        print(f"\n{CYAN}📈 Current breakdown:{RESET}")
        for ctx, count in sorted(current_breakdown.items()):
            print(f"  {ctx}: {count}")
        
        # Run tagging
        print(f"\n{CYAN}🔄 Running EVENT_MODE tagging...{RESET}")
        
        # Use the tag_event_mode function with custom query
        from app.services.events.event_mode_tagger import _determine_event_context, _determine_event_name, _determine_event_phase
        
        tagged_count = 0
        event_matches = 0
        domestic_matches = 0
        breakdown = {}
        updates = []
        
        for pred in predictions:
            # Skip if already tagged with non-default values
            if (pred.get("event_context") and pred.get("event_context") != "DOMESTIC_LEAGUE" and 
                pred.get("is_event_match") is not None):
                continue
            
            # Determine event context
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
            
            # Prepare update
            update_data = {
                "id": pred["id"],
                "fixture_id": pred["fixture_id"],
                "home_team": pred["home_team"],
                "away_team": pred["away_team"],
                "league": pred["league"],
                "old_context": pred.get("event_context", "DOMESTIC_LEAGUE"),
                "new_context": event_context,
                "event_name": event_name,
                "event_phase": event_phase,
                "is_event_match": is_event_match
            }
            
            updates.append(update_data)
            tagged_count += 1
            
            # Verbose output
            if args.verbose and tagged_count <= 10:
                print(f"  {pred['home_team']} vs {pred['away_team']}")
                print(f"    League: {pred['league']}")
                print(f"    Context: {pred.get('event_context', 'DOMESTIC_LEAGUE')} → {event_context}")
                print(f"    Event: {event_name}")
                print(f"    Phase: {event_phase}")
                print()
        
        # Apply updates if not dry run
        if not args.dry_run:
            print(f"{CYAN}💾 Applying {len(updates)} updates...{RESET}")
            
            for update in updates:
                update_data = {
                    "event_context": update["new_context"],
                    "event_name": update["event_name"],
                    "is_event_match": update["is_event_match"],
                    "event_phase": update["event_phase"]
                }
                
                # NO DUPLICATE GUARANTEE: Only update existing rows
                # Uses .update() + .eq() to modify existing prediction only
                # Never inserts new predictions or creates duplicates
                repo._client.table("predictions").update(update_data).eq("id", update["id"]).execute()
            
            print(f"{GREEN}✅ {len(updates)} predictions updated (no duplicates created){RESET}")
        else:
            print(f"{YELLOW}⚠️  Dry run - {len(updates)} predictions would be updated{RESET}")
        
        # Show results
        print(f"\n{CYAN}📊 Backfill results:{RESET}")
        print(f"  Predictions tagged: {tagged_count}")
        print(f"  Event matches: {event_matches}")
        print(f"  Domestic matches: {domestic_matches}")
        
        print(f"\n{CYAN}📈 New breakdown:{RESET}")
        for ctx, count in sorted(breakdown.items()):
            print(f"  {ctx}: {count}")
        
        # Specific event counts
        international_friendlies = breakdown.get("INTERNATIONAL_FRIENDLY", 0)
        world_cup_matches = breakdown.get("WORLD_CUP", 0)
        youth_tournaments = breakdown.get("YOUTH_TOURNAMENT", 0)
        
        print(f"\n{CYAN}🎯 Event type breakdown:{RESET}")
        print(f"  International Friendlies: {international_friendlies}")
        print(f"  World Cup matches: {world_cup_matches}")
        print(f"  Youth tournaments: {youth_tournaments}")
        
        # Success message
        if args.dry_run:
            print(f"\n{YELLOW}⚠️  DRY RUN COMPLETE - No changes made{RESET}")
            print(f"Run without --dry-run to apply changes")
        else:
            print(f"\n{GREEN}✅ BACKFILL COMPLETE{RESET}")
            print(f"EVENT_MODE data updated for {len(updates)} predictions")
        
        return True
        
    except Exception as e:
        print(f"{RED}❌ Backfill failed: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    args = parse_arguments()
    
    # Check if EVENT_MODE is enabled
    event_mode_enabled = os.getenv('EVENT_MODE_ENABLED', 'false').lower() == 'true'
    
    if not event_mode_enabled:
        print(f"{YELLOW}⚠️  EVENT_MODE_ENABLED=false in .env{RESET}")
        print(f"Set EVENT_MODE_ENABLED=true to enable EVENT_MODE features")
        return False
    
    success = backfill_event_mode(args)
    
    if success:
        print(f"\n{GREEN}🎉 BACKFILL SUCCESSFUL{RESET}")
        print(f"\n{CYAN}Next steps:{RESET}")
        print(f"  1. Verify with: python audit_event_mode.py --days {args.days}")
        print(f"  2. Check API: curl http://localhost:5000/api/event-mode")
        print(f"  3. Run cycle: python scripts/run_tracking_cycle.py --once")
    else:
        print(f"\n{RED}❌ BACKFILL FAILED{RESET}")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
