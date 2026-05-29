"""
Data Source Diagnostics
Provides detailed diagnostics about data sources and pipeline status
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class DataSourceDiagnostics:
    """Complete data source diagnostics"""
    
    # Provider info
    data_provider: str
    data_mode: str  # "REAL" | "MOCK" | "MIXED" | "ERROR"
    
    # Source breakdown
    matches_source: str  # "REAL" | "MOCK"
    odds_source: str  # "REAL" | "MOCK" | "MISSING"
    history_source: str  # "REAL" | "MOCK" | "MISSING"
    h2h_source: str  # "REAL" | "MOCK" | "MISSING"
    
    # Date validation
    date_checked: str
    today_date: str
    matches_are_today: bool
    
    # Counts
    real_matches_count: int
    mock_matches_count: int
    outdated_matches_count: int
    
    # Coverage
    competitions_detected: List[str]
    countries_detected: List[str]
    
    # Status
    provider_errors: List[str]
    cache_status: str  # "HIT" | "MISS" | "DISABLED"
    
    # Connection status
    provider_reachable: bool
    api_status: str  # "OK" | "FORBIDDEN" | "ERROR" | "TIMEOUT"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def is_real_data_working(self) -> bool:
        """Check if real data pipeline is working"""
        return (
            self.data_mode == "REAL" and
            self.provider_reachable and
            self.api_status == "OK" and
            self.real_matches_count > 0
        )
    
    def get_status_summary(self) -> str:
        """Get human-readable status summary"""
        if self.is_real_data_working():
            return "✅ REAL DATA PIPELINE OK"
        elif self.data_mode == "MOCK":
            return "🔴 MOCK DATA ONLY (Demo Mode)"
        elif not self.provider_reachable:
            return "❌ REAL DATA NOT CONNECTED (Provider Unreachable)"
        elif self.api_status == "FORBIDDEN":
            return "❌ REAL DATA BLOCKED (API Forbidden 403)"
        elif len(self.provider_errors) > 0:
            return f"⚠️ REAL DATA ERROR ({len(self.provider_errors)} errors)"
        else:
            return "⚠️ REAL DATA UNCERTAIN"


def get_data_source_diagnostics(
    manager,
    scan_data: Dict[str, Any]
) -> DataSourceDiagnostics:
    """
    Get comprehensive data source diagnostics
    
    Args:
        manager: DataSourceManager instance
        scan_data: Scanner output data
        
    Returns:
        DataSourceDiagnostics object
    """
    
    # Basic provider info
    data_provider = manager.provider.config.name
    is_real = manager.is_real_data
    
    # Get scan results
    source_status = scan_data.get("source_status", {})
    single_bets = scan_data.get("single_bets", [])
    
    # Analyze data sources
    real_count = 0
    mock_count = 0
    outdated_count = 0
    
    competitions = set()
    countries = set()
    
    today = date.today()
    
    for bet in single_bets:
        # Check data source
        if bet.get("data_source") == "REAL":
            real_count += 1
        else:
            mock_count += 1
        
        # Check if match is today
        kickoff = bet.get("kickoff_time", "")
        if kickoff:
            try:
                match_date = datetime.fromisoformat(kickoff.replace('Z', '+00:00')).date()
                if match_date != today:
                    outdated_count += 1
            except:
                pass
        
        # Collect competitions and countries
        if bet.get("competition"):
            competitions.add(bet.get("competition"))
        if bet.get("country"):
            countries.add(bet.get("country"))
    
    # Determine data mode
    if real_count > 0 and mock_count == 0:
        data_mode = "REAL"
    elif mock_count > 0 and real_count == 0:
        data_mode = "MOCK"
    elif real_count > 0 and mock_count > 0:
        data_mode = "MIXED"
    else:
        data_mode = "ERROR"
    
    # Check provider reachability
    provider_errors = source_status.get("errors", [])
    provider_reachable = len(provider_errors) == 0
    
    # Determine API status
    api_status = "OK"
    if not provider_reachable:
        if any("403" in str(err) or "Forbidden" in str(err) for err in provider_errors):
            api_status = "FORBIDDEN"
        elif any("timeout" in str(err).lower() for err in provider_errors):
            api_status = "TIMEOUT"
        else:
            api_status = "ERROR"
    
    # Determine source types
    matches_source = "REAL" if is_real and provider_reachable else "MOCK"
    
    # Odds source (check if any bet has real odds)
    has_real_odds = any(
        bet.get("odd") is not None and bet.get("data_source") == "REAL"
        for bet in single_bets
    )
    odds_source = "REAL" if has_real_odds else ("MOCK" if single_bets else "MISSING")
    
    # History and H2H (typically mocked unless explicitly real)
    history_source = "REAL" if is_real and provider_reachable else "MOCK"
    h2h_source = "REAL" if is_real and provider_reachable else "MOCK"
    
    # Cache status
    cache_enabled = manager.config.cache_enabled
    cache_status = "DISABLED" if not cache_enabled else "HIT"
    
    return DataSourceDiagnostics(
        data_provider=data_provider,
        data_mode=data_mode,
        matches_source=matches_source,
        odds_source=odds_source,
        history_source=history_source,
        h2h_source=h2h_source,
        date_checked=datetime.now().isoformat(),
        today_date=today.isoformat(),
        matches_are_today=(outdated_count == 0),
        real_matches_count=real_count,
        mock_matches_count=mock_count,
        outdated_matches_count=outdated_count,
        competitions_detected=sorted(list(competitions)),
        countries_detected=sorted(list(countries)),
        provider_errors=provider_errors,
        cache_status=cache_status,
        provider_reachable=provider_reachable,
        api_status=api_status
    )


def print_diagnostics(diagnostics: DataSourceDiagnostics):
    """Print diagnostics in readable format"""
    
    print("\n" + "="*60)
    print("DATA SOURCE DIAGNOSTICS")
    print("="*60)
    
    print(f"\n{diagnostics.get_status_summary()}\n")
    
    print(f"Provider: {diagnostics.data_provider}")
    print(f"Data Mode: {diagnostics.data_mode}")
    print(f"API Status: {diagnostics.api_status}")
    print(f"Provider Reachable: {'✅ Yes' if diagnostics.provider_reachable else '❌ No'}")
    
    print(f"\nData Sources:")
    print(f"  Matches: {diagnostics.matches_source}")
    print(f"  Odds: {diagnostics.odds_source}")
    print(f"  History: {diagnostics.history_source}")
    print(f"  H2H: {diagnostics.h2h_source}")
    
    print(f"\nMatch Counts:")
    print(f"  Real: {diagnostics.real_matches_count}")
    print(f"  Mock: {diagnostics.mock_matches_count}")
    print(f"  Outdated: {diagnostics.outdated_matches_count}")
    print(f"  Today's matches: {'✅ Yes' if diagnostics.matches_are_today else '⚠️ Some outdated'}")
    
    print(f"\nCoverage:")
    print(f"  Countries: {len(diagnostics.countries_detected)}")
    if diagnostics.countries_detected:
        print(f"    {', '.join(diagnostics.countries_detected[:10])}")
    print(f"  Competitions: {len(diagnostics.competitions_detected)}")
    if diagnostics.competitions_detected:
        for comp in diagnostics.competitions_detected[:10]:
            print(f"    - {comp}")
    
    if diagnostics.provider_errors:
        print(f"\n⚠️ Provider Errors ({len(diagnostics.provider_errors)}):")
        for error in diagnostics.provider_errors[:5]:
            print(f"  - {error}")
    
    print(f"\nCache: {diagnostics.cache_status}")
    print(f"Checked: {diagnostics.date_checked}")
    
    print("\n" + "="*60 + "\n")
