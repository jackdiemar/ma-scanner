#!/usr/bin/env python3
"""
M&A Scanner V11.0 — Email Alert System
Clean, professional design with company logos.
Apple Mail + iOS Mail optimized (table layout, inline CSS only).
"""

import smtplib
import json
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from secure_config import get_env

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = get_env("SMTP_USER")
SMTP_PASSWORD = get_env("SMTP_PASSWORD")
RECIPIENT     = get_env("SMTP_RECIPIENT", SMTP_USER)
FMP_KEY       = get_env("FMP_API_KEY")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIR = os.path.join(REPO_ROOT, "data", "scans")

# FMP logo URL — publicly accessible, no key needed
def _logo_url(ticker):
    return f"https://financialmodelingprep.com/image-stock/{ticker}.png"

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────

C = {
    'page_bg':       '#F5F5F5',
    'white':         '#FFFFFF',
    'black':         '#000000',
    'text_primary':  '#1A1A1A',
    'text_secondary':'#555555',
    'text_tertiary': '#999999',
    'border':        '#E8E8E8',
    'border_light':  '#F0F0F0',
    'green':         '#00C805',   # Robinhood green
    'green_text':    '#007800',
    'green_bg':      '#F0FFF0',
    'red':           '#FF2D20',
    'red_bg':        '#FFF5F5',
    'amber':         '#FF9500',
    'amber_bg':      '#FFFBF0',
    'gray':          '#8C8C8C',
    'gray_bg':       '#F7F7F7',
    'dark_bg':       '#141414',
    'dark_border':   '#2A2A2A',
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_mcap(m):
    if m is None: return '—'
    if m >= 1000: return f'${m/1000:.1f}B'
    return f'${m:.0f}M'

def _fmt_runway(r):
    if r is None: return '—'
    return f'{r:.1f}Q'

def _fmt_price(p):
    if p is None: return '—'
    return f'${p:.2f}'

def _conviction_color(tier):
    return {
        'HIGH_CONVICTION':   C['red'],
        'MEDIUM_CONVICTION': C['amber'],
        'WATCH':             C['gray'],
        'BANKRUPTCY_RISK':   '#444444',
    }.get(tier, C['gray'])

def _conviction_label(tier):
    return {
        'HIGH_CONVICTION':   'HIGH CONVICTION',
        'MEDIUM_CONVICTION': 'MEDIUM',
        'WATCH':             'WATCH',
        'BANKRUPTCY_RISK':   'EXCLUDED',
    }.get(tier, tier)

def _metric_cell(value, label, border_left=True, color=None):
    bl = f'border-left:1px solid {C["border"]};' if border_left else ''
    vc = color if color else C['text_primary']
    return f"""
    <td style="text-align:center;padding:10px 16px;{bl}">
      <div style="font-size:15px;font-weight:600;color:{vc};line-height:1.2;">{value}</div>
      <div style="font-size:10px;color:{C['text_tertiary']};text-transform:uppercase;
                  letter-spacing:0.6px;margin-top:3px;">{label}</div>
    </td>"""

# ─────────────────────────────────────────────────────────────────────────────
# COMPANY LOGO CELL
# ─────────────────────────────────────────────────────────────────────────────

def _logo_cell(ticker, size=44):
    """Circular company logo from FMP with ticker fallback."""
    url = _logo_url(ticker)
    initials = ticker[:2].upper()
    return f"""
<td width="{size}" style="padding-right:14px;vertical-align:middle;">
  <img src="{url}" width="{size}" height="{size}" alt="{ticker}"
    style="width:{size}px;height:{size}px;border-radius:{size//2}px;
           display:block;background:{C['border_light']};
           object-fit:contain;"
    onerror="this.style.display='none'">
</td>"""

# ─────────────────────────────────────────────────────────────────────────────
# ACQUISITION PATTERN BLOCK — featured section inside each stock card
# ─────────────────────────────────────────────────────────────────────────────

def _acq_pattern_block(acq_pat):
    """Renders the acquisition pattern match section for a stock card.
    Returns empty string if no pattern data."""
    if not acq_pat or not acq_pat.get('similar_deals') and not acq_pat.get('matched_patterns'):
        return ''

    similar     = acq_pat.get('similar_deals', [])
    patterns    = acq_pat.get('matched_patterns', [])
    acquirers   = acq_pat.get('acquirer_interest', [])
    impl_prem   = acq_pat.get('implied_premium', 0)
    pat_score   = acq_pat.get('pattern_score', 0)

    if pat_score < 2:
        return ''

    # Deal comparison chips
    deal_chips = ''
    for deal in similar[:3]:
        deal_chips += f"""
      <span style="display:inline-block;background:#FFF8E7;border:1px solid #FFD966;
                   border-radius:4px;padding:3px 8px;font-size:10px;font-weight:600;
                   color:#7A5C00;margin:2px 3px 2px 0;white-space:nowrap;">
        {deal['ticker']} → {deal['acquirer']}
        &nbsp;·&nbsp; ${deal['deal_B']:.1f}B
        &nbsp;·&nbsp; +{deal['premium']}%
      </span>"""

    # Pattern match tags
    pattern_tags = ''
    for p in patterns[:3]:
        pattern_tags += f"""
      <div style="font-size:11px;color:#5C4A00;margin-top:3px;line-height:1.4;">
        <span style="color:#F5A623;font-weight:700;">▶</span>&nbsp;{p[:90]}
      </div>"""

    # Acquirer interest line
    acquirer_html = ''
    if acquirers:
        acquirer_html = f"""
    <div style="margin-top:6px;font-size:11px;color:#555555;">
      <span style="font-weight:600;color:#333333;">Likely acquirers:</span>&nbsp;
      {' · '.join(acquirers[:4])}
    </div>"""

    # Implied premium
    prem_html = ''
    if impl_prem > 0:
        prem_html = f"""
      <div style="font-size:11px;color:#7A5C00;font-weight:600;margin-top:4px;">
        Implied acquisition premium: +{impl_prem:.0f}%
        &nbsp;<span style="font-weight:400;color:#999;">(based on comparable deals)</span>
      </div>"""

    return f"""
  <!-- Acquisition Pattern Match -->
  <tr>
    <td style="padding:0 20px 14px 20px;border-top:1px solid #FFF0C0;
               background:linear-gradient(to bottom, #FFFDF0, #FFFFFF);">

      <!-- Section label -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
        style="margin-top:10px;">
        <tr>
          <td>
            <span style="font-size:10px;font-weight:800;color:#B8860B;
                         text-transform:uppercase;letter-spacing:1px;">
              🎯 Acquisition Pattern Match
            </span>
            <span style="font-size:10px;color:#999999;margin-left:6px;">
              +{pat_score:.0f} pts · mirrors recent completed deals
            </span>
          </td>
        </tr>
      </table>

      <!-- Comparable deals -->
      <div style="margin-top:6px;">
        {deal_chips}
      </div>

      <!-- Pattern descriptions -->
      {pattern_tags}

      {prem_html}
      {acquirer_html}

    </td>
  </tr>"""


# ─────────────────────────────────────────────────────────────────────────────
# STOCK CARD — HIGH and MEDIUM tiers
# ─────────────────────────────────────────────────────────────────────────────

def _stock_card(r, is_first=False):
    tier       = r.get('conviction_tier', 'WATCH')
    score      = r.get('score', 0)
    ticker     = r.get('ticker', '')
    company    = r.get('company', '')
    price      = r.get('price', 0) or 0
    mcap       = _fmt_mcap(r.get('mcap_M'))
    runway     = _fmt_runway(r.get('runway_Q'))
    phase3     = r.get('phase3_count', 0)
    phase2     = r.get('phase2_count', 0)
    rev        = r.get('revenue_M', 0) or 0
    profitable = r.get('is_profitable', False)
    sell_pct   = r.get('sell_pct', 0) or 0
    has_buy    = r.get('has_buying', False)
    pt_up      = r.get('pt_upside_pct', 0) or 0
    hotspot    = r.get('hotspot') or {}
    acq_pat    = r.get('acq_pattern') or {}
    signals    = [s for s in r.get('signals', []) if s.get('pts', 0) > 0][:5]
    flags      = r.get('flags', [])

    # Tracking badge
    is_new      = r.get('is_new_pick', True)
    days        = r.get('days_tracked', 0)
    first_price = r.get('first_price')
    scan_count  = r.get('scan_count', 0)
    if is_new:
        track_html = (f'<span style="background:#E8F5E9;color:#2E7D32;font-size:9px;'
                      f'font-weight:700;padding:2px 6px;border-radius:3px;'
                      f'letter-spacing:0.5px;">NEW PICK</span>')
    else:
        price_chg_str = ''
        if first_price and price:
            chg = ((price - first_price) / first_price) * 100
            sign = '+' if chg >= 0 else ''
            clr = C['green_text'] if chg >= 0 else C['red']
            price_chg_str = (f' &nbsp;<span style="color:{clr};font-weight:600;">'
                             f'{sign}{chg:.0f}%</span>')
        if days >= 180:
            bg, fg = '#FFF3E0', '#E65100'
        elif days >= 90:
            bg, fg = '#FFF8E1', '#F57F17'
        else:
            bg, fg = '#F3F3F3', '#666666'
        track_html = (f'<span style="background:{bg};color:{fg};font-size:9px;'
                      f'font-weight:600;padding:2px 6px;border-radius:3px;">'
                      f'↩ {days}d · {scan_count} scans{price_chg_str}</span>')

    conv_color = _conviction_color(tier)
    conv_label = _conviction_label(tier)
    mt = 'margin-top:0;' if is_first else 'margin-top:12px;'

    # Pipeline summary
    if phase3 >= 1:
        pipeline_str = f'Phase 3: {phase3}'
        if phase2 > 0: pipeline_str += f'  ·  Phase 2: {phase2}'
    elif phase2 >= 1:
        pipeline_str = f'Phase 2: {phase2}'
    else:
        pipeline_str = 'No registered trials'

    # Revenue summary
    if rev >= 50:
        rev_str = f'${rev:.0f}M revenue' + (' · profitable' if profitable else '')
    elif rev >= 5:
        rev_str = f'${rev:.0f}M revenue'
    else:
        rev_str = 'Pre-revenue'

    # Insider activity
    if has_buy and sell_pct < 1.0:
        insider_str = 'Buying'
        insider_color = C['green_text']
    elif sell_pct >= 2.0:
        insider_str = f'{sell_pct:.1f}% selling'
        insider_color = C['red']
    elif sell_pct >= 0.5:
        insider_str = f'{sell_pct:.1f}% selling'
        insider_color = C['amber']
    else:
        insider_str = 'Neutral'
        insider_color = C['text_tertiary']

    # Analyst upside
    if pt_up >= 20:
        analyst_str = f'+{pt_up:.0f}%'
        analyst_color = C['green_text']
    elif pt_up > 0:
        analyst_str = f'+{pt_up:.0f}%'
        analyst_color = C['text_secondary']
    else:
        analyst_str = '—'
        analyst_color = C['text_tertiary']

    # Hotspot
    hotspot_name = hotspot.get('name', '') if hotspot else ''

    # Build signal list
    sig_rows = ''
    for sig in signals:
        pts    = sig.get('pts', 0)
        s_type = sig.get('type', '')
        detail = sig.get('detail', '')[:70]
        sig_rows += f"""
    <tr>
      <td style="padding:7px 0;border-top:1px solid {C['border_light']};
                 font-size:12px;line-height:1.4;">
        <span style="color:{C['green_text']};font-weight:600;font-size:11px;">
          +{pts:.0f} pts
        </span>
        &nbsp;
        <span style="color:{C['text_secondary']};">{s_type}</span>
        <br>
        <span style="color:{C['text_tertiary']};font-size:11px;">{detail}</span>
      </td>
    </tr>"""

    # Flags
    flag_rows = ''
    for flag in flags[:2]:
        flag_rows += f"""
    <tr>
      <td style="padding:5px 0;font-size:11px;color:{C['amber']};
                 border-top:1px solid {C['border_light']};">
        {flag}
      </td>
    </tr>"""

    return f"""
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="{mt}background:{C['white']};border-radius:10px;
         border:1px solid {C['border']};overflow:hidden;">

  <!-- Card header: logo + name + score -->
  <tr>
    <td style="padding:18px 20px 14px 20px;
               border-bottom:1px solid {C['border_light']};">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          {_logo_cell(ticker, size=42)}
          <td style="vertical-align:middle;">
            <div style="font-size:18px;font-weight:700;color:{C['text_primary']};
                        letter-spacing:-0.3px;line-height:1.1;">{ticker}
              &nbsp;{track_html}
            </div>
            <div style="font-size:12px;color:{C['text_tertiary']};margin-top:2px;
                        white-space:nowrap;overflow:hidden;">
              {company[:45]}{'…' if len(company) > 45 else ''}
            </div>
          </td>
          <td align="right" style="vertical-align:middle;white-space:nowrap;">
            <div style="display:inline-block;background:{conv_color};
                        color:#FFFFFF;font-size:10px;font-weight:700;
                        letter-spacing:0.8px;text-transform:uppercase;
                        padding:4px 10px;border-radius:4px;">
              {conv_label}
            </div>
            <div style="font-size:24px;font-weight:800;color:{C['text_primary']};
                        letter-spacing:-0.8px;margin-top:6px;text-align:right;">
              {score:.0f}
              <span style="font-size:11px;font-weight:400;color:{C['text_tertiary']};">pts</span>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Metrics row -->
  <tr>
    <td style="background:{C['gray_bg']};padding:0;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          {_metric_cell(_fmt_price(price), 'Price', border_left=False)}
          {_metric_cell(mcap, 'Mkt Cap')}
          {_metric_cell(runway, 'Runway')}
          {_metric_cell(insider_str, 'Insider', color=insider_color)}
          {_metric_cell(analyst_str, 'PT Upside', color=analyst_color)}
        </tr>
      </table>
    </td>
  </tr>

  <!-- Pipeline / Revenue / Hotspot row -->
  <tr>
    <td style="padding:10px 20px;border-top:1px solid {C['border_light']};
               border-bottom:1px solid {C['border_light']};">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="font-size:12px;color:{C['text_secondary']};">
            <strong style="color:{C['text_primary']};">Pipeline:</strong>
            {pipeline_str}
          </td>
          <td style="font-size:12px;color:{C['text_secondary']};
                     border-left:1px solid {C['border']};padding-left:16px;
                     text-align:right;">
            {rev_str}
            {'&nbsp;&nbsp;<strong style="color:' + C['green_text'] + ';">●</strong> ' + hotspot_name if hotspot_name else ''}
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Signals -->
  <tr>
    <td style="padding:0 20px 4px 20px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        {sig_rows}
        {flag_rows}
      </table>
    </td>
  </tr>

  {_acq_pattern_block(acq_pat)}

</table>"""


# ─────────────────────────────────────────────────────────────────────────────
# WATCH ROW — compact
# ─────────────────────────────────────────────────────────────────────────────

def _watch_row(r, is_last=False):
    ticker  = r.get('ticker', '')
    company = r.get('company', '')
    score   = r.get('score', 0)
    price   = r.get('price', 0) or 0
    mcap    = _fmt_mcap(r.get('mcap_M'))
    runway  = _fmt_runway(r.get('runway_Q'))
    phase3  = r.get('phase3_count', 0)
    rev_m   = r.get('revenue_M', 0) or 0
    hotspot = (r.get('hotspot') or {}).get('name', '')
    has_buy = r.get('has_buying', False)

    tags = []
    if phase3 > 0: tags.append(f'Ph3×{phase3}')
    if rev_m > 10: tags.append(f'${rev_m:.0f}M rev')
    if hotspot:    tags.append(hotspot)
    if has_buy:    tags.append('Insider buying')
    tag_str = '  ·  '.join(tags[:3]) or 'Monitor'

    bb = '' if is_last else f'border-bottom:1px solid {C["border_light"]};'

    return f"""
<tr>
  <td style="padding:11px 16px;{bb}">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        {_logo_cell(ticker, size=32)}
        <td style="vertical-align:middle;">
          <div style="font-size:14px;font-weight:700;color:{C['text_primary']};
                      letter-spacing:-0.2px;">{ticker}
            <span style="font-size:11px;font-weight:400;color:{C['text_tertiary']};
                         margin-left:6px;">{company[:30]}{'…' if len(company)>30 else ''}</span>
          </div>
          <div style="font-size:11px;color:{C['text_tertiary']};margin-top:2px;">{tag_str}</div>
        </td>
        <td align="right" style="vertical-align:middle;white-space:nowrap;">
          <div style="font-size:14px;font-weight:600;color:{C['text_primary']};">{score:.0f}</div>
          <div style="font-size:10px;color:{C['text_tertiary']};">${price:.2f} · {mcap}</div>
        </td>
      </tr>
    </table>
  </td>
</tr>"""


# ─────────────────────────────────────────────────────────────────────────────
# BANKRUPT ROW
# ─────────────────────────────────────────────────────────────────────────────

def _bankrupt_row(r, is_last=False):
    ticker  = r.get('ticker', '')
    price   = r.get('price', 0) or 0
    mcap    = _fmt_mcap(r.get('mcap_M'))
    reasons = r.get('flags', [])
    reason  = reasons[0][:80] if reasons else 'Failed exclusion filter'
    bb = '' if is_last else f'border-bottom:1px solid {C["dark_border"]};'
    return f"""
<tr>
  <td style="padding:10px 16px;{bb}">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td>
          <span style="font-size:13px;font-weight:600;color:#555555;">{ticker}</span>
          <span style="font-size:11px;color:#444444;margin-left:8px;">${price:.2f} · {mcap}</span>
          <br>
          <span style="font-size:11px;color:#444444;line-height:1.5;">{reason}</span>
        </td>
      </tr>
    </table>
  </td>
</tr>"""


# ─────────────────────────────────────────────────────────────────────────────
# SECTION HEADER
# ─────────────────────────────────────────────────────────────────────────────

def _section_header(label, color, mt='24px'):
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="margin-top:{mt};">
  <tr>
    <td style="padding:0 0 10px 0;">
      <span style="font-size:11px;font-weight:700;color:{color};
                   text-transform:uppercase;letter-spacing:1.2px;">{label}</span>
    </td>
  </tr>
</table>"""


# ─────────────────────────────────────────────────────────────────────────────
# FULL EMAIL BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_email(results):
    high     = sorted([r for r in results if r.get('conviction_tier') == 'HIGH_CONVICTION'],
                      key=lambda x: -x.get('score', 0))
    medium   = sorted([r for r in results if r.get('conviction_tier') == 'MEDIUM_CONVICTION'],
                      key=lambda x: -x.get('score', 0))
    watch    = sorted([r for r in results if r.get('conviction_tier') == 'WATCH'],
                      key=lambda x: -x.get('score', 0))
    bankrupt = [r for r in results if r.get('conviction_tier') == 'BANKRUPTCY_RISK']

    total    = len(results)
    now      = datetime.now()
    date_str = now.strftime('%B %d, %Y')
    time_str = now.strftime('%I:%M %p ET')

    # Subject
    if high:
        subject = f'{len(high)} High Conviction Alert{"s" if len(high)>1 else ""} — BSC M&A · {date_str}'
    elif medium:
        subject = f'{len(medium)} Medium Alert{"s" if len(medium)>1 else ""} — BSC M&A · {date_str}'
    else:
        subject = f'M&A Daily Scan — Watch Only · {date_str}'

    # Top bar
    if high:
        bar_color  = C['red']
        bar_label  = f'{len(high)} High Conviction · Review before open'
    elif medium:
        bar_color  = C['amber']
        bar_label  = f'{len(medium)} Medium Conviction · Research recommended'
    else:
        bar_color  = C['gray']
        bar_label  = f'No actionable signals · {len(watch)} on watch'

    # ── Stat summary row ───────────────────────────────────────────────────

    def _stat(n, label, color):
        return f"""
      <td style="text-align:center;padding:16px 0;">
        <div style="font-size:28px;font-weight:700;color:{color};
                    letter-spacing:-1px;line-height:1;">{n}</div>
        <div style="font-size:10px;color:{C['text_tertiary']};
                    text-transform:uppercase;letter-spacing:0.8px;
                    margin-top:4px;">{label}</div>
      </td>"""

    def _stat_divider():
        return f'<td style="width:1px;background:{C["border"]};padding:10px 0;"></td>'

    # Count stocks with acquisition pattern matches
    pattern_hits = sum(
        1 for r in results
        if (r.get('acq_pattern') or {}).get('pattern_score', 0) >= 3
    )

    stats_html = (
        _stat(len(high),    'High',        C['red']   if high   else C['text_tertiary']) +
        _stat_divider() +
        _stat(len(medium),  'Medium',      C['amber'] if medium else C['text_tertiary']) +
        _stat_divider() +
        _stat(len(watch),   'Watch',       C['text_primary']) +
        _stat_divider() +
        _stat(pattern_hits, 'Acq Pattern', '#B8860B' if pattern_hits else C['text_tertiary']) +
        _stat_divider() +
        _stat(total,        'Scanned',     C['text_tertiary'])
    )

    # ── Sections ───────────────────────────────────────────────────────────

    high_html = ''
    if high:
        high_html = _section_header('High Conviction', C['red'], mt='0')
        for i, r in enumerate(high):
            high_html += _stock_card(r, is_first=(i == 0))

    med_html = ''
    if medium:
        mt = '0' if not high else '24px'
        med_html = _section_header('Medium Conviction', C['amber'], mt=mt)
        for i, r in enumerate(medium):
            med_html += _stock_card(r, is_first=(i == 0))

    watch_html = ''
    if watch:
        mt = '0' if not high and not medium else '24px'
        watch_html = _section_header('Watch List', C['text_secondary'], mt=mt)
        watch_rows = ''
        display = watch[:10]
        for i, r in enumerate(display):
            watch_rows += _watch_row(r, is_last=(i == len(display)-1))
        watch_html += f"""
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background:{C['white']};border-radius:10px;
         border:1px solid {C['border']};overflow:hidden;">
  {watch_rows}
</table>"""
        if len(watch) > 10:
            watch_html += (
                f'<p style="font-size:11px;color:{C["text_tertiary"]};'
                f'text-align:center;margin:8px 0 0 0;">+{len(watch)-10} more on watch list</p>'
            )

    bankrupt_html = ''
    if bankrupt:
        bankrupt_html = f"""
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="margin-top:24px;">
  <tr>
    <td style="padding:0 0 10px 0;">
      <span style="font-size:11px;font-weight:700;color:#555555;
                   text-transform:uppercase;letter-spacing:1.2px;">
        Excluded — Failed Risk Filter ({len(bankrupt)})
      </span>
    </td>
  </tr>
</table>
<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background:{C['dark_bg']};border-radius:10px;overflow:hidden;">"""
        for i, r in enumerate(bankrupt):
            bankrupt_html += _bankrupt_row(r, is_last=(i == len(bankrupt)-1))
        bankrupt_html += '</table>'

    # ── Assemble ───────────────────────────────────────────────────────────

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <title>BSC M&amp;A Scanner — {date_str}</title>
</head>
<body style="margin:0;padding:0;background:{C['page_bg']};
             font-family:-apple-system,'SF Pro Text','Helvetica Neue',Helvetica,Arial,sans-serif;
             -webkit-font-smoothing:antialiased;color:{C['text_primary']};">

<table width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background:{C['page_bg']};min-height:100%;">
  <tr>
    <td align="center" style="padding:24px 0 48px 0;">
      <table width="600" cellpadding="0" cellspacing="0" border="0"
        style="max-width:600px;width:100%;">

        <!-- ══ TOP BAR ══════════════════════════════════════════════════════ -->
        <tr>
          <td style="background:{bar_color};padding:10px 20px;border-radius:8px 8px 0 0;">
            <span style="font-size:11px;font-weight:600;color:#FFFFFF;
                         letter-spacing:0.3px;">{bar_label}</span>
          </td>
        </tr>

        <!-- ══ HEADER ═══════════════════════════════════════════════════════ -->
        <tr>
          <td style="background:{C['white']};padding:22px 28px 18px 28px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="vertical-align:bottom;">
                  <div style="font-size:20px;font-weight:800;color:{C['black']};
                               letter-spacing:-0.5px;line-height:1;">
                    Black Starlight Capital
                  </div>
                  <div style="font-size:11px;color:{C['text_tertiary']};margin-top:4px;">
                    M&amp;A Intelligence · V12.0
                  </div>
                </td>
                <td align="right" style="vertical-align:bottom;">
                  <div style="font-size:12px;color:{C['text_secondary']};
                               font-weight:500;">{date_str}</div>
                  <div style="font-size:11px;color:{C['text_tertiary']};
                               margin-top:2px;">{time_str}</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ══ STAT ROW ═════════════════════════════════════════════════════ -->
        <tr>
          <td style="background:{C['white']};
                     border-top:1px solid {C['border']};
                     border-bottom:1px solid {C['border']};
                     padding:0 28px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                {stats_html}
              </tr>
            </table>
          </td>
        </tr>

        <!-- ══ MAIN CONTENT ══════════════════════════════════════════════════ -->
        <tr>
          <td style="background:{C['white']};padding:24px 28px 32px 28px;
                     border-radius:0 0 10px 10px;">
            {high_html}
            {med_html}
            {watch_html}
            {bankrupt_html}
          </td>
        </tr>

        <!-- ══ FOOTER ════════════════════════════════════════════════════════ -->
        <tr>
          <td style="padding:20px 0 0 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="text-align:center;">
                  <p style="font-size:10px;color:{C['text_tertiary']};
                             line-height:1.7;margin:0;padding:0 24px;">
                    <strong style="color:{C['text_secondary']};">
                      Black Starlight Capital &nbsp;·&nbsp; M&amp;A Intelligence
                    </strong><br>
                    Scoring: High ≥86 &nbsp;·&nbsp; Medium ≥78 &nbsp;·&nbsp; Watch ≥70 &nbsp;·&nbsp; V12<br>
                    Gates: HIGH requires Phase 3 or $25M+ rev &nbsp;·&nbsp; MEDIUM requires Phase 3 or $10M+ rev<br>
                    Model: strategic pipeline &nbsp;·&nbsp; acquirability &nbsp;·&nbsp;
                    financial health &nbsp;·&nbsp; catalyst &nbsp;·&nbsp;
                    acq pattern &nbsp;·&nbsp;
                    <strong style="color:#B8860B;">institutional research signals</strong><br>
                    Patent cliff alignment · strategic scarcity · acquirer hunger · EV/Rev comps<br>
                    Staleness penalty: -5pts after 90d · -10pts after 180d on watchlist<br><br>
                    For informational purposes only. Not investment advice.
                    Past signals do not guarantee future outcomes.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>

</body>
</html>"""

    return html, subject


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL SENDER
# ─────────────────────────────────────────────────────────────────────────────

def send_email(html_body, subject, to=RECIPIENT):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f'BSC M&A Scanner <{SMTP_USER}>'
    msg['To']      = to
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to, msg.as_string())

    print(f'✅ Sent to {to}: {subject}')


# ─────────────────────────────────────────────────────────────────────────────
# LOAD SCAN RESULTS
# ─────────────────────────────────────────────────────────────────────────────

def load_latest_scan():
    import glob
    # V12 is the active production scanner.
    files = sorted(glob.glob(os.path.join(SCAN_DIR, 'scan_v12_*.json')))
    if not files:
        raise FileNotFoundError(f'No scan results found in {SCAN_DIR}')
    path = files[-1]
    with open(path) as f:
        data = json.load(f)
    print(f'📂 Loaded: {os.path.basename(path)} ({len(data)} records)')
    return data


def load_scan_file(path):
    with open(path) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='BSC M&A Scanner V12 — Email Alert')
    parser.add_argument('--file',    type=str, help='Path to scan JSON (default: latest)')
    parser.add_argument('--to',      type=str, default=RECIPIENT, help='Recipient email')
    parser.add_argument('--preview', action='store_true', help='Save HTML preview, do not send')
    args = parser.parse_args()

    results = load_scan_file(args.file) if args.file else load_latest_scan()
    html, subject = build_email(results)

    if args.preview:
        preview_path = os.path.join(SCAN_DIR, 'email_preview.html')
        with open(preview_path, 'w') as f:
            f.write(html)
        print(f'📄 Preview: {preview_path}')
        print(f'   Subject: {subject}')
    else:
        send_email(html, subject, to=args.to)
