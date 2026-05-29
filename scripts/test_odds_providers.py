"""
Test Odds Providers Script
Test and demonstrate odds providers functionality
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.odds import MockOddsProvider, MarketType


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_mock_odds_provider():
    """Test MockOddsProvider"""
    
    print("\n" + "="*80)
    print("TEST: Mock Odds Provider")
    print("="*80)
    
    provider = MockOddsProvider()
    
    # Test 1: Get odds for single match
    print("\n📊 Test 1: Get odds for single match")
    response = provider.get_match_odds("match_001")
    
    if response.success:
        print(f"✅ Success! Found {len(response.data)} odds")
        
        # Display first 5 odds
        for i, odd in enumerate(response.data[:5], 1):
            print(f"\n  {i}. {odd.market_type.value}")
            print(f"     Line: {odd.line}")
            print(f"     Odd: {odd.odd}")
            print(f"     Bookmaker: {odd.bookmaker}")
    else:
        print(f"❌ Error: {response.error}")
    
    # Test 2: Get odds for specific markets
    print("\n" + "="*80)
    print("📊 Test 2: Get odds for specific markets")
    print("="*80)
    
    critical_markets = [
        MarketType.HT_UNDER_05,
        MarketType.FT_UNDER_25,
        MarketType.FT_UNDER_85,
        MarketType.BTTS_YES
    ]
    
    response = provider.get_match_odds("match_002", markets=critical_markets)
    
    if response.success:
        print(f"\n✅ Found odds for {len(response.data)} markets:")
        
        for odd in response.data:
            print(f"\n  • {odd.market_type.value}")
            print(f"    Line: {odd.line if odd.line else 'N/A'}")
            print(f"    Odd: {odd.odd}")
            print(f"    Bookmaker: {odd.bookmaker}")
    
    # Test 3: Get today's odds
    print("\n" + "="*80)
    print("📊 Test 3: Get today's odds")
    print("="*80)
    
    response = provider.get_today_odds()
    
    if response.success:
        print(f"\n✅ Found {len(response.data)} total odds")
        
        # Count by market type
        market_counts = {}
        for odd in response.data:
            market = odd.market_type.value
            market_counts[market] = market_counts.get(market, 0) + 1
        
        print("\nBy market type:")
        for market, count in sorted(market_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {market}: {count}")
    
    # Test 4: Generate anomaly odds
    print("\n" + "="*80)
    print("📊 Test 4: Generate anomaly odds")
    print("="*80)
    
    # Normal odds
    normal_response = provider.get_match_odds("match_003", [MarketType.FT_UNDER_25])
    normal_odd = normal_response.data[0]
    
    print(f"\nNormal odd:")
    print(f"  Market: {normal_odd.market_type.value}")
    print(f"  Odd: {normal_odd.odd}")
    
    # Overvalued anomaly
    overvalued = provider.generate_anomaly_odds(
        "match_003",
        MarketType.FT_UNDER_25,
        anomaly_type="overvalued"
    )
    
    print(f"\nOvervalued anomaly:")
    print(f"  Market: {overvalued.market_type.value}")
    print(f"  Odd: {overvalued.odd}")
    print(f"  Difference: +{((overvalued.odd / normal_odd.odd - 1) * 100):.1f}%")
    
    # Undervalued anomaly
    undervalued = provider.generate_anomaly_odds(
        "match_003",
        MarketType.FT_UNDER_25,
        anomaly_type="undervalued"
    )
    
    print(f"\nUndervalued anomaly:")
    print(f"  Market: {undervalued.market_type.value}")
    print(f"  Odd: {undervalued.odd}")
    print(f"  Difference: {((undervalued.odd / normal_odd.odd - 1) * 100):.1f}%")
    
    return True


def test_priority_markets():
    """Test priority markets configuration"""
    
    print("\n" + "="*80)
    print("TEST: Priority Markets")
    print("="*80)
    
    provider = MockOddsProvider()
    markets = provider.get_priority_markets()
    
    print(f"\n📋 Total priority markets: {len(markets)}")
    
    # Group by category
    ft_under_over = [m for m in markets if m.value.startswith("ft_")]
    ht_under_over = [m for m in markets if m.value.startswith("ht_")]
    btts = [m for m in markets if m.value.startswith("btts_")]
    
    print(f"\nBy category:")
    print(f"  FT Under/Over: {len(ft_under_over)}")
    print(f"  HT Under/Over: {len(ht_under_over)}")
    print(f"  BTTS: {len(btts)}")
    
    print(f"\nAll priority markets:")
    for market in markets:
        print(f"  • {market.value}")
    
    return True


def test_odds_ranges():
    """Test odds value ranges"""
    
    print("\n" + "="*80)
    print("TEST: Odds Value Ranges")
    print("="*80)
    
    provider = MockOddsProvider()
    
    # Test different market types
    test_markets = [
        MarketType.HT_UNDER_05,
        MarketType.FT_UNDER_25,
        MarketType.FT_UNDER_85,
        MarketType.BTTS_YES
    ]
    
    print("\nGenerating 10 odds for each market to check ranges:\n")
    
    for market in test_markets:
        odds_values = []
        
        for i in range(10):
            response = provider.get_match_odds(f"match_{i}", [market])
            if response.success and response.data:
                odds_values.append(response.data[0].odd)
        
        min_odd = min(odds_values)
        max_odd = max(odds_values)
        avg_odd = sum(odds_values) / len(odds_values)
        
        print(f"{market.value}:")
        print(f"  Min: {min_odd:.2f}")
        print(f"  Max: {max_odd:.2f}")
        print(f"  Avg: {avg_odd:.2f}")
        print()
    
    return True


def main():
    """Run all tests"""
    
    print("\n" + "="*80)
    print("🎲 ODDS PROVIDERS TESTS")
    print("="*80)
    
    tests = [
        ("Mock Odds Provider", test_mock_odds_provider),
        ("Priority Markets", test_priority_markets),
        ("Odds Ranges", test_odds_ranges)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test {name} failed: {e}", exc_info=True)
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
