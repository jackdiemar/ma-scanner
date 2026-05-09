#!/usr/bin/env python3
"""
financial_analyzer.py - Revenue, profitability, and cash flow analysis
Uses FMP income statement, balance sheet, and cash flow APIs
"""

import requests
import time
from datetime import datetime
from secure_config import get_env

FMP_API_KEY = get_env("FMP_API_KEY")

class FinancialAnalyzer:
    """Analyzes company financial health for M&A prediction"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/stable"
    
    def _get(self, endpoint, params):
        """Make FMP API request"""
        try:
            params['apikey'] = self.api_key
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            time.sleep(0.12)  # Rate limit
            return response.json()
        except Exception as e:
            print(f"  API Error: {e}")
            return None
    
    def get_income_statement(self, ticker, period='quarter', limit=8):
        """Get quarterly income statements"""
        return self._get('income-statement', {
            'symbol': ticker,
            'period': period,
            'limit': limit
        })
    
    def get_balance_sheet(self, ticker, period='quarter', limit=4):
        """Get quarterly balance sheets"""
        return self._get('balance-sheet-statement', {
            'symbol': ticker,
            'period': period,
            'limit': limit
        })
    
    def get_cash_flow(self, ticker, period='quarter', limit=4):
        """Get quarterly cash flow statements"""
        return self._get('cash-flow-statement', {
            'symbol': ticker,
            'period': period,
            'limit': limit
        })
    
    def analyze_revenue_trend(self, income_statements):
        """Calculate revenue growth and trend"""
        if not income_statements or len(income_statements) < 2:
            return {
                'revenue_latest': 0,
                'revenue_growth_qoq': 0,
                'revenue_growth_yoy': 0,
                'revenue_trend': 'UNKNOWN'
            }
        
        latest = income_statements[0]
        prev_quarter = income_statements[1]
        
        revenue_latest = latest.get('revenue', 0)
        revenue_prev = prev_quarter.get('revenue', 0)
        
        # Quarter-over-quarter growth
        qoq_growth = 0
        if revenue_prev > 0:
            qoq_growth = ((revenue_latest - revenue_prev) / revenue_prev) * 100
        
        # Year-over-year (compare to 4 quarters ago)
        yoy_growth = 0
        if len(income_statements) >= 5:
            revenue_year_ago = income_statements[4].get('revenue', 0)
            if revenue_year_ago > 0:
                yoy_growth = ((revenue_latest - revenue_year_ago) / revenue_year_ago) * 100
        
        # Trend
        if qoq_growth > 20:
            trend = 'EXPLOSIVE'
        elif qoq_growth > 10:
            trend = 'STRONG'
        elif qoq_growth > 0:
            trend = 'GROWING'
        elif qoq_growth > -10:
            trend = 'FLAT'
        else:
            trend = 'DECLINING'
        
        return {
            'revenue_latest': revenue_latest,
            'revenue_growth_qoq': qoq_growth,
            'revenue_growth_yoy': yoy_growth,
            'revenue_trend': trend
        }
    
    def analyze_profitability(self, income_statements):
        """Check if company is profitable or improving"""
        if not income_statements:
            return {
                'is_profitable': False,
                'operating_income': 0,
                'net_income': 0,
                'gross_margin': 0,
                'margin_trend': 'UNKNOWN'
            }
        
        latest = income_statements[0]
        
        operating_income = latest.get('operatingIncome', 0)
        net_income = latest.get('netIncome', 0)
        revenue = latest.get('revenue', 1)
        gross_profit = latest.get('grossProfit', 0)
        
        is_profitable = operating_income > 0
        gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
        
        # Check if margins improving
        margin_trend = 'STABLE'
        if len(income_statements) >= 2:
            prev_margin = 0
            prev_revenue = income_statements[1].get('revenue', 1)
            prev_gross = income_statements[1].get('grossProfit', 0)
            if prev_revenue > 0:
                prev_margin = (prev_gross / prev_revenue * 100)
            
            if gross_margin > prev_margin + 5:
                margin_trend = 'IMPROVING'
            elif gross_margin < prev_margin - 5:
                margin_trend = 'DECLINING'
        
        return {
            'is_profitable': is_profitable,
            'operating_income': operating_income,
            'net_income': net_income,
            'gross_margin': gross_margin,
            'margin_trend': margin_trend
        }
    
    def analyze_cash_position(self, balance_sheets, cash_flows):
        """Analyze cash runway and burn rate"""
        if not balance_sheets or not cash_flows:
            return {
                'cash': 0,
                'quarterly_burn': 0,
                'cash_runway_quarters': 999,
                'burn_accelerating': False
            }
        
        latest_balance = balance_sheets[0]
        latest_cash_flow = cash_flows[0]
        
        # Cash and equivalents
        cash = latest_balance.get('cashAndCashEquivalents', 0)
        short_term_investments = latest_balance.get('shortTermInvestments', 0)
        total_cash = cash + short_term_investments
        
        # Operating cash flow (negative = burning cash)
        operating_cash_flow = latest_cash_flow.get('netCashProvidedByOperatingActivities', 0)
        
        # If negative, that's the quarterly burn
        quarterly_burn = abs(operating_cash_flow) if operating_cash_flow < 0 else 0
        
        # Cash runway
        cash_runway = 999
        if quarterly_burn > 0:
            cash_runway = total_cash / quarterly_burn
        
        # Check if burn is accelerating
        burn_accelerating = False
        if len(cash_flows) >= 2:
            prev_burn = abs(cash_flows[1].get('netCashProvidedByOperatingActivities', 0))
            if quarterly_burn > prev_burn * 1.2:  # 20% increase in burn
                burn_accelerating = True
        
        return {
            'cash': total_cash,
            'quarterly_burn': quarterly_burn,
            'cash_runway_quarters': cash_runway,
            'burn_accelerating': burn_accelerating
        }
    
    def get_comprehensive_analysis(self, ticker):
        """Get complete financial analysis for a ticker"""
        print(f"  Analyzing financials for {ticker}...")
        
        # Get all statements
        income_statements = self.get_income_statement(ticker)
        balance_sheets = self.get_balance_sheet(ticker)
        cash_flows = self.get_cash_flow(ticker)
        
        if not income_statements:
            return None
        
        # Analyze
        revenue_analysis = self.analyze_revenue_trend(income_statements)
        profitability = self.analyze_profitability(income_statements)
        cash_analysis = self.analyze_cash_position(balance_sheets, cash_flows)
        
        return {
            'ticker': ticker,
            **revenue_analysis,
            **profitability,
            **cash_analysis,
            'has_revenue': revenue_analysis['revenue_latest'] > 0,
            'revenue_millions': revenue_analysis['revenue_latest'] / 1e6
        }

def score_financial_health(analysis):
    """
    Score financial health for M&A prediction
    Returns points and signals
    """
    if not analysis:
        return 0, []
    
    score = 0
    signals = []
    
    # Revenue signals (20 pts max)
    trend = analysis['revenue_trend']
    growth = analysis['revenue_growth_qoq']
    
    if trend == 'EXPLOSIVE':
        score += 15
        signals.append((f'Explosive Revenue Growth (+{growth:.0f}% Q/Q)', 15))
    elif trend == 'STRONG':
        score += 12
        signals.append((f'Strong Revenue Growth (+{growth:.0f}% Q/Q)', 12))
    elif trend == 'GROWING':
        score += 8
        signals.append((f'Revenue Growing (+{growth:.0f}% Q/Q)', 8))
    elif analysis['has_revenue']:
        score += 5
        signals.append(('Revenue Generating', 5))
    
    # Profitability signals (15 pts max)
    if analysis['is_profitable']:
        score += 15
        signals.append(('Profitable Company', 15))
    elif analysis['margin_trend'] == 'IMPROVING':
        score += 10
        signals.append(('Margins Improving', 10))
    
    # Cash runway signals (25 pts max)
    runway = analysis['cash_runway_quarters']
    if runway < 3:
        score += 25
        signals.append((f'Critical Cash Runway ({runway:.1f}Q)', 25))
    elif runway < 5:
        score += 15
        signals.append((f'Low Cash Runway ({runway:.1f}Q)', 15))
    elif runway < 8:
        score += 8
        signals.append((f'Moderate Cash Runway ({runway:.1f}Q)', 8))
    
    # Burn acceleration (10 pts)
    if analysis['burn_accelerating']:
        score += 10
        signals.append(('Cash Burn Accelerating', 10))
    
    return score, signals

# Test
if __name__ == "__main__":
    analyzer = FinancialAnalyzer(FMP_API_KEY)
    
    test_tickers = ['KALA', 'NVAX', 'BLUE']
    
    for ticker in test_tickers:
        print(f"\n{'='*60}")
        print(f"Testing: {ticker}")
        print('='*60)
        
        analysis = analyzer.get_comprehensive_analysis(ticker)
        
        if analysis:
            print(f"\nRevenue: ${analysis['revenue_millions']:.1f}M")
            print(f"Revenue Growth (Q/Q): {analysis['revenue_growth_qoq']:.1f}%")
            print(f"Revenue Trend: {analysis['revenue_trend']}")
            print(f"Profitable: {analysis['is_profitable']}")
            print(f"Gross Margin: {analysis['gross_margin']:.1f}%")
            print(f"Cash: ${analysis['cash']/1e6:.1f}M")
            print(f"Cash Runway: {analysis['cash_runway_quarters']:.1f} quarters")
            
            score, signals = score_financial_health(analysis)
            print(f"\nFINANCIAL HEALTH SCORE: {score}/70")
            for signal, pts in signals:
                print(f"  • {signal}: +{pts}pts")
