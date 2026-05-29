"""
StatsEngine Usage Examples
Demonstrates how to use the StatsEngine for calculating team statistics
"""

import json
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.stats import StatsEngine


def example_basic_usage():
    """Basic usage example"""
    
    print("=" * 60)
    print("EXAMPLE 1: Basic Stats Calculation")
    print("=" * 60)
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # Initialize stats engine
        engine = StatsEngine(db)
        
        # Calculate stats for a team
        team_id = 1
        stats = engine.calculate_team_stats(
            team_id=team_id,
            home_away="all",  # "home", "away", or "all"
            last_n=15  # Last 15 matches
        )
        
        if stats:
            print(f"\n✅ Stats calculated for Team {team_id}")
            print(f"Sample size: {stats.sample_size} matches")
            print(f"Data quality: {stats.data_quality_score:.2%}")
            print(f"\nFull Time:")
            print(f"  Avg total goals: {stats.avg_total_goals:.2f}")
            print(f"  Under 2.5 rate: {stats.under_2_5_rate:.1f}%")
            print(f"  Over 2.5 rate: {stats.over_2_5_rate:.1f}%")
            print(f"  BTTS rate: {stats.btts_rate:.1f}%")
            print(f"\nFirst Half:")
            print(f"  Avg HT goals: {stats.avg_ht_goals:.2f}")
            print(f"  HT 0-0 rate: {stats.ht_0_0_rate:.1f}%")
            print(f"\nStability:")
            print(f"  Consistency score: {stats.consistency_score:.2f}")
            print(f"  Stability score: {stats.stability_score:.2f}")
        else:
            print(f"❌ Insufficient data for Team {team_id}")
    
    finally:
        db.close()


def example_home_away_split():
    """Example with home/away split"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Home/Away Split")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        engine = StatsEngine(db)
        team_id = 1
        
        # Home stats
        home_stats = engine.calculate_team_stats(
            team_id=team_id,
            home_away="home",
            last_n=10
        )
        
        # Away stats
        away_stats = engine.calculate_team_stats(
            team_id=team_id,
            home_away="away",
            last_n=10
        )
        
        if home_stats and away_stats:
            print(f"\n📊 Team {team_id} - Home vs Away")
            print(f"\nGoals Scored:")
            print(f"  Home: {home_stats.avg_goals_scored:.2f}")
            print(f"  Away: {away_stats.avg_goals_scored:.2f}")
            print(f"\nGoals Conceded:")
            print(f"  Home: {home_stats.avg_goals_conceded:.2f}")
            print(f"  Away: {away_stats.avg_goals_conceded:.2f}")
            print(f"\nBTTS Rate:")
            print(f"  Home: {home_stats.btts_rate:.1f}%")
            print(f"  Away: {away_stats.btts_rate:.1f}%")
    
    finally:
        db.close()


def example_json_export():
    """Example exporting stats to JSON"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 3: JSON Export")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        engine = StatsEngine(db)
        
        stats = engine.calculate_team_stats(
            team_id=1,
            home_away="all",
            last_n=15
        )
        
        if stats:
            # Convert to JSON
            stats_json = stats.to_json()
            
            # Pretty print
            print("\n📄 Stats as JSON:")
            print(json.dumps(stats_json, indent=2))
            
            # Save to file
            with open("team_stats.json", "w") as f:
                json.dump(stats_json, f, indent=2)
            
            print("\n✅ Stats saved to team_stats.json")
    
    finally:
        db.close()


def example_multiple_teams():
    """Example calculating stats for multiple teams"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Multiple Teams Comparison")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        engine = StatsEngine(db)
        
        team_ids = [1, 2, 3]
        all_stats = []
        
        for team_id in team_ids:
            stats = engine.calculate_team_stats(
                team_id=team_id,
                home_away="all",
                last_n=15
            )
            if stats:
                all_stats.append(stats)
        
        if all_stats:
            print(f"\n📊 Comparison of {len(all_stats)} teams:")
            print(f"\n{'Team':<20} {'Avg Goals':<12} {'Under 2.5%':<12} {'Stability':<12}")
            print("-" * 60)
            
            for stats in all_stats:
                print(f"{stats.team_name:<20} "
                      f"{stats.avg_total_goals:<12.2f} "
                      f"{stats.under_2_5_rate:<12.1f} "
                      f"{stats.stability_score:<12.2f}")
    
    finally:
        db.close()


def example_data_quality_check():
    """Example checking data quality"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Data Quality Check")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        engine = StatsEngine(db)
        
        stats = engine.calculate_team_stats(
            team_id=1,
            home_away="all",
            last_n=15
        )
        
        if stats:
            print(f"\n🔍 Data Quality Report:")
            print(f"  Sample size: {stats.sample_size} matches")
            print(f"  Missing FT data: {stats.missing_ft_data_count}")
            print(f"  Missing HT data: {stats.missing_ht_data_count}")
            print(f"  Quality score: {stats.data_quality_score:.2%}")
            
            if stats.data_quality_score >= 0.9:
                print("\n  ✅ Excellent data quality")
            elif stats.data_quality_score >= 0.7:
                print("\n  ⚠️ Good data quality")
            else:
                print("\n  ❌ Poor data quality - use with caution")
    
    finally:
        db.close()


def example_trending_analysis():
    """Example analyzing trending metrics"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Trending Analysis")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        engine = StatsEngine(db)
        
        stats = engine.calculate_team_stats(
            team_id=1,
            home_away="all",
            last_n=15
        )
        
        if stats:
            print(f"\n📈 Trending Metrics:")
            print(f"  Last 5 avg goals: {stats.last_5_avg_goals:.2f}")
            print(f"  Last 10 avg goals: {stats.last_10_avg_goals:.2f}")
            print(f"  Overall avg goals: {stats.avg_total_goals:.2f}")
            print(f"\n  Momentum score: {stats.momentum_score:.2f}")
            
            if stats.momentum_score > 0.2:
                print("  📊 Trending UP (improving)")
            elif stats.momentum_score < -0.2:
                print("  📉 Trending DOWN (declining)")
            else:
                print("  ➡️ Stable form")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🚀 StatsEngine Usage Examples\n")
    
    # Run all examples
    example_basic_usage()
    example_home_away_split()
    example_json_export()
    example_multiple_teams()
    example_data_quality_check()
    example_trending_analysis()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed")
    print("=" * 60)
