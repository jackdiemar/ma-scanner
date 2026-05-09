#!/usr/bin/env python3
"""
DUAL_SCANNER.py - Wrapper that adds Model A + Model B scoring to existing scanner
Runs PRODUCTION_SCANNER_V10.py and enhances results with dual model analysis
"""

import json
import sys
from datetime import datetime
from dual_model_scorer import calculate_dual_scores

def enhance_scan_with_dual_models(scan_file):
    """
    Takes existing scan results and adds Model A/B scores
    """
    
    print("="*80)
    print("BSC DUAL-MODEL ENHANCEMENT")
    print("="*80)
    print(f"\nEnhancing scan: {scan_file}")
    print("Adding Model A (Distressed) + Model B (Strategic) scores...\n")
    
    # Load existing scan
    try:
        with open(scan_file, 'r') as f:
            scan_data = json.load(f)
    except Exception as e:
        print(f"Error loading scan file: {e}")
        return None
    
    results = scan_data.get('results', {})
    enhanced_results = {}
    
    print(f"Processing {len(results)} stocks...\n")
    print("="*80)
    
    for ticker, data in results.items():
        # Prepare stock data for dual scoring
        stock_data = {
            'ticker': ticker,
            'has_c_level_selling': data.get('has_sec', False),
            'has_board_selling': False,  # Would need to enhance SEC scraper
            'cash_runway_quarters': data.get('cash_runway_quarters', 999),
            'market_cap': data.get('market_cap', 0),
            'crash_from_high': data.get('crash_from_high', 0),
            'price_target_upside': data.get('price_target_upside', 0),
            'institutional_ownership': data.get('institutional_ownership', 0),
            'rsi': data.get('rsi', 50),
            'is_profitable': False,  # Would get from financials
            'revenue': 0,  # Would get from FMP
            'revenue_growth_pct': 0,  # Would get from FMP
            'phase3_trials': 0,  # Would get from pipeline scraper
            'has_commercialized_product': False,  # Would get from pipeline
            'has_breakthrough_designation': False,  # Would get from pipeline
            'has_orphan_status': False  # Would get from pipeline
        }
        
        # Calculate dual scores
        dual_result = calculate_dual_scores(stock_data)
        
        # Enhance original data
        enhanced_data = data.copy()
        enhanced_data['dual_model'] = dual_result
        enhanced_data['model_a_score'] = dual_result['model_a_score']
        enhanced_data['model_b_score'] = dual_result['model_b_score']
        enhanced_data['primary_model'] = dual_result['primary_model']
        enhanced_data['recommendation'] = dual_result['recommendation']
        enhanced_data['confidence'] = dual_result['confidence']
        
        enhanced_results[ticker] = enhanced_data
    
    # Sort by primary score
    sorted_results = sorted(
        enhanced_results.items(),
        key=lambda x: x[1]['dual_model']['primary_score'],
        reverse=True
    )
    
    # Display top 10
    print(f"\nTOP 10 STOCKS (Dual-Model Scoring)")
    print("="*80)
    print(f"{'Rank':<6} {'Ticker':<8} {'Model':<7} {'Score':<7} {'Rec':<8} {'Conf':<8}")
    print("-"*80)
    
    for i, (ticker, data) in enumerate(sorted_results[:10], 1):
        dual = data['dual_model']
        model = f"Model {dual['primary_model']}"
        score = dual['primary_score']
        rec = dual['recommendation']
        conf = dual['confidence']
        
        print(f"{i:<6} {ticker:<8} {model:<7} {score:<7.1f} {rec:<8} {conf:<8}")
    
    print("="*80)
    
    # Show BUY signals
    buy_signals = [
        (ticker, data) for ticker, data in sorted_results
        if data['recommendation'] == 'BUY'
    ]
    
    if buy_signals:
        print(f"\n🎯 BUY SIGNALS: {len(buy_signals)}")
        print("="*80)
        
        for ticker, data in buy_signals:
            dual = data['dual_model']
            print(f"\n{ticker} (Model {dual['primary_model']}) - Score: {dual['primary_score']:.1f}")
            print(f"  Confidence: {dual['confidence']}")
            print(f"  Model A: {dual['model_a_score']:.1f} | Model B: {dual['model_b_score']:.1f}")
            print(f"  Top Signals:")
            
            # Show top 3 signals from primary model
            primary_signals = (dual['model_a_signals'] if dual['primary_model'] == 'A' 
                             else dual['model_b_signals'])
            
            for signal_name, signal_pts, model in primary_signals[:3]:
                print(f"    • {signal_name}: +{signal_pts}pts")
    
    # Save enhanced results
    output_file = scan_file.replace('.json', '_DUAL.json')
    scan_data['results'] = enhanced_results
    scan_data['dual_model_metadata'] = {
        'enhanced_at': datetime.now().isoformat(),
        'total_buy_signals': len(buy_signals),
        'models_used': ['A', 'B']
    }
    
    with open(output_file, 'w') as f:
        json.dump(scan_data, f, indent=2)
    
    print(f"\n\n✅ Enhanced results saved to: {output_file}")
    print("="*80)
    
    return enhanced_results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Find most recent scan
        import glob
        scans = glob.glob('scan_v10_*.json')
        if not scans:
            print("No scan files found. Run PRODUCTION_SCANNER_V10.py first.")
            sys.exit(1)
        
        scan_file = max(scans, key=lambda x: x)
        print(f"Using most recent scan: {scan_file}\n")
    else:
        scan_file = sys.argv[1]
    
    enhance_scan_with_dual_models(scan_file)
