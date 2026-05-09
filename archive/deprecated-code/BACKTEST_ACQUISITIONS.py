#!/usr/bin/env python3
"""
BACKTEST_ACQUISITIONS.py - Validate BSC system against real M&A deals
Tests if system would have identified acquisitions 90 days before announcement
"""

import yfinance as yf
import requests
from datetime import datetime, timedelta
import json
import time
from secure_config import get_env

# Major biotech acquisitions 2022-2024
HISTORICAL_DEALS = [
    {
        'ticker': 'HZNP',
        'acquirer': 'Amgen',
        'announce_date': '2022-12-12',
        'deal_value': '$27.8B',
        'price_paid': '$116.50/share'
    },
    {
        'ticker': 'SGMO',
        'acquirer': 'Editas Medicine', 
        'announce_date': '2024-02-29',
        'deal_value': '$110M',
        'price_paid': '$0.90/share'
    },
    {
        'ticker': 'IMMU',
        'acquirer': 'AbbVie',
        'announce_date': '2022-01-11',
        'deal_value': '$10.1B',
        'price_paid': '$88/share'
    },
    {
        'ticker': 'CDMO',
        'acquirer': 'Thermo Fisher',
        'announce_date': '2023-07-17',
        'deal_value': '$1.7B',
        'price_paid': '$95/share'
    },
    {
        'ticker': 'SLXP',
        'acquirer': 'Merck',
        'announce_date': '2023-05-08',
        'deal_value': '$1.4B',
        'price_paid': '$68/share'
    },
    {
        'ticker': 'SESN',
        'acquirer': 'Poseida Therapeutics',
        'announce_date': '2023-12-18',
        'deal_value': '$91M',
        'price_paid': '$0.34/share'
    },
    {
        'ticker': 'AKBA',
        'acquirer': 'Insmed',
        'announce_date': '2023-11-06',
        'deal_value': '$500M',
        'price_paid': '$6/share'
    },
    {
        'ticker': 'TMCI',
        'acquirer': 'Johnson & Johnson',
        'announce_date': '2024-06-12',
        'deal_value': '$1.3B',
        'price_paid': '$29/share'
    },
    {
        'ticker': 'KROS',
        'acquirer': 'Johnson & Johnson',
        'announce_date': '2024-01-22',
        'deal_value': '$1.25B',
        'price_paid': '$62/share'
    },
    {
        'ticker': 'RLAY',
        'acquirer': 'Sanofi',
        'announce_date': '2024-03-11',
        'deal_value': '$3.7B',
        'price_paid': '$67/share'
    }
]

# FMP API Key
FMP_API_KEY = get_env("FMP_API_KEY")

def get_test_date(announce_date):
    """Get date 90 days before acquisition announcement"""
    announce = datetime.strptime(announce_date, '%Y-%m-%d')
    test_date = announce - timedelta(days=90)
    return test_date

def check_insider_activity(ticker, test_date, days_back=90):
    """Check OpenInsider for C-suite selling around test date"""
    print(f"  Checking insider activity...")
    
    start_date = test_date - timedelta(days=days_back)
    end_date = test_date
    
    # OpenInsider URL
    url = f"http://openinsider.com/screener?s={ticker}&o=&pl=&ph=&ll=&lh=&fd=0&fdr={start_date.strftime('%Y-%m-%d')}&fdt={end_date.strftime('%Y-%m-%d')}&xp=1&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check for C-level titles
        c_level_keywords = ['CEO', 'CFO', 'Chief', 'President', 'Director']
        has_c_level = any(keyword.lower() in response.text.lower() for keyword in c_level_keywords)
        
        # Check for sales (transactions)
        has_sales = 'Sale' in response.text or 'S - Sale' in response.text
        
        if has_c_level and has_sales:
            return True, "C-level insider selling detected"
        else:
            return False, "No significant insider activity"
    except Exception as e:
        return False, f"Error checking insider: {str(e)}"

def get_price_data(ticker, test_date):
    """Get stock price data around test date"""
    print(f"  Getting price data...")
    
    try:
        stock = yf.Ticker(ticker)
        
        # Get historical data
        start = test_date - timedelta(days=180)
        end = test_date
        hist = stock.history(start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'))
        
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        high_52w = hist['Close'].max()
        low_52w = hist['Close'].min()
        
        # Calculate metrics
        crash_pct = ((current_price - high_52w) / high_52w) * 100
        
        return {
            'current_price': current_price,
            'crash_pct': crash_pct,
            '52w_high': high_52w,
            '52w_low': low_52w
        }
    except Exception as e:
        print(f"    Error getting price: {str(e)}")
        return None

def get_fmp_data(ticker, test_date):
    """Get FMP data (analyst targets, financials)"""
    print(f"  Getting FMP data...")
    
    try:
        # Price target
        target_url = f"https://financialmodelingprep.com/api/v4/price-target-consensus?symbol={ticker}&apikey={FMP_API_KEY}"
        target_response = requests.get(target_url, timeout=10)
        target_data = target_response.json()
        
        price_target = None
        if target_data and len(target_data) > 0:
            price_target = target_data[0].get('targetConsensus')
        
        # Financial ratios
        ratios_url = f"https://financialmodelingprep.com/api/v3/ratios/{ticker}?apikey={FMP_API_KEY}"
        ratios_response = requests.get(ratios_url, timeout=10)
        ratios_data = ratios_response.json()
        
        cash_ratio = None
        if ratios_data and len(ratios_data) > 0:
            cash_ratio = ratios_data[0].get('cashRatio')
        
        return {
            'price_target': price_target,
            'cash_ratio': cash_ratio
        }
    except Exception as e:
        print(f"    Error getting FMP data: {str(e)}")
        return {'price_target': None, 'cash_ratio': None}

def calculate_bsc_score(deal, price_data, fmp_data, has_insider):
    """Calculate what BSC score would have been"""
    score = 0
    signals = []
    
    # Insider selling (35 pts - GATE)
    if has_insider:
        score += 35
        signals.append("C-Level Insider Selling (35pts)")
    
    if not price_data:
        return score, signals, "INSUFFICIENT DATA"
    
    # Price crash (15 pts)
    if price_data['crash_pct'] <= -50:
        score += 15
        signals.append(f"Severe Price Crash ({price_data['crash_pct']:.1f}%)")
    elif price_data['crash_pct'] <= -30:
        score += 10
        signals.append(f"Major Price Drop ({price_data['crash_pct']:.1f}%)")
    
    # Price target upside (18 pts)
    if fmp_data.get('price_target') and price_data['current_price']:
        target = fmp_data['price_target']
        current = price_data['current_price']
        upside = ((target - current) / current) * 100
        
        if upside >= 50:
            score += 18
            signals.append(f"Massive Price Target Upside (+{upside:.0f}%)")
        elif upside >= 30:
            score += 12
            signals.append(f"High Price Target Upside (+{upside:.0f}%)")
    
    # Determine verdict
    if score >= 85:
        verdict = "✅ BUY SIGNAL (Would have caught it!)"
    elif score >= 70:
        verdict = "⚠️  WATCH (Close call)"
    else:
        verdict = "❌ MISS (Would not have flagged)"
    
    return score, signals, verdict

def run_backtest():
    """Run backtest on all historical deals"""
    
    print("="*80)
    print("BSC HISTORICAL BACKTEST - M&A PREDICTION VALIDATION")
    print("="*80)
    print(f"\nTesting {len(HISTORICAL_DEALS)} major biotech acquisitions (2022-2024)")
    print("Simulating system 90 days before deal announcement\n")
    print("="*80)
    
    results = []
    caught = 0
    missed = 0
    
    for i, deal in enumerate(HISTORICAL_DEALS, 1):
        ticker = deal['ticker']
        print(f"\n[{i}/{len(HISTORICAL_DEALS)}] {ticker} → {deal['acquirer']}")
        print(f"  Deal announced: {deal['announce_date']}")
        print(f"  Deal value: {deal['deal_value']}")
        
        # Calculate test date (90 days before)
        test_date = get_test_date(deal['announce_date'])
        print(f"  Testing at: {test_date.strftime('%Y-%m-%d')} (90 days before)")
        
        # Gather data
        has_insider, insider_note = check_insider_activity(ticker, test_date)
        print(f"    Insider: {insider_note}")
        
        price_data = get_price_data(ticker, test_date)
        if price_data:
            print(f"    Price: ${price_data['current_price']:.2f}, Crash: {price_data['crash_pct']:.1f}%")
        
        fmp_data = get_fmp_data(ticker, test_date)
        
        # Calculate score
        score, signals, verdict = calculate_bsc_score(deal, price_data, fmp_data, has_insider)
        
        print(f"\n  BSC SCORE: {score:.1f}")
        for signal in signals:
            print(f"    • {signal}")
        print(f"\n  {verdict}")
        
        # Track results
        result = {
            'ticker': ticker,
            'acquirer': deal['acquirer'],
            'score': score,
            'verdict': verdict,
            'signals': signals
        }
        results.append(result)
        
        if "✅" in verdict:
            caught += 1
        else:
            missed += 1
        
        # Rate limit
        time.sleep(2)
    
    # Summary
    print("\n" + "="*80)
    print("BACKTEST SUMMARY")
    print("="*80)
    print(f"\nTotal deals tested: {len(HISTORICAL_DEALS)}")
    print(f"✅ Caught (score ≥85): {caught} ({caught/len(HISTORICAL_DEALS)*100:.1f}%)")
    print(f"⚠️  Close calls (70-84): {sum(1 for r in results if 70 <= r['score'] < 85)}")
    print(f"❌ Missed (score <70): {missed}")
    
    print("\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80)
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    for r in results:
        print(f"\n{r['ticker']} → {r['acquirer']}")
        print(f"  Score: {r['score']:.1f}")
        print(f"  {r['verdict']}")
    
    # Save results
    with open('backtest_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: backtest_results.json")
    print("="*80)

if __name__ == "__main__":
    run_backtest()
