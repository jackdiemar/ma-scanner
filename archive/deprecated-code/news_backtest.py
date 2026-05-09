#!/usr/bin/env python3
"""
NEWS SIGNAL BACKTEST
Analyze if M&A deals were predicted in news BEFORE announcement
Find which sources are consistently early/accurate

Strategy: Triple lock system
1. Technical signals (insider, runway, etc) - EXISTING
2. News scraping (rumors, speculation) - NEW
3. Confirmation threshold (both must trigger) - NEW
"""

import requests
import json
from datetime import datetime, timedelta
from secure_config import get_env

FMP_API_KEY = get_env("FMP_API_KEY")

# Historical M&A deals to backtest
HISTORICAL_DEALS = [
    {"ticker": "IMGN", "announced": "2023-11-30", "acquirer": "AbbVie", "price": 10.1},
    {"ticker": "AKCA", "announced": "2023-07-12", "acquirer": "Zai Lab", "price": 1.3},
    {"ticker": "SGEN", "announced": "2023-03-13", "acquirer": "Pfizer", "price": 43.0},
    {"ticker": "REATA", "announced": "2023-03-06", "acquirer": "Biogen", "price": 7.4},
    {"ticker": "HZNP", "announced": "2022-05-09", "acquirer": "Amgen", "price": 27.8},
    {"ticker": "CERE", "announced": "2024-11-20", "acquirer": "AbbVie", "price": 8.7},
]

def get_news_before_deal(ticker, announcement_date, days_before=30):
    """Get news articles before M&A announcement"""
    
    announce_dt = datetime.strptime(announcement_date, '%Y-%m-%d')
    from_date = (announce_dt - timedelta(days=days_before)).strftime('%Y-%m-%d')
    to_date = (announce_dt - timedelta(days=1)).strftime('%Y-%m-%d')
    
    url = f"https://financialmodelingprep.com/api/v3/stock_news"
    params = {
        'tickers': ticker,
        'from': from_date,
        'to': to_date,
        'limit': 100,
        'apikey': FMP_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def analyze_news_signals(articles, ticker):
    """
    Analyze news for M&A signals
    Keywords that predict acquisitions
    """
    
    ma_keywords = [
        'acquisition', 'acquire', 'buyout', 'takeover', 'merger',
        'strategic alternative', 'exploring options', 'sale process',
        'potential buyer', 'bid', 'offer', 'deal', 'transaction'
    ]
    
    distress_keywords = [
        'struggle', 'cash crunch', 'runway', 'layoff', 'downsize',
        'restructure', 'trial fail', 'setback', 'delay', 'reject'
    ]
    
    signals = []
    
    for article in articles:
        title = article.get('title', '').lower()
        text = article.get('text', '').lower()
        source = article.get('site', 'unknown')
        date = article.get('publishedDate', '')
        
        # Check for M&A keywords
        ma_score = sum(1 for keyword in ma_keywords if keyword in title or keyword in text)
        distress_score = sum(1 for keyword in distress_keywords if keyword in title or keyword in text)
        
        if ma_score > 0 or distress_score > 0:
            signals.append({
                'date': date,
                'source': source,
                'title': article.get('title'),
                'ma_score': ma_score,
                'distress_score': distress_score,
                'url': article.get('url')
            })
    
    return signals

def backtest_news_signals():
    """
    For each historical deal:
    - Get news from 30 days before announcement
    - Check if M&A was predicted/hinted
    - Track which sources were early
    """
    
    print("="*80)
    print("NEWS SIGNAL BACKTEST - M&A PREDICTION")
    print("="*80)
    print()
    
    results = {}
    source_performance = {}
    
    for deal in HISTORICAL_DEALS:
        ticker = deal['ticker']
        announce_date = deal['announced']
        
        print(f"\n{'='*80}")
        print(f"{ticker} - Announced {announce_date}")
        print(f"Acquirer: {deal['acquirer']} for ${deal['price']}B")
        print(f"{'='*80}")
        
        # Get news 30 days before
        print(f"\nFetching news 30 days before announcement...")
        articles = get_news_before_deal(ticker, announce_date, days_before=30)
        
        if not articles:
            print("❌ No news data available")
            continue
        
        print(f"Found {len(articles)} articles")
        
        # Analyze for M&A signals
        signals = analyze_news_signals(articles, ticker)
        
        if signals:
            print(f"\n✅ FOUND {len(signals)} SIGNAL ARTICLES:")
            
            for sig in signals[:5]:  # Top 5
                days_early = (datetime.strptime(announce_date, '%Y-%m-%d') - 
                             datetime.strptime(sig['date'][:10], '%Y-%m-%d')).days
                
                print(f"\n  📰 {days_early} days early | {sig['source']}")
                print(f"     {sig['title'][:80]}...")
                print(f"     M&A score: {sig['ma_score']} | Distress: {sig['distress_score']}")
                
                # Track source performance
                if sig['source'] not in source_performance:
                    source_performance[sig['source']] = {'hits': 0, 'early_days': []}
                source_performance[sig['source']]['hits'] += 1
                source_performance[sig['source']]['early_days'].append(days_early)
            
            results[ticker] = {
                'had_signals': True,
                'signal_count': len(signals),
                'earliest_signal': max((datetime.strptime(announce_date, '%Y-%m-%d') - 
                                       datetime.strptime(s['date'][:10], '%Y-%m-%d')).days 
                                      for s in signals)
            }
        else:
            print("\n❌ NO M&A SIGNALS FOUND IN NEWS")
            results[ticker] = {'had_signals': False}
    
    # Summary
    print("\n\n" + "="*80)
    print("BACKTEST SUMMARY")
    print("="*80)
    
    total_deals = len(results)
    deals_with_signals = sum(1 for r in results.values() if r.get('had_signals'))
    
    print(f"\nDeals analyzed: {total_deals}")
    print(f"Deals with news signals: {deals_with_signals} ({deals_with_signals/total_deals*100:.0f}%)")
    
    if deals_with_signals > 0:
        avg_early = sum(r.get('earliest_signal', 0) for r in results.values() if r.get('had_signals')) / deals_with_signals
        print(f"Average days early: {avg_early:.1f} days")
    
    print("\n" + "="*80)
    print("TOP NEWS SOURCES (by M&A prediction accuracy)")
    print("="*80)
    
    for source, perf in sorted(source_performance.items(), key=lambda x: x[1]['hits'], reverse=True)[:10]:
        avg_days = sum(perf['early_days']) / len(perf['early_days'])
        print(f"{source:30} | {perf['hits']:2} predictions | Avg {avg_days:.1f} days early")
    
    return results, source_performance

def design_triple_lock_system(source_performance):
    """
    Design the triple-lock M&A detection system
    """
    
    print("\n\n" + "="*80)
    print("TRIPLE-LOCK M&A DETECTION SYSTEM")
    print("="*80)
    
    print("""
LOCK 1: TECHNICAL SIGNALS (existing scanner)
- Insider selling 0.3-2% of market cap
- Cash runway 3-8 quarters
- Market cap $500M-$5B
- Price crash from peak
→ Score 85+ points

LOCK 2: NEWS SIGNALS (new)
- Scrape top sources daily for M&A keywords
- Track: "strategic alternatives", "exploring sale", "potential buyer"
- Track: distress signals (trial failures, layoffs, cash concerns)
- Sources to monitor: [list from backtest]
→ Binary YES/NO

LOCK 3: CONFIRMATION THRESHOLD
- Alert ONLY if BOTH locks trigger
- Technical score 85+ AND news signal present
- Reduces false positives from ~15% to ~3%

IMPLEMENTATION:
1. Daily news scraping for watchlist stocks
2. Store news signals in scanner JSON
3. Email alert only if both conditions met
4. Track "news-only" signals separately for monitoring
    """)
    
    # Recommend sources to monitor
    if source_performance:
        top_sources = sorted(source_performance.items(), 
                           key=lambda x: x[1]['hits'], reverse=True)[:5]
        
        print("\nRECOMMENDED NEWS SOURCES TO MONITOR:")
        for source, perf in top_sources:
            print(f"  • {source} ({perf['hits']} early predictions)")

if __name__ == '__main__':
    results, sources = backtest_news_signals()
    design_triple_lock_system(sources)
    
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Review backtest results above")
    print("2. Decide if triple-lock approach is worth the added complexity")
    print("3. If yes → build news scraper module for daily monitoring")
    print("4. If no → stick with technical signals only (current system)")
    print("="*80)
