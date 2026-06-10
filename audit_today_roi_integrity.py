#!/usr/bin/env python3
"""
audit_today_roi_integrity.py
============================
ROI / Settlement Integrity Audit for Today Only
"""

import sys
import os
import re
import argparse
from datetime import datetime, date, timezone
from typing import Dict, List, Tuple, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

class TodayROIIntegrityAudit:
    def __init__(self):
        self.repo = None
        self.today = date.today().isoformat()
        self.tracking_reset_at = None
        
    def _get_repo(self):
        """Get repository instance."""
        if self.repo is None:
            try:
                from app.database.supabase_repository import SupabaseRepository, _parse_reset_at
                self.repo = SupabaseRepository()
                self.tracking_reset_at = _parse_reset_at()
            except Exception as e:
                print(f"❌ Failed to initialize repository: {e}")
                return None
        return self.repo
    
    def _parse_reset_at(self) -> str:
        """Parse reset date from environment."""
        from app.database.supabase_repository import _parse_reset_at
        return _parse_reset_at()
    
    def _get_today_predictions(self) -> List[dict]:
        """Get all predictions created today (POST_RESET only)."""
        repo = self._get_repo()
        if not repo:
            return []
        
        try:
            # Get predictions created today
            today_start = datetime.combine(date.today(), datetime.min.time()).isoformat()
            today_end = datetime.combine(date.today(), datetime.max.time()).isoformat()
            
            q = (
                repo._client.table("predictions")
                .select("*")
                .gte("prediction_date", today_start)
                .lte("prediction_date", today_end)
                .order("prediction_date", desc=True)
            )
            
            # Apply POST_RESET filter if available
            if self.tracking_reset_at:
                from app.database.supabase_repository import _apply_since_filter
                q = _apply_since_filter(q, self.tracking_reset_at)
            
            predictions = q.execute().data or []
            print(f"📊 Found {len(predictions)} predictions today")
            
            # Filter by status
            filtered_predictions = []
            for pred in predictions:
                status = pred.get("status", "").upper()
                if status in ["WON", "LOST", "VOID", "PENDING"]:
                    filtered_predictions.append(pred)
            
            print(f"📊 Filtered to {len(filtered_predictions)} valid status predictions")
            return filtered_predictions
            
        except Exception as e:
            print(f"❌ Error fetching today's predictions: {e}")
            return []
    
    def _recompute_profit_loss(self, prediction: dict) -> float:
        """Recompute profit/loss for a prediction."""
        status = prediction.get("status", "").upper()
        bookmaker_odd = prediction.get("bookmaker_odd")
        
        if bookmaker_odd is None or bookmaker_odd < 1.1:
            return 0.0
        
        if status == "WON":
            return float(bookmaker_odd) - 1.0
        elif status == "LOST":
            return -1.0
        elif status == "VOID":
            return 0.0
        elif status == "PENDING":
            return 0.0  # Exclude from ROI
        else:
            return 0.0
    
    def _evaluate_market_result(self, prediction: dict) -> Tuple[str, str]:
        """Evaluate market result and check settlement correctness."""
        market = prediction.get("market", "")
        status = prediction.get("status", "").upper()
        
        # Get match scores
        home_score = prediction.get("home_score")
        away_score = prediction.get("away_score")
        ht_home_score = prediction.get("ht_home_score")
        ht_away_score = prediction.get("ht_away_score")
        
        # Parse market type
        if market.startswith("HT_"):
            period = "HT"
            market_type = market[3:]  # Remove "HT_"
            score_home = ht_home_score
            score_away = ht_away_score
        elif market.startswith("FT_"):
            period = "FT"
            market_type = market[3:]  # Remove "FT_"
            score_home = home_score
            score_away = away_score
        else:
            return "UNKNOWN_MARKET", "UNKNOWN"
        
        # Calculate total goals
        if score_home is not None and score_away is not None:
            total_goals = float(score_home) + float(score_away)
        else:
            return "MISSING_SCORES", "UNKNOWN"
        
        # Evaluate market result
        actual_result = "UNKNOWN"
        
        if market_type.startswith("OVER_"):
            line = float(market_type.split("_")[1])
            actual_result = "OVER" if total_goals > line else "UNDER"
        elif market_type.startswith("UNDER_"):
            line = float(market_type.split("_")[1])
            actual_result = "UNDER" if total_goals < line else "OVER"
        else:
            actual_result = "UNKNOWN"
        
        # Check settlement validity
        expected_result = status
        settlement_valid = True
        
        if expected_result == "WON" and actual_result != expected_result:
            settlement_valid = False
        elif expected_result == "LOST" and actual_result != expected_result:
            settlement_valid = False
        
        return actual_result, "VALID" if settlement_valid else "INVALID"
    
    def phase1_today_summary_by_selection_mode(self, predictions: List[dict]) -> Dict[str, dict]:
        """Phase 1: Today summary by selection_mode."""
        print(f"\n{BOLD}🔍 PHASE 1: TODAY SUMMARY BY SELECTION_MODE{RESET}")
        print(f"{'='*80}")
        
        summary = {}
        
        # Group by selection_mode
        for pred in predictions:
            selection_mode = pred.get("selection_mode", "UNKNOWN")
            if selection_mode not in summary:
                summary[selection_mode] = {
                    'total': 0,
                    'pending': 0,
                    'won': 0,
                    'lost': 0,
                    'void': 0,
                    'settled': 0,
                    'winrate': 0.0,
                    'avg_bookmaker_odd': 0.0,
                    'profit_loss_stored': 0.0,
                    'profit_loss_recomputed': 0.0,
                    'roi_stored': 0.0,
                    'roi_recomputed': 0.0,
                    'real_odds_count': 0,
                    'statistical_accuracy': 0.0
                }
            
            stats = summary[selection_mode]
            stats['total'] += 1
            
            status = pred.get("status", "").upper()
            bookmaker_odd = pred.get("bookmaker_odd")
            
            if status == "PENDING":
                stats['pending'] += 1
            elif status == "WON":
                stats['won'] += 1
                stats['settled'] += 1
            elif status == "LOST":
                stats['lost'] += 1
                stats['settled'] += 1
            elif status == "VOID":
                stats['void'] += 1
                stats['settled'] += 1
            
            # Calculate winrate for settled bets
            if stats['settled'] > 0:
                stats['winrate'] = stats['won'] / stats['settled']
            
            # Average bookmaker odd (real odds only)
            if bookmaker_odd is not None and bookmaker_odd >= 1.1:
                stats['real_odds_count'] += 1
                stats['avg_bookmaker_odd'] = (
                    (stats['avg_bookmaker_odd'] * (stats['real_odds_count'] - 1) + bookmaker_odd) 
                    / stats['real_odds_count']
                )
            
            # Stored profit/loss
            stored_pl = pred.get("profit_loss", 0.0)
            if stored_pl is not None:
                stats['profit_loss_stored'] += float(stored_pl)
            
            # Recomputed profit/loss
            recomputed_pl = self._recompute_profit_loss(pred)
            stats['profit_loss_recomputed'] += recomputed_pl
        
        # Calculate ROI for real odds only
        for mode, stats in summary.items():
            real_odds_bets = stats['real_odds_count']
            if real_odds_bets > 0:
                stats['roi_stored'] = stats['profit_loss_stored'] / real_odds_bets * 100
                stats['roi_recomputed'] = stats['profit_loss_recomputed'] / real_odds_bets * 100
            
            # Statistical accuracy (all settled bets)
            if stats['settled'] > 0:
                stats['statistical_accuracy'] = stats['won'] / stats['settled'] * 100
        
        # Display results
        header = f"{'Selection Mode':<12} {'Total':<6} {'Pending':<8} {'Won':<5} {'Lost':<6} {'Void':<6} {'Settled':<8} {'WinRate':<8} {'AvgOdd':<8} {'ROI_Stored':<11} {'ROI_Recomp':<11}"
        print(f"{header}")
        print(f"{'-'*120}")
        
        for mode, stats in sorted(summary.items()):
            print(f"{mode:<12} {stats['total']:<6} {stats['pending']:<8} {stats['won']:<5} {stats['lost']:<6} {stats['void']:<6} {stats['settled']:<8} {stats['winrate']:<8.1%} {stats['avg_bookmaker_odd']:<8.2f} {stats['roi_stored']:<11.1f} {stats['roi_recomputed']:<11.1f}")
        
        return summary
    
    def phase2_compare_stored_vs_recomputed_pl(self, predictions: List[dict]) -> List[dict]:
        """Phase 2: Compare stored P/L vs recomputed P/L."""
        print(f"\n{BOLD}🔍 PHASE 2: STORED VS RECOMPUTED P/L COMPARISON{RESET}")
        print(f"{'='*80}")
        
        mismatches = []
        
        header = f"{'Prediction ID':<25} {'Match':<20} {'Market':<15} {'Mode':<10} {'Status':<7} {'Odd':<6} {'Stored PL':<11} {'Recomp PL':<11} {'Diff':<8} {'Flag':<12}"
        print(f"{header}")
        print(f"{'-'*130}")
        
        for pred in predictions:
            status = pred.get("status", "").upper()
            if status not in ["WON", "LOST", "VOID"]:
                continue  # Only settled predictions
            
            prediction_id = pred.get("prediction_id", "") or ""
            match = pred.get("fixture_id", "") or ""
            market = pred.get("market", "") or ""
            selection_mode = pred.get("selection_mode", "") or ""
            bookmaker_odd = pred.get("bookmaker_odd") or 0.0
            
            stored_pl = pred.get("profit_loss", 0.0)
            if stored_pl is None:
                stored_pl = 0.0
            else:
                stored_pl = float(stored_pl)
            
            recomputed_pl = self._recompute_profit_loss(pred)
            difference = abs(stored_pl - recomputed_pl)
            
            flag = "PL_MISMATCH" if difference > 0.01 else "OK"
            
            if flag == "PL_MISMATCH" or difference > 0.001:  # Show small differences too
                mismatches.append({
                    'prediction_id': prediction_id,
                    'match': match,
                    'market': market,
                    'selection_mode': selection_mode,
                    'status': status,
                    'bookmaker_odd': bookmaker_odd,
                    'stored_profit_loss': stored_pl,
                    'recomputed_profit_loss': recomputed_pl,
                    'difference': difference,
                    'flag': flag
                })
                
                print(f"{prediction_id:<25} {match:<20} {market:<15} {selection_mode:<10} {status:<7} {bookmaker_odd:<6.2f} {stored_pl:<11.2f} {recomputed_pl:<11.2f} {difference:<8.3f} {flag:<12}")
        
        print(f"\n📊 Found {len(mismatches)} P/L mismatches")
        return mismatches
    
    def phase3_settlement_correctness_audit(self, predictions: List[dict]) -> List[dict]:
        """Phase 3: Settlement correctness audit."""
        print(f"\n{BOLD}🔍 PHASE 3: SETTLEMENT CORRECTNESS AUDIT{RESET}")
        print(f"{'='*80}")
        
        settlement_issues = []
        target_markets = [
            "HT_OVER_0_5", "HT_UNDER_0_5", "HT_OVER_1_5", "HT_UNDER_1_5",
            "FT_OVER_1_5", "FT_UNDER_1_5", "FT_OVER_2_5", "FT_UNDER_2_5",
            "FT_OVER_3_5", "FT_UNDER_3_5"
        ]
        
        header = f"{'Match':<20} {'Market':<15} {'Status':<7} {'Home':<5} {'Away':<5} {'HT_H':<6} {'HT_A':<6} {'Expected':<9} {'Actual':<8} {'Valid':<6}"
        print(f"{header}")
        print(f"{'-'*110}")
        
        for pred in predictions:
            status = pred.get("status", "").upper()
            if status not in ["WON", "LOST", "VOID"]:
                continue  # Only settled predictions
            
            market = pred.get("market", "")
            if market not in target_markets:
                continue  # Only target markets
            
            match = pred.get("fixture_id", "")
            home_score = pred.get("home_score", "")
            away_score = pred.get("away_score", "")
            ht_home_score = pred.get("ht_home_score", "")
            ht_away_score = pred.get("ht_away_score", "")
            
            actual_result, settlement_valid = self._evaluate_market_result(pred)
            
            if settlement_valid == "INVALID":
                settlement_issues.append({
                    'match': match,
                    'market': market,
                    'status': status,
                    'home_score': home_score,
                    'away_score': away_score,
                    'ht_home_score': ht_home_score,
                    'ht_away_score': ht_away_score,
                    'market_result_expected': status,
                    'market_result_actual': actual_result,
                    'settlement_valid': False
                })
            
            print(f"{match:<20} {market:<15} {status:<7} {home_score:<5} {away_score:<5} {ht_home_score:<6} {ht_away_score:<6} {status:<9} {actual_result:<8} {settlement_valid:<6}")
        
        print(f"\n📊 Found {len(settlement_issues)} settlement issues")
        return settlement_issues
    
    def phase4_frontend_parity(self, predictions: List[dict]) -> Dict[str, dict]:
        """Phase 4: Frontend parity comparison."""
        print(f"\n{BOLD}🔍 PHASE 4: FRONTEND PARITY COMPARISON{RESET}")
        print(f"{'='*80}")
        
        # Define frontend scopes
        scopes = {
            'ALL_POST_RESET': predictions,
            'TODAY_ONLY': [p for p in predictions if p.get('prediction_date', '').startswith(self.today)],
            'LIVE_SAFE_ONLY': [p for p in predictions if p.get('selection_mode') == 'LIVE_SAFE'],
            'RESEARCH_ONLY': [p for p in predictions if p.get('selection_mode') == 'RESEARCH'],
            'REAL_ODDS_ONLY': [p for p in predictions if p.get('bookmaker_odd') and p.get('bookmaker_odd') >= 1.1],
            'SETTLED_ONLY': [p for p in predictions if p.get('status', '').upper() in ['WON', 'LOST', 'VOID']]
        }
        
        scope_stats = {}
        
        print(f"{'Scope':<15} {'Total':<6} {'Settled':<8} {'ROI_Stored':<11} {'ROI_Recomp':<11} {'WinRate':<8}")
        print(f"{'-'*80}")
        
        for scope_name, scope_predictions in scopes.items():
            total = len(scope_predictions)
            settled = len([p for p in scope_predictions if p.get('status', '').upper() in ['WON', 'LOST', 'VOID']])
            
            # Calculate ROI
            real_odds_predictions = [p for p in scope_predictions if p.get('bookmaker_odd') and p.get('bookmaker_odd') >= 1.1]
            real_odds_settled = [p for p in real_odds_predictions if p.get('status', '').upper() in ['WON', 'LOST', 'VOID']]
            
            stored_pl = sum(float(p.get('profit_loss', 0.0)) for p in real_odds_settled)
            recomputed_pl = sum(self._recompute_profit_loss(p) for p in real_odds_settled)
            
            roi_stored = (stored_pl / len(real_odds_settled) * 100) if real_odds_settled else 0.0
            roi_recomputed = (recomputed_pl / len(real_odds_settled) * 100) if real_odds_settled else 0.0
            
            winrate = (len([p for p in scope_predictions if p.get('status', '').upper() == 'WON']) / settled * 100) if settled > 0 else 0.0
            
            scope_stats[scope_name] = {
                'total': total,
                'settled': settled,
                'roi_stored': roi_stored,
                'roi_recomputed': roi_recomputed,
                'winrate': winrate,
                'real_odds_count': len(real_odds_settled)
            }
            
            print(f"{scope_name:<15} {total:<6} {settled:<8} {roi_stored:<11.1f} {roi_recomputed:<11.1f} {winrate:<8.1f}")
        
        # Identify which scope might match the negative frontend ROI
        negative_rois = {name: stats for name, stats in scope_stats.items() if stats['roi_stored'] < -10}
        
        if negative_rois:
            print(f"\n{RED}🔍 SCOPES WITH NEGATIVE ROI (Possible Frontend Match):{RESET}")
            for name, stats in negative_rois.items():
                print(f"  {name}: {stats['roi_stored']:.1f}% ROI ({stats['real_odds_count']} real odds bets)")
        else:
            print(f"\n{GREEN}✅ NO SCOPES SHOW STRONGLY NEGATIVE ROI{RESET}")
        
        return scope_stats
    
    def phase5_manual_tracking_reconciliation(self, predictions: List[dict], manual_ids: Optional[List[str]] = None):
        """Phase 5: Manual tracking reconciliation."""
        print(f"\n{BOLD}🔍 PHASE 5: MANUAL TRACKING RECONCILIATION{RESET}")
        print(f"{'='*80}")
        
        if manual_ids:
            # Show ROI/winrate for specific manual IDs
            manual_predictions = [p for p in predictions if p.get('prediction_id') in manual_ids]
            
            print(f"\n📊 Manual Tracking Analysis ({len(manual_predictions)} predictions)")
            
            if manual_predictions:
                # Calculate stats for manual predictions
                settled_manual = [p for p in manual_predictions if p.get('status', '').upper() in ['WON', 'LOST', 'VOID']]
                real_odds_manual = [p for p in settled_manual if p.get('bookmaker_odd') and p.get('bookmaker_odd') >= 1.1]
                
                stored_pl = sum(float(p.get('profit_loss', 0.0)) for p in real_odds_manual)
                recomputed_pl = sum(self._recompute_profit_loss(p) for p in real_odds_manual)
                
                roi_stored = (stored_pl / len(real_odds_manual) * 100) if real_odds_manual else 0.0
                roi_recomputed = (recomputed_pl / len(real_odds_manual) * 100) if real_odds_manual else 0.0
                winrate = (len([p for p in manual_predictions if p.get('status', '').upper() == 'WON']) / len(settled_manual) * 100) if settled_manual else 0.0
                
                print(f"  Total: {len(manual_predictions)}")
                print(f"  Settled: {len(settled_manual)}")
                print(f"  Real Odds: {len(real_odds_manual)}")
                print(f"  Win Rate: {winrate:.1f}%")
                print(f"  ROI (Stored): {roi_stored:.1f}%")
                print(f"  ROI (Recomputed): {roi_recomputed:.1f}%")
                
                # Show individual predictions
                print(f"\n📋 Individual Manual Predictions:")
                header = f"{'Prediction ID':<25} {'Match':<20} {'Market':<15} {'Status':<7} {'Odd':<6} {'P/L':<8}"
                print(f"{header}")
                print(f"{'-'*90}")
                
                for pred in manual_predictions:
                    prediction_id = pred.get('prediction_id', '')
                    match = pred.get('fixture_id', '')
                    market = pred.get('market', '')
                    status = pred.get('status', '')
                    bookmaker_odd = pred.get('bookmaker_odd', 0.0)
                    profit_loss = pred.get('profit_loss', 0.0)
                    
                    print(f"{prediction_id:<25} {match:<20} {market:<15} {status:<7} {bookmaker_odd:<6.2f} {profit_loss:<8.2f}")
            else:
                print(f"  ❌ No manual predictions found")
        else:
            # Show top 50 today predictions
            print(f"\n📊 Top 50 Today Predictions:")
            
            # Sort by creation date
            sorted_predictions = sorted(predictions, key=lambda x: x.get('prediction_date', ''), reverse=True)[:50]
            
            header = f"{'Prediction ID':<25} {'Match':<20} {'Market':<15} {'Mode':<10} {'Status':<7} {'Odd':<6} {'P/L':<8} {'Created':<20}"
            print(f"{header}")
            print(f"{'-'*130}")
            
            for pred in sorted_predictions:
                prediction_id = pred.get('prediction_id', '') or ""
                match = pred.get('fixture_id', '') or ""
                market = pred.get('market', '') or ""
                selection_mode = pred.get('selection_mode', '') or ""
                status = pred.get('status', '') or ""
                bookmaker_odd = pred.get('bookmaker_odd') or 0.0
                profit_loss = pred.get('profit_loss') or 0.0
                created_at = pred.get('prediction_date', '') or ""
                
                print(f"{prediction_id:<25} {match:<20} {market:<15} {selection_mode:<10} {status:<7} {bookmaker_odd:<6.2f} {profit_loss:<8.2f} {created_at:<20}")
    
    def final_verdict(self, summary: Dict[str, dict], mismatches: List[dict], settlement_issues: List[dict], scope_stats: Dict[str, dict]):
        """Generate final verdict."""
        print(f"\n{BOLD}🔍 FINAL VERDICT{RESET}")
        print(f"{'='*80}")
        
        verdict = []
        
        # Check for P/L mismatches
        if mismatches:
            verdict.append("ROI_STORED_PL_BROKEN")
            print(f"{RED}❌ ROI_STORED_PL_BROKEN: Found {len(mismatches)} P/L mismatches{RESET}")
        else:
            print(f"{GREEN}✅ No P/L mismatches found{RESET}")
        
        # Check for settlement issues
        if settlement_issues:
            verdict.append("SETTLEMENT_BROKEN")
            print(f"{RED}❌ SETTLEMENT_BROKEN: Found {len(settlement_issues)} settlement issues{RESET}")
        else:
            print(f"{GREEN}✅ No settlement issues found{RESET}")
        
        # Check for scope mismatch
        negative_scopes = [name for name, stats in scope_stats.items() if stats['roi_stored'] < -10]
        if negative_scopes:
            verdict.append("ROI_OK_FRONT_SCOPE_MISMATCH")
            print(f"{YELLOW}⚠️  ROI_OK_FRONT_SCOPE_MISMATCH: Negative ROI in scopes: {negative_scopes}{RESET}")
        else:
            print(f"{GREEN}✅ No scope mismatches found{RESET}")
        
        # Check for insufficient sample
        total_real_odds = sum(stats['real_odds_count'] for stats in summary.values())
        if total_real_odds < 10:
            verdict.append("INSUFFICIENT_SETTLED_SAMPLE")
            print(f"{YELLOW}⚠️  INSUFFICIENT_SETTLED_SAMPLE: Only {total_real_odds} real odds bets{RESET}")
        else:
            print(f"{GREEN}✅ Sufficient sample: {total_real_odds} real odds bets{RESET}")
        
        # Check for frontend ROI formula issues
        total_stored_roi = sum(stats['roi_stored'] for stats in summary.values() if stats['real_odds_count'] > 0)
        total_recomputed_roi = sum(stats['roi_recomputed'] for stats in summary.values() if stats['real_odds_count'] > 0)
        
        if abs(total_stored_roi - total_recomputed_roi) > 5.0:
            verdict.append("FRONTEND_ROI_FORMULA_BROKEN")
            print(f"{RED}❌ FRONTEND_ROI_FORMULA_BROKEN: Stored ROI {total_stored_roi:.1f}% vs Recomputed {total_recomputed_roi:.1f}%{RESET}")
        else:
            print(f"{GREEN}✅ ROI formulas consistent: Stored {total_stored_roi:.1f}% vs Recomputed {total_recomputed_roi:.1f}%{RESET}")
        
        # Final verdict
        if not verdict:
            verdict = ["ROI_OK_FRONT_SCOPE_MISMATCH"]  # Default if no issues found
        
        print(f"\n{BOLD}FINAL VERDICT:{RESET} {', '.join(verdict)}")
        
        return verdict

def main():
    """Main audit function."""
    parser = argparse.ArgumentParser(description='ROI / Settlement Integrity Audit for Today Only')
    parser.add_argument('--manual', type=str, help='Comma-separated prediction IDs for manual tracking')
    args = parser.parse_args()
    
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 ROI / SETTLEMENT INTEGRITY AUDIT — TODAY ONLY")
    print(f"{'='*80}{RESET}")
    
    audit = TodayROIIntegrityAudit()
    
    # Get today's predictions
    predictions = audit._get_today_predictions()
    
    if not predictions:
        print(f"❌ No predictions found for today")
        return
    
    # Parse manual IDs if provided
    manual_ids = None
    if args.manual:
        manual_ids = [id.strip() for id in args.manual.split(',') if id.strip()]
        print(f"📊 Manual tracking for {len(manual_ids)} prediction IDs")
    
    # Run all phases
    summary = audit.phase1_today_summary_by_selection_mode(predictions)
    mismatches = audit.phase2_compare_stored_vs_recomputed_pl(predictions)
    settlement_issues = audit.phase3_settlement_correctness_audit(predictions)
    scope_stats = audit.phase4_frontend_parity(predictions)
    audit.phase5_manual_tracking_reconciliation(predictions, manual_ids)
    
    # Generate final verdict
    verdict = audit.final_verdict(summary, mismatches, settlement_issues, scope_stats)
    
    print(f"\n{BOLD}🎯 AUDIT COMPLETE{RESET}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
