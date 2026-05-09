#!/usr/bin/env python3
"""
FMP DATA DIAGNOSTIC - Verify analyst and technical data is actually loading
"""

import requests
import json
from datetime import datetime
from secure_config import get_env

API_KEY = get_env("FMP_API_KEY")
BASE_URL = "https://financialmodelingprep.com/stable"

# Test these stocks from your scan
TEST_SYMBOLS = ['KALA', 'ARCT', 'SNGX', 'EDIT', 'CRSP']

def get_fmp(endpoint, params=None):
    """Make FMP API call"""
    params = params or {}
    params['apikey'] = API_KEY
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {'error': str(e)}

print("="*80)
print("FMP DATA DIAGNOSTIC - CHECKING ACTUAL API RESPONSES")
print("="*80)
print()

for symbol in TEST_SYMBOLS:
    print(f"\n{'='*80}")
    print(f"SYMBOL: {symbol}")
    print(f"{'='*80}")
    
    # 1. Price Target Consensus
    print(f"\n1️⃣  PRICE TARGET CONSENSUS:")
    pt_data = get_fmp("price-target-consensus", {'symbol': symbol})
    if 'error' in pt_data:
        print(f"   ❌ Error: {pt_data['error']}")
    elif isinstance(pt_data, list) and len(pt_data) > 0:
        pt = pt_data[0]
        current = pt.get('lastPrice', 'N/A')
        target = pt.get('targetConsensus', 'N/A')
        high = pt.get('targetHigh', 'N/A')
        low = pt.get('targetLow', 'N/A')
        
        print(f"   ✅ Current Price: ${current}")
        print(f"   ✅ Consensus Target: ${target}")
        print(f"   ✅ Target High: ${high}")
        print(f"   ✅ Target Low: ${low}")
        
        if current != 'N/A' and target != 'N/A' and current > 0:
            upside = ((target - current) / current) * 100
            print(f"   📊 UPSIDE: {upside:.1f}%")
            
            if upside >= 50:
                print(f"   🎯 SHOULD GET: 18 points (Massive Upside)")
            elif upside >= 30:
                print(f"   🎯 SHOULD GET: 12 points (High Upside)")
            elif upside >= 15:
                print(f"   🎯 SHOULD GET: 6 points (Moderate Upside)")
    else:
        print(f"   ⚠️  No data (empty response)")
        print(f"   Raw response: {pt_data}")
    
    # 2. Analyst Grades
    print(f"\n2️⃣  ANALYST GRADES:")
    grades_data = get_fmp("grades", {'symbol': symbol})
    if 'error' in grades_data:
        print(f"   ❌ Error: {grades_data['error']}")
    elif isinstance(grades_data, list):
        print(f"   ✅ Found {len(grades_data)} grade records")
        
        # Count downgrades
        recent_10 = grades_data[:10]
        downgrades = sum(1 for g in recent_10 
                        if 'downgrad' in g.get('gradingAction', '').lower())
        
        print(f"   📊 Recent downgrades (last 10): {downgrades}")
        
        if downgrades >= 3:
            print(f"   🎯 SHOULD GET: 12 points (Downgrade Cascade)")
        elif downgrades >= 2:
            print(f"   🎯 SHOULD GET: 8 points (Multiple Downgrades)")
        elif downgrades == 1:
            print(f"   🎯 SHOULD GET: 4 points (Recent Downgrade)")
        
        # Show recent grades
        print(f"   Recent grades:")
        for i, grade in enumerate(recent_10[:5], 1):
            action = grade.get('gradingAction', 'N/A')
            firm = grade.get('gradingCompany', 'N/A')
            date = grade.get('date', 'N/A')
            print(f"      {i}. {firm}: {action} ({date})")
    else:
        print(f"   ⚠️  No data")
        print(f"   Raw response: {grades_data}")
    
    # 3. Grades Consensus
    print(f"\n3️⃣  GRADES CONSENSUS:")
    consensus_data = get_fmp("grades-consensus", {'symbol': symbol})
    if 'error' in consensus_data:
        print(f"   ❌ Error: {consensus_data['error']}")
    elif isinstance(consensus_data, list) and len(consensus_data) > 0:
        cons = consensus_data[0]
        print(f"   ✅ Strong Buy: {cons.get('strongBuy', 0)}")
        print(f"   ✅ Buy: {cons.get('buy', 0)}")
        print(f"   ✅ Hold: {cons.get('hold', 0)}")
        print(f"   ✅ Sell: {cons.get('sell', 0)}")
        print(f"   ✅ Strong Sell: {cons.get('strongSell', 0)}")
    else:
        print(f"   ⚠️  No data")
    
    # 4. RSI
    print(f"\n4️⃣  RSI INDICATOR:")
    rsi_data = get_fmp("technical-indicators/rsi", {
        'symbol': symbol,
        'periodLength': 14,
        'timeframe': '1day'
    })
    if 'error' in rsi_data:
        print(f"   ❌ Error: {rsi_data['error']}")
    elif isinstance(rsi_data, list) and len(rsi_data) > 0:
        latest = rsi_data[-1]
        rsi = latest.get('rsi', 'N/A')
        date = latest.get('date', 'N/A')
        close = latest.get('close', 'N/A')
        
        print(f"   ✅ RSI: {rsi}")
        print(f"   ✅ Date: {date}")
        print(f"   ✅ Close: ${close}")
        
        if rsi != 'N/A':
            if rsi < 25:
                print(f"   🎯 SHOULD GET: 12 points (Extremely Oversold)")
            elif rsi < 30:
                print(f"   🎯 SHOULD GET: 9 points (Deeply Oversold)")
            elif rsi < 40:
                print(f"   🎯 SHOULD GET: 5 points (Oversold)")
    else:
        print(f"   ⚠️  No data (empty response)")
        print(f"   Raw response: {rsi_data}")
    
    # 5. SMA
    print(f"\n5️⃣  50-DAY SMA:")
    sma_data = get_fmp("technical-indicators/sma", {
        'symbol': symbol,
        'periodLength': 50,
        'timeframe': '1day'
    })
    if 'error' in sma_data:
        print(f"   ❌ Error: {sma_data['error']}")
    elif isinstance(sma_data, list) and len(sma_data) > 0:
        latest = sma_data[-1]
        sma = latest.get('sma', 'N/A')
        close = latest.get('close', 'N/A')
        date = latest.get('date', 'N/A')
        
        print(f"   ✅ SMA-50: ${sma}")
        print(f"   ✅ Current: ${close}")
        print(f"   ✅ Date: {date}")
        
        if sma != 'N/A' and close != 'N/A' and sma > 0:
            discount = ((close - sma) / sma) * 100
            print(f"   📊 Discount: {discount:.1f}%")
            
            if discount < -20:
                print(f"   🎯 SHOULD GET: 8 points (Severe Discount)")
            elif discount < -15:
                print(f"   🎯 SHOULD GET: 6 points (Deep Discount)")
            elif discount < -8:
                print(f"   🎯 SHOULD GET: 3 points (Below SMA)")
    else:
        print(f"   ⚠️  No data (empty response)")
        print(f"   Raw response: {sma_data}")

print(f"\n{'='*80}")
print("DIAGNOSTIC COMPLETE")
print(f"{'='*80}")
print()
print("IF YOU SEE:")
print("  ✅ Green checkmarks with actual data = FMP is working")
print("  ⚠️  Empty responses = Data exists but stocks lack coverage")
print("  ❌ Errors = API issue (check key, endpoint, or rate limit)")
print()
print("NEXT STEP:")
print("  If data is loading but scores are low, the issue is in the scoring logic")
print("  If data is NOT loading, the issue is in the API client")
print("="*80)
