#!/usr/bin/env python3
"""
REVERSE MERGER SHELL HUNTING ANALYSIS
How big is the dead SPAC market really?
"""

import yfinance as yf
import requests
import time
from datetime import datetime, timedelta
from secure_config import get_env

FMP_API_KEY = get_env("FMP_API_KEY")

# Known dead SPACs / shells (trading < $3, no business)
KNOWN_SHELLS = [
    # Recent failed de-SPACs
    "TALK", "NRGV", "SOND", "ASPS", "FRSG", "IONQ", "ARQQ", "LFCR",
    "AMSC", "EOSE", "ENVX", "GOEV", "MVST", "STEM", "CLSK", "CANO",
    
    # Old SPACs that never merged
    "ACTD", "ADRA", "AERS", "AFAR", "AGBA", "AHPA", "ALIT", "ALSA",
    "ALTU", "AMAO", "ANAC", "AONE", "APSG", "APTM", "ASAQ", "ASAX",
    "ASCA", "ASPA", "ASTS", "ATAQ", "ATCX", "ATMV", "ATRO", "ATVI",
    
    # Micro-cap shells
    "BKYI", "BPTS", "BRLI", "BTCT", "BTTX", "BYFC", "CBAT", "CETX",
    "CFBK", "CFMS", "CHCI", "CHEK", "CLBS", "CLNN", "CMRA", "CNSP",
]

def get_spac_list():
    """Get comprehensive SPAC list from FMP"""
    url = f"https://financialmodelingprep.com/api/v3/stock-screener"
    params = {
        'apikey': FMP_API_KEY,
        'limit': 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Filter for SPACs (look for keywords in company name)
            spacs = []
            for stock in data:
                name = stock.get('companyName', '').upper()
                if any(keyword in name for keyword in ['ACQUISITION', 'SPAC', 'CAPITAL']):
                    spacs.append(stock['symbol'])
            
            return spacs
    except:
        pass
    
    return []

def analyze_shell(ticker):
    """Analyze if ticker is a viable reverse merger shell"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period='1mo')
        
        if hist.empty:
            return None
        
        price = hist['Close'].iloc[-1]
        volume = hist['Volume'].mean()
        
        # Shell criteria
        market_cap = info.get('marketCap', 0) / 1_000_000  # In millions
        cash = info.get('totalCash', 0) / 1_000_000
        
        # Is this a shell?
        is_shell = (
            price < 3.0 and  # Trading like shit
            market_cap < 100 and  # Small enough
            volume > 10000  # Some liquidity
        )
        
        if not is_shell:
            return None
        
        return {
            'ticker': ticker,
            'price': price,
            'market_cap': market_cap,
            'cash': cash,
            'volume': volume,
            'cash_per_share': cash / (market_cap / price) if market_cap > 0 and price > 0 else 0
        }
        
    except Exception as e:
        return None

def calculate_market_size():
    """Calculate total addressable market for shell hunting"""
    
    print("="*80)
    print("REVERSE MERGER SHELL HUNTING - MARKET SIZE ANALYSIS")
    print("="*80)
    print()
    
    # Get comprehensive list
    print("Fetching SPAC list from FMP...")
    fmp_spacs = get_spac_list()
    
    all_candidates = list(set(KNOWN_SHELLS + fmp_spacs))
    
    print(f"Analyzing {len(all_candidates)} potential shells...")
    print()
    
    viable_shells = []
    
    for i, ticker in enumerate(all_candidates, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(all_candidates)}")
        
        result = analyze_shell(ticker)
        if result:
            viable_shells.append(result)
        
        time.sleep(0.1)  # Rate limit
    
    # Analysis
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    if not viable_shells:
        print("\n❌ No viable shells found")
        return
    
    # Sort by cash per share (best value)
    viable_shells.sort(key=lambda x: x['cash_per_share'], reverse=True)
    
    total_shells = len(viable_shells)
    total_market_cap = sum(s['market_cap'] for s in viable_shells)
    total_cash = sum(s['cash'] for s in viable_shells)
    avg_price = sum(s['price'] for s in viable_shells) / total_shells
    
    print(f"\n📊 MARKET SIZE:")
    print(f"   Total viable shells: {total_shells}")
    print(f"   Combined market cap: ${total_market_cap:.1f}M")
    print(f"   Total cash on balance sheets: ${total_cash:.1f}M")
    print(f"   Average price: ${avg_price:.2f}")
    
    # Calculate investment scenarios
    print(f"\n💰 INVESTMENT SCENARIOS:")
    
    basket_10 = viable_shells[:10]
    basket_cost = sum(s['price'] for s in basket_10) * 100  # 100 shares each
    
    print(f"\n   BASKET STRATEGY (Top 10 shells):")
    print(f"   Cost: ${basket_cost:.0f} (100 shares each)")
    print(f"   If 1 shell gets reverse merger at 100% pop:")
    print(f"   Return: ${basket_10[0]['price'] * 100:.0f} profit")
    print(f"   ROI: {(basket_10[0]['price'] * 100 / basket_cost * 100):.1f}%")
    
    print(f"\n   SHOTGUN STRATEGY (All {total_shells} shells):")
    all_cost = sum(s['price'] for s in viable_shells) * 100
    print(f"   Cost: ${all_cost:.0f} (100 shares each)")
    print(f"   Need {int(all_cost / (viable_shells[0]['price'] * 100))} reverse mergers at 100% to break even")
    
    # Historical context
    print(f"\n📈 HISTORICAL CONTEXT:")
    print(f"   Reverse mergers happen ~10-20 per year in micro-cap space")
    print(f"   Average pop on announcement: 50-200%")
    print(f"   If you own {total_shells} shells:")
    print(f"   Probability of hitting 1-2 mergers per year: ~10-20%")
    print(f"   Expected annual return: Break-even to 2x")
    
    # Top opportunities
    print(f"\n🎯 TOP 10 OPPORTUNITIES (by cash/share):")
    print(f"{'Ticker':<8} {'Price':<8} {'Market Cap':<12} {'Cash':<10} {'Cash/Share':<12}")
    print("-"*60)
    
    for shell in viable_shells[:10]:
        print(f"{shell['ticker']:<8} ${shell['price']:<7.2f} ${shell['market_cap']:<11.1f}M ${shell['cash']:<9.1f}M ${shell['cash_per_share']:<11.2f}")
    
    # Risk assessment
    print(f"\n⚠️  RISKS:")
    print(f"   - Most shells will go to $0 (delisting)")
    print(f"   - Liquidity risk (hard to exit)")
    print(f"   - Could take 1-3 years for merger")
    print(f"   - Reverse splits can wipe you out")
    print(f"   - Capital tied up in dead stocks")
    
    print(f"\n✅ VERDICT:")
    
    if total_shells < 20:
        print(f"   ❌ MARKET TOO SMALL ({total_shells} shells)")
        print(f"   Not enough opportunities to diversify risk")
    elif total_shells < 50:
        print(f"   ⚠️  MARGINAL ({total_shells} shells)")
        print(f"   Possible but requires lucky timing")
        print(f"   Better for side bet (<5% of portfolio)")
    else:
        print(f"   ✅ VIABLE MARKET ({total_shells} shells)")
        print(f"   Enough shells to build diversified basket")
        print(f"   Allocate 5-10% of portfolio, expect 1-3 year hold")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    calculate_market_size()
