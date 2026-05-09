#!/usr/bin/env python3
"""
Quick test to verify FMP insider data is working in V10.3 REVISED
Uses correct field names from debug output
"""

import requests
from datetime import datetime, timedelta
import time
from secure_config import get_env

FMP_API_KEY = get_env("FMP_API_KEY")

class FMPInsiderAnalyzer:
    """Test FMP insider analyzer with CORRECT field names"""
    
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
    
    def analyze_insider_transactions(self, ticker):
        """Get insider transactions from FMP stable API"""
        try:
            url = f"https://financialmodelingprep.com/stable/insider-trading/search?symbol={ticker}&page=0&limit=100&apikey={self.api_key}"
            
            response = requests.get(url, timeout=10)
            time.sleep(0.12)
            
            if response.status_code != 200:
                print(f"HTTP {response.status_code}")
                return None
            
            data = response.json()
            
            if not data or not isinstance(data, list):
                return None
            
            # Filter to last 6 months and sales only
            cutoff_date = datetime.now() - timedelta(days=180)
            transactions = []
            
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
                    
                    # Only sales (D = Disposition)
                    if acquisition_or_disposition != 'D':
                        continue
                    
                    securities = trade.get('securitiesTransacted', 0)
                    if securities <= 0:
                        continue
                    
                    price = trade.get('price', 0)
                    if price <= 0:
                        continue
                    
                    value = abs(securities) * price
                    is_c = self.is_c_level(type_of_owner, reporting_name)
                    
                    transactions.append({
                        'insider': reporting_name,
                        'title': type_of_owner,
                        'is_c_level': is_c,
                        'value': value
                    })
                    
                except Exception as e:
                    continue
            
            if not transactions:
                return None
            
            # Aggregate
            c_level_value = sum(t['value'] for t in transactions if t['is_c_level'])
            c_level_count = sum(1 for t in transactions if t['is_c_level'])
            
            return {
                'c_level_sale_value': c_level_value,
                'c_level_filings': c_level_count,
                'total_filings': len(transactions)
            }
            
        except Exception as e:
            print(f"Error: {e}")
            return None

# Test on 5 stocks
print("="*70)
print("TESTING FMP INSIDER API - FIXED VERSION")
print("="*70)

analyzer = FMPInsiderAnalyzer(FMP_API_KEY)

test_stocks = ['AAPL', 'MRNA', 'FATE', 'KALA', 'BLUE']

results = []

for ticker in test_stocks:
    print(f"\nTesting {ticker}...", end=" ")
    
    data = analyzer.analyze_insider_transactions(ticker)
    
    if data:
        c_level_value = data['c_level_sale_value'] / 1_000_000
        print(f"✓ ${c_level_value:.2f}M in C-level sales ({data['c_level_filings']} txns)")
        results.append((ticker, c_level_value))
    else:
        print("✗ No C-level sales with price data")
        results.append((ticker, 0))

print("\n" + "="*70)
print("RESULTS")
print("="*70)

has_data = sum(1 for _, val in results if val > 0)
total = len(results)

print(f"\nStocks with C-level insider sales: {has_data}/{total}")

if has_data >= 2:
    print("\n✅ FMP INSIDER API IS NOW WORKING!")
    print("\nV10.3 REVISED should pull insider data correctly now.")
    print("Run: python3 PRODUCTION_SCANNER_V10.3_REVISED.py")
else:
    print("\n⚠️  FEW RESULTS - This could be normal:")
    print("- Many stocks have no recent C-level sales")
    print("- Price data often missing (price=0)")
    print("- Only counting last 6 months")
    print("\nScanner should still work - run it and check output!")

