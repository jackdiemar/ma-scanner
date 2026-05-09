#!/usr/bin/env python3
"""
COMPREHENSIVE M&A INSIDER ANALYSIS
Pull 500 biotech acquisitions and analyze insider selling patterns
Use this data to calibrate V10.3 scoring thresholds
"""

import requests
import time
import json
from datetime import datetime, timedelta
from statistics import mean, median, stdev
from secure_config import get_env

FMP_API_KEY = get_env("FMP_API_KEY")

# Known biotech acquisitions 2020-2024 (we'll use FMP to get more)
KNOWN_ACQUISITIONS = [
    # 2024
    'AKCA', 'ICPT', 'MIRM', 'IMMP', 'VKTX', 'PCRX', 'TBPH', 'MNOV', 'ENSC', 'CLDX',
    # 2023  
    'IMGN', 'CERE', 'SGEN', 'ADMA', 'KARB', 'MDXG', 'ADVM', 'PRTA', 'TYME', 'XNCR', 'CHRS', 'APLS',
    # 2022
    'HZNP', 'REATA', 'GLPG', 'IMMU', 'CDMO', 'KRTX', 'DMTK', 'CBAY', 'ONCE', 'CGEM', 'FDMT', 'ORIC', 'SYRS', 'DRNA',
    # 2021
    'ALKS', 'MYOV', 'ADPT', 'ARQL', 'BOLD', 'EIGR', 'LOXO', 'VIRC',
    # 2020
    'IMUX', 'PTCT', 'TLSA',
]

class ComprehensiveM_AAnalyzer:
    """Analyze insider patterns across 500 acquisitions"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.c_level_keywords = [
            'ceo', 'chief executive',
            'cfo', 'chief financial', 
            'coo', 'chief operating',
            'president',
            'chairman', 'chair',
            'cmo', 'chief medical',
            'cso', 'chief scientific',
            'cto', 'chief technology',
            'officer'
        ]
    
    def is_c_level(self, type_of_owner, reporting_name):
        """Check if insider is C-level"""
        if type_of_owner:
            text = str(type_of_owner).lower()
            if any(keyword in text for keyword in self.c_level_keywords):
                return True
        
        if reporting_name:
            text = str(reporting_name).lower()
            if any(keyword in text for keyword in self.c_level_keywords):
                return True
        
        return False
    
    def get_company_profile(self, ticker):
        """Get company market cap using correct FMP endpoint"""
        try:
            # Use /stable/market-capitalization endpoint
            url = f"https://financialmodelingprep.com/stable/market-capitalization?symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            time.sleep(0.12)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            if not data or not isinstance(data, list):
                return None
            
            mcap = data[0].get('marketCap', 0) / 1_000_000  # Convert to millions
            
            return mcap if mcap > 0 else None
            
        except Exception as e:
            return None
    
    def get_recent_ma_deals(self, limit=500):
        """Get recent M&A deals from FMP to expand our dataset"""
        try:
            all_deals = []
            page = 0
            
            # FMP returns 100 per page max
            while len(all_deals) < limit:
                url = f"https://financialmodelingprep.com/stable/mergers-acquisitions-latest?page={page}&limit=100&apikey={self.api_key}"
                response = requests.get(url, timeout=10)
                time.sleep(0.12)
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                if not data or not isinstance(data, list) or len(data) == 0:
                    break
                
                all_deals.extend(data)
                page += 1
                
                if len(data) < 100:  # Last page
                    break
            
            return all_deals
            
        except Exception as e:
            return []
    
    def get_insider_data(self, ticker):
        """Get insider trading for 6 months before acquisition"""
        try:
            url = f"https://financialmodelingprep.com/stable/insider-trading/search?symbol={ticker}&page=0&limit=200&apikey={self.api_key}"
            
            response = requests.get(url, timeout=10)
            time.sleep(0.12)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data or not isinstance(data, list):
                return None
            
            # Look at 12 months of data (6 months before acquisition typical)
            cutoff_date = datetime.now() - timedelta(days=730)  # 2 years back
            c_level_sales = 0
            
            for trade in data:
                try:
                    filing_date_str = trade.get('filingDate', '')
                    if not filing_date_str:
                        continue
                    
                    filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d')
                    
                    if filing_date < cutoff_date:
                        continue
                    
                    reporting_name = trade.get('reportingName', '')
                    type_of_owner = trade.get('typeOfOwner', '')
                    acquisition_or_disposition = trade.get('acquisitionOrDisposition', '')
                    
                    # Only sales
                    if acquisition_or_disposition != 'D':
                        continue
                    
                    securities = trade.get('securitiesTransacted', 0)
                    if securities <= 0:
                        continue
                    
                    price = trade.get('price', 0)
                    if price <= 0:
                        continue
                    
                    value = abs(securities) * price
                    
                    # Check if C-level
                    if self.is_c_level(type_of_owner, reporting_name):
                        c_level_sales += value
                    
                except Exception as e:
                    continue
            
            return c_level_sales if c_level_sales > 0 else None
            
        except Exception as e:
            return None
    
    def analyze_acquisition(self, ticker):
        """Analyze a single acquisition"""
        print(f"  Analyzing {ticker}...", end=" ")
        
        # Get market cap
        mcap = self.get_company_profile(ticker)
        if not mcap:
            print("✗ No market cap data")
            return None
        
        # Get insider data
        insider = self.get_insider_data(ticker)
        if not insider:
            print(f"✗ No insider data (mcap: ${mcap:.0f}M)")
            return None
        
        insider_millions = insider / 1_000_000
        insider_pct = (insider_millions / mcap) * 100
        
        print(f"✓ ${insider_millions:.2f}M ({insider_pct:.3f}%)")
        
        return {
            'ticker': ticker,
            'market_cap': mcap,
            'insider_sales': insider_millions,
            'insider_pct': insider_pct
        }

def main():
    print("="*80)
    print("COMPREHENSIVE M&A INSIDER ANALYSIS")
    print("="*80)
    
    analyzer = ComprehensiveM_AAnalyzer(FMP_API_KEY)
    
    # Step 1: Get recent M&A deals from FMP
    print("\nStep 1: Discovering M&A deals from FMP...")
    print("-"*80)
    
    ma_deals = analyzer.get_recent_ma_deals(limit=500)
    
    if ma_deals:
        print(f"✓ Found {len(ma_deals)} M&A deals from FMP")
        
        # Extract biotech tickers (filter by industry later if needed)
        fmp_tickers = []
        for deal in ma_deals:
            symbol = deal.get('symbol', '')
            if symbol and symbol not in fmp_tickers:
                fmp_tickers.append(symbol)
        
        print(f"✓ Extracted {len(fmp_tickers)} unique acquirer tickers")
    else:
        print("⚠️  Could not fetch M&A deals from FMP")
        fmp_tickers = []
    
    # Step 2: Combine with known acquisitions
    all_tickers = list(set(KNOWN_ACQUISITIONS + fmp_tickers[:200]))  # Cap at 200 total
    
    print(f"\nStep 2: Analyzing {len(all_tickers)} companies...")
    print("-"*80)
    
    results = []
    
    for i, ticker in enumerate(all_tickers, 1):
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(all_tickers)}...")
        
        result = analyzer.analyze_acquisition(ticker)
        if result:
            results.append(result)
        
        # Rate limit
        time.sleep(0.15)
        
        # Stop if we have enough good data
        if len(results) >= 50:
            print(f"\n  ✓ Collected {len(results)} valid results - stopping early")
            break
    
    print(f"\n{'='*80}")
    print(f"RESULTS - {len(results)} acquisitions with insider data")
    print(f"{'='*80}")
    
    if len(results) < 10:
        print("\n⚠️  Too few results to draw conclusions")
        print("Possible issues:")
        print("  - FMP may not have historical insider data")
        print("  - Many acquired companies delisted (no current data)")
        print("  - Price data missing for many transactions")
        return
    
    # Calculate statistics
    insider_pcts = [r['insider_pct'] for r in results]
    insider_amounts = [r['insider_sales'] for r in results]
    market_caps = [r['market_cap'] for r in results]
    
    print(f"\nINSIDER AS % OF MARKET CAP:")
    print(f"  Mean:     {mean(insider_pcts):.3f}%")
    print(f"  Median:   {median(insider_pcts):.3f}%")
    print(f"  Std Dev:  {stdev(insider_pcts):.3f}%")
    print(f"  Min:      {min(insider_pcts):.3f}%")
    print(f"  Max:      {max(insider_pcts):.3f}%")
    
    # Percentiles
    sorted_pcts = sorted(insider_pcts)
    p10 = sorted_pcts[int(len(sorted_pcts) * 0.10)]
    p25 = sorted_pcts[int(len(sorted_pcts) * 0.25)]
    p50 = sorted_pcts[int(len(sorted_pcts) * 0.50)]
    p75 = sorted_pcts[int(len(sorted_pcts) * 0.75)]
    p90 = sorted_pcts[int(len(sorted_pcts) * 0.90)]
    
    print(f"\nPERCENTILES:")
    print(f"  10th: {p10:.3f}%")
    print(f"  25th: {p25:.3f}%")
    print(f"  50th: {p50:.3f}%")
    print(f"  75th: {p75:.3f}%")
    print(f"  90th: {p90:.3f}%")
    
    print(f"\nINSIDER ABSOLUTE AMOUNTS:")
    print(f"  Mean:     ${mean(insider_amounts):.2f}M")
    print(f"  Median:   ${median(insider_amounts):.2f}M")
    print(f"  Min:      ${min(insider_amounts):.2f}M")
    print(f"  Max:      ${max(insider_amounts):.2f}M")
    
    print(f"\nMARKET CAPS:")
    print(f"  Mean:     ${mean(market_caps):.0f}M")
    print(f"  Median:   ${median(market_caps):.0f}M")
    print(f"  Min:      ${min(market_caps):.0f}M")
    print(f"  Max:      ${max(market_caps):.0f}M")
    
    # Distribution analysis
    print(f"\n{'='*80}")
    print("DISTRIBUTION ANALYSIS")
    print(f"{'='*80}")
    
    ranges = [
        (0.0, 0.01, "Minimal"),
        (0.01, 0.05, "Notable"),
        (0.05, 0.1, "Moderate"),
        (0.1, 0.2, "Substantial"),
        (0.2, 0.5, "Heavy"),
        (0.5, 1.0, "Massive"),
        (1.0, 100.0, "Extreme"),
    ]
    
    for min_pct, max_pct, label in ranges:
        count = sum(1 for pct in insider_pcts if min_pct <= pct < max_pct)
        percentage = (count / len(insider_pcts)) * 100
        print(f"  {min_pct:5.2f}% - {max_pct:5.2f}%  ({label:12}) : {count:3} deals ({percentage:5.1f}%)")
    
    # Recommended thresholds
    print(f"\n{'='*80}")
    print("RECOMMENDED SCORING THRESHOLDS")
    print(f"{'='*80}")
    
    print(f"\nBased on {len(results)} acquisitions with insider data:")
    print(f"\n  Insider % | Points | Percentile | Rationale")
    print(f"  ----------|--------|------------|--------------------------------")
    print(f"  {p90:7.3f}%+ |  35pts | 90th+      | Top 10% of acquisitions (extreme)")
    print(f"  {p75:7.3f}%+ |  30pts | 75th+      | Top 25% (massive)")
    print(f"  {p50:7.3f}%+ |  25pts | 50th+      | Above median (heavy)")
    print(f"  {p25:7.3f}%+ |  20pts | 25th+      | Above lower quartile (substantial)")
    print(f"  {p10:7.3f}%+ |  15pts | 10th+      | Above bottom 10% (moderate)")
    print(f"  {min(insider_pcts):7.3f}%+ |  10pts | Any        | Any insider signal (notable)")
    
    # Top 10 examples
    print(f"\n{'='*80}")
    print("TOP 10 ACQUISITIONS BY INSIDER %")
    print(f"{'='*80}")
    
    top_10 = sorted(results, key=lambda x: x['insider_pct'], reverse=True)[:10]
    print(f"\nTicker  Market Cap    Insider      % of Cap")
    print(f"------  ----------  -----------  -----------")
    for r in top_10:
        print(f"{r['ticker']:6}  ${r['market_cap']:9.0f}M  ${r['insider_sales']:9.2f}M     {r['insider_pct']:6.3f}%")
    
    # Save results
    output = {
        'analysis_date': datetime.now().isoformat(),
        'total_analyzed': len(results),
        'statistics': {
            'mean_pct': mean(insider_pcts),
            'median_pct': median(insider_pcts),
            'std_dev_pct': stdev(insider_pcts),
            'p10': p10,
            'p25': p25,
            'p50': p50,
            'p75': p75,
            'p90': p90
        },
        'deals': results
    }
    
    filename = f'ma_insider_analysis_{datetime.now().strftime("%Y%m%d")}.json'
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Results saved to: {filename}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
