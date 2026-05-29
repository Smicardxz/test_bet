"""
Test League Targeting V2
Validates recalibrated targeting system
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.targeting.league_targeting_v2 import (
    LeagueTargetingServiceV2,
    TargetLevel,
    BookmakerCoverageLevel
)


def test_bettable_minor():
    """Test bettable minor leagues"""
    print("\n" + "="*60)
    print(" TEST: BETTABLE MINOR LEAGUES")
    print("="*60)
    
    service = LeagueTargetingServiceV2(include_extreme_obscure=False)
    
    test_cases = [
        ("Premier League", "Kazakhstan"),
        ("V.League 1", "Vietnam"),
        ("Brasileiro Serie B", "Brazil"),
        ("Primera A", "Colombia"),
        ("First League", "Bulgaria"),
        ("Premier League", "Egypt"),
        ("K League 2", "South Korea"),
        ("J2 League", "Japan"),
        ("Copa Libertadores", "South America"),
        ("Women's Super League", "England"),
    ]
    
    for competition, country in test_cases:
        profile = service.analyze_league(competition, country)
        
        print(f"\n{competition} ({country})")
        print(f"  Target Level: {profile.target_level}")
        print(f"  Target Score: {profile.target_score:.0f}/100")
        print(f"  Bookmaker Coverage: {profile.bookmaker_coverage.coverage_score:.0f}/100 ({profile.bookmaker_coverage.coverage_level})")
        print(f"  Likely Markets: {', '.join(profile.bookmaker_coverage.likely_markets[:3])}")
        print(f"  Should Include: {service.should_include(profile)}")
        
        # Assertions
        assert profile.target_level == TargetLevel.BETTABLE_MINOR.value
        assert profile.target_score >= 50
        assert service.should_include(profile)
    
    print("\n✅ All bettable minor leagues passed")


def test_extreme_obscure():
    """Test extreme obscure leagues"""
    print("\n" + "="*60)
    print(" TEST: EXTREME OBSCURE LEAGUES")
    print("="*60)
    
    service = LeagueTargetingServiceV2(include_extreme_obscure=False)
    
    test_cases = [
        ("Liga 3", "Georgia"),
        ("Esiliiga B", "Estonia"),
        ("Esiliiga A", "Estonia"),
        ("Regional Division", "Belarus"),
    ]
    
    for competition, country in test_cases:
        profile = service.analyze_league(competition, country)
        
        print(f"\n{competition} ({country})")
        print(f"  Target Level: {profile.target_level}")
        print(f"  Target Score: {profile.target_score:.0f}/100")
        print(f"  Bookmaker Coverage: {profile.bookmaker_coverage.coverage_score:.0f}/100")
        print(f"  Should Include (extreme_obscure=False): {service.should_include(profile)}")
        
        # Should be extreme obscure
        assert profile.target_level == TargetLevel.EXTREME_OBSCURE.value
        # Should NOT be included when extreme_obscure=False
        assert not service.should_include(profile)
    
    # Test with extreme_obscure=True
    service_with_extreme = LeagueTargetingServiceV2(include_extreme_obscure=True)
    
    for competition, country in test_cases:
        profile = service_with_extreme.analyze_league(competition, country)
        print(f"\n{competition} ({country}) [with extreme_obscure=True]")
        print(f"  Should Include: {service_with_extreme.should_include(profile)}")
    
    print("\n✅ Extreme obscure filtering works correctly")


def test_major_excluded():
    """Test major leagues exclusion"""
    print("\n" + "="*60)
    print(" TEST: MAJOR LEAGUES EXCLUSION")
    print("="*60)
    
    service = LeagueTargetingServiceV2()
    
    test_cases = [
        ("Premier League", "England"),
        ("La Liga", "Spain"),
        ("Serie A", "Italy"),
        ("Bundesliga", "Germany"),
        ("Ligue 1", "France"),
    ]
    
    for competition, country in test_cases:
        profile = service.analyze_league(competition, country)
        
        print(f"\n{competition} ({country})")
        print(f"  Target Level: {profile.target_level}")
        print(f"  Should Include: {service.should_include(profile)}")
        
        # Should be excluded
        assert profile.target_level == TargetLevel.MAJOR_EXCLUDED.value
        assert not service.should_include(profile)
    
    print("\n✅ Major leagues correctly excluded")


def test_bookmaker_coverage():
    """Test bookmaker coverage estimation"""
    print("\n" + "="*60)
    print(" TEST: BOOKMAKER COVERAGE ESTIMATION")
    print("="*60)
    
    service = LeagueTargetingServiceV2()
    
    # High coverage
    profile = service.analyze_league("Copa Libertadores", "South America")
    print(f"\nCopa Libertadores:")
    print(f"  Coverage: {profile.bookmaker_coverage.coverage_score:.0f}/100 ({profile.bookmaker_coverage.coverage_level})")
    print(f"  Markets: {profile.bookmaker_coverage.likely_markets}")
    assert profile.bookmaker_coverage.coverage_level == BookmakerCoverageLevel.HIGH.value
    
    # Medium coverage
    profile = service.analyze_league("Premier League", "Egypt")
    print(f"\nEgypt Premier League:")
    print(f"  Coverage: {profile.bookmaker_coverage.coverage_score:.0f}/100 ({profile.bookmaker_coverage.coverage_level})")
    assert profile.bookmaker_coverage.coverage_level in [BookmakerCoverageLevel.MEDIUM.value, BookmakerCoverageLevel.HIGH.value]
    
    # Low coverage
    profile = service.analyze_league("Liga 3", "Georgia")
    print(f"\nGeorgia Liga 3:")
    print(f"  Coverage: {profile.bookmaker_coverage.coverage_score:.0f}/100 ({profile.bookmaker_coverage.coverage_level})")
    assert profile.bookmaker_coverage.coverage_level == BookmakerCoverageLevel.LOW.value
    
    print("\n✅ Bookmaker coverage estimation works correctly")


def test_priority_countries():
    """Test priority countries"""
    print("\n" + "="*60)
    print(" TEST: PRIORITY COUNTRIES")
    print("="*60)
    
    service = LeagueTargetingServiceV2()
    
    priority_countries = [
        "Kazakhstan", "Vietnam", "Brazil", "Colombia",
        "Egypt", "Bulgaria", "Ethiopia", "South Korea"
    ]
    
    for country in priority_countries:
        profile = service.analyze_league("Division 1", country)
        print(f"\n{country} Division 1:")
        print(f"  Priority Score: {profile.priority_score:.0f}/100")
        print(f"  Target Score: {profile.target_score:.0f}/100")
        
        # Should have decent scores
        assert profile.priority_score >= 50
        assert profile.target_score >= 50
    
    print("\n✅ Priority countries have good scores")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print(" LEAGUE TARGETING V2 - TEST SUITE")
    print("="*60)
    
    try:
        test_bettable_minor()
        test_extreme_obscure()
        test_major_excluded()
        test_bookmaker_coverage()
        test_priority_countries()
        
        print("\n" + "="*60)
        print(" ✅ ALL TESTS PASSED")
        print("="*60)
        print("\n✅ League Targeting V2 is working correctly!")
        print("✅ Bettable minor leagues prioritized")
        print("✅ Extreme obscure leagues filtered")
        print("✅ Bookmaker coverage estimated")
        print("✅ Priority countries boosted")
        print("\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
