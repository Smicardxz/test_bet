"""
Mock Dataset Generator - Create realistic test data
Generates obscure leagues with intentional anomalies for testing
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict
from dataclasses import dataclass, asdict


@dataclass
class MockTeam:
    """Mock team data"""
    id: int
    name: str
    league: str
    country: str
    
    # Statistical profile
    avg_goals_scored: float
    avg_goals_conceded: float
    avg_ht_goals: float
    ht_0_0_rate: float  # %
    btts_rate: float  # %
    variance: float
    stability: float


@dataclass
class MockMatch:
    """Mock match data"""
    id: int
    home_team_id: int
    away_team_id: int
    league: str
    match_date: str
    status: str
    
    # Scores
    home_score: int
    away_score: int
    home_score_ht: int
    away_score_ht: int


@dataclass
class MockOdds:
    """Mock bookmaker odds"""
    match_id: int
    
    # FT Under/Over
    under_15_odds: float
    under_25_odds: float
    over_25_odds: float
    under_35_odds: float
    over_35_odds: float
    under_65_odds: float
    under_85_odds: float
    under_105_odds: float
    
    # HT Under/Over
    ht_under_05_odds: float
    ht_over_05_odds: float
    ht_under_15_odds: float
    
    # BTTS
    btts_yes_odds: float
    btts_no_odds: float


class MockDatasetGenerator:
    """
    Generate realistic mock dataset for testing
    
    Features:
    - Obscure leagues (women, youth, lower divisions)
    - Intentional anomalies (strong, weak)
    - Coherent and incoherent lines
    - Various variance profiles
    """
    
    def __init__(self):
        """Initialize generator"""
        self.teams = []
        self.matches = []
        self.odds = []
        
        self.team_id_counter = 1
        self.match_id_counter = 1
    
    def generate_full_dataset(self) -> Dict:
        """
        Generate complete dataset
        
        Returns:
            Dictionary with teams, matches, and odds
        """
        
        print("🎲 Generating mock dataset...")
        
        # Generate teams
        self._generate_obscure_league_teams()
        print(f"   ✅ Generated {len(self.teams)} teams")
        
        # Generate historical matches
        self._generate_historical_matches()
        print(f"   ✅ Generated {len(self.matches)} historical matches")
        
        # Generate odds with anomalies
        self._generate_odds_with_anomalies()
        print(f"   ✅ Generated odds for {len(self.odds)} matches")
        
        # Generate upcoming matches
        upcoming = self._generate_upcoming_matches()
        print(f"   ✅ Generated {len(upcoming)} upcoming matches")
        
        dataset = {
            "teams": [asdict(t) for t in self.teams],
            "historical_matches": [asdict(m) for m in self.matches],
            "upcoming_matches": [asdict(m) for m in upcoming],
            "odds": [asdict(o) for o in self.odds],
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_teams": len(self.teams),
                "total_historical_matches": len(self.matches),
                "total_upcoming_matches": len(upcoming),
                "leagues": list(set(t.league for t in self.teams))
            }
        }
        
        print(f"\n✅ Dataset complete!")
        return dataset
    
    def _generate_obscure_league_teams(self):
        """Generate teams from obscure leagues"""
        
        # Women's leagues
        self._add_womens_league_teams()
        
        # Youth leagues
        self._add_youth_league_teams()
        
        # Lower divisions
        self._add_lower_division_teams()
        
        # Regional leagues
        self._add_regional_league_teams()
    
    def _add_womens_league_teams(self):
        """Add women's league teams"""
        
        league = "England Women's Championship"
        
        # Profile 1: Very defensive teams (HT Under anomalies)
        teams_defensive = [
            ("London City Lionesses Women", 0.6, 0.4, 0.2, 75.0, 25.0, 0.3, 0.85),
            ("Bristol City Women", 0.7, 0.5, 0.3, 70.0, 30.0, 0.35, 0.82),
            ("Charlton Athletic Women", 0.5, 0.3, 0.2, 80.0, 20.0, 0.25, 0.88),
            ("Durham Women", 0.6, 0.4, 0.25, 72.0, 28.0, 0.32, 0.84),
        ]
        
        for name, scored, conceded, ht_goals, ht_00, btts, var, stab in teams_defensive:
            self.teams.append(MockTeam(
                id=self.team_id_counter,
                name=name,
                league=league,
                country="England",
                avg_goals_scored=scored,
                avg_goals_conceded=conceded,
                avg_ht_goals=ht_goals,
                ht_0_0_rate=ht_00,
                btts_rate=btts,
                variance=var,
                stability=stab
            ))
            self.team_id_counter += 1
        
        # Profile 2: Moderate teams
        teams_moderate = [
            ("Lewes Women", 1.2, 1.0, 0.5, 50.0, 55.0, 0.8, 0.65),
            ("Southampton Women", 1.1, 1.1, 0.6, 45.0, 60.0, 0.85, 0.62),
        ]
        
        for name, scored, conceded, ht_goals, ht_00, btts, var, stab in teams_moderate:
            self.teams.append(MockTeam(
                id=self.team_id_counter,
                name=name,
                league=league,
                country="England",
                avg_goals_scored=scored,
                avg_goals_conceded=conceded,
                avg_ht_goals=ht_goals,
                ht_0_0_rate=ht_00,
                btts_rate=btts,
                variance=var,
                stability=stab
            ))
            self.team_id_counter += 1
    
    def _add_youth_league_teams(self):
        """Add youth league teams"""
        
        league = "England U21 Premier League Division 1"
        
        # Profile: High variance, unpredictable
        teams = [
            ("Manchester United U21", 2.5, 1.8, 1.0, 30.0, 70.0, 2.5, 0.45),
            ("Chelsea U21", 2.3, 1.6, 0.9, 35.0, 68.0, 2.3, 0.48),
            ("Arsenal U21", 2.1, 1.9, 0.8, 40.0, 65.0, 2.6, 0.42),
            ("Liverpool U21", 2.4, 2.0, 1.1, 28.0, 72.0, 2.8, 0.40),
        ]
        
        for name, scored, conceded, ht_goals, ht_00, btts, var, stab in teams:
            self.teams.append(MockTeam(
                id=self.team_id_counter,
                name=name,
                league=league,
                country="England",
                avg_goals_scored=scored,
                avg_goals_conceded=conceded,
                avg_ht_goals=ht_goals,
                ht_0_0_rate=ht_00,
                btts_rate=btts,
                variance=var,
                stability=stab
            ))
            self.team_id_counter += 1
    
    def _add_lower_division_teams(self):
        """Add lower division teams"""
        
        league = "England National League North"
        
        # Profile: Very low scoring (Extreme Under anomalies)
        teams = [
            ("Curzon Ashton", 0.8, 0.7, 0.3, 65.0, 35.0, 0.5, 0.78),
            ("Farsley Celtic", 0.9, 0.8, 0.35, 60.0, 40.0, 0.55, 0.75),
            ("Brackley Town", 0.7, 0.6, 0.25, 70.0, 30.0, 0.45, 0.82),
            ("Kidderminster Harriers", 1.0, 0.9, 0.4, 58.0, 42.0, 0.6, 0.72),
            ("Spennymoor Town", 0.8, 0.8, 0.3, 62.0, 38.0, 0.52, 0.76),
            ("Blyth Spartans", 0.9, 1.0, 0.35, 60.0, 40.0, 0.58, 0.70),
        ]
        
        for name, scored, conceded, ht_goals, ht_00, btts, var, stab in teams:
            self.teams.append(MockTeam(
                id=self.team_id_counter,
                name=name,
                league=league,
                country="England",
                avg_goals_scored=scored,
                avg_goals_conceded=conceded,
                avg_ht_goals=ht_goals,
                ht_0_0_rate=ht_00,
                btts_rate=btts,
                variance=var,
                stability=stab
            ))
            self.team_id_counter += 1
    
    def _add_regional_league_teams(self):
        """Add regional league teams"""
        
        league = "France National 3 - Group A"
        
        # Profile: Mixed (for testing various scenarios)
        teams = [
            ("US Avranches", 1.5, 1.2, 0.6, 45.0, 58.0, 1.2, 0.68),
            ("Stade Briochin", 1.3, 1.4, 0.5, 50.0, 52.0, 1.3, 0.65),
            ("Granville", 1.1, 1.0, 0.4, 55.0, 48.0, 0.9, 0.72),
            ("Vitré", 1.4, 1.3, 0.55, 48.0, 55.0, 1.1, 0.66),
        ]
        
        for name, scored, conceded, ht_goals, ht_00, btts, var, stab in teams:
            self.teams.append(MockTeam(
                id=self.team_id_counter,
                name=name,
                league=league,
                country="France",
                avg_goals_scored=scored,
                avg_goals_conceded=conceded,
                avg_ht_goals=ht_goals,
                ht_0_0_rate=ht_00,
                btts_rate=btts,
                variance=var,
                stability=stab
            ))
            self.team_id_counter += 1
    
    def _generate_historical_matches(self):
        """Generate historical matches (last 15 per team)"""
        
        # Group teams by league
        leagues = {}
        for team in self.teams:
            if team.league not in leagues:
                leagues[team.league] = []
            leagues[team.league].append(team)
        
        # Generate matches for each league
        for league, teams in leagues.items():
            if len(teams) < 2:
                continue
            
            # Generate 15 matches per team (home and away)
            for team in teams:
                # Home matches
                for i in range(8):
                    opponent = random.choice([t for t in teams if t.id != team.id])
                    match = self._generate_match(team, opponent, is_home=True, days_ago=i*7+random.randint(1,6))
                    self.matches.append(match)
                
                # Away matches
                for i in range(7):
                    opponent = random.choice([t for t in teams if t.id != team.id])
                    match = self._generate_match(team, opponent, is_home=False, days_ago=i*7+random.randint(1,6))
                    self.matches.append(match)
    
    def _generate_match(self, team: MockTeam, opponent: MockTeam, is_home: bool, days_ago: int) -> MockMatch:
        """Generate a single match based on team profiles"""
        
        if is_home:
            home_team = team
            away_team = opponent
        else:
            home_team = opponent
            away_team = team
        
        # Generate scores based on team profiles
        home_goals = self._generate_goals(home_team.avg_goals_scored, home_team.variance)
        away_goals = self._generate_goals(away_team.avg_goals_scored, away_team.variance)
        
        # Generate HT scores (typically lower)
        home_ht = self._generate_ht_goals(home_team.avg_ht_goals, home_team.ht_0_0_rate)
        away_ht = self._generate_ht_goals(away_team.avg_ht_goals, away_team.ht_0_0_rate)
        
        # Ensure HT <= FT
        home_ht = min(home_ht, home_goals)
        away_ht = min(away_ht, away_goals)
        
        match_date = datetime.utcnow() - timedelta(days=days_ago)
        
        return MockMatch(
            id=self.match_id_counter,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league=home_team.league,
            match_date=match_date.isoformat(),
            status="finished",
            home_score=home_goals,
            away_score=away_goals,
            home_score_ht=home_ht,
            away_score_ht=away_ht
        )
    
    def _generate_goals(self, avg: float, variance: float) -> int:
        """Generate goals with variance"""
        
        # Use Poisson-like distribution with variance
        goals = max(0, int(random.gauss(avg, variance)))
        return min(goals, 8)  # Cap at 8
    
    def _generate_ht_goals(self, avg_ht: float, zero_zero_rate: float) -> int:
        """Generate HT goals"""
        
        # Check if 0-0
        if random.random() * 100 < zero_zero_rate:
            return 0
        
        # Otherwise generate based on average
        return max(0, int(random.gauss(avg_ht, 0.4)))
    
    def _generate_upcoming_matches(self) -> List[MockMatch]:
        """Generate upcoming matches for today"""
        
        upcoming = []
        
        # Group teams by league
        leagues = {}
        for team in self.teams:
            if team.league not in leagues:
                leagues[team.league] = []
            leagues[team.league].append(team)
        
        # Generate 2-3 matches per league
        for league, teams in leagues.items():
            if len(teams) < 2:
                continue
            
            num_matches = random.randint(2, 3)
            used_teams = set()
            
            for _ in range(num_matches):
                available = [t for t in teams if t.id not in used_teams]
                if len(available) < 2:
                    break
                
                home = random.choice(available)
                used_teams.add(home.id)
                available = [t for t in available if t.id != home.id]
                away = random.choice(available)
                used_teams.add(away.id)
                
                match_time = datetime.utcnow() + timedelta(hours=random.randint(2, 10))
                
                self.match_id_counter += 1
                upcoming.append(MockMatch(
                    id=self.match_id_counter,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    league=league,
                    match_date=match_time.isoformat(),
                    status="scheduled",
                    home_score=0,
                    away_score=0,
                    home_score_ht=0,
                    away_score_ht=0
                ))
        
        return upcoming
    
    def _generate_odds_with_anomalies(self):
        """Generate odds with intentional anomalies"""
        
        # Get upcoming matches
        upcoming_matches = [m for m in self.matches if m.status == "scheduled"]
        
        for match in upcoming_matches:
            home_team = next(t for t in self.teams if t.id == match.home_team_id)
            away_team = next(t for t in self.teams if t.id == match.away_team_id)
            
            # Determine anomaly type for this match
            anomaly_type = self._select_anomaly_type(home_team, away_team)
            
            odds = self._generate_odds_for_match(home_team, away_team, anomaly_type)
            odds.match_id = match.id
            
            self.odds.append(odds)
    
    def _select_anomaly_type(self, home: MockTeam, away: MockTeam) -> str:
        """Select anomaly type based on team profiles"""
        
        avg_ht = (home.avg_ht_goals + away.avg_ht_goals) / 2
        avg_ft = (home.avg_goals_scored + away.avg_goals_scored + 
                  home.avg_goals_conceded + away.avg_goals_conceded) / 2
        
        # Very low HT goals → HT Under anomaly
        if avg_ht < 0.4:
            return "ht_under_strong"
        
        # Very low FT goals → Extreme Under anomaly
        elif avg_ft < 1.8:
            return "extreme_under_strong"
        
        # High BTTS rate → BTTS anomaly
        elif (home.btts_rate + away.btts_rate) / 2 > 60:
            return "btts_strong"
        
        # Low variance → Stable anomaly
        elif (home.variance + away.variance) / 2 < 0.6:
            return "stable_under"
        
        # High variance → False positive risk
        elif (home.variance + away.variance) / 2 > 2.0:
            return "high_variance"
        
        # Random mix
        else:
            return random.choice([
                "weak_anomaly",
                "coherent",
                "slight_incoherent"
            ])
    
    def _generate_odds_for_match(self, home: MockTeam, away: MockTeam, anomaly_type: str) -> MockOdds:
        """Generate odds based on anomaly type"""
        
        # Calculate expected probabilities
        avg_total = (home.avg_goals_scored + home.avg_goals_conceded + 
                     away.avg_goals_scored + away.avg_goals_conceded) / 2
        avg_ht = (home.avg_ht_goals + away.avg_ht_goals) / 2
        btts_prob = (home.btts_rate + away.btts_rate) / 200  # Convert to 0-1
        
        if anomaly_type == "ht_under_strong":
            # Strong HT Under anomaly - bookmaker underestimates 0-0 HT
            ht_00_prob = (home.ht_0_0_rate + away.ht_0_0_rate) / 200
            # Bookmaker offers 2.50 (40%) but real is 70%
            ht_under_05_odds = 2.50  # Should be ~1.43
            ht_over_05_odds = 1.60
            
        elif anomaly_type == "extreme_under_strong":
            # Strong Extreme Under anomaly
            under_105_odds = 1.50  # Should be ~1.10
            under_85_odds = 1.40
            under_65_odds = 1.35
            
        elif anomaly_type == "btts_strong":
            # Strong BTTS anomaly
            btts_yes_odds = 2.20  # Should be ~1.50
            btts_no_odds = 1.70
            
        elif anomaly_type == "stable_under":
            # Stable low scoring
            under_25_odds = 2.00  # Should be ~1.60
            over_25_odds = 1.90
            
        elif anomaly_type == "high_variance":
            # High variance - coherent odds but risky
            under_25_odds = 1.90
            over_25_odds = 2.00
            
        elif anomaly_type == "weak_anomaly":
            # Weak anomaly - small discrepancy
            under_25_odds = 2.10  # Should be ~2.00
            over_25_odds = 1.80
            
        elif anomaly_type == "coherent":
            # Coherent odds
            under_25_odds = 2.00
            over_25_odds = 1.95
            
        else:  # slight_incoherent
            # Slightly incoherent
            under_25_odds = 2.30
            over_25_odds = 1.70
        
        # Generate all odds (with some defaults)
        return MockOdds(
            match_id=0,  # Will be set later
            under_15_odds=self._calc_odds(avg_total, 1.5, "under", anomaly_type),
            under_25_odds=self._calc_odds(avg_total, 2.5, "under", anomaly_type),
            over_25_odds=self._calc_odds(avg_total, 2.5, "over", anomaly_type),
            under_35_odds=self._calc_odds(avg_total, 3.5, "under", anomaly_type),
            over_35_odds=self._calc_odds(avg_total, 3.5, "over", anomaly_type),
            under_65_odds=self._calc_odds(avg_total, 6.5, "under", anomaly_type),
            under_85_odds=self._calc_odds(avg_total, 8.5, "under", anomaly_type),
            under_105_odds=self._calc_odds(avg_total, 10.5, "under", anomaly_type),
            ht_under_05_odds=self._calc_ht_odds(avg_ht, 0.5, "under", anomaly_type),
            ht_over_05_odds=self._calc_ht_odds(avg_ht, 0.5, "over", anomaly_type),
            ht_under_15_odds=self._calc_ht_odds(avg_ht, 1.5, "under", anomaly_type),
            btts_yes_odds=self._calc_btts_odds(btts_prob, anomaly_type),
            btts_no_odds=self._calc_btts_odds(1 - btts_prob, anomaly_type)
        )
    
    def _calc_odds(self, avg: float, line: float, direction: str, anomaly: str) -> float:
        """Calculate odds with anomaly adjustment"""
        
        # Base probability (simplified Poisson)
        if direction == "under":
            base_prob = min(0.95, max(0.05, 1 - (avg / (line + 1))))
        else:
            base_prob = min(0.95, max(0.05, avg / (line + 1)))
        
        # Adjust for anomaly
        if "strong" in anomaly and direction == "under":
            base_prob *= 0.7  # Bookmaker underestimates
        elif "weak" in anomaly:
            base_prob *= 0.95
        
        # Convert to odds with margin
        odds = (1 / base_prob) * 1.05
        return round(odds, 2)
    
    def _calc_ht_odds(self, avg_ht: float, line: float, direction: str, anomaly: str) -> float:
        """Calculate HT odds"""
        
        if direction == "under":
            base_prob = min(0.95, max(0.10, 1 - (avg_ht / (line + 0.5))))
        else:
            base_prob = min(0.95, max(0.10, avg_ht / (line + 0.5)))
        
        # Strong HT anomaly
        if anomaly == "ht_under_strong" and direction == "under":
            base_prob *= 0.6
        
        odds = (1 / base_prob) * 1.05
        return round(odds, 2)
    
    def _calc_btts_odds(self, prob: float, anomaly: str) -> float:
        """Calculate BTTS odds"""
        
        if anomaly == "btts_strong":
            prob *= 0.7
        
        odds = (1 / max(0.1, prob)) * 1.05
        return round(odds, 2)


def generate_and_save_dataset():
    """Generate dataset and save to JSON files"""
    
    generator = MockDatasetGenerator()
    dataset = generator.generate_full_dataset()
    
    # Save complete dataset
    with open("mock_dataset_complete.json", "w") as f:
        json.dump(dataset, f, indent=2)
    
    print(f"\n💾 Saved complete dataset to mock_dataset_complete.json")
    
    # Save separate files for easier import
    with open("mock_teams.json", "w") as f:
        json.dump(dataset["teams"], f, indent=2)
    
    with open("mock_matches.json", "w") as f:
        json.dump(dataset["historical_matches"], f, indent=2)
    
    with open("mock_upcoming.json", "w") as f:
        json.dump(dataset["upcoming_matches"], f, indent=2)
    
    with open("mock_odds.json", "w") as f:
        json.dump(dataset["odds"], f, indent=2)
    
    print(f"💾 Saved separate files:")
    print(f"   - mock_teams.json ({len(dataset['teams'])} teams)")
    print(f"   - mock_matches.json ({len(dataset['historical_matches'])} matches)")
    print(f"   - mock_upcoming.json ({len(dataset['upcoming_matches'])} matches)")
    print(f"   - mock_odds.json ({len(dataset['odds'])} odds)")
    
    # Print summary
    print(f"\n📊 Dataset Summary:")
    print(f"   Leagues: {len(dataset['metadata']['leagues'])}")
    for league in dataset['metadata']['leagues']:
        teams_in_league = [t for t in dataset['teams'] if t['league'] == league]
        print(f"   - {league}: {len(teams_in_league)} teams")
    
    return dataset


if __name__ == "__main__":
    generate_and_save_dataset()
