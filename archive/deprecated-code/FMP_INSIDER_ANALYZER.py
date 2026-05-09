#!/usr/bin/env python3
"""
FINANCIAL MODELING PREP API - INSIDER TRANSACTIONS
Professional-grade insider data ($180/year - let's make it worth it)
"""

import requests
import time
from datetime import datetime, timedelta
from secure_config import get_env

class FMPInsiderAnalyzer:
    """
    Insider transaction analyzer using FinancialModelingPrep API
    Reliable, paid, professional data
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key or get_env("FMP_API_KEY")
        self.base_url = 'https://financialmodelingprep.com/api/v4'
        self.session = requests.Session()
        self.c_level_titles = [
            'ceo', 'chief executive',
            'cfo', 'chief financial',
            'coo', 'chief operating',
            'president',
            'chairman', 'chair',
            'cmo', 'chief medical',
            'cso', 'chief scientific',
            'cto', 'chief technology',
            'evp', 'executive vice president',
            'svp', 'senior vice president'
        ]
    
    def is_c_level(self, title):
        """Check if title is C-level"""
        if not title:
            return False
        title_lower = str(title).lower()
        return any(t in title_lower for t in self.c_level_titles)
    
    def analyze_insider_transactions(self, ticker):
        """
        Get insider transactions from FMP API
        Returns: dict with detailed breakdown
        """
        try:
            # FMP insider trading endpoint
            url = f"{self.base_url}/insider-trading"
            
            params = {
                'symbol': ticker,
                'limit': 100,
                'apikey': self.api_key
            }
            
            r = self.session.get(url, params=params, timeout=15)
            
            if r.status_code != 200:
                return None
            
            data = r.json()
            
            if not data or len(data) == 0:
                return None
            
            # Filter to last 90 days (extended for December blackout)
            cutoff_date = datetime.now() - timedelta(days=90)
            
            transactions = []
            for txn in data:
                try:
                    # Parse transaction date
                    txn_date_str = txn.get('transactionDate', '')
                    if not txn_date_str:
                        continue
                    
                    txn_date = datetime.strptime(txn_date_str, '%Y-%m-%d')
                    
                    if txn_date < cutoff_date:
                        continue
                    
                    # Extract transaction details
                    reporting_name = txn.get('reportingName', 'Unknown')
                    type_of_owner = txn.get('typeOfOwner', '')
                    transaction_type = txn.get('acquistionOrDisposition', '')  # A = Acquisition, D = Disposition
                    
                    # Securities transacted
                    securities_transacted = float(txn.get('securitiesTransacted', 0))
                    price = float(txn.get('price', 0))
                    
                    # Calculate value
                    value = securities_transacted * price if price > 0 else 0
                    
                    # Check if C-level
                    is_c = self.is_c_level(type_of_owner)
                    
                    # Store transaction
                    transactions.append({
                        'date': txn_date_str,
                        'insider': reporting_name,
                        'title': type_of_owner,
                        'is_c_level': is_c,
                        'transaction_type': transaction_type,
                        'shares': securities_transacted,
                        'price': price,
                        'value': abs(value),
                        'sec_link': txn.get('link', '')
                    })
                    
                except Exception as e:
                    continue
            
            if not transactions:
                return None
            
            # Aggregate analysis
            analysis = {
                'total_filings': len(transactions),
                'c_level_filings': 0,
                'total_sale_value': 0,
                'total_purchase_value': 0,
                'c_level_sale_value': 0,
                'c_level_purchase_value': 0,
                'total_shares_sold': 0,
                'total_shares_bought': 0,
                'filings': []
            }
            
            for txn in transactions:
                is_sale = txn['transaction_type'] == 'D'  # Disposition = Sale
                is_purchase = txn['transaction_type'] == 'A'  # Acquisition = Purchase
                
                if is_sale:
                    analysis['total_sale_value'] += txn['value']
                    analysis['total_shares_sold'] += txn['shares']
                    
                    if txn['is_c_level']:
                        analysis['c_level_filings'] += 1
                        analysis['c_level_sale_value'] += txn['value']
                
                elif is_purchase:
                    analysis['total_purchase_value'] += txn['value']
                    analysis['total_shares_bought'] += txn['shares']
                    
                    if txn['is_c_level']:
                        analysis['c_level_purchase_value'] += txn['value']
                
                # Store significant transactions
                if txn['value'] > 50000:
                    analysis['filings'].append({
                        'date': txn['date'],
                        'insider': txn['insider'][:60],
                        'position': txn['title'][:60],
                        'is_c_level': txn['is_c_level'],
                        'sale_value': txn['value'] if is_sale else 0,
                        'purchase_value': txn['value'] if is_purchase else 0,
                        'shares': txn['shares'],
                        'transaction': 'Sale' if is_sale else 'Purchase',
                        'sec_url': txn['sec_link']
                    })
            
            analysis['has_sales'] = analysis['total_sale_value'] > 0
            analysis['has_purchases'] = analysis['total_purchase_value'] > 0
            analysis['has_c_level_sales'] = analysis['c_level_sale_value'] > 0
            
            return analysis
            
        except Exception as e:
            print(f"FMP API error for {ticker}: {e}")
            return None


# TEST THE API
if __name__ == '__main__':
    print("="*70)
    print("TESTING FMP API - YOUR $180 INVESTMENT")
    print("="*70)
    print()
    
    analyzer = FMPInsiderAnalyzer()
    
    # Test on 2 stocks - verify API works
    test_tickers = ['AAPL', 'RARE']
    
    for ticker in test_tickers:
        print(f"\nTesting {ticker}...")
        
        result = analyzer.analyze_insider_transactions(ticker)
        
        if result:
            print(f"✓ Found {result['total_filings']} transactions")
            print(f"  Total sales: ${result['total_sale_value']:,.0f}")
            print(f"  C-level sales: ${result['c_level_sale_value']:,.0f}")
            
            if result['c_level_sale_value'] > 0:
                print(f"\n  C-LEVEL SALES:")
                for filing in result['filings']:
                    if filing['is_c_level'] and filing['sale_value'] > 0:
                        print(f"    {filing['date']} - {filing['insider']}: ${filing['sale_value']:,.0f}")
                        if filing.get('sec_url'):
                            print(f"      Link: {filing['sec_url']}")
        else:
            print(f"  No transactions found")
        
        time.sleep(0.5)
    
    print()
    print("="*70)
    print("FMP API TEST COMPLETE")
    print("="*70)
    print()
    print("If you see transaction data above:")
    print("  ✅ API is working")
    print("  ✅ Your $180 is active")
    print("  ✅ Ready to integrate into scanner")
