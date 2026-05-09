"""
trade_logic.py — Event-driven trade decision engine for M&A Scanner V12.

Converts raw scanner output (score, signals, layer flags) into deterministic
trade recommendations with calibrated P(deal), EV, position sizing, and expiry.

Design principles:
- Every decision is deterministic and auditable (no model inference)
- Capital preservation over aggressiveness: all caps are hard limits
- P(deal) values are conservative estimates pending historical calibration
- BUY requires real process evidence — score-only names are WATCH at best
"""

from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# CALIBRATED P(DEAL) TABLE  (conservative; update when actuals are available)
# ─────────────────────────────────────────────────────────────────────────────

P_DEAL = {
    'sa_affirm':        0.42,   # SA affirm: ~60-70% deal within 24mo; ~42% within 12mo
    'merger_agreement': 0.92,   # Signed merger agreement — near certain
    'banker_retained':  0.25,   # Banker retained / potential sale language
    'activist_fresh':   0.30,   # Known biotech activist 13D, ≤30 days old
    'activist_aged':    0.18,   # Activist 13D, 31-60 days old
    'rofn_rofr':        0.20,   # ROFN/ROFR clause with named pharma
    'score_high':       0.10,   # Score ≥86, no L7 — pure fundamentals
    'score_medium':     0.06,   # Score 78-85, no L7
    'score_watch':      0.03,   # Score 70-77, no L7 — noise floor
}

STALENESS_P_MULTIPLIER = 0.70   # Applied when staleness_pen ≥10

# ─────────────────────────────────────────────────────────────────────────────
# TRADE RULE CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MIN_EV_PER_SHARE     = 0.12    # Minimum EV to be BUY-eligible (covers spread + slippage)
MIN_P_DEAL_BUY       = 0.15    # P(deal) floor for BUY
MAX_FRESHNESS_BUY    = 45      # L7 signal must be ≤45 days old for BUY
MAX_FRESHNESS_WATCH  = 90      # L7 signal 46-90d → WATCH; >90d → score-only P(deal)
PRICED_IN_LOW_RATIO  = 1.55    # price/year_low above this → reduce upside assumption
PRICED_IN_ENTRY_RATIO = 1.35   # price/first_price above this → WATCH only (already ran)
MIN_MCAP_BUY         = 200     # $200M mcap minimum for BUY (tighter than bankruptcy gate)
MIN_MCAP_ILLIQ       = 400     # Below $400M → apply illiquidity haircut to position

DEFAULT_UPSIDE_PCT   = 0.70    # Calibrated: backtest median 75%, mean 78%; -8pt haircut for pre-announcement run-up → 0.70
DEFAULT_DOWNSIDE_PCT = 0.30    # Typical downside if deal fails / thesis collapses

STOP_LOSS_PCT        = 0.22    # 22% drawdown from entry → mandatory exit

# Max position sizes by signal quality (% of portfolio, hard caps)
MAX_POSITION = {
    'AFFIRM':    0.030,   # SA affirm: 3.0%
    'PROCESS':   0.020,   # Banker retained or fresh activist 13D: 2.0%
    'ROFR':      0.015,   # ROFN/ROFR clause: 1.5%
    'SCORE_ONLY': 0.000,  # Score-only: no position, WATCH only
    'BOILERPLATE': 0.000, # Boilerplate SA: never tradeable
}

# Signal expiry windows (days from freshest L7 filing date)
EXPIRY_DAYS = {
    'sa_affirm':        300,
    'merger_agreement': 180,
    'banker_retained':  210,
    'activist':         365,
    'rofn_rofr':        540,
    'score_only':        60,
}


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def classify_signal_quality(result: dict) -> str:
    """
    Returns a single label describing the best/dominant L7 signal present.

    AFFIRM      — SA affirm in 8-K (board explicitly exploring sale)
    MERGER      — Signed merger agreement
    PROCESS     — Banker retained or fresh activist 13D (≤45d)
    ROFR        — ROFN/ROFR/ROFO clause with named pharma
    BOILERPLATE — Strategic alternatives mentioned but sa_is_affirm=False
    SCORE_ONLY  — No L7 signal; score-driven thesis only
    """
    ts    = result.get('_text_signals', {}) or {}
    act   = result.get('_activist_signal', {}) or {}

    if ts.get('merger_agreement'):
        return 'MERGER'
    if result.get('strategic_alternatives') and ts.get('sa_is_affirm', False):
        return 'AFFIRM'
    if result.get('strategic_alternatives') and not ts.get('sa_is_affirm', False):
        return 'BOILERPLATE'
    if result.get('banker_retained'):
        return 'PROCESS'
    if act and signal_freshness_days(result) <= 45:
        return 'PROCESS'
    if result.get('has_rofn') or result.get('has_rofr'):
        return 'ROFR'
    return 'SCORE_ONLY'


def signal_freshness_days(result: dict) -> int:
    """
    Returns age in days of the freshest L7 signal (filing or 8-K date).
    Returns 999 if no L7 signal date is available.
    """
    act       = result.get('_activist_signal', {}) or {}
    ts        = result.get('_text_signals', {}) or {}
    proxy     = result.get('_proxy_signal', {}) or {}
    scan_date = result.get('scan_date', datetime.now().isoformat())

    try:
        today = datetime.fromisoformat(scan_date)
    except (ValueError, TypeError):
        today = datetime.now()

    candidates = []

    filing_date = act.get('filing_date', '')
    if filing_date:
        try:
            candidates.append(datetime.fromisoformat(filing_date[:10]))
        except (ValueError, TypeError):
            pass

    for key in ('filing_date', '8k_date', 'date'):
        val = ts.get(key, '')
        if val:
            try:
                candidates.append(datetime.fromisoformat(str(val)[:10]))
                break
            except (ValueError, TypeError):
                pass

    if not candidates:
        return 999

    freshest = max(candidates)
    return max(0, (today - freshest).days)


def score_to_p_deal(result: dict) -> float:
    """
    Maps scanner output to a calibrated P(deal) probability.
    Applies staleness discount if staleness_pen >= 10.
    """
    ts  = result.get('_text_signals', {}) or {}
    act = result.get('_activist_signal', {}) or {}

    # Signed merger agreement — highest confidence
    if ts.get('merger_agreement'):
        p = P_DEAL['merger_agreement']

    elif result.get('strategic_alternatives') and ts.get('sa_is_affirm', False):
        p = P_DEAL['sa_affirm']
        if result.get('has_rofn') or result.get('has_rofr'):
            p = min(p + 0.08, 0.50)

    elif result.get('banker_retained'):
        p = P_DEAL['banker_retained']

    elif act:
        age = signal_freshness_days(result)
        p   = P_DEAL['activist_fresh'] if age <= 30 else P_DEAL['activist_aged']

    elif result.get('has_rofn') or result.get('has_rofr'):
        p = P_DEAL['rofn_rofr']

    else:
        # Score-only — no real process evidence
        score = result.get('score', 0)
        if score >= 86:
            p = P_DEAL['score_high']
        elif score >= 78:
            p = P_DEAL['score_medium']
        else:
            p = P_DEAL['score_watch']

    # Staleness discount
    staleness_pen = result.get('layer_scores', {}).get('penalties', 0)
    if staleness_pen >= 10:
        p *= STALENESS_P_MULTIPLIER

    return round(p, 4)


def compute_ev(p_deal: float, price: float,
               upside_pct: float = DEFAULT_UPSIDE_PCT,
               downside_pct: float = DEFAULT_DOWNSIDE_PCT) -> float:
    """
    EV = P(deal) × (upside_pct × price) − (1 − P(deal)) × (downside_pct × price)
    Returns expected value per share in dollars.
    """
    ev = p_deal * (upside_pct * price) - (1 - p_deal) * (downside_pct * price)
    return round(ev, 4)


def half_kelly_size(p_deal: float,
                    upside_pct: float = DEFAULT_UPSIDE_PCT,
                    downside_pct: float = DEFAULT_DOWNSIDE_PCT) -> float:
    """
    Returns half-Kelly fraction of portfolio to allocate (0.0–1.0).
    Formula: f = 0.5 × (P×W − (1−P)×L) / W
    Returns 0.0 if Kelly is negative (negative EV).
    """
    kelly = (p_deal * upside_pct - (1 - p_deal) * downside_pct) / upside_pct
    return max(0.0, round(0.5 * kelly, 4))


def is_priced_in(result: dict) -> bool:
    """
    Returns True if the stock has already run significantly, reducing risk/reward.
    Triggers when price/year_low > 1.55 OR price/first_price > 1.35.
    """
    price      = result.get('price', 0) or 0
    year_low   = result.get('year_low') or price
    first_price = result.get('first_price') or price

    if price <= 0:
        return False

    low_ratio   = price / year_low   if year_low   > 0 else 1.0
    entry_ratio = price / first_price if first_price > 0 else 1.0

    return low_ratio > PRICED_IN_LOW_RATIO or entry_ratio > PRICED_IN_ENTRY_RATIO


def is_trade_expired(result: dict) -> bool:
    """
    Returns True if the dominant signal has exceeded its holding window.
    """
    ts  = result.get('_text_signals', {}) or {}
    act = result.get('_activist_signal', {}) or {}
    age = signal_freshness_days(result)

    if ts.get('merger_agreement'):
        return age > EXPIRY_DAYS['merger_agreement']
    if result.get('strategic_alternatives') and ts.get('sa_is_affirm', False):
        return age > EXPIRY_DAYS['sa_affirm']
    if result.get('banker_retained'):
        return age > EXPIRY_DAYS['banker_retained']
    if act:
        return age > EXPIRY_DAYS['activist']
    if result.get('has_rofn') or result.get('has_rofr'):
        return age > EXPIRY_DAYS['rofn_rofr']
    return age > EXPIRY_DAYS['score_only']


def _expiry_days_remaining(result: dict) -> int:
    """Returns days until the dominant signal expires (negative = already expired)."""
    ts  = result.get('_text_signals', {}) or {}
    act = result.get('_activist_signal', {}) or {}
    age = signal_freshness_days(result)

    if ts.get('merger_agreement'):
        window = EXPIRY_DAYS['merger_agreement']
    elif result.get('strategic_alternatives') and ts.get('sa_is_affirm', False):
        window = EXPIRY_DAYS['sa_affirm']
    elif result.get('banker_retained'):
        window = EXPIRY_DAYS['banker_retained']
    elif act:
        window = EXPIRY_DAYS['activist']
    elif result.get('has_rofn') or result.get('has_rofr'):
        window = EXPIRY_DAYS['rofn_rofr']
    else:
        window = EXPIRY_DAYS['score_only']

    return window - age


def build_trade_rec(result: dict, portfolio_size: float = 1_000_000) -> dict:
    """
    Assembles a complete, deterministic trade recommendation from scanner output.

    Returns dict with:
        trade_decision  — 'BUY' | 'WATCH' | 'IGNORE'
        no_trade_reason — human-readable reason when not BUY ('' if BUY)
        p_deal          — calibrated deal probability
        ev_per_share    — expected value per share ($)
        position_pct    — % of portfolio to allocate (0.0 if not BUY)
        position_usd    — dollar amount to allocate
        signal_age_days — age of freshest L7 signal in days
        expiry_days     — days until signal expires
        signal_quality  — 'AFFIRM' | 'MERGER' | 'PROCESS' | 'ROFR' | 'BOILERPLATE' | 'SCORE_ONLY'
        stop_loss_pct   — hard stop-loss % below entry
    """
    price     = result.get('price', 0) or 0
    mcap      = result.get('mcap_M', 0) or 0
    score     = result.get('score', 0) or 0
    staleness = result.get('layer_scores', {}).get('penalties', 0)
    ts        = result.get('_text_signals', {}) or {}

    sig_quality = classify_signal_quality(result)
    p_deal      = score_to_p_deal(result)
    age_days    = signal_freshness_days(result)
    expiry_rem  = _expiry_days_remaining(result)
    expired     = expiry_rem < 0

    # Upside adjustment for priced-in stocks
    upside_pct   = DEFAULT_UPSIDE_PCT
    downside_pct = DEFAULT_DOWNSIDE_PCT
    priced_in    = is_priced_in(result)
    if priced_in:
        upside_pct = round(upside_pct * 0.60, 3)   # 40% haircut to upside

    ev = compute_ev(p_deal, price, upside_pct, downside_pct)

    # ── NO-TRADE GATE — evaluate in priority order ───────────────────────────
    no_trade_reason = ''

    if sig_quality == 'BOILERPLATE':
        no_trade_reason = 'Boilerplate SA language — sa_is_affirm=False; not a live process'
    elif sig_quality == 'MERGER':
        no_trade_reason = 'Merger agreement already signed — enter at tender price, no new position'
    elif sig_quality == 'SCORE_ONLY':
        no_trade_reason = 'No real process evidence — score-only names are WATCH floor only'
    elif expired:
        no_trade_reason = f'Signal expired ({age_days}d old; window is {age_days - expiry_rem}d)'
    elif staleness >= 10:
        no_trade_reason = f'Staleness penalty {staleness}pts — pick stale >180d with no new signal'
    elif mcap < MIN_MCAP_BUY:
        no_trade_reason = f'mcap ${mcap:.0f}M below ${MIN_MCAP_BUY}M liquidity floor'
    elif p_deal < MIN_P_DEAL_BUY:
        no_trade_reason = f'P(deal) {p_deal:.2f} below {MIN_P_DEAL_BUY} floor'
    elif priced_in:
        no_trade_reason = 'Stock already ran >35% from entry or >55% from year-low — risk/reward degraded'
    elif ev < MIN_EV_PER_SHARE:
        no_trade_reason = f'EV ${ev:.3f}/share below ${MIN_EV_PER_SHARE} minimum'
    elif age_days > MAX_FRESHNESS_BUY:
        no_trade_reason = f'L7 signal {age_days}d old — exceeds {MAX_FRESHNESS_BUY}d freshness gate for BUY'

    # ── POSITION SIZING ───────────────────────────────────────────────────────
    if no_trade_reason:
        # Determine if WATCH or IGNORE
        watchable = (
            sig_quality in ('AFFIRM', 'PROCESS', 'ROFR')
            and not expired
            and score >= 70
            and mcap >= 150
        )
        trade_decision = 'WATCH' if watchable else 'IGNORE'
        position_pct   = 0.0
        position_usd   = 0.0
    else:
        trade_decision = 'BUY'
        max_pct  = MAX_POSITION.get(sig_quality, 0.0)
        raw_kelly = half_kelly_size(p_deal, upside_pct, downside_pct)
        position_pct = min(raw_kelly, max_pct)

        # Staleness soft discount
        if staleness >= 5:
            position_pct *= 0.50

        # Illiquidity haircut
        if mcap < MIN_MCAP_ILLIQ:
            position_pct *= 0.70

        position_pct = round(position_pct, 4)
        position_usd = round(position_pct * portfolio_size, 2)

    return {
        'trade_decision':  trade_decision,
        'no_trade_reason': no_trade_reason,
        'p_deal':          p_deal,
        'ev_per_share':    ev,
        'position_pct':    position_pct,
        'position_usd':    position_usd,
        'signal_age_days': age_days if age_days < 999 else None,
        'expiry_days':     max(expiry_rem, 0),
        'signal_quality':  sig_quality,
        'stop_loss_pct':   STOP_LOSS_PCT,
    }
