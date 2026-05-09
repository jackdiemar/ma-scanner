#!/usr/bin/env python3
"""
DUAL_MODEL_SCORER.py - Model A (Distressed) + Model B (Strategic) scoring
Import this into the scanner for dual scoring capability
"""

def calculate_model_a_score(stock_data):
    """
    MODEL A: DISTRESSED ACQUISITION
    Target: $100M-$600M market cap, <5Q cash runway
    Threshold: 85+ = BUY
    """
    score = 0
    signals = []
    
    # GATE: C-Level Insider Selling (35 pts)
    if stock_data.get('has_c_level_selling'):
        score += 35
        signals.append(('C-Level Insider Selling', 35, 'A'))
    
    # Cash Runway (20 pts max)
    cash_quarters = stock_data.get('cash_runway_quarters', 999)
    if cash_quarters < 3:
        score += 20
        signals.append(('Critical Cash Runway (<3Q)', 20, 'A'))
    elif cash_quarters < 5:
        score += 12
        signals.append(('Low Cash Runway (<5Q)', 12, 'A'))
    elif cash_quarters < 8:
        score += 5
        signals.append(('Moderate Cash Runway (<8Q)', 5, 'A'))
    
    # Market Cap (15 pts max)
    market_cap = stock_data.get('market_cap', 0)
    if 100e6 <= market_cap <= 300e6:
        score += 15
        signals.append(('Sweet Spot Market Cap ($100M-$300M)', 15, 'A'))
    elif 300e6 < market_cap <= 600e6:
        score += 10
        signals.append(('Acquisition Range ($300M-$600M)', 10, 'A'))
    
    # Price Crash (15 pts max)
    crash_pct = stock_data.get('crash_from_high', 0)
    if crash_pct <= -70:
        score += 15
        signals.append((f'Severe Price Crash ({crash_pct:.0f}%)', 15, 'A'))
    elif crash_pct <= -50:
        score += 10
        signals.append((f'Major Price Drop ({crash_pct:.0f}%)', 10, 'A'))
    elif crash_pct <= -30:
        score += 5
        signals.append((f'Significant Decline ({crash_pct:.0f}%)', 5, 'A'))
    
    # Analyst Price Target Upside (18 pts max)
    upside = stock_data.get('price_target_upside', 0)
    if upside >= 100:
        score += 18
        signals.append((f'Massive Price Target Upside (+{upside:.0f}%)', 18, 'A'))
    elif upside >= 50:
        score += 12
        signals.append((f'High Price Target Upside (+{upside:.0f}%)', 12, 'A'))
    elif upside >= 30:
        score += 6
        signals.append((f'Moderate Price Target Upside (+{upside:.0f}%)', 6, 'A'))
    
    # Institutional Ownership (10 pts max)
    inst_own = stock_data.get('institutional_ownership', 0)
    if 40 <= inst_own <= 70:
        score += 10
        signals.append((f'Optimal Institutional Holdings ({inst_own:.0f}%)', 10, 'A'))
    elif 30 <= inst_own < 40 or 70 < inst_own <= 85:
        score += 5
        signals.append((f'Moderate Institutional Holdings ({inst_own:.0f}%)', 5, 'A'))
    
    # RSI Oversold (12 pts max)
    rsi = stock_data.get('rsi', 50)
    if rsi < 20:
        score += 12
        signals.append((f'Extremely Oversold RSI ({rsi:.0f})', 12, 'A'))
    elif rsi < 30:
        score += 8
        signals.append((f'Oversold RSI ({rsi:.0f})', 8, 'A'))
    
    # Cap at 100
    score = min(score, 100)
    
    return score, signals

def calculate_model_b_score(stock_data):
    """
    MODEL B: STRATEGIC ACQUISITION
    Target: $1B-$10B market cap, revenue-generating, pipeline value
    Threshold: 75+ = BUY
    """
    score = 0
    signals = []
    
    # Insider Activity (25 pts)
    if stock_data.get('has_c_level_selling'):
        score += 25
        signals.append(('C-Level Insider Selling', 25, 'B'))
    elif stock_data.get('has_board_selling'):
        score += 15
        signals.append(('Board Member Selling', 15, 'B'))
    
    # Financial Health (20 pts max)
    is_profitable = stock_data.get('is_profitable', False)
    revenue_growth = stock_data.get('revenue_growth_pct', 0)
    has_revenue = stock_data.get('revenue', 0) > 0
    
    if is_profitable:
        score += 15
        signals.append(('Profitable Company', 15, 'B'))
    elif revenue_growth > 50:
        score += 15
        signals.append((f'Explosive Revenue Growth (+{revenue_growth:.0f}%)', 15, 'B'))
    elif revenue_growth > 20:
        score += 12
        signals.append((f'Strong Revenue Growth (+{revenue_growth:.0f}%)', 12, 'B'))
    elif has_revenue:
        score += 8
        signals.append(('Revenue Generating', 8, 'B'))
    
    # Pipeline Value (30 pts max)
    phase3_count = stock_data.get('phase3_trials', 0)
    has_commercial = stock_data.get('has_commercialized_product', False)
    has_breakthrough = stock_data.get('has_breakthrough_designation', False)
    has_orphan = stock_data.get('has_orphan_status', False)
    
    if has_commercial:
        score += 20
        signals.append(('Commercialized Product', 20, 'B'))
    
    if phase3_count >= 2:
        score += 25
        signals.append((f'Multiple Phase 3 Programs ({phase3_count})', 25, 'B'))
    elif phase3_count == 1:
        score += 15
        signals.append(('Phase 3 Pipeline', 15, 'B'))
    
    if has_breakthrough:
        score += 15
        signals.append(('FDA Breakthrough Designation', 15, 'B'))
    
    if has_orphan:
        score += 10
        signals.append(('Orphan Drug Status', 10, 'B'))
    
    # Market Position (15 pts max)
    market_cap = stock_data.get('market_cap', 0)
    if 1e9 <= market_cap <= 5e9:
        score += 15
        signals.append((f'Sweet Spot Market Cap (${market_cap/1e9:.1f}B)', 15, 'B'))
    elif 5e9 < market_cap <= 10e9:
        score += 10
        signals.append((f'Large Cap Strategic (${market_cap/1e9:.1f}B)', 10, 'B'))
    elif market_cap > 10e9:
        score += 5
        signals.append((f'Mega Cap (${market_cap/1e9:.1f}B)', 5, 'B'))
    
    # Analyst Price Target (12 pts max)
    upside = stock_data.get('price_target_upside', 0)
    if upside >= 50:
        score += 12
        signals.append((f'High Analyst Upside (+{upside:.0f}%)', 12, 'B'))
    elif upside >= 30:
        score += 8
        signals.append((f'Analyst Upside (+{upside:.0f}%)', 8, 'B'))
    
    # Cap at 100
    score = min(score, 100)
    
    return score, signals

def get_primary_model(market_cap, cash_runway_quarters):
    """Determine which model should be primary for this stock"""
    
    # Model A criteria: Small cap + distressed
    if market_cap < 1e9 and cash_runway_quarters < 8:
        return 'A'
    
    # Model B criteria: Mid/large cap OR revenue-generating
    elif market_cap >= 1e9:
        return 'B'
    
    # Default to A for small caps
    return 'A'

def calculate_dual_scores(stock_data):
    """
    Calculate both Model A and Model B scores
    Returns: {
        'model_a_score': 75,
        'model_a_signals': [...],
        'model_b_score': 65,
        'model_b_signals': [...],
        'primary_model': 'A',
        'recommendation': 'BUY' | 'WATCH' | 'PASS',
        'confidence': 'HIGH' | 'MEDIUM' | 'LOW'
    }
    """
    
    # Calculate both scores
    score_a, signals_a = calculate_model_a_score(stock_data)
    score_b, signals_b = calculate_model_b_score(stock_data)
    
    # Determine primary model
    market_cap = stock_data.get('market_cap', 0)
    cash_runway = stock_data.get('cash_runway_quarters', 999)
    primary = get_primary_model(market_cap, cash_runway)
    
    # Determine recommendation based on primary model
    primary_score = score_a if primary == 'A' else score_b
    
    if primary == 'A':
        if primary_score >= 85:
            recommendation = 'BUY'
            confidence = 'HIGH'
        elif primary_score >= 70:
            recommendation = 'WATCH'
            confidence = 'MEDIUM'
        else:
            recommendation = 'PASS'
            confidence = 'LOW'
    else:  # Model B
        if primary_score >= 75:
            recommendation = 'BUY'
            confidence = 'HIGH'
        elif primary_score >= 60:
            recommendation = 'WATCH'
            confidence = 'MEDIUM'
        else:
            recommendation = 'PASS'
            confidence = 'LOW'
    
    # Boost confidence if both models agree
    if score_a >= 70 and score_b >= 60:
        if confidence == 'MEDIUM':
            confidence = 'HIGH'
    
    return {
        'model_a_score': score_a,
        'model_a_signals': signals_a,
        'model_b_score': score_b,
        'model_b_signals': signals_b,
        'primary_model': primary,
        'primary_score': primary_score,
        'recommendation': recommendation,
        'confidence': confidence
    }

# Export functions
__all__ = [
    'calculate_model_a_score',
    'calculate_model_b_score',
    'calculate_dual_scores',
    'get_primary_model'
]
