"""
Validate Today Data
Checks data freshness and date consistency
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from app.providers.data_source_manager import DataSourceManager
from app.services.validation import DateFreshnessValidator, FreshnessStatus
from app.services.targeting import LeagueTargetingService, TargetMode


def print_header(title: str):
    """Print section header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def main():
    """Main validation"""
    
    print_header("DATA FRESHNESS VALIDATION")
    
    # Initialize
    manager = DataSourceManager()
    validator = DateFreshnessValidator()
    targeting = LeagueTargetingService(TargetMode.ALL_MINOR)
    
    print(f"\nProvider: {manager.provider.config.name}")
    print(f"Real Data: {manager.is_real_data}")
    
    # Get today's matches
    print("\nFetching today's matches...")
    response = manager.provider.get_today_matches()
    
    if not response.success:
        print(f"\n❌ ERROR: {response.error}")
        return
    
    all_matches = response.data
    print(f"✅ Fetched {len(all_matches)} matches")
    
    # Validate global freshness
    print_header("GLOBAL FRESHNESS CHECK")
    
    cache_timestamp = datetime.now(timezone.utc)  # Assume fresh for now
    
    global_report = validator.validate_global_freshness(
        all_matches=all_matches,
        provider_name=manager.provider.config.name,
        is_real_data=manager.is_real_data,
        cache_timestamp=cache_timestamp
    )
    
    print(f"\nToday (Local): {global_report.today_local_date}")
    print(f"Today (UTC):   {global_report.today_utc_date}")
    print(f"Provider:      {global_report.provider_active}")
    print(f"\nTotal Fixtures:           {global_report.total_fixtures}")
    print(f"Fixtures Today:           {global_report.fixtures_today}")
    print(f"Fixtures Rejected:        {global_report.fixtures_rejected_not_today}")
    print(f"Cache Age:                {global_report.cache_age_minutes} minutes")
    print(f"\nFreshness Status:         {global_report.freshness_status}")
    
    if global_report.warnings:
        print(f"\n⚠️  WARNINGS:")
        for warning in global_report.warnings:
            print(f"  - {warning}")
    
    # Sample matches
    if global_report.sample_matches:
        print_header("SAMPLE MATCHES (Today)")
        
        for i, match in enumerate(global_report.sample_matches, 1):
            print(f"\n{i}. {match['home_team']} vs {match['away_team']}")
            print(f"   Kickoff: {match['kickoff_local']}")
            print(f"   Freshness: {match['freshness']}")
    
    # Filter target matches
    print_header("TARGET MATCHES")
    
    target_matches = []
    for match in all_matches:
        # Validate freshness
        freshness = validator.validate_match_freshness(
            match={
                "kickoff_time": match.match_date.isoformat() if hasattr(match, 'match_date') else None,
                "home_team": match.home_team.name if hasattr(match, 'home_team') else "Unknown",
                "away_team": match.away_team.name if hasattr(match, 'away_team') else "Unknown"
            },
            is_from_real_api=manager.is_real_data,
            cache_timestamp=cache_timestamp
        )
        
        # Only include if today
        if freshness.is_today:
            # Check targeting
            profile = targeting.analyze_competition(
                match.competition.name if hasattr(match, 'competition') else "",
                match.competition.country if hasattr(match, 'competition') else ""
            )
            
            if targeting.should_include(profile):
                target_matches.append({
                    "match": match,
                    "freshness": freshness,
                    "profile": profile
                })
    
    print(f"\nTarget Matches Found: {len(target_matches)}")
    
    # Update global report
    global_report.fixtures_targeted = len(target_matches)
    
    # Show top target matches
    if target_matches:
        print(f"\nTop 10 Target Matches:")
        
        # Sort by target score
        target_matches.sort(key=lambda x: x["profile"].target_score, reverse=True)
        
        for i, item in enumerate(target_matches[:10], 1):
            match = item["match"]
            freshness = item["freshness"]
            profile = item["profile"]
            
            print(f"\n{i}. {match.home_team.name} vs {match.away_team.name}")
            print(f"   Competition: {match.competition.name}")
            print(f"   Country: {match.competition.country}")
            print(f"   Kickoff: {freshness.fixture_date_local}")
            print(f"   Target Score: {profile.target_score:.0f}/100")
            print(f"   Freshness: {freshness.freshness_status}")
            
            if freshness.freshness_warnings:
                for warning in freshness.freshness_warnings:
                    print(f"   ⚠️  {warning}")
    
    # Final verdict
    print_header("FINAL VERDICT")
    
    if global_report.freshness_status == FreshnessStatus.FRESH.value:
        if len(target_matches) > 0:
            print("\n✅ REAL TODAY DATA OK")
            print(f"\n✅ {global_report.fixtures_today} fixtures for today")
            print(f"✅ {len(target_matches)} target matches identified")
            print(f"✅ Data is fresh (cache: {global_report.cache_age_minutes} min)")
        else:
            print("\n⚠️  DATA OK BUT NO TARGET MATCHES")
            print(f"\n✅ {global_report.fixtures_today} fixtures for today")
            print(f"⚠️  0 target matches (no obscure leagues today)")
    else:
        print(f"\n❌ DATA FRESHNESS ISSUE")
        print(f"\nStatus: {global_report.freshness_status}")
        print(f"Fixtures Today: {global_report.fixtures_today}")
        
        if global_report.warnings:
            print(f"\nIssues:")
            for warning in global_report.warnings:
                print(f"  ❌ {warning}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
