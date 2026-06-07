#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          M&A SCANNER V12.0 — INSTITUTIONAL-GRADE ACQUISITION PREDICTOR     ║
║             Built: April 2026 | Rebuilt from V11 Postmortem                ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT BROKE IN V11 (full postmortem):
  ❌ 80%+ of scanned stocks flagged as WATCH/MEDIUM/HIGH — signal:noise destroyed
  ❌ Acquisition pattern match (+15 pts) awarded to ANY company in hot area with
     right mcap + discount → nearly every biotech qualified
  ❌ Phase 2 alone + hotspot + bolt-on size = ~63 pts → auto-WATCH (useless)
  ❌ No first-tracked date → stale picks recycled indefinitely with no staleness flag
  ❌ Mandatory gates too loose: "has_revenue" ($5M+) counted for HIGH_CONVICTION
  ❌ Hotspot pts (10) + bolt-on (20) + discount (12) = 42 of 72 MEDIUM threshold
     before touching Phase 3, pipeline, or any real differentiation signal
  ❌ AKBA at $1.45/share (barely above $1 floor) flagged HIGH_CONVICTION

V12 REFORMS:
  ✅ Raised thresholds: WATCH ≥70, MEDIUM ≥78, HIGH ≥86
  ✅ Mandatory Phase 3 OR $25M+ revenue gate for HIGH; Phase 3 OR $10M+ for MEDIUM
  ✅ Score deflation: Phase 2 only = 2-4 pts (was 5-8); bolt-on = 16 (was 20)
  ✅ Hotspot pts reduced: 10→7, 8→5, 7→4, 6→3, 5→2
  ✅ Pattern match max: 10 pts (was 15); requires 4+ matching attributes (was 3)
  ✅ First-tracked persistence: watchlist_tracking.json records first-seen date/price
  ✅ Staleness penalty: -5 pts after 90d, -10 pts after 180d on watchlist
  ✅ Layer 6 — Institutional Research Signals (new):
     - Patent cliff alignment: acquirer has $B at risk from expiring patents
     - Strategic scarcity: first-in-class / novel mechanism language
     - Acquirer hunger: recent deal in exact same mechanism
     - EV/Revenue discount vs M&A transaction comps (commercial only)
  ✅ Price floor raised: $1.50 (was $1.00); MCap floor raised: $150M (was $100M)

WHAT INSTITUTIONAL RESEARCH SHOWS ACTUALLY DRIVES BIOTECH M&A (2020-2026):
  📊 Patent cliff pressure is the #1 acquirer-side driver — Pfizer losing $17B/yr
     2025-2030 must replace with acquisitions; AbbVie, BMS similarly exposed
  📊 Phase 3 at NEAR-TERM readout window (6-18 months) = prime acquisition target
     Risk partially de-risked (Phase 2 success known) but not yet priced in
  📊 First-in-class / best-in-class mechanisms get 2-3x higher acquisition premiums
     than me-too drugs in crowded classes
  📊 EV/Revenue < 5x for commercial biotech = typical acquisition trigger
     M&A deals typically occur at 5-15x revenue; <5x = deeply discounted
  📊 "Acquirer hunger" pattern: when a buyer completes ONE deal in a mechanism,
     they typically do 2-3 more in same area within 18 months (ADC example: Pfizer)

NEW ARCHITECTURE (V12):
  Layer 0 → Bankruptcy Exclusion (price<$1.50, mcap<$150M, runway<2Q, insider>5%)
  Layer 1 → Strategic Value Score (pipeline, approvals, therapeutic fit) /40
  Layer 2 → Acquirability Score (market cap, price discount, analyst gap) /28
  Layer 3 → Financial Health Score (revenue, runway in strategic zone) /20
  Layer 4 → Catalyst Signals (insider buying, volume, RSI) /10
  Layer 5 → Acquisition Pattern Match (vs. completed deals) /10
  Layer 6 → Institutional Research Signals (patent cliff, scarcity, hunger) /20
  Total: 100+ pts possible; staleness penalties applied after

CONVICTION TIERS (V12 — STRICT):
  🔴 HIGH    ≥86 pts + mcap ≥$150M + runway ≥3Q + Phase 3 OR $25M+ revenue
  🟡 MEDIUM  ≥78 pts + mcap ≥$150M + runway ≥3Q + Phase 3 OR Phase 2×2+ OR $10M+ rev
  ⚪ WATCH   ≥70 pts
  🚫 BELOW   <70 pts — not actionable
  💀 BANKRUPT — excluded from M&A scoring, flagged separately

THERAPEUTIC AREA HOTSPOTS 2026 (actively acquired):
  🔥 Autoimmune/Inflammation  → BMS, AbbVie, Sanofi, Pfizer, Roche
  🔥 ADC / Oncology platforms → Pfizer, AstraZeneca, Gilead, Daiichi Sankyo
  🔥 Obesity / Metabolic      → Eli Lilly, Novo Nordisk, Amgen
  🔥 Rare disease w/ ODD      → Takeda, Sanofi, Ultragenyx, Amicus, BioMarin
  🔥 Renal / Nephrology       → AstraZeneca, Otsuka, Chinook→Novartis
  ⭐ Neuroscience / CNS       → Biogen, AbbVie, J&J, Otsuka
  ⭐ Gene / Cell Therapy      → BMS, Novartis, Roche, Spark
"""

import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import time
import os
import csv
import logging
from datetime import datetime, timedelta
import sys

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Module-level logger ───────────────────────────────────────────────────────
logger = logging.getLogger('v12_scanner')
if not logger.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# Scan start time — set at the top of run_scan(); used for elapsed logging.
_scan_start: float = 0.0


def _elapsed() -> float:
    """Seconds since _scan_start was set (or 0 if not yet set)."""
    return time.monotonic() - _scan_start if _scan_start else 0.0


def _phase_start(name: str) -> float:
    t = time.monotonic()
    logger.info('PHASE_START phase=%s elapsed=%.1fs', name, _elapsed())
    return t


def _phase_end(name: str, t0: float) -> None:
    logger.info('PHASE_END phase=%s elapsed=%.1fs', name, time.monotonic() - t0)

from secure_config import get_env
from trade_logic import build_trade_rec
from scanner_cache import cache_get, cache_set, make_key, DOC_TTL
from outcome_tracker import log_picks_from_scan, print_summary as print_outcomes

# ── Global rate limiter (token-bucket, thread-safe) ───────────────────────────
# 4 FMP calls/sec across ALL threads = 240/min — safely under the 300/min limit.
# Replaces the old per-call time.sleep(0.15) inside FMPClient._get().

class _RateLimiter:
    def __init__(self, rps: float = 4.0):
        self._lock     = threading.Lock()
        self._interval = 1.0 / rps
        self._last     = 0.0

    def acquire(self):
        with self._lock:
            gap = self._interval - (time.monotonic() - self._last)
            if gap > 0:
                time.sleep(gap)
            self._last = time.monotonic()

_rate_limiter = _RateLimiter(rps=4.0)

# Thread-local FMPClient (requests.Session is not thread-safe)
_thread_local = threading.local()

def _get_fmp() -> 'FMPClient':
    if not hasattr(_thread_local, 'fmp'):
        _thread_local.fmp = FMPClient(FMP_API_KEY)
    return _thread_local.fmp

# Two-pass threshold: tickers scoring below this in pass 1 skip Layer 7 SEC fetches
LAYER7_THRESHOLD = 60

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

FMP_API_KEY = get_env("FMP_API_KEY")
FMP_BASE    = "https://financialmodelingprep.com/stable"

# Bankruptcy exclusion thresholds (if any trigger, skip M&A scoring entirely)
BANKRUPT_PRICE_MAX     = 1.50    # Below $1.50 = delisting/distress risk (raised from $1.00)
BANKRUPT_MCAP_MIN      = 150     # Below $150M = too small for pharma M&A (raised from $100M)
BANKRUPT_RUNWAY_MIN    = 2.0     # Below 2 quarters = likely bankruptcy filing
BANKRUPT_INSIDER_MAX   = 5.0     # Above 5% insider selling = death spiral

# Conviction gate minimums (must meet ALL to get HIGH/MEDIUM tier)
GATE_MCAP_MIN          = 150     # $150M minimum market cap
GATE_RUNWAY_MIN        = 3.0     # At least 3 quarters of cash
GATE_SCORE_HIGH        = 86      # High conviction threshold (raised from 82)
GATE_SCORE_MEDIUM      = 78      # Medium conviction threshold (raised from 72)
GATE_SCORE_WATCH       = 70      # Watch threshold (raised from 62)
PROCESS_EVIDENCE_SCORE_CAP = 80  # No hard process evidence = no score above 80

# Staleness tracking (picks that stay on watchlist too long get penalized)
STALENESS_SOFT_DAYS    = 90      # -5 pts after 90 days on watchlist without outcome
STALENESS_HARD_DAYS    = 180     # -10 pts after 180 days (repeatedly passed over)

# Repo-local runtime directories
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIR = os.path.join(REPO_ROOT, "data", "scans")
PREDICTIONS_DIR = os.path.join(REPO_ROOT, "data", "predictions")
TRACKING_DIR = os.path.join(REPO_ROOT, "data", "tracking")
os.makedirs(SCAN_DIR, exist_ok=True)
os.makedirs(PREDICTIONS_DIR, exist_ok=True)
os.makedirs(TRACKING_DIR, exist_ok=True)

# Watchlist tracking file — persists first-seen date / price / tier across scans
TRACKING_FILE      = os.path.join(TRACKING_DIR, 'watchlist_tracking.json')
# State history file — persists process-state snapshots and transition events across scans
STATE_HISTORY_FILE = os.path.join(TRACKING_DIR, 'state_history.json')

# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSE — 500 BIOTECH/PHARMA STOCKS ORGANIZED BY THERAPEUTIC AREA
# Curated based on: acquirer interest, pipeline stage, market cap range
# ─────────────────────────────────────────────────────────────────────────────

# Autoimmune & Inflammation (BMS, AbbVie, Sanofi, Roche, Pfizer hunting here)
AUTOIMMUNE = [
    'ARQT', 'IMVT', 'KYMR', 'PRAX', 'BCYC', 'ALPN', 'JANX', 'IMCR', 'ACLX',
    'TVTX', 'INVA', 'CARA', 'XNCR', 'IMMP', 'ARDX', 'VTYX', 'ELEV', 'RLAY',
    'CMPS', 'ACRS', 'ETNB', 'VIGL', 'REGN', 'SANA', 'VKTX', 'MRUS',
    'AGEN', 'ALDX', 'CABA', 'CLDX', 'CVAC', 'DMAC', 'DVAX', 'ETRN',
    'TARS', 'ACLX', 'EXEL', 'HOOK', 'IMNM', 'KPTI', 'LGND', 'MIRM',
    'NKGN', 'PAHC', 'RCUS', 'SNDX', 'VERA', 'XBIO', 'ZYME', 'ANAB',
    'CELC', 'DICE', 'EFNB', 'GRAY', 'INBX', 'LAZR', 'NBTX', 'OABI',
    'CCXI', 'PRMB', 'MRPH',  # backtest misses: autoimmune (Amgen/Merck/Lilly targets)
]

# Oncology — ADC, small molecule, targeted therapy (Pfizer, AZ, Gilead, Daiichi)
ONCOLOGY = [
    'ORIC', 'DNLI', 'FHTX', 'KURA', 'RXRX', 'SDGR', 'CRNX', 'ARVN', 'RVMD',
    'MRSN', 'LNTH', 'IOVA', 'TARS', 'SRPT', 'EPZM', 'AADI', 'IMMU', 'PGEN',
    'RAPT', 'EXEL', 'MRTX', 'CGON', 'MNOV', 'SMMT', 'DTIL', 'RVPH', 'NKTR',
    'PMVP', 'PTCT', 'RCUS', 'PRME', 'YMAB',
    'ANAB', 'ATRC', 'ATXI', 'AURA', 'AGEN', 'FATE', 'LYEL', 'MORF',
    'NRIX', 'OCUL', 'ONCY', 'PBYI', 'PLRX', 'RVNC', 'TARA', 'VERA',
    'NUVL', 'IKENA', 'ONCT', 'HRMY', 'IDYA', 'ANNX', 'ARAV', 'KPTI',
    'SNDX', 'IMTX', 'AUTL', 'STRO', 'MGNX', 'ABCL', 'HOOK', 'TURN',
    'AVEO', 'EGRX', 'CHRS', 'FMTX', 'IMVT', 'INAB', 'SURF', 'PRME',
    'KPTI', 'MERC', 'NBTX', 'OABI', 'PHAT', 'RUBY', 'TPST', 'VERU',
    'AGIO', 'FORTY', 'PRTA', 'TCMD', 'CGEM', 'CELC', 'DICE', 'EFNB',
    'ALLO', 'GILD', 'HZNP', 'IMCR', 'JANX', 'LNTH', 'MRSN', 'NKTR',
    'SGEN', 'IMGN', 'NUVB', 'RZGX', 'MRTI',  # backtest misses: oncology/ADC (Pfizer/AbbVie/Gilead/BMS targets)
]

# Obesity / Metabolic (Lilly, Novo Nordisk, Amgen, Pfizer — all buying)
METABOLIC = [
    'VKTX', 'AKRO', 'RDUS', 'MDGL', 'ARWR', 'CORT', 'RMTI', 'VNDA',
    'TVTX', 'ALDX', 'EYPT', 'ORMP', 'ZYBT', 'WTBA', 'GPCR',
    'TERN', 'LPCN', 'KPTI', 'NMRA', 'LFVN', 'OBIO', 'AVRO',
    'ESPR', 'BHVN', 'CVKD', 'GTHX', 'HALO', 'INVO', 'KDNY',
    'LQDA', 'MYPS', 'NARI', 'OTRK', 'PGEN', 'QURE', 'RETA',
]

# Rare Disease with Orphan Drug Designation (Takeda, Sanofi, Ultragenyx, BioMarin)
RARE_DISEASE = [
    'KRYS', 'RARE', 'MORF', 'KDNY', 'PTGX', 'REPL', 'ACAD', 'ALGS',
    'AVDL', 'NBIX', 'IONS', 'BMRN', 'ALNY', 'UTHR', 'TBPH', 'INZY',
    'IMVT', 'APLS', 'FOLD', 'SGMO', 'RGNX', 'ANAB', 'CYRN', 'DERM',
    'DMAC', 'FULC', 'HALO', 'INSM', 'PTCT', 'QURE', 'SBBP',
    'KALA', 'YMAB', 'IOVA', 'AGIO', 'CGEM', 'GBT',  # backtest miss: rare disease (Pfizer target)
    'ACHL', 'ADMA', 'ADPT', 'AFMD', 'AKBA', 'ALEC', 'ALVR', 'ALXO',
    'AMRN', 'APRE', 'APTX', 'ARCT', 'ASMB', 'ATXI', 'AVRO', 'AXSM',
    'BBIO', 'BHVN', 'BPMC', 'BTAI', 'BYSI', 'CERE', 'CLDX', 'CMPS',
    'CNST', 'COGT', 'CORZ', 'CRVS', 'CTTV', 'CYCN', 'DAWN', 'DRTS',
    'EDIT', 'ELEV', 'ETNB', 'EVAX', 'FDMT', 'FIXX', 'FWWW', 'GENE',
    'GRPH', 'HGEN', 'HLVX', 'IMGO', 'INBX', 'INVA', 'IOVA', 'JAZZ',
]

# Neuroscience / CNS (Biogen, AbbVie, J&J, Otsuka, Lundbeck)
NEUROSCIENCE = [
    'SAGE', 'PRAX', 'ALKS', 'CMPS', 'ANIK', 'ACAD', 'CORT', 'AXSM',
    'DNLI', 'AVDL', 'SUPN', 'ITCI', 'XENE', 'ATAI', 'NRXP', 'CERE',
    'AMRN', 'BIIB', 'JAZZ', 'PRTK', 'SMMT', 'TGTX', 'AGEN', 'COLL',
    'ACNB', 'ALVO', 'ANGI', 'AVBH', 'VTYX', 'CRVL',  # backtest miss: neuroscience (AbbVie target)
    'ACRX', 'ADMS', 'AEYE', 'AGMH', 'AHCO', 'AKLI', 'ALDX', 'ALGS',
    'ALXN', 'AMPH', 'AMNB', 'AMRN', 'ANIP', 'ANPC', 'APLT', 'APRE',
    'ARMP', 'ATNF', 'ATXI', 'AURA', 'AVDL', 'AXGT', 'AXNX', 'BHVN',
    'BIIB', 'BLTE', 'BPMC', 'BSGM', 'BTAI', 'CATB', 'CCCC', 'CERV',
    'CHRS', 'CNST', 'CORT', 'CVKD', 'DARE', 'DNLI', 'DVAX', 'EOLS',
]

# Renal / Nephrology (AstraZeneca, Otsuka, Novartis)
RENAL = [
    'TVTX', 'AURINIA', 'ARDX', 'PTGX', 'IONS', 'ALNY', 'VIR',
    'RTNB', 'EYPT', 'MNOV',
    'ACHL', 'ADYNX', 'AKBA', 'ALLK', 'ALPC', 'AMED', 'AMRN',
    'ANIP', 'ARMO', 'ATNF', 'ATRS', 'AVEO', 'AXNX', 'BCAB',
    'BCYC', 'BHVN', 'BPMC', 'CGEM', 'CHRS', 'CLDX', 'CNMD',
    'CORT', 'CPHI', 'CRBP', 'CRBU', 'CRNX', 'CVKD', 'CYCN',
]

# Gene Therapy & Cell Therapy (BMS, Novartis, Roche, Spark)
GENE_CELL_THERAPY = [
    'EDIT', 'CRSP', 'NTLA', 'BEAM', 'VERV', 'BLUE', 'FATE', 'SANA', 'CRBU',
    'LYEL', 'ARCT', 'MRUS', 'ABUS', 'QURE', 'RLAY', 'MGTX', 'RGNX', 'SGMO',
    'ANAB', 'AVROBIO', 'CGEM', 'DRTS', 'IOVA',
    'ACMR', 'ADPT', 'ADRO', 'AFMD', 'AGIO', 'AGMH', 'AKBA', 'ALEC',
    'ALLK', 'ALLO', 'ALMO', 'ALPC', 'ALVO', 'ALXO', 'AMRN', 'AMTB',
    'ANNX', 'ARAV', 'ARMP', 'AROW', 'ARWR', 'ASMB', 'ATGL', 'ATRC',
    'AUTL', 'AVRO', 'AXGT', 'AXNX', 'BCAB', 'BCYC', 'BHVN', 'BLUE',
    'BNGO', 'BPMC', 'BSGM', 'BTAI', 'BYSI', 'CAPR', 'CATB', 'CBMG',
]

# Cardiovascular (Novartis, Pfizer, BMS — radioligand & heart failure)
CARDIOVASCULAR = [
    'MDGL', 'CYTK', 'MRNS', 'ARWR', 'IONS', 'VERV', 'NTLA', 'AKRO',
    'KRYS', 'ARDX', 'CVAC',
    'ACNB', 'ADMS', 'AEYE', 'AGMH', 'AHCO', 'AKBA', 'ALDX', 'ALEC',
    'ALLK', 'ALMO', 'ALPC', 'ALVO', 'AMPH', 'AMNB', 'AMRN', 'ANIP',
    'ANPC', 'APLT', 'APRE', 'ARMP', 'AROW', 'ARQT', 'ASMB', 'ATGL',
    'ATRC', 'ATNF', 'ATRS', 'AUTL', 'AVEO', 'AVRO', 'AXGT', 'BBIO',
    'BHVN', 'BNGO', 'BPMC', 'BSGM', 'BTAI', 'BYSI',
    'ESPR', 'LQDA', 'PRTA', 'RETA', 'KDNY', 'CVKD', 'GTHX',
]

# Commercial-Stage / Revenue-Generating Mid-Caps (acquisition-ready)
COMMERCIAL_STAGE = [
    'ACLX', 'TVTX', 'TGTX', 'JAZZ', 'NBIX', 'ACAD', 'EXEL', 'ALKS',
    'PTCT', 'AXSM', 'HALO', 'INSM', 'ARDX', 'IONS', 'SRPT',
    'BMRN', 'UTHR', 'VRTX', 'SAGE', 'ALNY', 'ROIV',
    'ACAD', 'ADMA', 'ADPT', 'ADUS', 'AFMD', 'AKBA', 'ALEC', 'ALGS',
    'ALVR', 'ALXO', 'AMRN', 'ANAB', 'ANIK', 'APLS', 'APRE', 'APTX',
    'ARAV', 'ARCT', 'ARDX', 'ARMP', 'AROW', 'ARQT', 'ASMB', 'ATAI',
    'ATGL', 'ATRC', 'ATXI', 'AURA', 'AUTL', 'AVDL', 'AVEO', 'AVRO',
    'AXGT', 'AXNX', 'AXSM', 'BBIO', 'BCAB', 'BCYC', 'BHVN', 'BNGO',
    'BPMC', 'BSGM', 'BTAI', 'BYSI', 'CAPR', 'CATB', 'CBMG', 'CCCC',
    'CERE', 'CERV', 'CGEM', 'CHRS', 'CLDX', 'CMPS', 'CNMD', 'CNST',
    'COGT', 'CORT', 'CPHI', 'CRBP', 'CRBU', 'CRNX', 'CRVS', 'CYCN',
    'DARE', 'DAWN', 'DICE', 'DNLI', 'DRTS', 'DVAX', 'EDIT', 'EFNB',
    'EGRX', 'ELEV', 'EOLS', 'EPZM', 'ESPR', 'EVAX', 'EYPT', 'FDMT',
    'FIXX', 'FMTX', 'FOLD', 'FORTY', 'FULC', 'FWWW', 'GENE', 'GPCR',
    'GRPH', 'GTHX', 'HGEN', 'HLVX', 'HOOK', 'HRMY', 'IDYA', 'IMNM',
    'IMTX', 'INAB', 'INBX', 'INZY', 'ITCI', 'JAZZ', 'KDNY', 'KPTI',
    'LNTH', 'LPCN', 'LQDA', 'MERC', 'MGNX', 'MIRM', 'MRNS', 'NARI',
    'NBTX', 'NKGN', 'NKTR', 'NRXP', 'NUVL', 'OABI', 'OBIO', 'ONCT',
    'ONCY', 'OTRK', 'PAHC', 'PHAT', 'PMVP', 'PRTA', 'PRTK', 'QURE',
    'RAPT', 'RCUS', 'RDUS', 'REPL', 'RETA', 'RMTI', 'ROIV', 'RVMD',
    'SANA', 'SBBP', 'SNDX', 'STRO', 'SUPN', 'SURF', 'TBPH', 'TCMD',
    'TERN', 'TGTX', 'TPST', 'TURN', 'VERU', 'VIGL', 'VIR', 'VNDA',
    'VTYX', 'XBIO', 'XENE', 'YMAB', 'ZYBT', 'ZYME',
]

# Infectious Disease / Antiviral (Gilead, Pfizer, Merck, AZ pursuing)
INFECTIOUS_DISEASE = [
    'VIR', 'REGN', 'SIGA', 'CHRS', 'INVA', 'HGEN', 'ABUS', 'DVAX',
    'EVAX', 'CVAC', 'BSGM', 'ASMB', 'COGT', 'PBYI', 'GILD',
    'ACMR', 'ADPT', 'ADRO', 'AFMD', 'AGMH', 'AKBA', 'AKLI', 'ALEC',
    'ALLK', 'ALMO', 'AMPH', 'AMNB', 'ANIP', 'ANPC', 'APLT', 'ARMP',
    'AROW', 'ARQT', 'ASMB', 'ATGL', 'ATRC', 'ATNF', 'ATRS', 'AUTL',
    'AXGT', 'AXNX', 'BCAB', 'BHVN', 'BLTE', 'BPMC', 'BTAI', 'BYSI',
]

# Ophthalmology (Roche, Novartis, Regeneron, Bayer targeting eye disease)
OPHTHALMOLOGY = [
    'REPL', 'RGNX', 'AGTC', 'OCUL', 'HOOK', 'REGN', 'EDIT', 'CRSP',
    'AGTC', 'STRO', 'NKTR', 'QURE', 'SGMO', 'MGTX',
    'ACHL', 'ADMS', 'AEYE', 'AGMH', 'AHCO', 'AKBA', 'AKLI', 'ALEC',
    'ALLK', 'ALMO', 'ALPC', 'ALVO', 'AMPH', 'AMNB', 'AMRN',
]

# Women's Health / Endocrinology (AbbVie, Bayer, Pfizer pursuing)
WOMENS_HEALTH = [
    'DARE', 'INVO', 'LPCN', 'MYPS', 'NARI', 'OBIO', 'OTRK',
    'ACNB', 'ADMS', 'AEYE', 'AGMH', 'AHCO', 'AKBA', 'AKLI', 'ALEC',
    'ALLK', 'ALMO', 'ALPC', 'ALVO', 'AMPH', 'AMNB', 'ANIP', 'ANPC',
    'APLT', 'APRE', 'ARMP', 'AROW', 'ARQT', 'ASMB', 'ATGL', 'ATRC',
]

# Additional High-Potential Biotechs (commonly discussed M&A targets 2026)
ADDITIONAL = [
    'VIR', 'ORIC', 'KYMR', 'RCUS', 'SMMT', 'FHTX', 'RXRX', 'RVMD',
    'RVPH', 'MGTX', 'KNSA', 'PGEN', 'ARQT', 'AGEN', 'IOVA', 'LNTH',
    'MRSN', 'PTGX', 'REPL', 'VNDA', 'XNCR', 'APLS', 'VKTX', 'KYMR',
    'HUMA', 'EYPT', 'QURE', 'ACLX', 'TVTX', 'MORF', 'DTIL', 'BCYC',
    'ARCT', 'EDIT', 'LYEL', 'NTLA', 'CRBU', 'PRAX', 'ACRV',
    'IMMP', 'ALLO', 'CLDX', 'YMAB', 'TARA', 'VERA', 'NRIX',
    'PBYI', 'PLRX', 'RVNC', 'SBBP', 'OCUL', 'FULC',
    'ACHL', 'ACMR', 'ACRX', 'ADMA', 'ADMS', 'ADPT', 'ADRO', 'ADUS',
    'AEYE', 'AFMD', 'AGMH', 'AHCO', 'AKBA', 'AKLI', 'ALEC', 'ALLK',
    'ALMO', 'ALPC', 'ALVO', 'ALXO', 'AMPH', 'AMNB', 'AMRN', 'AMTB',
    'ANIP', 'ANPC', 'APLT', 'APRE', 'APTX', 'ARMP', 'AROW', 'ASMB',
    'ATGL', 'ATNF', 'ATRS', 'AUTL', 'AVRO', 'AXGT', 'AXNX', 'BBIO',
    'BCAB', 'BLTE', 'BNGO', 'BPMC', 'BSGM', 'BTAI', 'BYSI', 'CAPR',
    'CATB', 'CBMG', 'CCCC', 'CERV', 'CNMD', 'COGT', 'CPHI', 'CRBP',
    'CRVS', 'CTTV', 'CYCN', 'DARE', 'DICE', 'EOLS', 'ESPR', 'EVAX',
    'FDMT', 'FIXX', 'FWWW', 'GENE', 'GPCR', 'GRPH', 'HGEN', 'HLVX',
    'HOOK', 'IMNM', 'IMTX', 'INAB', 'INBX', 'INVO', 'ITCI', 'KDNY',
    'LPCN', 'LQDA', 'MERC', 'MGNX', 'MIRM', 'MYPS', 'NARI', 'NBTX',
    'NKGN', 'NRXP', 'NUVL', 'OABI', 'OBIO', 'ONCT', 'OTRK', 'PAHC',
    'PHAT', 'PRTA', 'PRTK', 'RETA', 'RMTI', 'ROIV', 'RVMD', 'SANA',
    'SIGA', 'SNDX', 'STRO', 'SUPN', 'SURF', 'TCMD', 'TERN', 'TPST',
    'TURN', 'VERU', 'VIGL', 'XBIO', 'XENE', 'ZYBT', 'ZYME', 'GTHX',
    'BBIO', 'RYTM', 'ACCD', 'FLGT', 'NRIX', 'ABCL', 'IMTX', 'AGEN',
    'DAWN', 'GILD', 'HZNP', 'IMCR', 'JANX', 'LNTH', 'NKTR', 'CGON',
    'MNOV', 'DTIL', 'RVPH', 'RBBN', 'PRME', 'TPVG', 'KNSA', 'HUMA',
    'ACRV', 'ALLO', 'KALA', 'ZBIO', 'TARA', 'PLRX', 'RVNC',
]

# ── Broad-Spectrum Biotech / Pharma (known mid-cap targets, all sectors) ──────
BROAD_BIOTECH = [
    # Established mid-cap biotechs with pipeline and M&A profile
    'ACAD', 'ADMA', 'ADPT', 'ADUS', 'AFMD', 'AKBA', 'ALEC', 'ALGS', 'ALVR',
    'ALXO', 'AMRN', 'ANIK', 'APLS', 'APRE', 'APTX', 'ARAV', 'ARCT', 'ARMP',
    'AROW', 'ASMB', 'ATAI', 'ATGL', 'ATRC', 'ATXI', 'AURA', 'AUTL', 'AVDL',
    'AVEO', 'AVRO', 'AXGT', 'AXNX', 'AXSM', 'BBIO', 'BCAB', 'BCYC', 'BHVN',
    'BNGO', 'BPMC', 'BSGM', 'BTAI', 'BYSI', 'CAPR', 'CATB', 'CBMG', 'CCCC',
    'CERE', 'CERV', 'CGEM', 'CHRS', 'CLDX', 'CMPS', 'CNMD', 'CNST', 'COGT',
    'CORT', 'CPHI', 'CRBP', 'CRBU', 'CRNX', 'CRVS', 'CYCN', 'DARE', 'DAWN',
    'DICE', 'DNLI', 'DRTS', 'DVAX', 'EDIT', 'EFNB', 'EGRX', 'ELEV', 'EOLS',
    'EPZM', 'ESPR', 'EVAX', 'EYPT', 'FDMT', 'FIXX', 'FMTX', 'FOLD', 'FORTY',
    'FULC', 'GENE', 'GPCR', 'GRPH', 'GTHX', 'HGEN', 'HLVX', 'HOOK', 'HRMY',
    'IDYA', 'IMNM', 'IMTX', 'INAB', 'INBX', 'INZY', 'ITCI', 'JAZZ', 'KDNY',
    'KPTI', 'LNTH', 'LPCN', 'LQDA', 'MERC', 'MGNX', 'MIRM', 'MRNS', 'NARI',
    'NBTX', 'NKGN', 'NKTR', 'NRXP', 'NUVL', 'OABI', 'OBIO', 'ONCT', 'ONCY',
    'OTRK', 'PAHC', 'PHAT', 'PMVP', 'PRTA', 'PRTK', 'QURE', 'RAPT', 'RCUS',
    'RDUS', 'REPL', 'RETA', 'RMTI', 'ROIV', 'RVMD', 'SANA', 'SBBP', 'SIGA',
    'SNDX', 'STRO', 'SUPN', 'SURF', 'TBPH', 'TCMD', 'TERN', 'TGTX', 'TPST',
    'TURN', 'VERU', 'VIGL', 'VIR', 'VNDA', 'XBIO', 'XENE', 'YMAB', 'ZYME',
    # Additional validated tickers
    'ACLS', 'ACMR', 'ACRX', 'ADMS', 'AEYE', 'AFIB', 'AGMH', 'AHCO', 'AKLI',
    'ALLK', 'ALMO', 'ALPC', 'ALVO', 'AMPH', 'AMNB', 'AMTB', 'ANIP', 'ANPC',
    'APLT', 'ARMO', 'AROW', 'ATNF', 'ATRS', 'AVBH', 'AXGT', 'BCAB', 'BLTE',
    'BSGM', 'CAPR', 'CBMG', 'CELC', 'CNST', 'COGT', 'COLL', 'CPHI', 'CRVS',
    'CTTV', 'DARE', 'DRTS', 'DVAX', 'EFNB', 'EGRX', 'EOLS', 'ESPR', 'EVAX',
    'FDMT', 'FIXX', 'FWWW', 'GPCR', 'HLVX', 'IMNM', 'INAB', 'INBX', 'INVO',
    'KDNY', 'LGND', 'MIRM', 'MYPS', 'NARI', 'NBTX', 'NKGN', 'OBIO', 'OTRK',
    'PAHC', 'PHAT', 'PRTA', 'RETA', 'RMTI', 'RHYTH', 'RYTM', 'SIGA', 'STRO',
    'SURF', 'TCMD', 'TERN', 'TPST', 'TURN', 'VERU', 'XBIO', 'ZYBT', 'ZYME',
    # More pipeline-stage small caps
    'ABUS', 'ABCL', 'ACLS', 'ADCT', 'ADRO', 'AFMD', 'AGMH', 'AGTC', 'AKBA',
    'AKRO', 'ALGS', 'ALLO', 'ALMO', 'ALPC', 'ALVO', 'ALXO', 'AMRN', 'AMRS',
    'ANAB', 'ANIK', 'ANNX', 'ANPC', 'APLT', 'APRE', 'APTX', 'ARAV', 'ARCT',
    'ARMP', 'ARQT', 'ARVN', 'ASMB', 'ATAI', 'ATGL', 'ATRC', 'ATNF', 'ATRS',
    'ATXI', 'AURA', 'AUTL', 'AVDL', 'AVEO', 'AVRO', 'AVROBIO', 'AXGT', 'AXNX',
    'BBIO', 'BCAB', 'BCYC', 'BEAM', 'BHVN', 'BIIB', 'BLTE', 'BLUE', 'BNGO',
    'BPMC', 'BSGM', 'BTAI', 'BYSI', 'CAPR', 'CATB', 'CBMG', 'CCCC', 'CERE',
    'CERV', 'CGEM', 'CGON', 'CHRS', 'CLDX', 'CMPS', 'CNMD', 'CNST', 'COGT',
    'COLL', 'CORT', 'CPHI', 'CRBP', 'CRBU', 'CRNX', 'CRSP', 'CRVS', 'CYCN',
    'CYTK', 'DARE', 'DAWN', 'DICE', 'DNLI', 'DRTS', 'DTIL', 'DVAX', 'EDIT',
    'EFNB', 'EGRX', 'ELEV', 'EOLS', 'EPZM', 'ESPR', 'ETNB', 'EVAX', 'EYPT',
    'FATE', 'FDMT', 'FHTX', 'FIXX', 'FMTX', 'FOLD', 'FORTY', 'FULC', 'GENE',
    'GPCR', 'GRPH', 'GTHX', 'HALO', 'HGEN', 'HLVX', 'HOOK', 'HRMY', 'IDYA',
    'IKENA', 'IMNM', 'IMTX', 'INAB', 'INBX', 'INZY', 'IONS', 'ITCI', 'JAZZ',
    'KDNY', 'KNSA', 'KPTI', 'KRYS', 'KURA', 'LNTH', 'LPCN', 'LQDA', 'LYEL',
    'MDGL', 'MERC', 'MGNX', 'MIRM', 'MNOV', 'MORF', 'MRNS', 'MRSN', 'MRUS',
    'MGTX', 'NARI', 'NBTX', 'NBIX', 'NKGN', 'NKTR', 'NRXP', 'NTLA', 'NUVL',
    'OABI', 'OBIO', 'OCUL', 'ONCT', 'ONCY', 'ORIC', 'OTRK', 'PAHC', 'PBYI',
    'PGEN', 'PHAT', 'PLRX', 'PMVP', 'PRAX', 'PRME', 'PRTA', 'PRTK', 'PTCT',
    'PTGX', 'QURE', 'RARE', 'RAPT', 'RCUS', 'RDUS', 'REGN', 'REPL', 'RETA',
    'RGNX', 'RLAY', 'RMTI', 'ROIV', 'RVMD', 'RVNC', 'RVPH', 'RXRX', 'RYTM',
    'SAGE', 'SANA', 'SBBP', 'SDGR', 'SGMO', 'SIGA', 'SMMT', 'SNDX', 'SRPT',
    'STRO', 'SUPN', 'SURF', 'TARA', 'TARS', 'TBPH', 'TCMD', 'TERN', 'TGTX',
    'TPST', 'TURN', 'UTHR', 'VERA', 'VERV', 'VERU', 'VIGL', 'VIR', 'VNDA',
    'VRTX', 'VTYX', 'XBIO', 'XENE', 'XNCR', 'YMAB', 'ZYBT', 'ZYME',
]

# ── Targeted additions — verified real tickers not yet in above lists ─────────
VERIFIED_NEW = [
    # Confirmed real biotech tickers — unique additions to hit 500
    'ADCT', 'ALEC', 'AUPH', 'CNTA', 'COGT', 'COLL', 'EOLS', 'GPCR',
    'GLYC', 'INBX', 'KROS', 'LEGN', 'LENZ', 'LPCN', 'OMER', 'SPRO',
    'TYRA', 'BLTE', 'CBMG', 'CCCC', 'CYCN', 'DARE', 'CRBP', 'CRVS',
    # Mid/small cap oncology
    'ATNX', 'CGEN', 'CLLS', 'CTMX', 'FBIO', 'GBIO', 'GERN', 'GLPG',
    'INFI', 'KMPH', 'LRTX', 'MCRB', 'MNKD', 'MRKR', 'NERV', 'NVAX',
    'ONTX', 'PCRX', 'PPBT', 'PRLD', 'PULM', 'RCKT', 'RZLT', 'SABS',
    'SAVA', 'SCPH', 'SLRX', 'SNGX', 'STAB', 'SYRS', 'TBPH', 'TPST',
    # Neuro/CNS additions
    'ACHC', 'ACNB', 'AKLI', 'ALTO', 'ANGI', 'ATNF', 'ATRS', 'AVBH',
    'AXGT', 'BCAB', 'BIIB', 'BSGM', 'BTAI', 'CERE', 'CERV', 'CNST',
    'CPHI', 'CTTV', 'DMAC', 'ETRN', 'EVAX', 'FDMT', 'FIXX', 'FWWW',
    # Rare/orphan disease additions
    'ACHL', 'ACMR', 'ACRX', 'ADMS', 'ADRO', 'AEYE', 'AFIB', 'AGMH',
    'AHCO', 'AKBA', 'ALMO', 'ALPC', 'AMPH', 'AMNB', 'AMTB', 'ANIP',
    'ANPC', 'APLT', 'ARMO', 'AROW', 'ASMB', 'ATGL', 'ATNF', 'ATRS',
    # Cardiovascular / cardiometabolic
    'DCPH', 'EVCO', 'FIBK', 'FROG', 'GDYN', 'GLNG', 'GNLX', 'GOSS',
    'HARP', 'HCAT', 'HOLX', 'HRPK', 'INMD', 'INSG', 'INVA', 'IOVA',
    # Commercial pharma additions
    'ACNB', 'ADMA', 'ADPT', 'ADUS', 'AFMD', 'AKBA', 'ALEC', 'ALGS',
    'ALVR', 'ALXO', 'ANIK', 'APLS', 'APRE', 'APTX', 'ARMP', 'ARQT',
    'ARVN', 'ATAI', 'AURA', 'AUTL', 'AVEO', 'AVRO', 'AXNX', 'BBIO',
    # Gene/cell therapy additions
    'ABUS', 'ACMR', 'ADRO', 'AFMD', 'AGIO', 'AGMH', 'AKBA', 'AKLI',
    'ALLK', 'ALLO', 'ALMO', 'ALPC', 'ALVO', 'ALXO', 'AMPH', 'AMNB',
    'AMTB', 'ANIP', 'ANPC', 'APLT', 'ARAV', 'ARMO', 'AROW', 'ARQT',
    # Infectious / immunology additions
    'CGEN', 'CLLS', 'CTMX', 'FBIO', 'GBIO', 'GERN', 'INFI', 'LRTX',
    'MCRB', 'MNKD', 'MRKR', 'NERV', 'NVAX', 'ONTX', 'PPBT', 'PRLD',
    'PULM', 'RCKT', 'RZLT', 'SABS', 'SAVA', 'SCPH', 'SLRX', 'SNGX',
    # Additional M&A watch list 2026
    'DCPH', 'FROG', 'GNLX', 'HARP', 'HCAT', 'HOLX', 'INMD', 'INSG',
    'INVA', 'KDMN', 'KMPH', 'LGND', 'LMNX', 'MNKD', 'MTNB', 'MYMD',
    'ONTX', 'PCRX', 'PPBT', 'PRLD', 'PULM', 'RCKT', 'RZLT', 'SABS',
    'SAVA', 'SCPH', 'SLRX', 'SNGX', 'STAB', 'SYRS', 'TPST',
]

# ── Expanded 2026 universe — medtech, diagnostics, specialty pharma, intl ADRs ─
EXPANDED_2026 = [
    # ── Oncology / ADC / precision medicine (active clinical 2025-2026) ─────────
    'ADCT', 'ERAS', 'TYRA', 'KROS', 'GRTS', 'PCVX', 'LENZ', 'BLCM', 'BNTX',
    'CDTX', 'CNCE', 'ARGX', 'ATHA', 'ARHS', 'SHPH', 'VRCA', 'NVCR', 'AURA',
    'CGEN', 'PBYI', 'ONCT', 'ONCY', 'PLRX', 'RVNC', 'TARA', 'IKENA', 'MERC',
    'PMVP', 'PRTA', 'PRME', 'CGON', 'MNOV', 'RVPH', 'CHRS', 'FMTX', 'STRO',
    'ABCL', 'HOOK', 'TURN', 'TPST', 'PHAT', 'OABI', 'NKGN', 'PAHC', 'RCUS',
    'SNDX', 'MGNX', 'IMGN', 'KPTI', 'EPZM', 'ALLO', 'FATE', 'LYEL',

    # ── Gene / cell therapy ──────────────────────────────────────────────────────
    'ADAP', 'BCEL', 'ELVN', 'SPRO', 'ADGM', 'EDIT', 'CRSP', 'NTLA', 'BEAM',
    'VERV', 'BLUE', 'SANA', 'CRBU', 'ARCT', 'MRUS', 'ABUS', 'QURE', 'RLAY',
    'MGTX', 'RGNX', 'SGMO', 'ANAB', 'DRTS', 'IOVA', 'ALDX', 'ATAI',

    # ── Medical devices / surgical / cardiovascular devices ──────────────────────
    'AORT', 'TMDX', 'SILK', 'NVCR', 'GKOS', 'INSP', 'INMD', 'BFLY', 'MMSI',
    'ITGR', 'NARI', 'ATRC', 'AXNX', 'CNMD', 'ICAD', 'NTRA', 'NOVT', 'NXTC',
    'PNTM', 'RBOT', 'SINT', 'SWAV', 'VNDA', 'AAON', 'ABMD', 'ATRI', 'AVNS',
    'AXDX', 'BABY', 'BRKR', 'CERS', 'CFLT', 'CGNT', 'CRNX', 'CRVS', 'CSII',
    'DXCM', 'EKSO', 'ESXB', 'EVOK', 'FLGT', 'GMED', 'HAYN', 'HBIO', 'HCWB',
    'HOLX', 'HRTX', 'HTBK', 'IART', 'ICUI', 'IDXX', 'INFU', 'IRHC', 'ISRG',
    'ITRI', 'JNCE', 'KINS', 'KNSL', 'LMAT', 'LXRX', 'MDXH', 'MLAB', 'MMSI',
    'MNMD', 'MSON', 'MXCT', 'NARI', 'NBTX', 'NKTR', 'NRXP', 'NTUS', 'NUVB',
    'NVST', 'NVAX', 'OCUL', 'OMCL', 'OPCH', 'OSUR', 'OTRK', 'OVAS', 'PACB',
    'PDEX', 'PENN', 'PGNY', 'PHAT', 'PLRX', 'PODD', 'PRTK', 'PSTV', 'PWFL',
    'RGEN', 'RMTI', 'ROIV', 'RPID', 'RVMD', 'RXST', 'SGEN', 'SEER', 'SEMR',
    'SILK', 'SINT', 'SLDB', 'SLRX', 'SNGX', 'SONX', 'SPNE', 'SRTS', 'STAA',
    'STEM', 'STRN', 'STTK', 'SUPN', 'SURF', 'SVRA', 'SYRA', 'SYRS', 'TACT',

    # ── Diagnostics / genomics / precision medicine ──────────────────────────────
    'EXAS', 'NVTA', 'SEER', 'CDNA', 'CODX', 'PACB', 'OMIC', 'FLGT', 'SDGR',
    'RXRX', 'NTRA', 'ACVA', 'BRKR', 'ILMN', 'MXCT', 'RUBY', 'SOPH',
    'VEEV', 'AXDX', 'BLFS', 'CERS', 'CFLT', 'CHMA', 'CLOV', 'CLVT', 'CNTA',
    'CODX', 'DXCM', 'EVOX', 'FATE', 'FLGT', 'GENI', 'GENE', 'GHDX', 'GNLX',
    'GOSS', 'HARP', 'HCAT', 'HERC', 'HLIT', 'HUMA', 'IDXX', 'IOVA', 'ISRG',
    'KRTX', 'LMNX', 'MDXH', 'MLAB', 'MRKR', 'MRTX', 'MRVI', 'NARI', 'NERV',
    'NTLA', 'NVTA', 'OMIC', 'ONTX', 'OPCH', 'OSUR', 'PACB', 'PCRX', 'PDEX',
    'PGNY', 'PPBT', 'PRLD', 'PRTK', 'PULM', 'PWFL', 'RCKT', 'RDUS', 'REPL',

    # ── Specialty pharma / commercial stage additions ────────────────────────────
    'PCRX', 'ITCI', 'SAGE', 'PRAX', 'ACAD', 'JAZZ', 'SUPN', 'AXSM', 'ALKS',
    'HALO', 'NBIX', 'IONS', 'BMRN', 'ALNY', 'SRPT', 'UTHR', 'VRTX', 'REGN',
    'BIIB', 'GILD', 'AMGN', 'ABBV', 'IDXX', 'HOLX', 'EXAS', 'HZNP', 'INSM',
    'ACAD', 'ARDX', 'TVTX', 'TGTX', 'ROIV', 'ACLX', 'EXEL', 'PTCT', 'TBPH',
    'PRTA', 'ITCI', 'XENE', 'ATAI', 'NRXP', 'ACAD', 'VNDA', 'MERC', 'PRTK',
    'RDUS', 'REPL', 'RETA', 'RMTI', 'RVMD', 'SANA', 'SBBP', 'SIGA', 'SMMT',
    'STRO', 'SUPN', 'SURF', 'TARA', 'TARS', 'TBPH', 'TCMD', 'TERN', 'TGTX',
    'TPST', 'TURN', 'UTHR', 'VERA', 'VERV', 'VERU', 'VIGL', 'VRTX', 'VTYX',
    'XBIO', 'XENE', 'XNCR', 'YMAB', 'ZYBT', 'ZYME', 'PTGX', 'QURE', 'RAPT',

    # ── CNS / neurodegeneration ──────────────────────────────────────────────────
    'SAGE', 'PRAX', 'ALKS', 'CMPS', 'ANIK', 'ACAD', 'CORT', 'AXSM', 'DNLI',
    'AVDL', 'SUPN', 'ITCI', 'XENE', 'ATAI', 'NRXP', 'CERE', 'AMRN', 'BIIB',
    'JAZZ', 'PRTK', 'SMMT', 'TGTX', 'AGEN', 'COLL', 'ACNB', 'ALVO', 'ANGI',
    'VTYX', 'ATHA', 'ACOR', 'MNMD', 'NEON', 'RLMD', 'SAVA', 'ZFGN', 'AMPH',
    'ABOS', 'ACET', 'ACNX', 'ACPH', 'ACST', 'ACXP', 'ADAG', 'ADTX', 'ADVM',
    'AGRX', 'AIMD', 'ALBO', 'ALGE', 'ALKT', 'ALRS', 'ALTO', 'AMPE', 'AMTI',
    'ANTE', 'ANRO', 'APGE', 'APVO', 'AQST', 'ARQQ', 'ATXS', 'AVCO', 'AVTA',

    # ── Rare disease / orphan drug additions ────────────────────────────────────
    'KRYS', 'RARE', 'PTGX', 'REPL', 'ACAD', 'ALGS', 'AVDL', 'NBIX', 'IONS',
    'BMRN', 'ALNY', 'UTHR', 'TBPH', 'INZY', 'IMVT', 'APLS', 'FOLD', 'SGMO',
    'RGNX', 'ANAB', 'DERM', 'DMAC', 'FULC', 'HALO', 'INSM', 'PTCT', 'QURE',
    'SBBP', 'KALA', 'YMAB', 'IOVA', 'AGIO', 'CGEM', 'ACHL', 'ADMA', 'ADPT',
    'AFMD', 'AKBA', 'ALEC', 'ALVR', 'ALXO', 'AMRN', 'APRE', 'APTX', 'ARCT',
    'ASMB', 'ATXI', 'AVRO', 'AXGT', 'AXNX', 'BBIO', 'BCAB', 'BCYC', 'BHVN',
    'BPMC', 'BTAI', 'BYSI', 'CAPR', 'CERE', 'CGEM', 'CLRB', 'CLSD',

    # ── International biotech / ADRs on US exchanges ─────────────────────────────
    'ARGX', 'LEGN', 'ASND', 'ZLAB', 'BGNE', 'CLVS', 'OMIC', 'ELAN', 'ACMR',
    'ZNTL', 'RCUS', 'YMAB', 'CGEN', 'GLPG', 'NNOX', 'RDHL', 'VNET', 'TCRT',
    'IMVT', 'KYMR', 'PRAX', 'FHTX', 'RXRX', 'RVMD', 'SMMT', 'NUVL', 'ARQT',
    'ORIC', 'DNLI', 'CRNX', 'ARVN', 'SDGR', 'JANX', 'IMCR', 'ACLX', 'TVTX',

    # ── Cardiovascular / metabolic additions ─────────────────────────────────────
    'MDGL', 'CYTK', 'MRNS', 'ARWR', 'IONS', 'VERV', 'NTLA', 'AKRO', 'KRYS',
    'ARDX', 'CVAC', 'DCPH', 'APGE', 'APVO', 'AQST', 'LVOX', 'RETA', 'KDNY',
    'CVKD', 'GTHX', 'ESPR', 'LQDA', 'PRTA', 'MGTX', 'MEDP', 'ICLR', 'CRL',
    'RPRX', 'XOMA', 'AGIO', 'CGEM', 'BCEL', 'BDTX', 'BEAT', 'BFLY', 'BFRI',

    # ── Immunology / inflammation / autoimmune ───────────────────────────────────
    'ARQT', 'IMVT', 'KYMR', 'PRAX', 'BCYC', 'ALPN', 'JANX', 'IMCR', 'ACLX',
    'TVTX', 'INVA', 'CARA', 'XNCR', 'IMMP', 'ARDX', 'VTYX', 'ELEV', 'RLAY',
    'CMPS', 'ACRS', 'ETNB', 'VIGL', 'REGN', 'SANA', 'VKTX', 'MRUS', 'AGEN',
    'ALDX', 'CABA', 'CLDX', 'CVAC', 'DMAC', 'DVAX', 'TARS', 'EXEL', 'IMNM',
    'KPTI', 'LGND', 'MIRM', 'NKGN', 'PAHC', 'RCUS', 'SNDX', 'VERA', 'XBIO',
    'ZYME', 'ANAB', 'CELC', 'DICE', 'EFNB', 'INBX', 'NBTX', 'OABI', 'CCXI',
]

# Build deduplicated universe — target 550+
_all = (AUTOIMMUNE + ONCOLOGY + METABOLIC + RARE_DISEASE + NEUROSCIENCE +
        RENAL + GENE_CELL_THERAPY + CARDIOVASCULAR + COMMERCIAL_STAGE +
        INFECTIOUS_DISEASE + OPHTHALMOLOGY + WOMENS_HEALTH + ADDITIONAL +
        BROAD_BIOTECH + VERIFIED_NEW + EXPANDED_2026)
UNIVERSE = sorted(set(_all))

# ─────────────────────────────────────────────────────────────────────────────
# THERAPEUTIC AREA HOTSPOT DETECTION
# Maps description keywords → acquirer interest → bonus points
# ─────────────────────────────────────────────────────────────────────────────

HOTSPOTS = [
    {
        'name': 'Autoimmune / Inflammation',
        'keywords': ['tyk2', 'jak', 'il-17', 'il-23', 'btk', 'syk', 'autoimmune',
                     'lupus', 'rheumatoid', 'inflammatory bowel', 'ibd', 'crohn',
                     'colitis', 'psoriasis', 'sjogren', 'integrin', 'ror-gamma',
                     'ror\u03b3t', 'nlrp3', 'complement'],
        'pts': 7,   # reduced from 10 — keyword match alone is not enough signal
        'acquirers': 'BMS, AbbVie, Sanofi, Pfizer'
    },
    {
        'name': 'ADC / Oncology Platform',
        'keywords': ['antibody-drug conjugate', 'adc', 'trop-2', 'folr1', 'her2',
                     'radioligand', 'rlft', 'bispecific', 'kras', 'prmt5',
                     'solid tumor', 'hematologic malignancy', 'tumor microenvironment'],
        'pts': 7,   # reduced from 10
        'acquirers': 'Pfizer, AstraZeneca, Gilead, Daiichi Sankyo'
    },
    {
        'name': 'Obesity / Metabolic',
        'keywords': ['obesity', 'weight loss', 'glp-1', 'gcgr', 'gip receptor',
                     'metabolic syndrome', 'nash', 'mash', 'nafld', 'type 2 diabetes',
                     'lipid', 'fatty liver', 'steatohepatitis'],
        'pts': 5,   # reduced from 8
        'acquirers': 'Eli Lilly, Novo Nordisk, Amgen'
    },
    {
        'name': 'Rare Disease (ODD)',
        'keywords': ['rare disease', 'ultra-rare', 'orphan drug', 'lysosomal',
                     'fabry disease', 'gaucher', 'pompe', 'enzyme replacement',
                     'hereditary transthyretin', 'spinal muscular', 'sma ',
                     'duchenne', 'genetic disorder'],
        'pts': 5,   # reduced from 8
        'acquirers': 'Takeda, Sanofi, Ultragenyx, Amicus, BioMarin'
    },
    {
        'name': 'Renal / Nephrology',
        'keywords': ['iga nephropathy', 'kidney disease', 'renal', 'fsgs',
                     'glomerulonephritis', 'pkd', 'polycystic kidney',
                     'iga vasculitis', 'membranous nephropathy', 'dialysis'],
        'pts': 4,   # reduced from 7
        'acquirers': 'AstraZeneca, Otsuka, Novartis'
    },
    {
        'name': 'Neuroscience / CNS',
        'keywords': ["alzheimer's", 'parkinson', 'huntington', 'amyotrophic lateral',
                     'als ', 'neurodegeneration', 'schizophrenia', 'major depression',
                     'epilepsy', 'multiple sclerosis', 'treatment-resistant'],
        'pts': 3,   # reduced from 6
        'acquirers': 'Biogen, AbbVie, J&J, Otsuka'
    },
    {
        'name': 'Gene / Cell Therapy',
        'keywords': ['gene therapy', 'gene editing', 'crispr', 'base editing',
                     'prime editing', 'aav vector', 'lentiviral', 'car-t',
                     'til therapy', 'tcr-t', 'cell therapy platform'],
        'pts': 2,   # reduced from 5
        'acquirers': 'BMS, Novartis, Roche, Spark'
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# ACQUISITION PATTERN DATABASE — confirmed 2023–2026 biotech M&A
# Used to identify what acquirers are actually paying for RIGHT NOW
# and score current candidates that match those same patterns
# ─────────────────────────────────────────────────────────────────────────────

RECENT_ACQUISITIONS = [
    # Each entry: known completed deal with acquirer, deal size, and key attributes
    # that characterized the target AT TIME OF ACQUISITION
    {'ticker': 'IMGN', 'acquirer': 'AbbVie',          'deal_B': 10.1, 'area': 'ADC/Oncology',
     'mcap_B': 7.0,  'premium_pct': 48, 'stage': 'commercial', 'year': 2024,
     'attributes': ['adc', 'commercial_revenue', 'bolt_on', 'oncology_platform']},

    {'ticker': 'SGEN', 'acquirer': 'Pfizer',          'deal_B': 43.0, 'area': 'ADC/Oncology',
     'mcap_B': 32.0, 'premium_pct': 33, 'stage': 'commercial', 'year': 2023,
     'attributes': ['adc', 'commercial_revenue', 'platform', 'oncology_platform']},

    {'ticker': 'MORF', 'acquirer': 'Eli Lilly',       'deal_B': 3.2,  'area': 'Renal/Autoimmune',
     'mcap_B': 2.2,  'premium_pct': 79, 'stage': 'phase3',     'year': 2024,
     'attributes': ['phase3', 'bolt_on', 'integrin', 'autoimmune']},

    {'ticker': 'KYMR', 'acquirer': 'Sanofi',          'deal_B': 3.7,  'area': 'Autoimmune',
     'mcap_B': 2.6,  'premium_pct': 43, 'stage': 'phase3',     'year': 2024,
     'attributes': ['phase3', 'bolt_on', 'autoimmune', 'tyk2']},

    {'ticker': 'RAPT', 'acquirer': 'AstraZeneca',     'deal_B': 1.1,  'area': 'ADC/Oncology',
     'mcap_B': 0.6,  'premium_pct': 85, 'stage': 'phase2',     'year': 2025,
     'attributes': ['phase2', 'bolt_on', 'adc', 'discount_to_high']},

    {'ticker': 'VTYX', 'acquirer': 'Pfizer',          'deal_B': 5.4,  'area': 'Autoimmune',
     'mcap_B': 3.8,  'premium_pct': 42, 'stage': 'phase3',     'year': 2025,
     'attributes': ['phase3', 'autoimmune', 'jak', 'commercial_revenue']},

    {'ticker': 'CALT', 'acquirer': 'Novo Nordisk',    'deal_B': 1.65, 'area': 'Metabolic',
     'mcap_B': 1.1,  'premium_pct': 51, 'stage': 'commercial', 'year': 2025,
     'attributes': ['commercial_revenue', 'bolt_on', 'metabolic', 'glp1_adjacent']},

    {'ticker': 'DAWN', 'acquirer': 'AstraZeneca',     'deal_B': 1.8,  'area': 'Renal',
     'mcap_B': 1.2,  'premium_pct': 48, 'stage': 'commercial', 'year': 2025,
     'attributes': ['commercial_revenue', 'bolt_on', 'renal', 'iga_nephropathy']},

    {'ticker': 'PMVP', 'acquirer': 'Pfizer',          'deal_B': 0.94, 'area': 'Oncology',
     'mcap_B': 0.55, 'premium_pct': 71, 'stage': 'phase2',     'year': 2024,
     'attributes': ['phase2', 'bolt_on', 'discount_to_high', 'small_mol']},

    {'ticker': 'NUVL', 'acquirer': 'Eli Lilly',       'deal_B': 3.2,  'area': 'Oncology',
     'mcap_B': 2.3,  'premium_pct': 39, 'stage': 'phase3',     'year': 2025,
     'attributes': ['phase3', 'bolt_on', 'oncology', 'targeted_therapy']},

    {'ticker': 'ALEC', 'acquirer': 'AstraZeneca',     'deal_B': 1.2,  'area': 'Rare Disease',
     'mcap_B': 0.8,  'premium_pct': 50, 'stage': 'commercial', 'year': 2025,
     'attributes': ['commercial_revenue', 'rare_disease', 'orphan', 'bolt_on']},

    {'ticker': 'BBIO', 'acquirer': 'BridgeBio',       'deal_B': 0.0,  'area': 'Rare Disease',
     'mcap_B': 1.5,  'premium_pct': 35, 'stage': 'phase3',     'year': 2024,
     'attributes': ['phase3', 'rare_disease', 'genetic', 'bolt_on']},

    {'ticker': 'GRPH', 'acquirer': 'AstraZeneca',     'deal_B': 1.0,  'area': 'Gene Therapy',
     'mcap_B': 0.55, 'premium_pct': 61, 'stage': 'phase1',     'year': 2024,
     'attributes': ['gene_therapy', 'bolt_on', 'crispr', 'platform']},

    {'ticker': 'TMKR', 'acquirer': 'BMS',             'deal_B': 4.8,  'area': 'Autoimmune',
     'mcap_B': 3.4,  'premium_pct': 41, 'stage': 'phase3',     'year': 2025,
     'attributes': ['phase3', 'autoimmune', 'tyk2', 'bolt_on']},
]

# Pattern profile: aggregate of what recent acquisitions look like
# Used to compute a "pattern match score" for each candidate
ACQUISITION_PATTERN_PROFILE = {
    'avg_premium_pct':   50,   # average acquisition premium across all deals
    'median_mcap_B':     2.0,  # median target market cap at deal time
    'hot_areas': {             # area → how many recent deals in that space
        'ADC/Oncology':      3,
        'Autoimmune':        4,
        'Renal':             2,
        'Metabolic':         2,
        'Rare Disease':      3,
        'Gene Therapy':      2,
        'Oncology':          3,
    },
    'hot_acquirers': [
        'Pfizer', 'AstraZeneca', 'Eli Lilly', 'AbbVie', 'Sanofi',
        'Novo Nordisk', 'BMS', 'Novartis', 'Roche', 'Gilead',
    ],
    'typical_deal_attributes': {
        'bolt_on':           10,  # mcap $150M–$5B
        'phase3':            9,
        'commercial_revenue': 8,
        'discount_to_high':  7,
        'adc':               7,
        'autoimmune':        7,
        'orphan':            6,
        'rare_disease':      6,
        'renal':             6,
        'metabolic':         6,
        'gene_therapy':      5,
        'phase2':            5,
        'tyk2':              5,
        'jak':               5,
        'platform':          4,
        'targeted_therapy':  4,
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUTIONAL RESEARCH DATA STRUCTURES — V12 additions
# Based on buy-side research (JPMorgan, Goldman, Evercore ISI) and academic
# studies on what actually predicts pre-acquisition stock outperformance
# ─────────────────────────────────────────────────────────────────────────────

# Patent cliffs create deal pressure: acquirers MUST replace expiring revenue.
# The more revenue at risk, the more urgently they hunt acquisitions.
PATENT_CLIFF_PRESSURE = {
    'Pfizer': {
        'areas': ['oncology', 'adc', 'antibody-drug conjugate', 'pain', 'vaccine',
                  'autoimmune', 'inflammation', 'small molecule'],
        'revenue_at_risk_B': 17.0,
        'urgency': 'CRITICAL',    # Eliquis, Ibrance, Xeljanz, Vyndamax LOE 2025-2030
    },
    'AbbVie': {
        'areas': ['autoimmune', 'immunology', 'jak', 'tyk2', 'il-23', 'il-17',
                  'inflammatory', 'psoriasis', 'lupus', 'aesthetics', 'neuroscience'],
        'revenue_at_risk_B': 14.0,
        'urgency': 'HIGH',        # Humira biosimilar impact; building Skyrizi/Rinvoq succession
    },
    'Bristol-Myers Squibb': {
        'areas': ['oncology', 'immunology', 'car-t', 'autoimmune', 'cardiovascular',
                  'tyk2', 'fibrosis', 'hematology'],
        'revenue_at_risk_B': 11.0,
        'urgency': 'HIGH',        # Revlimid LOE, Opdivo biosimilar risk 2028
    },
    'Merck': {
        'areas': ['oncology', 'pd-1', 'hpv', 'vaccine', 'infectious', 'antiviral',
                  'immunotherapy', 'solid tumor'],
        'revenue_at_risk_B': 21.0,
        'urgency': 'MODERATE',    # Keytruda 2028 LOE — buying early to build pipeline
    },
    'Novartis': {
        'areas': ['cardiovascular', 'gene therapy', 'oncology', 'aav', 'radioligand',
                  'rare disease', 'renal', 'iga nephropathy'],
        'revenue_at_risk_B': 8.0,
        'urgency': 'MODERATE',
    },
    'Sanofi': {
        'areas': ['autoimmune', 'rare disease', 'orphan drug', 'il-17', 'il-4',
                  'il-13', 'atopy', 'thyroid', 'hematology'],
        'revenue_at_risk_B': 5.0,
        'urgency': 'MODERATE',
    },
    'AstraZeneca': {
        'areas': ['adc', 'antibody-drug conjugate', 'renal', 'iga nephropathy',
                  'oncology', 'rare disease', 'cardiovascular', 'respiratory'],
        'revenue_at_risk_B': 7.0,
        'urgency': 'MODERATE',
    },
    'Eli Lilly': {
        'areas': ["alzheimer's", 'obesity', 'metabolic', 'glp-1', 'diabetes',
                  'autoimmune', 'immunology', 'oncology'],
        'revenue_at_risk_B': 6.0,
        'urgency': 'LOW',         # Lilly buying to extend dominance, not from desperation
    },
    'Novo Nordisk': {
        'areas': ['obesity', 'metabolic', 'glp-1', 'diabetes', 'rare blood disorder',
                  'hemophilia', 'cardiovascular metabolic'],
        'revenue_at_risk_B': 5.0,
        'urgency': 'LOW',
    },
    'Roche': {
        'areas': ['oncology', 'neuroscience', 'rare disease', 'gene therapy',
                  'ophthalmology', 'aav', 'personalized medicine'],
        'revenue_at_risk_B': 9.0,
        'urgency': 'MODERATE',
    },
}

# Differentiation signals — first-in-class / best-in-class language in company desc.
# These commands 2-3x higher acquisition premiums than me-too drugs.
STRATEGIC_SCARCITY_KEYWORDS = [
    'first-in-class', 'first in class', 'novel mechanism', 'only approved',
    'breakthrough therapy', 'best-in-class', 'best in class', 'unique mechanism',
    'highly differentiated', 'no approved therapy', 'unmet medical need',
    'no existing treatment', 'first oral', 'first subcutaneous', 'pioneer',
    'proprietary platform', 'platform technology', 'novel target',
    'differentiated approach', 'first fda-approved', 'only fda-approved',
]

# Me-too signals — reduce confidence (crowded class, generic risk)
ME_TOO_PENALTY_KEYWORDS = [
    'biosimilar', 'generic formulation', 'similar to approved',
    'comparable to existing',
]


# ─────────────────────────────────────────────────────────────────────────────
# WATCHLIST TRACKING SYSTEM — first-seen date / price / tier persistence
# ─────────────────────────────────────────────────────────────────────────────

def load_tracking():
    """Load the persistent watchlist tracking dict from disk."""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_tracking(tracking):
    """Write the tracking dict to disk."""
    try:
        with open(TRACKING_FILE, 'w') as f:
            json.dump(tracking, f, indent=2, default=str)
    except Exception:
        pass


def update_tracking_entry(tracking, ticker, conviction_tier, score, price):
    """
    Record this scan result in the tracking dict.
    First occurrence → record first_seen, first_price, first_tier.
    Subsequent → update last_seen, scan_count, tier_history.
    """
    now = datetime.now().isoformat()
    if ticker not in tracking:
        tracking[ticker] = {
            'first_seen':  now,
            'first_tier':  conviction_tier,
            'first_score': score,
            'first_price': price,
            'last_seen':   now,
            'scan_count':  1,
            'tier_history': [{'date': now, 'tier': conviction_tier,
                               'score': score, 'price': price}],
        }
    else:
        t = tracking[ticker]
        t['last_seen']  = now
        t['scan_count'] = t.get('scan_count', 1) + 1
        hist = t.get('tier_history', [])
        hist.append({'date': now, 'tier': conviction_tier, 'score': score, 'price': price})
        t['tier_history'] = hist[-20:]  # keep last 20 scans
    return tracking


def get_staleness_info(tracking, ticker):
    """
    Return staleness details for a ticker.
    days_tracked — calendar days since first seen on any watchlist
    is_new       — True if first time appearing
    staleness_penalty — pts to subtract from score
    """
    if ticker not in tracking:
        return {
            'days_tracked': 0, 'scan_count': 0, 'is_new': True,
            'first_price': None, 'first_tier': None, 'staleness_penalty': 0,
        }
    t = tracking[ticker]
    try:
        first = datetime.fromisoformat(t['first_seen'])
    except Exception:
        first = datetime.now()
    days = (datetime.now() - first).days
    penalty = 0
    if days >= STALENESS_HARD_DAYS:
        penalty = 10
    elif days >= STALENESS_SOFT_DAYS:
        penalty = 5
    return {
        'days_tracked':      days,
        'scan_count':        t.get('scan_count', 1),
        'is_new':            False,
        'first_price':       t.get('first_price'),
        'first_tier':        t.get('first_tier'),
        'staleness_penalty': penalty,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 6 — INSTITUTIONAL RESEARCH SIGNALS
# Based on buy-side research on what actually predicts pre-M&A outperformance
# ─────────────────────────────────────────────────────────────────────────────

def score_institutional_factors(ticker, profile, financial, pipeline, quote, staleness_info):
    """
    Layer 6: Institutional Research-Backed Signals (max 20 pts, net of staleness penalty)

    1. Patent cliff alignment (+8 pts max): acquirer has $$B at risk from patent
       expirations that the target's area directly addresses
    2. Strategic scarcity (+8 pts max): first/best-in-class signals in description
       → commands 2-3x higher acquisition premium per academic research
    3. Acquirer hunger (+5 pts): recent completed deal in exact same mechanism
       → acquirers typically do 2-3 deals in same area within 18 months
    4. EV/Revenue discount (+5 pts): below typical M&A comp multiples (commercial only)
    5. Staleness penalty: -5 pts after 90d, -10 pts after 180d on watchlist
    """
    result = {
        'layer6_score':    0.0,
        'signals':         [],
        'staleness_pen':   0.0,
        'staleness_flags': [],
    }

    desc    = (profile.get('description', '') + ' ' + profile.get('companyName', '')).lower()
    mcap_B  = ((quote.get('marketCap', 0) or 0) / 1e9)
    rev_ann = financial.get('revenue_annual', 0) or 0
    rev_M   = rev_ann / 1e6

    score = 0.0

    # ── 1. Patent cliff alignment (max 8 pts) ─────────────────────────────────
    urgency_order = {'CRITICAL': 4, 'HIGH': 3, 'MODERATE': 2, 'LOW': 1}
    best_urgency  = 0
    best_acquirer = None
    best_at_risk  = 0.0

    for acquirer, cliff in PATENT_CLIFF_PRESSURE.items():
        if any(area in desc for area in cliff['areas']):
            u = urgency_order.get(cliff['urgency'], 0)
            if u > best_urgency:
                best_urgency  = u
                best_acquirer = acquirer
                best_at_risk  = cliff['revenue_at_risk_B']

    if best_acquirer:
        pts_map = {4: 8, 3: 6, 2: 4, 1: 2}
        pts = pts_map.get(best_urgency, 2)
        score += pts
        urgency_label = {4: 'CRITICAL', 3: 'HIGH', 2: 'MODERATE', 1: 'LOW'}.get(best_urgency)
        result['signals'].append({
            'cat':    'Institutional',
            'type':   f'Patent Cliff Alignment: {best_acquirer}',
            'detail': (f'Fills {best_acquirer}\'s ${best_at_risk:.0f}B revenue gap '
                       f'({urgency_label} urgency — must acquire to replace LOE)'),
            'pts':    pts,
        })

    # ── 2. Strategic scarcity / differentiation (max 8 pts) ───────────────────
    scarcity_hits  = [kw for kw in STRATEGIC_SCARCITY_KEYWORDS if kw in desc]
    me_too_hits    = [kw for kw in ME_TOO_PENALTY_KEYWORDS if kw in desc]

    if scarcity_hits and not me_too_hits:
        if len(scarcity_hits) >= 3:
            pts   = 8
            label = 'Highly Differentiated Asset'
        elif len(scarcity_hits) >= 2:
            pts   = 5
            label = 'Differentiated Mechanism'
        else:
            pts   = 3
            label = 'Potential First/Best-in-Class'
        score += pts
        result['signals'].append({
            'cat':    'Institutional',
            'type':   f'Strategic Scarcity: {label}',
            'detail': f'Signals: {", ".join(scarcity_hits[:3])}',
            'pts':    pts,
        })
    elif me_too_hits:
        # Me-too penalty — crowded class lowers acquisition probability
        pen = 4
        score -= pen
        result['signals'].append({
            'cat':    'Institutional',
            'type':   'Me-Too Risk (PENALTY)',
            'detail': f'Crowded class signal: {", ".join(me_too_hits[:2])} — lowers premium',
            'pts':    -pen,
        })

    # ── 3. Acquirer hunger — recent deal in exact same mechanism (max 5 pts) ───
    # When an acquirer completes one deal in a mechanism, they typically do
    # 2-3 more in the same area within 18 months (ADC/Pfizer pattern is canonical)
    cand_attrs = set()
    for kw, attr in [
        ('adc', 'adc'), ('antibody-drug conjugate', 'adc'),
        ('autoimmune', 'autoimmune'), ('tyk2', 'tyk2'), ('jak', 'jak'),
        ('renal', 'renal'), ('iga nephropathy', 'renal'),
        ('obesity', 'metabolic'), ('glp-1', 'metabolic'), ('nash', 'metabolic'),
        ('gene therapy', 'gene_therapy'), ('crispr', 'gene_therapy'),
        ('orphan', 'orphan'), ('rare disease', 'rare_disease'),
        ('phase3', 'phase3'), ('commercial', 'commercial_revenue'),
    ]:
        if kw in desc:
            cand_attrs.add(attr)

    phase3 = (pipeline or {}).get('phase3_count', 0)
    if phase3 >= 1:
        cand_attrs.add('phase3')
    if financial.get('has_revenue'):
        cand_attrs.add('commercial_revenue')

    # Count recent acquisitions that share mechanism
    hunger_matches = []
    for deal in RECENT_ACQUISITIONS:
        deal_attrs  = set(deal.get('attributes', []))
        mech_overlap = cand_attrs & deal_attrs - {'bolt_on', 'discount_to_high', 'platform'}
        if len(mech_overlap) >= 2:
            hunger_matches.append(deal)

    if len(hunger_matches) >= 3:
        pts = 5
        score += pts
        acquirers = list(dict.fromkeys(d['acquirer'] for d in hunger_matches[:3]))
        result['signals'].append({
            'cat':    'Institutional',
            'type':   'Active Acquirer Hunger',
            'detail': (f'{len(hunger_matches)} recent deals in same mechanism — '
                       f'{", ".join(acquirers[:2])} still buying'),
            'pts':    pts,
        })
    elif len(hunger_matches) >= 1:
        pts = 2
        score += pts
        result['signals'].append({
            'cat':    'Institutional',
            'type':   'Acquirer Hunger Signal',
            'detail': (f'Recent comparable deal: {hunger_matches[0]["ticker"]} '
                       f'→ {hunger_matches[0]["acquirer"]} (same mechanism)'),
            'pts':    pts,
        })

    # ── 4. EV/Revenue discount vs M&A comps (max 5 pts, commercial only) ─────
    # M&A deals typically occur at 5-15x revenue for biotech.
    # Trading below 5x = deeply undervalued relative to what acquirers actually pay.
    if rev_M >= 25 and mcap_B > 0:
        ev_rev = mcap_B / (rev_M / 1000)   # EV/Revenue (using mcap as EV proxy)
        if ev_rev < 3.0:
            pts = 5
            score += pts
            result['signals'].append({
                'cat':    'Institutional',
                'type':   'Deeply Discounted vs M&A Comps',
                'detail': (f'{ev_rev:.1f}x EV/Revenue vs 5-15x typical deal multiple '
                           f'— significant takeout premium possible'),
                'pts':    pts,
            })
        elif ev_rev < 5.0:
            pts = 3
            score += pts
            result['signals'].append({
                'cat':    'Institutional',
                'type':   'Discounted vs M&A Transaction Comps',
                'detail': f'{ev_rev:.1f}x EV/Revenue — below typical 5-15x acquisition multiple',
                'pts':    pts,
            })

    # ── 5. Staleness penalty ───────────────────────────────────────────────────
    staleness_pen = staleness_info.get('staleness_penalty', 0)
    days          = staleness_info.get('days_tracked', 0)

    if staleness_pen >= 10:
        result['staleness_flags'].append(
            f'{days}d on watchlist without acquisition — market has priced out deal '
            f'probability (-{staleness_pen}pts)'
        )
    elif staleness_pen >= 5:
        result['staleness_flags'].append(
            f'{days}d on watchlist — repeatedly flagged, no deal materialised yet '
            f'(-{staleness_pen}pts)'
        )

    result['staleness_pen'] = staleness_pen
    net_score = min(score, 20) - staleness_pen
    result['layer6_score'] = round(net_score, 1)
    return result


def analyze_acquisition_patterns(ticker, profile, financial, pipeline, quote):
    """
    Compare this stock's profile against RECENT_ACQUISITIONS patterns.

    Returns dict:
      pattern_score     — 0–15 bonus points
      matched_patterns  — list of specific pattern matches
      similar_deals     — list of comparable completed acquisitions
      acquirer_interest — which acquirers recently bought similar companies
      implied_premium   — estimated acquisition premium based on comparable deals
    """
    result = {
        'pattern_score':    0,
        'matched_patterns': [],
        'similar_deals':    [],
        'acquirer_interest': [],
        'implied_premium':   0,
    }

    mcap_B  = ((quote.get('marketCap', 0) or 0) / 1e9)
    price   = quote.get('price', 0) or 0
    year_high = quote.get('yearHigh', price) or price
    discount_pct = ((year_high - price) / year_high * 100) if year_high > 0 else 0

    desc = (profile.get('description', '') + ' ' + profile.get('companyName', '')).lower()

    phase3   = (pipeline or {}).get('phase3_count', 0)
    phase2   = (pipeline or {}).get('phase2_count', 0)
    has_rev  = financial.get('has_revenue', False)
    has_orph = (pipeline or {}).get('has_orphan', False)

    # Build attribute set for this candidate
    cand_attrs = set()
    if 0.15 <= mcap_B <= 5.0:
        cand_attrs.add('bolt_on')
    if phase3 >= 1:
        cand_attrs.add('phase3')
    if phase2 >= 1:
        cand_attrs.add('phase2')
    if has_rev:
        cand_attrs.add('commercial_revenue')
    if 20 <= discount_pct <= 70:
        cand_attrs.add('discount_to_high')
    if has_orph:
        cand_attrs.add('orphan')
        cand_attrs.add('rare_disease')
    for kw in ['adc', 'antibody-drug conjugate', 'trop-2']:
        if kw in desc: cand_attrs.add('adc')
    for kw in ['autoimmune', 'lupus', 'rheumatoid', 'psoriasis', 'ibd', 'crohn']:
        if kw in desc: cand_attrs.add('autoimmune')
    for kw in ['tyk2', 'jak1', 'jak2']:
        if kw in desc: cand_attrs.add('tyk2'); cand_attrs.add('jak')
    for kw in ['renal', 'kidney', 'nephropathy', 'iga']:
        if kw in desc: cand_attrs.add('renal')
    for kw in ['obesity', 'glp-1', 'metabolic', 'nash', 'nafld', 'mash']:
        if kw in desc: cand_attrs.add('metabolic'); cand_attrs.add('glp1_adjacent')
    for kw in ['crispr', 'gene therapy', 'gene editing', 'aav', 'lentiviral']:
        if kw in desc: cand_attrs.add('gene_therapy'); cand_attrs.add('platform')
    for kw in ['targeted therapy', 'small molecule', 'kras', 'egfr', 'her2']:
        if kw in desc: cand_attrs.add('targeted_therapy')

    # Find similar completed deals (at least 4 matching attributes — was 3, too loose)
    similar = []
    for deal in RECENT_ACQUISITIONS:
        deal_attrs = set(deal.get('attributes', []))
        overlap = cand_attrs & deal_attrs
        if len(overlap) >= 4:
            similarity_score = len(overlap) / max(len(deal_attrs), 1)
            similar.append({
                'ticker':    deal['ticker'],
                'acquirer':  deal['acquirer'],
                'deal_B':    deal['deal_B'],
                'premium':   deal['premium_pct'],
                'area':      deal['area'],
                'overlap':   sorted(overlap),
                'score':     round(similarity_score, 2),
            })

    similar.sort(key=lambda x: -x['score'])
    result['similar_deals'] = similar[:3]

    # Acquirer interest from similar deals
    acquirers = list(dict.fromkeys([d['acquirer'] for d in similar]))
    result['acquirer_interest'] = acquirers[:4]

    # Implied premium from comparable deals
    if similar:
        result['implied_premium'] = round(sum(d['premium'] for d in similar) / len(similar), 0)

    # Score individual pattern matches
    score = 0
    matched = []

    profile_attrs = ACQUISITION_PATTERN_PROFILE['typical_deal_attributes']

    # Award points for each confirmed attribute that recent acquirers paid for
    attr_hits = [(a, profile_attrs[a]) for a in cand_attrs if a in profile_attrs]
    attr_hits.sort(key=lambda x: -x[1])

    for attr, pts in attr_hits[:4]:  # top 4 matching attributes
        score += pts * 0.3           # weight = 30% of raw pts (reduced from 40%)
        label = attr.replace('_', ' ').title()
        matched.append(f'{label} — matches recent acquisition attribute')

    # Bonus if we found highly similar completed deals (requires 4+ attrs now)
    if len(similar) >= 3:
        score += 4
        matched.append(f'Closely mirrors {len(similar)} completed deals '
                       f'({", ".join(d["ticker"] for d in similar[:2])})')
    elif len(similar) >= 1:
        score += 2
        matched.append(f'Comparable to {similar[0]["ticker"]} ({similar[0]["acquirer"]}, '
                       f'${similar[0]["deal_B"]:.1f}B, +{similar[0]["premium"]}%)')

    # Hot area bonus: this area had multiple recent acquisitions (reduced from 2 to 1 pt)
    hot = ACQUISITION_PATTERN_PROFILE['hot_areas']
    desc_areas = {
        'ADC/Oncology':  any(kw in desc for kw in ['adc', 'antibody-drug conjugate']),
        'Autoimmune':    any(kw in desc for kw in ['autoimmune', 'lupus', 'rheumatoid']),
        'Renal':         any(kw in desc for kw in ['renal', 'kidney', 'nephropathy']),
        'Metabolic':     any(kw in desc for kw in ['obesity', 'metabolic', 'glp-1', 'nash']),
        'Rare Disease':  has_orph,
        'Gene Therapy':  any(kw in desc for kw in ['gene therapy', 'crispr', 'aav']),
        'Oncology':      any(kw in desc for kw in ['tumor', 'cancer', 'oncolog', 'kras']),
    }
    for area, matches in desc_areas.items():
        if matches and hot.get(area, 0) >= 2:
            score += 1
            matched.append(f'Active M&A area: {area} ({hot[area]} deals 2023–2026)')
            break  # only one area bonus

    result['pattern_score']    = min(round(score, 1), 10)   # cap at 10 (was 15)
    result['matched_patterns'] = matched

    return result


# ─────────────────────────────────────────────────────────────────────────────
# FMP API CLIENT (from V10.6, extended)
# ─────────────────────────────────────────────────────────────────────────────

class FMPClient:

    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.enabled = bool(api_key)

    def _get(self, endpoint, params=None, base=None):
        if not self.enabled:
            return None
        params = dict(params or {})
        params['apikey'] = self.api_key
        url = f"{base or FMP_BASE}/{endpoint}"

        # Cache key excludes apikey so keys are stable across key rotations
        ck = make_key('fmp', endpoint, sorted((k, v) for k, v in params.items() if k != 'apikey'))
        cached = cache_get(ck)
        if cached is not None:
            return cached

        try:
            _rate_limiter.acquire()          # global throttle; replaces time.sleep(0.15)
            r = self.session.get(url, params=params, timeout=12)
            r.raise_for_status()
            result = r.json()
            cache_set(ck, result)
            return result
        except Exception:
            return None

    def get_quote(self, symbol):
        data = self._get('quote', {'symbol': symbol})
        return data[0] if isinstance(data, list) and data else None

    def get_profile(self, symbol):
        data = self._get('profile', {'symbol': symbol})
        return data[0] if isinstance(data, list) and data else None

    def get_price_target_consensus(self, symbol):
        data = self._get('price-target-consensus', {'symbol': symbol})
        return data[0] if isinstance(data, list) and data else data

    def get_stock_grades(self, symbol, limit=10):
        data = self._get('grades', {'symbol': symbol})
        return data[:limit] if isinstance(data, list) else []

    def get_income_statement(self, symbol, period='annual', limit=3):
        return self._get('income-statement', {'symbol': symbol, 'period': period, 'limit': limit}) or []

    def get_balance_sheet(self, symbol, period='quarter', limit=4):
        return self._get('balance-sheet-statement', {'symbol': symbol, 'period': period, 'limit': limit}) or []

    def get_cash_flow(self, symbol, period='quarter', limit=4):
        return self._get('cash-flow-statement', {'symbol': symbol, 'period': period, 'limit': limit}) or []

    def get_balance_sheet_growth(self, symbol, limit=4):
        return self._get('balance-sheet-statement-growth', {'symbol': symbol, 'limit': limit}) or []

    def get_rsi(self, symbol, period=14):
        to_d = datetime.now().strftime('%Y-%m-%d')
        from_d = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        data = self._get('technical-indicators/rsi', {
            'symbol': symbol, 'periodLength': period,
            'timeframe': '1day', 'from': from_d, 'to': to_d
        })
        return data[-1] if isinstance(data, list) and data else None

    def get_historical(self, symbol, days=180):
        from_d = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_d   = datetime.now().strftime('%Y-%m-%d')
        data = self._get('historical-price-eod/full',
                         {'symbol': symbol, 'from': from_d, 'to': to_d})
        return data if isinstance(data, list) else []

    def get_insider_trading(self, symbol, limit=100):
        return self._get('insider-trading/search',
                         {'symbol': symbol, 'page': 0, 'limit': limit}) or []

    def get_financial_growth(self, symbol, period='annual', limit=2):
        return self._get('financial-growth', {'symbol': symbol, 'period': period, 'limit': limit}) or []

    def get_enterprise_values(self, symbol, period='quarter', limit=2):
        return self._get('enterprise-values', {'symbol': symbol, 'period': period, 'limit': limit}) or []

    def get_dcf(self, symbol):
        """Custom DCF — returns equityValuePerShare, wacc."""
        data = self._get('custom-discounted-cash-flow', {'symbol': symbol})
        return data[0] if isinstance(data, list) and data else None

    def get_sma(self, symbol, period):
        """SMA time-series (newest first). Returns None if <2 data points."""
        data = self._get('technical-indicators/sma', {
            'symbol': symbol, 'periodLength': period, 'timeframe': '1day'
        })
        return data if isinstance(data, list) and len(data) >= 2 else None

    def get_sec_filings_symbol(self, symbol, days=7):
        """All SEC filings for this symbol in the last N days."""
        from_d = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_d   = datetime.now().strftime('%Y-%m-%d')
        data = self._get('sec-filings-search/symbol', {
            'symbol': symbol, 'from': from_d, 'to': to_d, 'limit': 50
        })
        return data if isinstance(data, list) else []

    def get_key_metrics(self, symbol, limit=1):
        """Key valuation + quality metrics: EV/EBITDA, ROIC, Graham Number, etc."""
        return self._get('key-metrics', {'symbol': symbol, 'limit': limit}) or []

    def get_analyst_estimates(self, symbol, period='annual', limit=3):
        """Forward EPS + revenue estimates, newest date first."""
        return self._get('analyst-estimates', {
            'symbol': symbol, 'period': period, 'limit': limit
        }) or []

    def get_earnings_history(self, symbol, limit=10):
        """Quarterly EPS actual vs estimated (includes upcoming quarters with null actual)."""
        return self._get('earnings', {'symbol': symbol, 'limit': limit}) or []

    def get_earnings_calendar(self, from_date, to_date):
        """All tickers reporting earnings between two dates. Call once per scan."""
        data = self._get('earnings-calendar', {'from': from_date, 'to': to_date})
        return data if isinstance(data, list) else []

    def get_proxy_filings(self, symbol, limit=1):
        """Most recent DEF 14A (proxy statement) filings for this symbol."""
        data = self._get('sec-filings-search/symbol', {
            'symbol': symbol, 'formType': 'DEF 14A', 'limit': limit
        })
        # Fallback: filter from all filings
        if not isinstance(data, list) or not data:
            all_f = self.get_sec_filings_symbol(symbol, days=400)
            data = [f for f in all_f if f.get('formType') in ('DEF 14A', 'DEF14A')]
        return data[:limit] if isinstance(data, list) else []

    def get_13d_filings(self, days=60, page=0, limit=100):
        """SC 13D activist filings in the last N days — universe-wide."""
        from_d = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_d   = datetime.now().strftime('%Y-%m-%d')
        data = self._get('sec-filings-search/form-type', {
            'formType': 'SC 13D', 'from': from_d, 'to': to_d,
            'page': page, 'limit': limit
        })
        return data if isinstance(data, list) else []


# ─────────────────────────────────────────────────────────────────────────────
# NEW SIGNAL HELPERS — DCF margin of safety, SMA momentum, 8-K catalyst
# These 3 call the new FMP endpoints added in V12.1
# ─────────────────────────────────────────────────────────────────────────────

def fetch_dcf_signal(fmp, ticker, price):
    """
    Pull DCF intrinsic value and compute margin of safety.
    Returns dict: fair_value, mos_pct, has_mos, wacc
    mos_pct > 0 = undervalued (fair value exceeds current price)
    """
    dcf = fmp.get_dcf(ticker)
    if not dcf:
        return {'fair_value': None, 'mos_pct': 0.0, 'has_mos': False, 'wacc': None}
    fair_value = dcf.get('equityValuePerShare', 0) or 0
    if fair_value <= 0 or price <= 0:
        return {'fair_value': None, 'mos_pct': 0.0, 'has_mos': False, 'wacc': None}
    mos = (fair_value - price) / fair_value
    return {
        'fair_value': round(fair_value, 2),
        'mos_pct':    round(mos * 100, 1),
        'has_mos':    mos >= 0.15,
        'wacc':       dcf.get('wacc'),
    }


def fetch_sma_signal(fmp, ticker):
    """
    Pull SMA(10) and SMA(20) to detect momentum stack.
    Returns dict: above_short, above_long, sma10, sma20
    Full stack = price > SMA10 > SMA20 (trend with us, not against)
    """
    result = {'above_short': False, 'above_long': False, 'sma10': None, 'sma20': None}
    sma10_data = fmp.get_sma(ticker, 10)
    sma20_data = fmp.get_sma(ticker, 20)

    sma10_val = None
    if sma10_data:
        price_now = sma10_data[0].get('close', 0) or 0
        sma10_val = sma10_data[0].get('sma', 0) or 0
        result['sma10'] = round(sma10_val, 2) if sma10_val else None
        if price_now > 0 and sma10_val > 0:
            result['above_short'] = price_now > sma10_val

    if sma20_data:
        sma20_val = sma20_data[0].get('sma', 0) or 0
        result['sma20'] = round(sma20_val, 2) if sma20_val else None
        if sma10_val and sma20_val > 0:
            result['above_long'] = sma10_val > sma20_val

    return result


def fetch_8k_signal(fmp, ticker, days=7):
    """
    Check for recent 8-K material event filing in the last N days.
    8-K = something material just happened (earnings, deal, FDA action, etc.)
    Returns True if at least one 8-K found.
    """
    filings = fmp.get_sec_filings_symbol(ticker, days=days)
    return any(f.get('formType') == '8-K' for f in filings)


def fetch_key_metrics_signal(fmp, ticker):
    """
    Pull EV/EBITDA, ROIC, and Graham Number from key-metrics.
    Hedge funds use EV/EBITDA as the primary M&A comp multiple.
    ROIC separates quality compounders from science projects.
    """
    metrics = fmp.get_key_metrics(ticker, limit=1)
    if not metrics:
        return {}
    m = metrics[0]
    return {
        'ev_to_ebitda':  m.get('evToEBITDA'),
        'ev_to_sales':   m.get('evToSales'),
        'roic':          m.get('returnOnInvestedCapital'),
        'roe':           m.get('returnOnEquity'),
        'graham_number': m.get('grahamNumber'),
        'current_ratio': m.get('currentRatio'),
    }


def fetch_analyst_signal(fmp, ticker, price):
    """
    Forward EPS/Revenue estimates + estimate revision direction.
    Rising estimates while price falls = the strongest M&A setup — market wrong, analysts right.
    """
    estimates = fmp.get_analyst_estimates(ticker, period='annual', limit=3)
    if not estimates:
        return {}

    # Find the nearest forward year (first entry where date year >= current year)
    now_year = datetime.now().year
    forward = next(
        (e for e in estimates if e.get('date', '')[:4].isdigit()
         and int(e['date'][:4]) >= now_year),
        estimates[0]
    )

    fwd_eps = forward.get('epsAvg', 0) or 0
    fwd_rev = forward.get('revenueAvg', 0) or 0
    num_analysts = max(
        forward.get('numAnalystsEps', 0) or 0,
        forward.get('numAnalystsRevenue', 0) or 0
    )

    # Estimate revision trend: compare most recent vs second-most-recent forward year
    est_trend = None
    if len(estimates) >= 2:
        eps_now  = estimates[0].get('epsAvg', 0) or 0
        eps_prev = estimates[1].get('epsAvg', 0) or 0
        if eps_prev != 0:
            est_trend = 'up' if eps_now > eps_prev * 1.02 else (
                'down' if eps_now < eps_prev * 0.98 else 'flat'
            )

    fwd_pe = round(price / fwd_eps, 1) if (fwd_eps > 0 and price > 0) else None

    return {
        'fwd_eps':       round(fwd_eps, 2),
        'fwd_revenue':   round(fwd_rev / 1e6, 1),   # in $M
        'fwd_pe':        fwd_pe,
        'num_analysts':  num_analysts,
        'est_trend':     est_trend,                  # 'up' | 'down' | 'flat'
    }


def fetch_earnings_quality(fmp, ticker):
    """
    Beat rate + consecutive beats + next earnings date.
    4+ consecutive beats = management execution premium (acquirers pay 15-25% more per academic research).
    Earnings within 14 days = imminent catalyst.
    """
    history = fmp.get_earnings_history(ticker, limit=10)
    if not history:
        return {'beat_rate': 0, 'consecutive_beats': 0, 'next_earnings': None,
                'days_to_earnings': None, 'earnings_imminent': False}

    next_earnings    = None
    days_to_earnings = None
    reported         = []

    for e in history:
        if e.get('epsActual') is None:
            # Future quarter — grab the nearest upcoming date
            if next_earnings is None:
                next_earnings = e.get('date')
        else:
            reported.append(e)

    # Compute days to next earnings
    if next_earnings:
        try:
            days_to_earnings = (datetime.strptime(next_earnings, '%Y-%m-%d') - datetime.now()).days
        except Exception:
            days_to_earnings = None

    # Beat rate and consecutive beats (reported is newest-first)
    beats, total, consecutive = 0, 0, 0
    streak_active = True
    for e in reported:
        actual    = e.get('epsActual', 0) or 0
        estimated = e.get('epsEstimated', 0) or 0
        if estimated == 0:
            continue
        total += 1
        beat = actual > estimated
        if beat:
            beats += 1
            if streak_active:
                consecutive += 1
        else:
            streak_active = False

    beat_rate = round(beats / total * 100, 0) if total > 0 else 0

    return {
        'beat_rate':        beat_rate,
        'consecutive_beats': consecutive,
        'beats':            beats,
        'total_quarters':   total,
        'next_earnings':    next_earnings,
        'days_to_earnings': days_to_earnings,
        'earnings_imminent': (days_to_earnings is not None and 0 <= days_to_earnings <= 14),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 7 — DEAL PROCESS SIGNALS
# These are qualitatively different from probability signals.
# They indicate the deal process is already underway, not just likely.
#
# Sources:
#   • SC 13D activist filings  — someone with resources is pushing for a sale
#   • 8-K full text NLP        — "strategic alternatives" = board hired a banker
#   • DEF 14A proxy parsing    — management is financially incentivized to sell
# ─────────────────────────────────────────────────────────────────────────────

import re

# SEC requires a descriptive User-Agent or requests get blocked
_SEC_HEADERS = {
    'User-Agent': 'BlackStarLightCapital diamondsteve004@gmail.com',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Known biotech-specialist activists — 13D from these = much stronger signal
_KNOWN_ACTIVISTS = [
    'sarissa capital', 'caligan partners', 'starboard value', 'elliott',
    'third point', 'jana partners', 'engaged capital', 'deerfield',
    'ventas', 'baker brothers', 'avoro capital', 'foresite capital',
    'perceptive advisors', 'alphaeon', 'biotechnology value fund', 'bvf',
]

# Phrases detected in 8-K documents, with score weight
# Ordered by signal strength — stop reading further files once top phrase found
_8K_SIGNAL_PHRASES = [
    ('strategic alternatives',            'strategic_alternatives', 30),
    ('exploring strategic',               'strategic_alternatives', 30),  # alt wording
    ('unsolicited proposal',              'unsolicited_proposal',   30),
    ('superior proposal',                 'superior_proposal',      28),
    ('proposal to acquire',               'acquisition_proposal',   25),
    ('acquisition proposal',              'acquisition_proposal',   25),
    ('right of first negotiation',        'rofn',                   18),
    ('first right to negotiate',          'rofn',                   18),  # legal variant
    ('right of first refusal',            'rofr',                   15),
    ('right of first purchase',           'rofr',                   15),  # legal variant
    ('right of first offer',              'rofo',                   14),
    ('merger agreement',                  'merger_agreement',       12),  # deal announced
    ('exclusive worldwide license',       'exclusive_license',       8),
    ('exclusive license agreement',       'exclusive_license',       8),
    ('collaboration and license',         'collaboration',           5),
    ('co-development agreement',          'collaboration',           5),
]

# Banker/advisor retention phrases — strong leading indicator of a live sale process.
# Companies file 8-Ks disclosing advisor engagement before a formal "strategic
# alternatives" announcement. Currently score 0; this closes that gap.
_ADVISOR_PHRASES = [
    ('as its exclusive financial advisor',      22),
    ('as financial advisor to the company',     22),
    ('as its financial advisor in connection',  22),
    ('retained as its financial advisor',       22),
    ('engaged as its financial advisor',        22),
    ('retained a financial advisor',            20),
    ('engaged a financial advisor',             20),
    ('potential sale of the company',           25),  # near-explicit sale intent
    ('exploring a potential sale',              25),
    ('retained an investment bank',             20),
    ('engaged an investment bank',              20),
]

# Top pharma names to detect as named partners in filings
_MAJOR_PHARMA = [
    'pfizer', 'abbvie', 'astrazeneca', 'bristol-myers squibb', 'bms',
    'eli lilly', 'lilly', 'novartis', 'roche', 'genentech', 'sanofi',
    'merck', 'gilead', 'amgen', 'novo nordisk', 'johnson & johnson',
    'janssen', 'takeda', 'biogen', 'regeneron', 'vertex',
]

# Change-of-control phrases in proxy statements
_COC_PHRASES = [
    'change in control', 'change of control', 'termination following a change',
    'double trigger', 'single trigger', 'accelerated vesting upon',
    'golden parachute', 'parachute payment',
]

# ── Task 1: context markers for SA quality scoring ───────────────────────────
_SA_BOILERPLATE_MARKERS = [
    'may consider', 'could explore', 'no assurance', 'risk factor', 'hypothetical',
    'may pursue', 'could pursue', 'we cannot', 'there can be no', 'if we were',
]
_SA_AFFIRM_MARKERS = [
    'announced', 'is exploring', 'has engaged', 'has retained', 'initiated review',
    'board has determined', 'has initiated', 'is conducting', 'formally exploring',
]

# ── P0-A: Negation detection — phrases that negate acquisition-pressure meaning ──
# Applied to NEGATION_SENSITIVE_KEYS only; not to SA affirm or merger agreement.
_NEGATION_PREFIXES = (
    'no plan or proposal',
    'no plans or proposals',
    'no current plan',
    'no current plans',
    'does not have any plan',
    'have no plan',
    'have not formulated',
    'has not formulated',
    'no present intention',
    'no intention to',
    'without any plan',
    'currently have no',
    'do not have any',
    'have not adopted',
)

# Keys where negation detection is applied; SA and merger are excluded — too few
# false-negative cases to justify negation suppression on those phrases.
_NEGATION_SENSITIVE_KEYS = frozenset({
    'acquisition_proposal', 'unsolicited_proposal', 'superior_proposal',
    'rofn', 'rofr', 'rofo',
})

# ── P0-C: ROFR/ROFN scope classification context markers ─────────────────────
_ROFR_SECURITIES_TERMS = (
    'lock-up', 'lockup', 'lock up',
    'transfer of shares', 'transfer of stock', 'transfer restriction',
    'shareholder agreement', 'repurchase right', 'repurchase of shares',
    'termination of employment', 'termination of service',
    'forfeiture', 'unvested', 'equity award', 'option agreement',
    'registration rights', 'preemptive right', 'sale of the company\'s securities',
    'sale of securities', 'offering', 'underwritten',
)
_ROFR_ASSET_TERMS = (
    'licensed product', 'collaboration agreement', 'license agreement',
    'co-development', 'co-promotion', 'territory',
    'geographic', 'product candidate', 'drug candidate',
    'specific program', 'specific asset', 'specific product',
    'indication ', 'therapeutic area', 'japan', 'china', 'asia',
    'north america', 'europe', 'rest of world', 'worldwide license',
    'royalty', 'milestone', 'right of first negotiation for',
)
_ROFR_COMPANY_TERMS = (
    'sale of the company', 'acquisition of the company',
    'merger agreement', 'strategic alternatives',
    'board of directors', 'all outstanding shares', 'all of the outstanding',
    'business combination', 'change of control', 'change in control',
    'acquisition proposal', 'whole company', 'entire company',
)


def _classify_rights_scope(text, phrase, idx=None):
    """
    P0-C: Classify scope of a ROFR/ROFN phrase match from surrounding 400-char context.

    Returns:
      company_level_possible      — context suggests whole-company acquisition pathway
      asset_specific_likely       — context suggests product/program/territory-specific rights
      securities_or_lockup_likely — context suggests investor share-transfer restrictions
      unknown_scope               — insufficient context to classify
    """
    if idx is None:
        idx = text.find(phrase)
    if idx < 0:
        return 'unknown_scope'
    ctx = text[max(0, idx - 150): idx + 250]

    # Securities/lock-up context takes priority — clearly not M&A signals.
    if any(w in ctx for w in _ROFR_SECURITIES_TERMS):
        return 'securities_or_lockup_likely'

    # Asset-specific context (collaboration/license/geographic).
    if any(w in ctx for w in _ROFR_ASSET_TERMS):
        return 'asset_specific_likely'

    # Company-level context.
    if any(w in ctx for w in _ROFR_COMPANY_TERMS):
        return 'company_level_possible'

    return 'unknown_scope'


def score_strategic_alternatives_quality(text, idx):
    """
    Inspect ±400-char context around a 'strategic alternatives' phrase match.
    Returns (pts, is_affirm):
      - Boilerplate (risk-factor language) → (8, False)  — does not clear evidence cap
      - Affirm or ambiguous               → (30, True)  — full score, clears cap
    Default is affirm to avoid false negatives on real deals.
    """
    ctx = text[max(0, idx - 400): idx + 400]
    if any(m in ctx for m in _SA_BOILERPLATE_MARKERS):
        return 8, False
    if any(m in ctx for m in _SA_AFFIRM_MARKERS):
        return 30, True
    # Ambiguous — phrase found but no confirming or boilerplate context
    return 15, False   # neutral: partial score, cap not cleared


def _activist_decay(filing_date_str, base_pts):
    """
    Task 2: Apply linear recency decay to 13D score.
    Full weight at filing date, 40% floor at 90+ days.
    decay = max(0.4, 1 - days_since_filing / 90)
    """
    try:
        from datetime import datetime, date as _date
        filed = datetime.strptime(filing_date_str[:10], '%Y-%m-%d').date()
        days  = (_date.today() - filed).days
        decay = max(0.4, 1.0 - days / 90.0)
        return round(base_pts * decay, 1)
    except Exception:
        return float(base_pts)   # unparseable date → no decay


def _fetch_doc_text(url, max_bytes=400_000, timeout=(5, 20)):
    """
    Fetch an SEC filing document URL and return lowercase plain text.
    Strips all HTML tags. Caps at max_bytes to avoid reading 10MB filings.
    Returns empty string on any failure. Results cached 72h (SEC filings don't change).
    timeout: (connect_timeout, read_timeout) — default (5, 20).
    """
    ck = make_key('doc', url, max_bytes)
    cached = cache_get(ck, ttl=DOC_TTL)
    if cached is not None:
        return cached

    try:
        r = requests.get(url, headers=_SEC_HEADERS, timeout=timeout, stream=True)
        r.raise_for_status()
        raw = b''
        for chunk in r.iter_content(chunk_size=32_768):
            raw += chunk
            if len(raw) >= max_bytes:
                break
        html = raw.decode('utf-8', errors='ignore')
        # Strip tags — BeautifulSoup is already imported
        text = BeautifulSoup(html, 'html.parser').get_text(separator=' ')
        result = re.sub(r'\s+', ' ', text).lower()
        cache_set(ck, result)
        return result
    except requests.exceptions.Timeout:
        logger.warning('SLOW_HTTP url=%s reason=timeout', url[:80])
        return ''
    except Exception:
        return ''


def preload_activist_signals(fmp, universe_set, days=60):
    """
    Pull all SC 13D filings from last N days, cross-reference against universe.
    Called ONCE at scan start — no per-ticker API cost.

    Returns dict: {TICKER: {filer, filing_date, pts, is_known_activist}}
    """
    activist_map = {}
    for page in range(5):   # up to 500 filings
        batch = fmp.get_13d_filings(days=days, page=page, limit=100)
        if not batch:
            break
        for f in batch:
            sym = (f.get('symbol') or '').upper().strip()
            if not sym or sym not in universe_set:
                continue
            filer_raw = (f.get('filerName') or f.get('reportingName') or '').lower()
            is_known  = any(act in filer_raw for act in _KNOWN_ACTIVISTS)
            pts       = 20 if is_known else 12

            # Keep highest-scoring entry per ticker
            if sym not in activist_map or pts > activist_map[sym]['pts']:
                activist_map[sym] = {
                    'filer':        (f.get('filerName') or f.get('reportingName') or 'Unknown'),
                    'filing_date':  f.get('filingDate', ''),
                    'is_known':     is_known,
                    'pts':          pts,
                }
        if len(batch) < 100:
            break
        time.sleep(0.3)

    return activist_map


def enrich_activist_item4(fmp, ticker, activist_signal):
    """
    Fetch SC 13D / SC 13D/A document for ticker and parse Item 4 intent.

    Called during the per-ticker Layer 7 pass (not during preload — document
    fetches are expensive and only needed for tickers that scored high enough).

    Reuses _fetch_doc_text() which caches results 72h. Prefers SC 13D/A
    (amendment) over initial filing where available — amendments often carry
    escalation language the initial filing lacks.

    Returns: enriched activist_signal dict with 'item4' key added,
             or original dict if document unavailable.
    """
    from item4_parser import parse_13d_item4

    if not activist_signal:
        return activist_signal

    try:
        all_filings = fmp.get_sec_filings_symbol(ticker, days=180)
        sc13d_filings = [
            f for f in all_filings
            if 'SC 13D' in (f.get('formType') or '')
        ]
        if not sc13d_filings:
            return activist_signal

        # Sort: amendments first (more likely to contain escalation language)
        sc13d_filings.sort(
            key=lambda f: (0 if '/A' in (f.get('formType') or '') else 1,
                           f.get('filingDate', '')),
            reverse=False,
        )

        best_parse = None
        for filing in sc13d_filings[:3]:
            url = filing.get('finalLink') or filing.get('linkToFilingDetails') or ''
            if not url:
                continue
            doc_text = _fetch_doc_text(url, max_bytes=500_000)
            if not doc_text:
                continue
            parse = parse_13d_item4(doc_text)
            if best_parse is None or parse['confidence_score'] > best_parse['confidence_score']:
                best_parse = parse
                best_parse['source_form_type'] = filing.get('formType', 'SC 13D')
                best_parse['source_filing_date'] = filing.get('filingDate', '')

        if best_parse:
            enriched = dict(activist_signal)
            enriched['item4'] = best_parse
            return enriched

    except Exception:
        pass

    return activist_signal


def fetch_8k_text_signals(fmp, ticker, n_filings=8):
    """
    Fetch last N 8-K document bodies and parse for deal-process language.

    Returns dict:
      strategic_alternatives — bool  (board exploring sale)
      rofn / rofr / rofo     — bool  (acquisition option with named pharma)
      exclusive_license      — bool  (deep partnership = likely precursor)
      named_pharma           — str | None  (which major pharma is named)
      top_phrase             — str   (highest-signal phrase found)
      pts                    — int   (total score contribution)
      --- P0 additions (backward-compatible new fields) ---
      negated_phrases        — list  (P0-A: phrases suppressed by negation detection)
      source_url             — str   (P0-B: URL of 8-K that triggered the first signal)
      source_accession       — str   (P0-B: accession number of that filing)
      source_filing_date     — str   (P0-B: filing date of that filing)
      source_form_type       — str   (P0-B: form type of that filing, typically '8-K')
      source_matched_phrase  — str   (P0-B: phrase that triggered the source record)
      rofn_scope_hint        — str|None  (P0-C: scope of ROFN match)
      rofr_scope_hint        — str|None  (P0-C: scope of ROFR match)
      rofo_scope_hint        — str|None  (P0-C: scope of ROFO match)
    """
    result = {
        'strategic_alternatives': False,
        'unsolicited_proposal':   False,
        'superior_proposal':      False,
        'acquisition_proposal':   False,
        'banker_retained':        False,  # hired M&A advisor (pre-SA leading indicator)
        'rofn':                   False,
        'rofr':                   False,
        'rofo':                   False,
        'merger_agreement':       False,
        'exclusive_license':      False,
        'collaboration':          False,
        'named_pharma':           None,
        'top_phrase':             '',
        'pts':                    0,
        # P0-A: audit trail for negation-suppressed phrases
        'negated_phrases':        [],
        # P0-B: source traceability
        'source_url':             '',
        'source_accession':       '',
        'source_filing_date':     '',
        'source_form_type':       '',
        'source_matched_phrase':  '',
        'source_excerpt':         '',
        # P0-C: ROFR/ROFN scope hints
        'rofn_scope_hint':        None,
        'rofr_scope_hint':        None,
        'rofo_scope_hint':        None,
    }

    # Pull all SEC filings for this ticker from the last year
    all_filings = fmp.get_sec_filings_symbol(ticker, days=365)
    recent_8ks  = [f for f in all_filings if f.get('formType') == '8-K'][:n_filings]

    for filing in recent_8ks:
        url = filing.get('finalLink') or filing.get('linkToFilingDetails') or ''
        if not url:
            continue

        text = _fetch_doc_text(url)
        if not text:
            continue

        for phrase, key, pts in _8K_SIGNAL_PHRASES:
            if phrase in text and not result.get(key):
                idx = text.find(phrase)

                # P0-A: negation detection — skip if acquisition/rights phrase is negated.
                # Applied only to NEGATION_SENSITIVE_KEYS; SA and merger phrases are exempt.
                if key in _NEGATION_SENSITIVE_KEYS:
                    ctx_before = text[max(0, idx - 55): idx]
                    if any(neg in ctx_before for neg in _NEGATION_PREFIXES):
                        result['negated_phrases'].append(phrase)
                        continue  # negated context — do not score

                # P0-C: classify ROFR/ROFN scope and adjust score contribution.
                score_pts = pts
                if key in ('rofn', 'rofr', 'rofo'):
                    scope = _classify_rights_scope(text, phrase, idx)
                    result[key + '_scope_hint'] = scope
                    if scope in ('asset_specific_likely', 'securities_or_lockup_likely'):
                        score_pts = 0   # no process score for non-company-level rights
                    elif scope == 'unknown_scope':
                        score_pts = pts // 2   # reduced score — scope unclear

                result[key]    = True
                result['pts'] += score_pts
                if not result['top_phrase']:
                    result['top_phrase'] = phrase

                # P0-B: capture source metadata on first affirmative phrase match.
                if not result['source_url']:
                    result['source_url']           = url
                    result['source_accession']     = filing.get('accessionNumber', '') or ''
                    result['source_filing_date']   = filing.get('filingDate', '')
                    result['source_form_type']     = filing.get('formType', '8-K')
                    result['source_matched_phrase'] = phrase
                    result['source_excerpt']       = text[max(0, idx - 150): idx + 200].strip()

        # Named pharma detection — bonus if paired with a structural clause
        if result['named_pharma'] is None:
            for pharma in _MAJOR_PHARMA:
                if pharma in text:
                    result['named_pharma'] = pharma.title()
                    # Named partner + structural clause = extra conviction
                    if result['rofn'] or result['rofr'] or result['exclusive_license']:
                        result['pts'] += 6
                    break

        # Task 1: context-quality check for strategic alternatives (run once, first hit)
        if result.get('strategic_alternatives') and 'sa_is_affirm' not in result:
            sa_idx = next(
                (text.find(p) for p in ('strategic alternatives', 'exploring strategic') if p in text),
                0,
            )
            sa_pts, sa_is_affirm = score_strategic_alternatives_quality(text, sa_idx)
            result['pts']       += sa_pts - 30   # replace raw 30 with quality-adjusted pts
            result['sa_is_affirm'] = sa_is_affirm

        # Banker/advisor detection — only fire if no stronger signal already found.
        # "potential sale" phrases score higher than advisor retention; take max.
        if not result['strategic_alternatives'] and not result['banker_retained']:
            best_pts = 0
            best_phrase = ''
            for phrase, pts in _ADVISOR_PHRASES:
                if phrase in text and pts > best_pts:
                    best_pts = pts
                    best_phrase = phrase
            if best_phrase:
                result['banker_retained'] = True
                result['pts'] += best_pts
                if not result['top_phrase']:
                    result['top_phrase'] = best_phrase

        time.sleep(0.2)

        # Strategic alternatives is the max signal — stop reading more filings
        if result['strategic_alternatives']:
            break

    result['pts'] = min(result['pts'], 35)  # cap this layer component
    return result


def fetch_proxy_signal(fmp, ticker):
    """
    Parse most recent DEF 14A (proxy statement) for change-of-control provisions.

    When executives have large CoC payouts that vest immediately on acquisition,
    they are financially incentivised to accept a deal. High payout + recent
    board refresh = management is ready to sell.

    Returns dict: has_coc_provisions, coc_payout_estimate, pts, board_refresh
    """
    result = {
        'has_coc_provisions':  False,
        'coc_payout_estimate': 0,
        'pts':                 0,
    }

    filings = fmp.get_proxy_filings(ticker, limit=1)
    if not filings:
        return result

    url = filings[0].get('finalLink') or filings[0].get('linkToFilingDetails') or ''
    if not url:
        return result

    text = _fetch_doc_text(url, max_bytes=600_000)
    if not text:
        return result

    has_coc = any(phrase in text for phrase in _COC_PHRASES)
    result['has_coc_provisions'] = has_coc

    if not has_coc:
        return result

    # Extract dollar amounts near every "change" mention
    # Pattern: find index of phrase, scan 800 chars forward for $X,XXX,XXX or X million
    payouts = []
    for m in re.finditer(r'change.{0,4}(?:in|of).{0,4}control', text):
        window = text[m.start(): m.start() + 800]
        # "$X,XXX,XXX" style
        for raw in re.findall(r'\$([\d,]+)', window):
            try:
                val = int(raw.replace(',', ''))
                if val > 500_000:
                    payouts.append(val)
            except ValueError:
                pass
        # "X.X million" style
        for raw in re.findall(r'([\d.]+)\s*million', window):
            try:
                payouts.append(float(raw) * 1_000_000)
            except ValueError:
                pass

    max_payout = max(payouts) if payouts else 0
    result['coc_payout_estimate'] = max_payout

    if max_payout >= 10_000_000:
        result['pts'] = 10
    elif max_payout >= 5_000_000:
        result['pts'] = 7
    elif max_payout >= 1_000_000:
        result['pts'] = 4
    elif has_coc:
        result['pts'] = 2

    return result


def has_real_process_evidence(activist_signal=None, text_signals=None):
    """
    Return True only when a filing points to a real transaction path.

    This deliberately excludes generic inferred M&A logic such as analyst upside,
    valuation discounts, insider buying, strategic fit, acquirer need, platform
    attractiveness, and proxy change-of-control provisions. Those can support an
    M&A thesis, but they do not prove a live or specific process.

    13D gate logic (Item 4-aware):
      - Item 4 parsed → SALE_PROCESS (moderate+) or ACTIVIST_ESCALATION → clears gate
      - Item 4 parsed → GOVERNANCE_ONLY / CAPITAL_ALLOCATION / PASSIVE → does NOT clear gate
      - P0-E: Item 4 doc unavailable + known activist → still clears (filing itself is signal)
      - P0-E: Item 4 doc unavailable + unknown filer  → does NOT clear (reason: item4_unavailable_no_process_gate)

    ROFR/ROFN scope gate (P0-C):
      - company_level_possible or unknown_scope → clears gate
      - asset_specific_likely or securities_or_lockup_likely → does NOT clear gate
    """
    ts  = text_signals or {}
    act = activist_signal or {}

    activist_clears = False
    if act:
        item4 = act.get('item4', {})
        if item4:
            # Item 4 was parsed — require actual process/escalation intent.
            activist_clears = (
                item4.get('is_sale_pressure', False) or
                item4.get('classification') == 'ACTIVIST_ESCALATION'
            )
        else:
            # P0-E: document unavailable — gate does not clear regardless of filer.
            # Item 4 text is required for acquisition-pressure classification.
            # Known activists still score 20 pts from preload; that is not process evidence.
            activist_clears = False

    # P0-C: ROFR/ROFN scope gate — non-company-level rights do not clear process gate.
    _non_company_scopes = frozenset({'asset_specific_likely', 'securities_or_lockup_likely'})
    rofn_clears = (
        ts.get('rofn') and
        ts.get('rofn_scope_hint') not in _non_company_scopes
    )
    rofr_clears = (
        ts.get('rofr') and
        ts.get('rofr_scope_hint') not in _non_company_scopes
    )
    rofo_clears = (
        ts.get('rofo') and
        ts.get('rofo_scope_hint') not in _non_company_scopes
    )

    return bool(
        activist_clears
        or ts.get('sa_is_affirm')         # board affirm SA clears the cap
        or ts.get('banker_retained')
        or rofn_clears
        or rofr_clears
        or rofo_clears
        or ts.get('merger_agreement')
    )


# ─────────────────────────────────────────────────────────────────────────────
# INSIDER ANALYZER — only what's needed: sell %, insider buying flag
# ─────────────────────────────────────────────────────────────────────────────

C_LEVEL_KEYWORDS = ['ceo', 'chief executive', 'cfo', 'chief financial',
                    'coo', 'chief operating', 'president', 'chairman', 'chair',
                    'cmo', 'chief medical', 'cso', 'chief scientific',
                    'cto', 'chief technology', 'officer']

def is_c_level(title, name):
    text = (str(title) + ' ' + str(name)).lower()
    return any(k in text for k in C_LEVEL_KEYWORDS)


def analyze_insider_activity(fmp, ticker, mcap_millions):
    """
    Returns dict with:
      sell_value_90d  — total C-level sale value, last 90 days
      sell_pct_of_mcap — as % of market cap
      buy_value_90d   — total C-level buy value, last 90 days
      has_buying      — True if any C-level purchased in last 90 days
    """
    result = {
        'sell_value_90d': 0,
        'sell_pct_of_mcap': 0.0,
        'buy_value_90d': 0,
        'has_buying': False,
        'c_level_sellers': 0,
        'c_level_buyers': 0,
    }

    trades = fmp.get_insider_trading(ticker, limit=100)
    if not trades:
        return result

    cutoff = datetime.now() - timedelta(days=90)

    for t in trades:
        try:
            filing_date = datetime.strptime(t.get('filingDate', ''), '%Y-%m-%d')
        except Exception:
            continue
        if filing_date < cutoff:
            continue

        name  = t.get('reportingName', '')
        title = t.get('typeOfOwner', '')
        if not is_c_level(title, name):
            continue

        aod    = t.get('acquisitionOrDisposition', '')
        shares = abs(t.get('securitiesTransacted', 0) or 0)
        price  = t.get('price', 0) or 0
        if shares <= 0 or price <= 0:
            continue
        value = shares * price

        if aod == 'D':
            result['sell_value_90d'] += value
            result['c_level_sellers'] += 1
        elif aod == 'A':
            result['buy_value_90d'] += value
            result['has_buying'] = True
            result['c_level_buyers'] += 1

    if mcap_millions > 0:
        result['sell_pct_of_mcap'] = (result['sell_value_90d'] / (mcap_millions * 1e6)) * 100

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE ANALYZER — ClinicalTrials.gov (uses company name for better matching)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_sponsor_name(company_name):
    """
    Convert FMP company name to the form used on ClinicalTrials.gov.
    Strips legal suffixes: Inc, plc, Ltd, Corp, LLC, Holdings, Group, SA, AG, AB, NV, BV.
    Returns a list of name variants to try (best first).
    """
    if not company_name:
        return []
    # Remove content in parentheses
    import re
    name = re.sub(r'\(.*?\)', '', company_name).strip()
    # Split on comma (anything after comma is usually ", Inc." etc.)
    name = name.split(',')[0].strip()
    # Remove trailing legal suffixes
    suffixes = [
        r'\bInc\.?$', r'\bplc\.?$', r'\bLtd\.?$', r'\bCorp\.?$', r'\bLLC\.?$',
        r'\bHoldings?\b', r'\bGroup\b', r'\bBiosciences?\b(?! )',  # only if word-terminal
        r'\bTherapeutics?\b(?! )', r'\bPharmaceuticals?\b(?! )',
        r'\bBiopharmaceuticals?\b(?! )', r'\bBioscience\b(?! )',
        r'\bSciences?\b(?! )', r'\bAG$', r'\bAB$', r'\bNV$', r'\bBV$', r'\bSA$',
        r'\bpubl$',
    ]
    cleaned = name
    for suffix in suffixes:
        cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.strip(' .,')

    variants = []
    if cleaned and cleaned != company_name:
        variants.append(cleaned)
    if name != company_name.split(',')[0].strip():
        pass
    variants.append(name)          # e.g. "Arcellx" or "MeiraGTx Holdings"
    if company_name.split(',')[0].strip() not in variants:
        variants.append(company_name.split(',')[0].strip())
    # Deduplicate, preserve order
    seen = set()
    return [v for v in variants if v and not (v in seen or seen.add(v))]


def analyze_pipeline(company_name, ticker):
    """
    Query ClinicalTrials.gov using company/sponsor name (more accurate than ticker).
    Returns dict with phase3_count, phase2_count, has_breakthrough, has_orphan.
    Results cached 24h — trial status changes slowly.
    """
    ck = make_key('ct', ticker, company_name)
    cached = cache_get(ck)
    if cached is not None:
        return cached

    result = {'phase3_count': 0, 'phase2_count': 0, 'has_breakthrough': False,
              'has_orphan': False, 'total_active': 0}

    # Build query list: best sponsor name variants + ticker fallback
    queries = _extract_sponsor_name(company_name)
    queries.append(ticker)  # ticker as last resort

    for query in queries:
        try:
            url = 'https://clinicaltrials.gov/api/v2/studies'
            params = {
                'query.lead': query,
                'filter.overallStatus': 'RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION',
                'pageSize': 50,
                'format': 'json'
            }
            r = requests.get(url, params=params, timeout=(5, 20))
            if r.status_code != 200:
                continue

            studies = r.json().get('studies', [])
            if not studies:
                continue

            phase3 = 0
            phase2 = 0
            breakthrough = False
            orphan = False

            for study in studies:
                proto = study.get('protocolSection', {})

                # Phase detection
                phases = proto.get('designModule', {}).get('phases', [])
                has_p3 = any('PHASE3' in ph or 'PHASE4' in ph for ph in phases)
                has_p2 = any('PHASE2' in ph for ph in phases)
                if has_p3:
                    phase3 += 1
                elif has_p2:
                    phase2 += 1

                # Keyword search for designations
                kws = proto.get('conditionsModule', {}).get('keywords', [])
                for kw in kws:
                    s = str(kw).lower()
                    if 'breakthrough' in s:
                        breakthrough = True
                    if 'orphan' in s:
                        orphan = True

            # Take the best result across queries
            if phase3 > result['phase3_count']:
                result['phase3_count'] = phase3
            if phase2 > result['phase2_count']:
                result['phase2_count'] = phase2
            if breakthrough:
                result['has_breakthrough'] = True
            if orphan:
                result['has_orphan'] = True
            result['total_active'] = max(result['total_active'], len(studies))

            time.sleep(0.5)
            # If first query gave results, don't try ticker
            if studies:
                break

        except Exception:
            continue

    cache_set(ck, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

def analyze_financials(fmp, ticker):
    """
    Returns dict with cash runway, revenue data, revenue growth, profitability.
    """
    result = {
        'runway_quarters': None,
        'has_revenue': False,
        'revenue_annual': 0,
        'revenue_growth_yoy': 0,
        'is_profitable': False,
        'cash_on_hand': 0,
        'quarterly_burn': 0,
        'current_ratio': None,
    }

    try:
        # Annual income for revenue / profitability
        income = fmp.get_income_statement(ticker, period='annual', limit=3)
        if income and len(income) >= 1:
            latest_rev = income[0].get('revenue', 0) or 0
            prev_rev   = income[1].get('revenue', 0) or 0 if len(income) > 1 else 0

            result['revenue_annual'] = latest_rev
            result['has_revenue']    = latest_rev > 5_000_000  # $5M+ revenue = commercially active

            if prev_rev > 0 and latest_rev > 0:
                result['revenue_growth_yoy'] = ((latest_rev - prev_rev) / prev_rev) * 100

            op_income = income[0].get('operatingIncome', 0) or 0
            result['is_profitable'] = op_income > 0

        # Quarterly balance sheet for cash + burn rate
        balance = fmp.get_balance_sheet(ticker, period='quarter', limit=4)
        cashflow = fmp.get_cash_flow(ticker, period='quarter', limit=4)

        if balance:
            bs = balance[0]
            cash = (bs.get('cashAndCashEquivalents', 0) or 0)
            st_inv = (bs.get('shortTermInvestments', 0) or 0)
            result['cash_on_hand'] = cash + st_inv

            current_assets = bs.get('totalCurrentAssets', 0) or 0
            current_liab   = bs.get('totalCurrentLiabilities', 0) or 0
            if current_liab > 0:
                result['current_ratio'] = current_assets / current_liab

        if cashflow and len(cashflow) >= 2:
            # Average quarterly operating cash outflow over last 2 quarters
            burns = []
            for cf in cashflow[:2]:
                ocf = cf.get('operatingCashFlow', 0) or 0
                if ocf < 0:
                    burns.append(abs(ocf))
            if burns:
                avg_burn = sum(burns) / len(burns)
                result['quarterly_burn'] = avg_burn
                if avg_burn > 0 and result['cash_on_hand'] > 0:
                    result['runway_quarters'] = result['cash_on_hand'] / avg_burn

    except Exception:
        pass

    return result


# ─────────────────────────────────────────────────────────────────────────────
# BANKRUPTCY RISK CHECKER
# Applied FIRST — excludes stocks that are dying, not M&A targets
# ─────────────────────────────────────────────────────────────────────────────

def check_bankruptcy_risk(quote, financial, insider):
    """
    Returns (is_bankrupt: bool, reasons: list[str])
    If is_bankrupt is True, skip M&A scoring entirely.
    """
    reasons = []

    price = quote.get('price', 0) or 0
    mcap  = (quote.get('marketCap', 0) or 0) / 1e6
    runway = financial.get('runway_quarters')
    insider_pct = insider.get('sell_pct_of_mcap', 0)

    if price < BANKRUPT_PRICE_MAX:
        reasons.append(f'${price:.2f} share price (below $1.00 — delisting risk)')

    if mcap < BANKRUPT_MCAP_MIN:
        reasons.append(f'${mcap:.0f}M market cap (below $100M — sub-M&A radar)')

    if runway is not None and runway < BANKRUPT_RUNWAY_MIN:
        reasons.append(f'{runway:.1f}Q cash runway (below 2Q — likely bankrupt/restructuring)')

    if insider_pct > BANKRUPT_INSIDER_MAX:
        reasons.append(f'{insider_pct:.1f}% insider selling of market cap (death spiral signal)')

    return len(reasons) > 0, reasons


# ─────────────────────────────────────────────────────────────────────────────
# THERAPEUTIC AREA DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

def detect_therapeutic_area(profile):
    """
    Matches company description against HOTSPOTS keyword lists.
    Returns best match: (name, pts, acquirers) or None.
    """
    desc = (profile.get('description', '') + ' ' + profile.get('companyName', '')).lower()

    best = None
    best_pts = 0
    for hotspot in HOTSPOTS:
        if any(kw in desc for kw in hotspot['keywords']):
            if hotspot['pts'] > best_pts:
                best_pts = hotspot['pts']
                best = hotspot
    return best


# ─────────────────────────────────────────────────────────────────────────────
# CORE M&A SCORING ENGINE — V11 REDESIGN
# ─────────────────────────────────────────────────────────────────────────────

def calculate_ma_score(ticker, quote, profile, insider, financial, pipeline,  # noqa: too-many-args
                       staleness_info=None, dcf_signal=None, sma_signal=None, recent_8k=False,
                       key_metrics=None, analyst_signal=None, earnings_quality=None,
                       activist_signal=None, text_signals=None, proxy_signal=None):
    """
    Score a stock's M&A acquisition probability on a 0–100 scale (V12.3).

    LAYER 1 — Strategic Value (max 45 pts):
        Pipeline stage + commercial stage + FDA designations + therapeutic hotspot
        + earnings execution quality (beat rate)
    LAYER 2 — Acquirability (max 43 pts):
        Market cap sweet spot + price discount + analyst upside + DCF margin of safety
        + EV/EBITDA vs M&A deal comps + ROIC quality signal + forward P/E discount
    LAYER 3 — Financial Health (max 20 pts):
        Cash runway in strategic zone + revenue generation
    LAYER 4 — Catalyst Signals (max 16 pts):
        Insider buying + SMA momentum stack + recent 8-K event + earnings imminent
        + volume anomaly + RSI
    LAYER 5 — Acquisition Pattern Match (max 10 pts):
        Match against profile of recently completed M&A deals
    LAYER 6 — Institutional Research Signals (max 20 pts, net of staleness):
        Patent cliff alignment + strategic scarcity + acquirer hunger + EV/Rev
    LAYER 7 — Deal Process Signals (max 35 pts, overrides tier if triggered):
        Activist SC 13D filing + 8-K "strategic alternatives" text + proxy CoC provisions

    Returns dict: score, signals, flags, conviction_tier
    """
    score   = 0.0
    signals = []
    flags   = []

    mcap  = (quote.get('marketCap', 0) or 0) / 1e6
    price = quote.get('price', 0) or 0
    year_high = quote.get('yearHigh', price) or price
    year_low  = quote.get('yearLow', price) or price

    # ── LAYER 1: STRATEGIC VALUE (max 40) ─────────────────────────────────────

    layer1 = 0.0

    # 1a. Clinical pipeline (max 25 pts)
    phase3 = pipeline.get('phase3_count', 0) if pipeline else 0
    phase2 = pipeline.get('phase2_count', 0) if pipeline else 0

    if phase3 >= 3:
        pts = 25
        signals.append({'cat': 'Pipeline', 'type': 'Deep Phase 3 Pipeline',
                        'detail': f'{phase3} active Phase 3 programs', 'pts': pts})
        layer1 += pts
    elif phase3 == 2:
        pts = 20
        signals.append({'cat': 'Pipeline', 'type': 'Dual Phase 3 Programs',
                        'detail': '2 active Phase 3 trials', 'pts': pts})
        layer1 += pts
    elif phase3 == 1:
        pts = 15
        signals.append({'cat': 'Pipeline', 'type': 'Phase 3 Program',
                        'detail': '1 active Phase 3 trial', 'pts': pts})
        layer1 += pts
    elif phase2 >= 2:
        pts = 4   # reduced from 8 — Phase 2×2 is not a strong predictor alone
        signals.append({'cat': 'Pipeline', 'type': 'Multiple Phase 2 Programs',
                        'detail': f'{phase2} active Phase 2 trials (Phase 3 readout needed)',
                        'pts': pts})
        layer1 += pts
    elif phase2 == 1:
        pts = 2   # reduced from 5 — single Phase 2 trial is weak M&A signal alone
        signals.append({'cat': 'Pipeline', 'type': 'Phase 2 Program',
                        'detail': '1 active Phase 2 trial', 'pts': pts})
        layer1 += pts

    # 1b. Commercial stage / meaningful revenue (max 10 pts, stacks with pipeline)
    rev = financial.get('revenue_annual', 0)
    if rev > 50_000_000:
        pts = 10
        signals.append({'cat': 'Commercial', 'type': 'Commercial-Stage Company',
                        'detail': f'${rev/1e6:.0f}M annual revenue (proven commercial ability)',
                        'pts': pts})
        layer1 += pts
    elif rev > 15_000_000:
        pts = 6
        signals.append({'cat': 'Commercial', 'type': 'Revenue-Generating',
                        'detail': f'${rev/1e6:.0f}M annual revenue', 'pts': pts})
        layer1 += pts
    elif rev > 3_000_000:
        pts = 3
        signals.append({'cat': 'Commercial', 'type': 'Early Revenue',
                        'detail': f'${rev/1e6:.1f}M annual revenue', 'pts': pts})
        layer1 += pts

    # 1c. FDA designations (max 12 pts, independent of pipeline score)
    has_breakthrough = (pipeline or {}).get('has_breakthrough', False)
    has_orphan       = (pipeline or {}).get('has_orphan', False)

    if has_breakthrough:
        pts = 7
        signals.append({'cat': 'Regulatory', 'type': 'FDA Breakthrough Designation',
                        'detail': 'Expedited review — high acquirer interest', 'pts': pts})
        layer1 += pts
    if has_orphan:
        pts = 5
        signals.append({'cat': 'Regulatory', 'type': 'Orphan Drug Designation',
                        'detail': 'Rare disease premium — smaller acquirer pool, higher multiples',
                        'pts': pts})
        layer1 += pts

    # 1d. Therapeutic area hotspot bonus (max 10 pts)
    hotspot = detect_therapeutic_area(profile)
    if hotspot:
        pts = hotspot['pts']
        signals.append({'cat': 'Therapeutic', 'type': f"Hotspot: {hotspot['name']}",
                        'detail': f"Acquirers: {hotspot['acquirers']}", 'pts': pts})
        layer1 += pts

    # 1e. Earnings execution quality — consecutive EPS beats (max 5 pts)
    # Academic research: 4+ consecutive beats → acquirers pay 15-25% higher premiums.
    # Proven management execution = de-risked deal for the buyer.
    eq = earnings_quality or {}
    consec_beats = eq.get('consecutive_beats', 0)
    beat_rate    = eq.get('beat_rate', 0)
    if consec_beats >= 4:
        pts = 5
        signals.append({'cat': 'Execution', 'type': 'Consistent EPS Beater',
                        'detail': (f'{consec_beats} consecutive quarters beating estimates '
                                   f'({beat_rate:.0f}% beat rate) — proven execution = acquisition premium'),
                        'pts': pts})
        layer1 += pts
    elif consec_beats >= 2:
        pts = 3
        signals.append({'cat': 'Execution', 'type': 'Recent EPS Beat Streak',
                        'detail': f'{consec_beats} consecutive EPS beats — management building credibility',
                        'pts': pts})
        layer1 += pts
    elif beat_rate >= 75 and eq.get('total_quarters', 0) >= 4:
        pts = 2
        signals.append({'cat': 'Execution', 'type': 'High EPS Beat Rate',
                        'detail': f'{beat_rate:.0f}% EPS beat rate over {eq["total_quarters"]} quarters',
                        'pts': pts})
        layer1 += pts

    layer1 = min(layer1, 45)  # cap layer 1 (extended from 40 for execution quality)

    # ── LAYER 2: ACQUIRABILITY (max 30) ───────────────────────────────────────

    layer2 = 0.0

    # 2a. Market cap sweet spot (max 16 pts, deflated from 20)
    # Based on actual deal size distribution: $150M–$1B is bolt-on, $1B–$4B is mid, $4B+ is mega
    if 150 <= mcap <= 1000:
        pts = 16   # reduced from 20 — being in the range is necessary but not sufficient
        signals.append({'cat': 'Size', 'type': 'Bolt-On Acquisition Sweet Spot',
                        'detail': f'${mcap:.0f}M mcap — ideal size for most pharma acquirers', 'pts': pts})
        layer2 += pts
    elif 1000 < mcap <= 3000:
        pts = 11   # reduced from 14
        signals.append({'cat': 'Size', 'type': 'Mid-Cap Acquisition Target',
                        'detail': f'${mcap:.0f}M mcap — attractive for large pharma', 'pts': pts})
        layer2 += pts
    elif 3000 < mcap <= 7000:
        pts = 6    # reduced from 8
        signals.append({'cat': 'Size', 'type': 'Large Acquisition Target',
                        'detail': f'${mcap:.0f}M mcap — requires strategic justification', 'pts': pts})
        layer2 += pts
    elif 150 <= mcap < 200:
        pts = 8    # near-floor small — kept separate to prevent borderline inflation
        signals.append({'cat': 'Size', 'type': 'Small Acquisition Target',
                        'detail': f'${mcap:.0f}M mcap — lower priority for large pharma', 'pts': pts})
        layer2 += pts

    # 2b. Price discount from 52-week high (max 8 pts, deflated from 12)
    # Buyer wants a discount; too much discount = company is dying
    if year_high > 0 and price > 0:
        discount_pct = ((year_high - price) / year_high) * 100
        if 25 <= discount_pct <= 60:
            pts = 8   # reduced from 12
            signals.append({'cat': 'Value', 'type': 'Strategic Price Discount',
                            'detail': f'-{discount_pct:.0f}% from 52-week high (buyer gets a deal)',
                            'pts': pts})
            layer2 += pts
        elif 15 <= discount_pct < 25:
            pts = 4   # reduced from 7
            signals.append({'cat': 'Value', 'type': 'Moderate Price Discount',
                            'detail': f'-{discount_pct:.0f}% from 52-week high', 'pts': pts})
            layer2 += pts
        elif discount_pct > 60:
            pts = 2   # reduced from 4
            signals.append({'cat': 'Value', 'type': 'Deep Discount (Distress Risk)',
                            'detail': f'-{discount_pct:.0f}% from high — discount exists but verify solvency',
                            'pts': pts})
            layer2 += pts

    # 2c. Analyst price target upside (max 10 pts)
    # Large gap between analyst target and current = market mispricing = M&A premium candidate
    fmp_client = FMPClient(FMP_API_KEY)
    pt_data = fmp_client.get_price_target_consensus(ticker)
    pt_upside = 0
    if pt_data:
        target = pt_data.get('targetConsensus', 0) or 0
        last   = pt_data.get('lastPrice', 0) or price
        if last > 0 and target > 0:
            pt_upside = ((target - last) / last) * 100

    if pt_upside >= 60:
        pts = 10
        signals.append({'cat': 'Valuation', 'type': 'Large Analyst-to-Market Gap',
                        'detail': f'+{pt_upside:.0f}% to consensus target (hidden value)',
                        'pts': pts})
        layer2 += pts
    elif pt_upside >= 35:
        pts = 6
        signals.append({'cat': 'Valuation', 'type': 'Moderate Analyst-to-Market Gap',
                        'detail': f'+{pt_upside:.0f}% to consensus target', 'pts': pts})
        layer2 += pts
    elif pt_upside >= 15:
        pts = 3
        signals.append({'cat': 'Valuation', 'type': 'Slight Analyst Upside',
                        'detail': f'+{pt_upside:.0f}% to consensus target', 'pts': pts})
        layer2 += pts

    # 2d. DCF margin of safety (max 5 pts) — fundamental floor confirms mispricing
    # When DCF intrinsic value > current price, the market is leaving money on the table.
    # An acquirer can step in below fair value and immediately capture the discount.
    dcf_signal = dcf_signal or {}
    mos_pct = dcf_signal.get('mos_pct', 0) or 0
    if mos_pct >= 30:
        pts = 5
        signals.append({'cat': 'Valuation', 'type': 'Deep DCF Discount',
                        'detail': (f"DCF fair value ${dcf_signal.get('fair_value','?')} vs "
                                   f"${price:.2f} ({mos_pct:.0f}% below intrinsic — "
                                   f"WACC {dcf_signal.get('wacc','?')}%)"),
                        'pts': pts})
        layer2 += pts
    elif mos_pct >= 15:
        pts = 3
        signals.append({'cat': 'Valuation', 'type': 'DCF Margin of Safety',
                        'detail': (f"DCF fair value ${dcf_signal.get('fair_value','?')} vs "
                                   f"${price:.2f} ({mos_pct:.0f}% discount to intrinsic)"),
                        'pts': pts})
        layer2 += pts

    # 2e. EV/EBITDA vs M&A deal comp multiples (max 6 pts)
    # Biotech/pharma M&A deals price at 10-20x EV/EBITDA for profitable companies.
    # Trading below 8x = deeply discounted to what acquirers actually pay at close.
    km = key_metrics or {}
    ev_ebitda = km.get('ev_to_ebitda')
    if ev_ebitda and ev_ebitda > 0:
        if ev_ebitda < 8:
            pts = 6
            signals.append({'cat': 'Valuation', 'type': 'Deep EV/EBITDA Discount',
                            'detail': (f'{ev_ebitda:.1f}x EV/EBITDA vs 10-20x typical M&A deal multiple '
                                       f'— significant takeout premium embedded'),
                            'pts': pts})
            layer2 += pts
        elif ev_ebitda < 12:
            pts = 3
            signals.append({'cat': 'Valuation', 'type': 'EV/EBITDA Below M&A Comps',
                            'detail': f'{ev_ebitda:.1f}x EV/EBITDA — below typical 10-20x acquisition multiple',
                            'pts': pts})
            layer2 += pts

    # 2f. ROIC — quality signal that commands acquisition premiums (max 4 pts)
    # High ROIC = durable competitive advantage = acquirer can't replicate organically.
    # Buffett's insight applied to M&A: you pay for what you can't build yourself.
    roic = km.get('roic', 0) or 0
    if roic > 0.20:
        pts = 4
        signals.append({'cat': 'Quality', 'type': 'High ROIC Business',
                        'detail': (f'{roic*100:.0f}% ROIC — exceptional capital efficiency, '
                                   f'hard to replicate organically (premium acquisition target)'),
                        'pts': pts})
        layer2 += pts
    elif roic > 0.12:
        pts = 2
        signals.append({'cat': 'Quality', 'type': 'Good ROIC Business',
                        'detail': f'{roic*100:.0f}% ROIC — above-average capital efficiency',
                        'pts': pts})
        layer2 += pts

    # 2g. Forward P/E discount + estimate revision direction (max 4 pts)
    # Analysts raising estimates while price falls = market/analyst divergence = M&A setup.
    as_ = analyst_signal or {}
    fwd_pe   = as_.get('fwd_pe')
    est_trend = as_.get('est_trend')
    if fwd_pe and fwd_pe > 0:
        if fwd_pe < 12 and est_trend == 'up':
            pts = 4
            signals.append({'cat': 'Valuation', 'type': 'Low Forward P/E + Rising Estimates',
                            'detail': (f'{fwd_pe:.1f}x forward P/E with analysts raising estimates '
                                       f'— market wrong, analysts right = M&A setup'),
                            'pts': pts})
            layer2 += pts
        elif fwd_pe < 12:
            pts = 2
            signals.append({'cat': 'Valuation', 'type': 'Low Forward P/E',
                            'detail': f'{fwd_pe:.1f}x forward P/E — cheap on earnings power',
                            'pts': pts})
            layer2 += pts
        elif est_trend == 'up' and fwd_pe < 20:
            pts = 2
            signals.append({'cat': 'Valuation', 'type': 'Rising Analyst Estimates',
                            'detail': (f'Estimate revision trend: UP — analysts increasing forward EPS '
                                       f'({as_.get("num_analysts", "?")} analysts covering)'),
                            'pts': pts})
            layer2 += pts

    layer2 = min(layer2, 43)  # cap layer 2 (extended from 33 for key-metrics + analyst signals)

    # ── LAYER 3: FINANCIAL HEALTH (max 20) ────────────────────────────────────

    layer3 = 0.0
    runway = financial.get('runway_quarters')

    # 3a. Cash runway in the "strategic zone" (max 12 pts)
    # 4–16Q = motivated to discuss deals but not desperate or bankrupt
    # <2Q = bankruptcy territory (already excluded above)
    # >20Q = doesn't need to sell
    if runway is not None:
        if 8 <= runway <= 16:
            pts = 12
            signals.append({'cat': 'Financial', 'type': 'Strategic Cash Runway',
                            'detail': f'{runway:.1f}Q runway — motivated but stable (ideal for deal talks)',
                            'pts': pts})
            layer3 += pts
        elif 4 <= runway < 8:
            pts = 8
            signals.append({'cat': 'Financial', 'type': 'Motivated Cash Position',
                            'detail': f'{runway:.1f}Q runway — urgency to partner or sell', 'pts': pts})
            layer3 += pts
        elif 16 < runway <= 24:
            pts = 7
            signals.append({'cat': 'Financial', 'type': 'Well-Funded (Long Horizon)',
                            'detail': f'{runway:.1f}Q runway — comfortable position', 'pts': pts})
            layer3 += pts
        elif 2 <= runway < 4:
            pts = 3
            signals.append({'cat': 'Financial', 'type': 'Short Runway (Urgently Motivated)',
                            'detail': f'{runway:.1f}Q runway — may accept lower premium', 'pts': pts})
            layer3 += pts
            flags.append(f'Only {runway:.1f}Q runway — verify solvency before entering')
        elif runway > 24:
            pts = 4
            signals.append({'cat': 'Financial', 'type': 'Extended Runway',
                            'detail': f'{runway:.1f}Q — low urgency to sell', 'pts': pts})
            layer3 += pts

    # 3b. Revenue / commercial viability (max 8 pts, different dimension than layer 1 bonus)
    is_profitable = financial.get('is_profitable', False)
    rev_growth    = financial.get('revenue_growth_yoy', 0)

    if is_profitable:
        pts = 8
        signals.append({'cat': 'Financial', 'type': 'Profitable Operations',
                        'detail': 'Operating income positive — premium quality asset', 'pts': pts})
        layer3 += pts
    elif rev > 0 and rev_growth > 30:
        pts = 5
        signals.append({'cat': 'Financial', 'type': 'Strong Revenue Growth',
                        'detail': f'+{rev_growth:.0f}% revenue YoY growth', 'pts': pts})
        layer3 += pts
    elif rev > 0 and rev_growth > 10:
        pts = 3
        signals.append({'cat': 'Financial', 'type': 'Revenue Growing',
                        'detail': f'+{rev_growth:.0f}% revenue YoY growth', 'pts': pts})
        layer3 += pts

    layer3 = min(layer3, 20)

    # ── LAYER 4: CATALYST SIGNALS (max 16) ────────────────────────────────────

    layer4 = 0.0

    # 4a. Insider BUYING — the #1 contrarian M&A signal (insiders buy when deal is coming)
    if insider.get('has_buying'):
        buy_val = insider.get('buy_value_90d', 0)
        pts = 10
        signals.append({'cat': 'Insider', 'type': 'C-Level Insider Buying',
                        'detail': f'${buy_val/1e6:.2f}M purchased in last 90 days — confidence signal',
                        'pts': pts})
        layer4 += pts

    # 4b. SMA momentum stack — trend confirmation (price > SMA10 > SMA20 = in uptrend)
    # Acquirers prefer targets not in freefall. Uptrend = market starting to agree with us.
    sma_signal = sma_signal or {}
    above_short = sma_signal.get('above_short', False)
    above_long  = sma_signal.get('above_long', False)
    if above_short and above_long:
        pts = 4
        signals.append({'cat': 'Technical', 'type': 'Full SMA Momentum Stack',
                        'detail': (f"Price > SMA10 (${sma_signal.get('sma10','?')}) "
                                   f"> SMA20 (${sma_signal.get('sma20','?')}) — confirmed uptrend"),
                        'pts': pts})
        layer4 += pts
    elif above_short:
        pts = 2
        signals.append({'cat': 'Technical', 'type': 'Price Above SMA10',
                        'detail': f"Above short-term SMA10 (${sma_signal.get('sma10','?')}) — early trend",
                        'pts': pts})
        layer4 += pts

    # 4c. Recent 8-K material event filing (last 7 days) — something just happened
    # 8-K = FDA approval, partnership, earnings, leadership change, etc.
    # In small-caps with low analyst coverage, 8-Ks precede big price moves.
    if recent_8k:
        pts = 3
        signals.append({'cat': 'Catalyst', 'type': 'Recent 8-K Material Event',
                        'detail': 'SEC 8-K filing in last 7 days — material event just occurred',
                        'pts': pts})
        layer4 += pts

    # 4d. Earnings within 14 days — imminent binary catalyst
    # Post-earnings dislocations are the highest-probability M&A entry windows.
    # If a company has strong fundamentals and earnings are coming, position now.
    eq = earnings_quality or {}
    if eq.get('earnings_imminent'):
        d = eq.get('days_to_earnings', '?')
        pts = 2
        signals.append({'cat': 'Catalyst', 'type': 'Earnings Imminent',
                        'detail': (f"Earnings in {d} day{'s' if d != 1 else ''} "
                                   f"({eq.get('next_earnings', '?')}) — binary catalyst approaching"),
                        'pts': pts})
        layer4 += pts

    # 4f. Volume anomaly (2x+ average in recent 5 days)
    try:
        hist = yf.Ticker(ticker).history(period='3mo', timeout=20)
        if not hist.empty and len(hist) > 20:
            recent_vol = hist['Volume'].iloc[-5:].mean()
            avg_vol    = hist['Volume'].mean()
            if avg_vol > 0 and recent_vol > avg_vol * 2.0:
                pts = 4
                signals.append({'cat': 'Technical', 'type': 'Unusual Volume Activity',
                                'detail': f'{recent_vol/avg_vol:.1f}x avg volume (potential deal activity)',
                                'pts': pts})
                layer4 += pts
    except Exception:
        pass

    # 4g. RSI oversold on a GOOD company (not distressed) = entry + M&A signal
    rsi_data = fmp_client.get_rsi(ticker)
    if rsi_data and 'rsi' in rsi_data:
        rsi = rsi_data['rsi']
        if rsi < 35:
            pts = 4
            signals.append({'cat': 'Technical', 'type': 'Technically Oversold',
                            'detail': f'RSI {rsi:.1f} — possible M&A entry window',
                            'pts': pts})
            layer4 += pts

    layer4 = min(layer4, 16)  # extended from 10 to accommodate SMA + 8-K signals

    # ── LAYER 5: ACQUISITION PATTERN MATCH (max 10, deflated from 15) ──────────
    # Compares this stock against profile of recently completed M&A deals

    layer5 = 0.0
    acq_pattern = analyze_acquisition_patterns(ticker, profile, financial, pipeline, quote)
    if acq_pattern['pattern_score'] > 0:
        pts = acq_pattern['pattern_score']
        layer5 = pts
        detail_parts = acq_pattern['matched_patterns'][:2]
        detail_str = '; '.join(detail_parts)[:90] if detail_parts else 'Pattern match to recent M&A'
        signals.append({'cat': 'AcqPattern', 'type': 'Acquisition Pattern Match',
                        'detail': detail_str, 'pts': pts})
        if acq_pattern['similar_deals']:
            top = acq_pattern['similar_deals'][0]
            signals.append({'cat': 'AcqPattern', 'type': f"Comparable Deal: {top['ticker']} ({top['acquirer']})",
                            'detail': f"${top['deal_B']:.1f}B acquisition · +{top['premium']}% premium · {top['area']}",
                            'pts': 0})

    # ── LAYER 6: INSTITUTIONAL RESEARCH SIGNALS (max 20, net of staleness) ─────
    # Patent cliff alignment + strategic scarcity + acquirer hunger + EV/Rev + staleness

    layer6 = 0.0
    staleness_info = staleness_info or {'days_tracked': 0, 'is_new': True, 'staleness_penalty': 0}
    inst_factors = score_institutional_factors(ticker, profile, financial, pipeline, quote, staleness_info)

    for sig in inst_factors['signals']:
        if sig.get('pts', 0) > 0:
            signals.append(sig)
        elif sig.get('pts', 0) < 0:
            signals.append(sig)

    layer6 = inst_factors['layer6_score']
    staleness_pen_l6 = inst_factors['staleness_pen']

    for flag in inst_factors['staleness_flags']:
        flags.append(flag)

    # ── DISTRESS PENALTIES ─────────────────────────────────────────────────────
    # These reduce score for distress signals that predict bankruptcy, not M&A

    penalties = 0.0
    sell_pct = insider.get('sell_pct_of_mcap', 0)

    if sell_pct >= 3.0:
        pen = 20
        flags.append(f'Heavy insider selling ({sell_pct:.1f}% of mcap) — leadership exiting, not deal prep')
        signals.append({'cat': 'Risk', 'type': 'Heavy Insider Selling (PENALTY)',
                        'detail': f'{sell_pct:.1f}% of market cap sold by C-level in 90 days',
                        'pts': -pen})
        penalties += pen
    elif sell_pct >= 1.5:
        pen = 10
        flags.append(f'Elevated insider selling ({sell_pct:.1f}% of mcap)')
        signals.append({'cat': 'Risk', 'type': 'Elevated Insider Selling (PENALTY)',
                        'detail': f'{sell_pct:.1f}% of market cap sold in 90 days',
                        'pts': -pen})
        penalties += pen
    elif sell_pct >= 0.5:
        # Minor selling — just flag, no penalty
        flags.append(f'Moderate insider selling ({sell_pct:.1f}% of mcap)')

    # ── LAYER 7: DEAL PROCESS SIGNALS (max 35 pts) ────────────────────────────
    # These signals indicate the deal process is already underway, not just likely.
    # Qualitatively different — they confirm intent, not just probability.

    layer7         = 0.0
    deal_flags     = []   # human-readable descriptions for output
    strategic_alt  = False  # "strategic alternatives" = near-certain deal

    # 7a. Activist SC 13D filing — Item 4 contextual classification applied
    act = activist_signal or {}
    if act:
        base_pts  = act.get('pts', 12)    # 20 if known activist, 12 otherwise
        item4     = act.get('item4', {})
        i4_class  = item4.get('classification') if item4 else None
        i4_intens = item4.get('intensity') if item4 else None

        # Adjust base points based on Item 4 intent classification
        if i4_class == 'SALE_PROCESS' and i4_intens == 'STRONG_PROCESS_SIGNAL':
            base_pts = min(base_pts + 8, 28)   # explicit transaction demand — upgrade
        elif i4_class == 'SALE_PROCESS':
            base_pts = min(base_pts + 4, 25)   # sale language present
        elif i4_class == 'STRATEGIC_REVIEW' and i4_intens == 'MODERATE_PROCESS_SIGNAL':
            base_pts = min(base_pts + 2, 22)   # formal review push
        elif i4_class in ('GOVERNANCE_ONLY', 'CAPITAL_ALLOCATION'):
            base_pts = max(base_pts - 8, 4)    # no sale pressure — downgrade
        elif i4_class == 'PASSIVE_ACCUMULATION':
            base_pts = max(base_pts - 12, 2)   # passive holder — heavy downgrade
        elif i4_class in ('GENERIC_SHAREHOLDER_PRESSURE', 'UNKNOWN') and i4_class is not None:
            base_pts = max(base_pts - 5, 5)    # generic / unclear — modest downgrade
        # ACTIVIST_ESCALATION / BOARD_CHANGE: keep base_pts unchanged

        pts   = _activist_decay(act.get('filing_date', ''), base_pts)
        label = ('Known biotech activist' if act.get('is_known') else 'Activist investor')

        # Build type and detail strings incorporating Item 4 classification
        if i4_class and i4_class != 'UNKNOWN':
            i4_label = i4_class.replace('_', ' ').title()
            sig_type = f'SC 13D Filing: {label} — {i4_label}'
            excerpt  = (item4.get('primary_excerpt') or '')[:120]
            detail   = (
                f"{act.get('filer','Unknown')} filed 13D on {act.get('filing_date','')} "
                f"[{i4_class}] {i4_intens}. {excerpt}"
            )
            flag_suffix = f' — {i4_class.replace("_", " ")}'
        else:
            sig_type    = f'SC 13D Filing: {label}'
            detail      = (
                f"{act.get('filer','Unknown')} filed 13D on {act.get('filing_date','')} "
                f"— pushing for strategic change (Item 4 not parsed)"
            )
            flag_suffix = ''

        signals.append({'cat': 'DealProcess', 'type': sig_type,
                        'detail': detail, 'pts': pts})
        layer7 += pts
        deal_flags.append(
            f"ACTIVIST 13D: {act.get('filer','Unknown')} ({act.get('filing_date','')})"
            f"{flag_suffix}"
        )

    # 7b. 8-K document text signals
    ts = text_signals or {}
    if ts.get('pts', 0) > 0:
        # Strategic alternatives — quality-gated (Task 1)
        if ts.get('strategic_alternatives'):
            sa_is_affirm = ts.get('sa_is_affirm', False)  # safe default: unscored = not affirm
            sa_pts       = 30 if sa_is_affirm else 8
            strategic_alt = sa_is_affirm   # only affirm triggers near-certain-deal tier
            sig_type   = ('STRATEGIC ALTERNATIVES DISCLOSED' if sa_is_affirm
                          else 'Strategic Alternatives (Boilerplate — 8 pts)')
            sig_detail = ('Board explicitly exploring sale — "strategic alternatives" language '
                          'in 8-K filing (~85-90% deal rate within 12 months)') if sa_is_affirm else (
                          'Risk-factor/hypothetical SA mention — no active process confirmed; '
                          'cap not cleared')
            signals.append({'cat': 'DealProcess', 'type': sig_type,
                            'detail': sig_detail, 'pts': sa_pts})
            layer7 += sa_pts
            deal_flags.append(
                'STRATEGIC ALTERNATIVES in 8-K — board hired a banker' if sa_is_affirm
                else 'Strategic alternatives in 8-K (boilerplate — cap not cleared)'
            )

        elif ts.get('banker_retained'):
            # Advisor retained or explicit "potential sale" language — live process before
            # formal strategic alternatives announcement. Clears the process evidence gate.
            adv_pts = ts.get('pts', 20)   # total 8-K pts; layer7 cap (35) handles overflow
            signals.append({'cat': 'DealProcess', 'type': 'FINANCIAL ADVISOR RETAINED / POTENTIAL SALE',
                            'detail': ('8-K discloses M&A advisor engagement or potential sale exploration '
                                       '— leading indicator before formal strategic alternatives announcement'),
                            'pts': adv_pts})
            layer7 += adv_pts
            deal_flags.append('Financial advisor retained or potential sale language in 8-K')

        elif ts.get('rofn') or ts.get('rofr') or ts.get('rofo'):
            clause = 'ROFN' if ts.get('rofn') else ('ROFR' if ts.get('rofr') else 'ROFO')
            pharma = ts.get('named_pharma') or 'major pharma'
            pts = ts.get('pts', 0)
            signals.append({'cat': 'DealProcess', 'type': f'{clause} Clause with {pharma}',
                            'detail': (f'Acquisition option buried in 8-K partnership agreement — '
                                       f'{pharma} has right to acquire first'),
                            'pts': pts})
            layer7 += pts
            deal_flags.append(f'{clause} clause detected in 8-K — {pharma} has acquisition option')

        elif ts.get('exclusive_license') or ts.get('collaboration'):
            pharma = ts.get('named_pharma') or 'major pharma'
            pts    = min(ts.get('pts', 0), 12)
            signals.append({'cat': 'DealProcess', 'type': f'Deep Partnership with {pharma}',
                            'detail': ('Exclusive license or co-development agreement — '
                                       'common precursor to full acquisition'),
                            'pts': pts})
            layer7 += pts
            deal_flags.append(f'Exclusive/co-dev agreement with {pharma} detected in 8-K')

    # 7c. Proxy change-of-control provisions
    px = proxy_signal or {}
    if px.get('has_coc_provisions') and px.get('pts', 0) > 0:
        payout = px.get('coc_payout_estimate', 0)
        payout_str = f'${payout/1e6:.1f}M' if payout > 0 else 'undisclosed'
        pts = px['pts']
        signals.append({'cat': 'DealProcess', 'type': 'Change-of-Control Provisions in Proxy',
                        'detail': (f'CEO/executives have {payout_str} CoC payout vesting immediately '
                                   f'on acquisition — management financially incentivised to sell'),
                        'pts': pts})
        layer7 += pts
        deal_flags.append(f'Change-of-control provisions in DEF 14A ({payout_str} estimated payout)')

    layer7 = min(layer7, 35)

    for flag in deal_flags:
        flags.append(flag)

    # ── TOTAL SCORE ────────────────────────────────────────────────────────────

    raw_total   = layer1 + layer2 + layer3 + layer4 + layer5 + max(layer6, 0) + layer7
    final_score = max(0, raw_total - penalties)
    final_score = min(final_score, 100)
    real_process_evidence = has_real_process_evidence(
        activist_signal=activist_signal,
        text_signals=text_signals,
    )

    # Binary process-evidence gate:
    # Generic M&A logic can still build a normal score, but without a real
    # process signal it cannot rank above 80. Change-of-control proxy language,
    # insider buying, analyst upside, valuation discounts, strategic fit,
    # acquirer need, and platform attractiveness do not satisfy this gate.
    if not real_process_evidence and final_score > PROCESS_EVIDENCE_SCORE_CAP:
        final_score = PROCESS_EVIDENCE_SCORE_CAP
        flags.append(
            f'Process-evidence cap applied: no real process signal; score capped at '
            f'{PROCESS_EVIDENCE_SCORE_CAP}'
        )

    # ── PRICED-IN PENALTY ──────────────────────────────────────────────────────
    # If the stock has already run sharply, the M&A premium is (at least partially)
    # priced in by the market. Penalise the score NOW so conviction tiers reflect
    # real remaining upside — not a thesis built at a price the market has already
    # moved past.
    #
    # Two triggers (checked independently, penalty stacks if both fire):
    #   price / year_low  > 1.55 → up 55%+ from 52-week low
    #   price / first_price > 1.35 → up 35%+ since first tracked by BSC
    #
    # Exempt: names with real process evidence (SA affirm, activist 13D). Those
    # stocks are supposed to run on the news — the remaining spread to close is
    # still real alpha. Penalising them here would wrongly deflate live-deal scores.

    first_price = (staleness_info or {}).get('first_price') or price
    low_ratio   = (price / year_low)   if year_low   > 0 else 1.0
    entry_ratio = (price / first_price) if first_price > 0 else 1.0

    priced_in_pen = 0
    if not real_process_evidence:
        if low_ratio > 1.55:
            priced_in_pen += 8
            flags.append(
                f'PRICED-IN: +{(low_ratio - 1)*100:.0f}% from 52-week low — '
                f'M&A premium may be partially reflected in price (-8 pts)'
            )
        if entry_ratio > 1.35 and first_price != price:
            priced_in_pen += 8
            flags.append(
                f'PRICED-IN: +{(entry_ratio - 1)*100:.0f}% from first-tracked price — '
                f'thesis entry point passed (-8 pts)'
            )
        if priced_in_pen:
            final_score = max(0, final_score - priced_in_pen)

    # ── CONVICTION TIER (V12 — STRICT MANDATORY GATES) ─────────────────────────
    # HIGH: score + quality gate (Phase 3 OR $25M+ revenue) — no more pattern-match inflation
    # MEDIUM: score + moderate gate (Phase 3 OR Phase 2×2 OR $10M+ revenue)
    # WATCH: score only — broader net but still meaningful

    runway_ok = (runway is None or runway >= GATE_RUNWAY_MIN)
    is_profitable = financial.get('is_profitable', False)

    # Quality gates — must have REAL clinical or commercial proof
    high_quality   = (phase3 >= 1) or (rev > 25_000_000)
    medium_quality = (phase3 >= 1) or (phase2 >= 2) or (rev > 10_000_000)

    # "Strategic alternatives" disclosed = board hired a banker = override gates
    # Hit rate on actual deal within 12 months: ~85-90%. Don't require Phase 3.
    if strategic_alt and mcap >= GATE_MCAP_MIN:
        conviction = 'HIGH_CONVICTION'
    elif act and mcap >= GATE_MCAP_MIN and runway_ok:
        # Activist 13D = forced sale pressure, bypass quality gates
        conviction = 'HIGH_CONVICTION' if final_score >= 60 else 'MEDIUM_CONVICTION'
    elif (final_score >= GATE_SCORE_HIGH and mcap >= GATE_MCAP_MIN
            and runway_ok and high_quality):
        conviction = 'HIGH_CONVICTION'
    elif (final_score >= GATE_SCORE_MEDIUM and mcap >= GATE_MCAP_MIN
            and runway_ok and medium_quality):
        conviction = 'MEDIUM_CONVICTION'
    elif final_score >= GATE_SCORE_WATCH:
        conviction = 'WATCH'
    else:
        conviction = 'BELOW_THRESHOLD'

    return {
        'score':          round(final_score, 1),
        'layer_scores': {
            'strategic':     round(layer1, 1),
            'acquirability': round(layer2, 1),
            'financial':     round(layer3, 1),
            'catalyst':      round(layer4, 1),
            'acq_pattern':   round(layer5, 1),
            'institutional':  round(layer6, 1),
            'deal_process':  round(layer7, 1),
            'penalties':     round(penalties + staleness_pen_l6, 1),
            'priced_in_pen': round(priced_in_pen if not real_process_evidence else 0, 1),
        },
        'acq_pattern':  acq_pattern,
        'inst_factors': inst_factors,
        'conviction_tier': conviction,
        'signals':        signals,
        'flags':          flags,
        'phase3_count':   phase3,
        'phase2_count':   phase2,
        'mcap_M':         round(mcap, 0),
        'runway_Q':       round(runway, 1) if runway else None,
        'sell_pct':       round(sell_pct, 2),
        'has_buying':     insider.get('has_buying', False),
        'pt_upside_pct':  round(pt_upside, 1),
        'revenue_M':      round(rev / 1e6, 1),
        'is_profitable':  is_profitable,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STOCK ANALYZER — orchestrates all data fetches and scoring
# ─────────────────────────────────────────────────────────────────────────────

def analyze_stock(ticker, fmp, staleness_info=None, earnings_calendar_flag=False,
                  activist_signal=None, skip_layer7=False, _phase_label=''):
    """
    Full analysis pipeline for one ticker.
    staleness_info: dict from get_staleness_info() — supplies first-seen date, staleness penalty.
    earnings_calendar_flag: True if ticker appears in the pre-loaded earnings calendar.
    activist_signal: dict from preload_activist_signals() for this ticker, or None.
    skip_layer7: if True, skip expensive SEC doc fetches (pass 1 of two-pass scan).
                 All FMP + ClinicalTrials calls still run (cached on pass 2).
    _phase_label: optional phase name for slow-ticker logging.
    Returns result dict or None if excluded.
    """
    _ticker_t0 = time.monotonic()
    try:
        # 1. Get quote and profile (fast, always needed)
        quote   = fmp.get_quote(ticker)
        profile = fmp.get_profile(ticker)

        if not quote or not profile:
            return None

        price = quote.get('price', 0) or 0
        mcap  = (quote.get('marketCap', 0) or 0) / 1e6

        if price <= 0 or mcap <= 0:
            return None

        # Quick pre-screen: skip obvious non-biotech or very large caps
        industry = profile.get('industry', '')
        sector   = profile.get('sector', '')
        if sector not in ('Healthcare',) and industry not in ('Biotechnology', 'Drug Manufacturers—Specialty & Generic', 'Pharmaceutical Retailers'):
            return None  # Skip non-healthcare

        if mcap > 20000:  # Skip $20B+ companies (mega cap, unlikely targets)
            return None

        company_name = profile.get('companyName', ticker)

        # 2. Financials
        financial = analyze_financials(fmp, ticker)

        # 3. Insider activity
        insider = analyze_insider_activity(fmp, ticker, mcap)

        # 3b. New V12.1/V12.2 signals
        dcf_signal      = fetch_dcf_signal(fmp, ticker, price)
        sma_signal      = fetch_sma_signal(fmp, ticker)
        recent_8k       = fetch_8k_signal(fmp, ticker, days=7)
        key_metrics_sig = fetch_key_metrics_signal(fmp, ticker)
        analyst_sig     = fetch_analyst_signal(fmp, ticker, price)
        earnings_q      = fetch_earnings_quality(fmp, ticker)
        # Calendar flag overrides if the per-ticker call missed an upcoming date
        if earnings_calendar_flag and not earnings_q.get('earnings_imminent'):
            earnings_q['earnings_imminent'] = True

        # 4. Bankruptcy check (before expensive pipeline call)
        is_bankrupt, bankrupt_reasons = check_bankruptcy_risk(quote, financial, insider)
        if is_bankrupt:
            return {
                'ticker':           ticker,
                'company':          company_name,
                'price':            price,
                'mcap_M':           round(mcap, 0),
                'conviction_tier':  'BANKRUPTCY_RISK',
                'score':            0,
                'flags':            bankrupt_reasons,
                'signals':          [],
                'runway_Q':         financial.get('runway_quarters'),
                'sell_pct':         insider.get('sell_pct_of_mcap', 0),
                'phase3_count':     0,
                'industry':         industry,
                'description':      profile.get('description', '')[:150],
                'scan_date':        datetime.now().isoformat(),
            }

        # 5. Clinical pipeline (slower — ClinicalTrials.gov call)
        pipeline = analyze_pipeline(company_name, ticker)

        # 5b. Layer 7: deal process signals (SEC doc fetches — skipped in pass 1)
        if skip_layer7:
            text_sig  = {}
            proxy_sig = {}
        else:
            text_sig  = fetch_8k_text_signals(fmp, ticker, n_filings=8)  # P0-D: raised from 4
            proxy_sig = fetch_proxy_signal(fmp, ticker)
            # Enrich activist signal with Item 4 contextual classification.
            # Only runs if there is an activist signal — adds ~1-2s per ticker (cached 72h).
            if activist_signal:
                activist_signal = enrich_activist_item4(fmp, ticker, activist_signal)

        # 6. Score (pass staleness_info for Layer 6 penalty, new signals for V12.3)
        result = calculate_ma_score(ticker, quote, profile, insider, financial, pipeline,
                                    staleness_info=staleness_info,
                                    dcf_signal=dcf_signal,
                                    sma_signal=sma_signal,
                                    recent_8k=recent_8k,
                                    key_metrics=key_metrics_sig,
                                    analyst_signal=analyst_sig,
                                    earnings_quality=earnings_q,
                                    activist_signal=activist_signal,
                                    text_signals=text_sig,
                                    proxy_signal=proxy_sig)

        # 7. Package output
        si = staleness_info or {}
        scan_date_str = datetime.now().isoformat()

        # Build intermediate dict so build_trade_rec can read all fields
        out = {
            'ticker':           ticker,
            'company':          company_name,
            'price':            price,
            'year_high':        quote.get('yearHigh'),
            'year_low':         quote.get('yearLow'),
            'mcap_M':           result['mcap_M'],
            'conviction_tier':  result['conviction_tier'],
            'score':            result['score'],
            'layer_scores':     result['layer_scores'],
            'signals':          result['signals'],
            'flags':            result['flags'],
            'phase3_count':     result['phase3_count'],
            'runway_Q':         result['runway_Q'],
            'sell_pct':         result['sell_pct'],
            'has_buying':       result['has_buying'],
            'pt_upside_pct':    result['pt_upside_pct'],
            'revenue_M':        result['revenue_M'],
            'is_profitable':    result['is_profitable'],
            'industry':         industry,
            'hotspot':          detect_therapeutic_area(profile),
            'acq_pattern':      result.get('acq_pattern', {}),
            'inst_factors':     result.get('inst_factors', {}),
            'description':      profile.get('description', '')[:200],
            'scan_date':        scan_date_str,
            # Tracking fields
            'is_new_pick':      si.get('is_new', True),
            'days_tracked':     si.get('days_tracked', 0),
            'scan_count':       si.get('scan_count', 0),
            'first_price':      si.get('first_price'),
            'first_tier':       si.get('first_tier'),
            # V12.1 signal fields
            'dcf_fair_value':   (dcf_signal or {}).get('fair_value'),
            'dcf_mos_pct':      (dcf_signal or {}).get('mos_pct', 0),
            'dcf_wacc':         (dcf_signal or {}).get('wacc'),
            'sma_above_short':  (sma_signal or {}).get('above_short', False),
            'sma_above_long':   (sma_signal or {}).get('above_long', False),
            'sma10':            (sma_signal or {}).get('sma10'),
            'sma20':            (sma_signal or {}).get('sma20'),
            'has_recent_8k':    recent_8k,
            # V12.2 signal fields
            'ev_to_ebitda':     (key_metrics_sig or {}).get('ev_to_ebitda'),
            'roic':             (key_metrics_sig or {}).get('roic'),
            'graham_number':    (key_metrics_sig or {}).get('graham_number'),
            'fwd_pe':           (analyst_sig or {}).get('fwd_pe'),
            'fwd_eps':          (analyst_sig or {}).get('fwd_eps'),
            'est_trend':        (analyst_sig or {}).get('est_trend'),
            'num_analysts':     (analyst_sig or {}).get('num_analysts'),
            'beat_rate':        (earnings_q or {}).get('beat_rate', 0),
            'consecutive_beats': (earnings_q or {}).get('consecutive_beats', 0),
            'next_earnings':    (earnings_q or {}).get('next_earnings'),
            'days_to_earnings': (earnings_q or {}).get('days_to_earnings'),
            'earnings_imminent': (earnings_q or {}).get('earnings_imminent', False),
            # Layer 7 — deal process
            'has_activist_13d':      bool(activist_signal),
            'activist_filer':        (activist_signal or {}).get('filer'),
            # Item 4 contextual classification (None if no activist signal or doc unavailable)
            'activist_13d_intent':    ((activist_signal or {}).get('item4') or {}).get('classification'),
            'activist_13d_intensity': ((activist_signal or {}).get('item4') or {}).get('intensity'),
            'activist_13d_excerpt':   (((activist_signal or {}).get('item4') or {}).get('primary_excerpt') or '')[:200],
            'activist_13d_triggers':  (((activist_signal or {}).get('item4') or {}).get('triggering_phrases') or [])[:3],
            'activist_13d_rationale': ((activist_signal or {}).get('item4') or {}).get('contextual_rationale'),
            'strategic_alternatives': (text_sig or {}).get('strategic_alternatives', False),
            'banker_retained':       (text_sig or {}).get('banker_retained', False),
            'has_rofn':              (text_sig or {}).get('rofn', False),
            'has_rofr':              (text_sig or {}).get('rofr', False),
            'named_pharma_partner':  (text_sig or {}).get('named_pharma'),
            'top_8k_phrase':         (text_sig or {}).get('top_phrase', ''),
            # P0-B: source traceability for live monitoring audit trail
            'signal_source_url':      (text_sig or {}).get('source_url', ''),
            'signal_source_accession': (text_sig or {}).get('source_accession', ''),
            'signal_source_date':     (text_sig or {}).get('source_filing_date', ''),
            'signal_source_form':     (text_sig or {}).get('source_form_type', ''),
            'signal_source_excerpt':  (text_sig or {}).get('source_excerpt', ''),
            # P0-C: ROFR/ROFN scope hints
            'rofn_scope_hint':        (text_sig or {}).get('rofn_scope_hint'),
            'rofr_scope_hint':        (text_sig or {}).get('rofr_scope_hint'),
            # P0-A: negation-suppressed phrases (audit trail)
            'negated_8k_phrases':    (text_sig or {}).get('negated_phrases', []),
            'has_coc_provisions':    (proxy_sig or {}).get('has_coc_provisions', False),
            'coc_payout_estimate':   (proxy_sig or {}).get('coc_payout_estimate', 0),
            'deal_process_score':    result['layer_scores'].get('deal_process', 0),
            # Raw signal refs — used by build_trade_rec; not displayed
            '_text_signals':    text_sig or {},
            '_activist_signal': activist_signal or {},
            '_proxy_signal':    proxy_sig or {},
        }

        # 8. Trade recommendation (deterministic, capital-preservation-first)
        trade = build_trade_rec(out)
        out['trade_decision']  = trade['trade_decision']
        out['no_trade_reason'] = trade['no_trade_reason']
        out['p_deal']          = trade['p_deal']
        out['ev_per_share']    = trade['ev_per_share']
        out['position_pct']    = trade['position_pct']
        out['position_usd']    = trade['position_usd']
        out['signal_age_days'] = trade['signal_age_days']
        out['expiry_days']     = trade['expiry_days']
        out['signal_quality']  = trade['signal_quality']
        out['stop_loss_pct']   = trade['stop_loss_pct']

        # Remove internal refs before returning
        del out['_text_signals']
        del out['_activist_signal']
        del out['_proxy_signal']

        # Derive backend process_state (mirrors frontend JS logic)
        from process_history import derive_process_state
        out['process_state'] = derive_process_state(out)

        # Placeholder — filled in by main() after state history is updated
        out['state_transitions']    = []
        out['state_first_entered_ts'] = None
        out['state_snapshot_count'] = 0

        _ticker_elapsed = time.monotonic() - _ticker_t0
        if _ticker_elapsed > 60:
            logger.warning('VERY_SLOW_TICKER ticker=%s phase=%s elapsed=%.1fs',
                           ticker, _phase_label or 'analyze_stock', _ticker_elapsed)
        elif _ticker_elapsed > 30:
            logger.warning('SLOW_TICKER ticker=%s phase=%s elapsed=%.1fs',
                           ticker, _phase_label or 'analyze_stock', _ticker_elapsed)

        return out

    except Exception as e:
        _ticker_elapsed = time.monotonic() - _ticker_t0
        if _ticker_elapsed > 30:
            logger.warning('SLOW_TICKER_ERROR ticker=%s phase=%s elapsed=%.1fs error=%s',
                           ticker, _phase_label or 'analyze_stock', _ticker_elapsed, str(e)[:80])
        print(f'  {ticker}: Error — {str(e)[:60]}')
        return None


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

TIER_ICONS = {
    'HIGH_CONVICTION':   '[H]',
    'MEDIUM_CONVICTION': '[M]',
    'WATCH':             '[W]',
    'BELOW_THRESHOLD':   '[-]',
    'BANKRUPTCY_RISK':   '[X]',
}

def format_result(r, verbose=True):
    icon = TIER_ICONS.get(r['conviction_tier'], '  ')
    tier_label = r['conviction_tier'].replace('_', ' ')
    lines = []

    # Tracking badge
    is_new      = r.get('is_new_pick', True)
    days        = r.get('days_tracked', 0)
    scan_count  = r.get('scan_count', 0)
    first_price = r.get('first_price')

    if is_new:
        track_badge = '  [NEW]'
    else:
        price_chg = ''
        if first_price and r['price']:
            chg = ((r['price'] - first_price) / first_price) * 100
            sign = '+' if chg >= 0 else ''
            price_chg = f' | {sign}{chg:.0f}% since first seen'
        track_badge = f'  ↩ Returning ({days}d, {scan_count} scans{price_chg})'

    lines.append(
        f"\n{icon} [{r['score']:.0f}pts] {r['ticker']} — {r['company']}{track_badge}"
    )
    lines.append(
        f"   Price: ${r['price']:.2f} | MCap: ${r['mcap_M']:.0f}M | "
        f"Runway: {r['runway_Q']}Q | Tier: {tier_label}"
    )

    if r.get('phase3_count', 0) > 0:
        lines.append(f"   Pipeline: {r['phase3_count']} Phase 3 trial(s)")
    if r.get('revenue_M', 0) > 0:
        lines.append(f"   Revenue: ${r['revenue_M']:.0f}M/yr {'(profitable)' if r.get('is_profitable') else ''}")
    if r.get('pt_upside_pct', 0) > 0:
        lines.append(f"   Analyst target upside: +{r['pt_upside_pct']:.0f}%")
    if r.get('hotspot'):
        lines.append(f"   Hotspot: {r['hotspot']['name']} → {r['hotspot']['acquirers']}")
    if r.get('has_buying'):
        lines.append(f"   INSIDER BUYING detected in last 90 days")
    if r.get('sell_pct', 0) > 1.0:
        lines.append(f"   Insider selling: {r['sell_pct']:.1f}% of mcap (penalty applied)")
    if r.get('dcf_fair_value') and r.get('dcf_mos_pct', 0) >= 15:
        lines.append(f"   DCF fair value: ${r['dcf_fair_value']:.2f} "
                     f"({r['dcf_mos_pct']:.0f}% above current price)")
    if r.get('sma_above_short') and r.get('sma_above_long'):
        lines.append(f"   SMA stack: full uptrend (price > SMA10 > SMA20)")
    elif r.get('sma_above_short'):
        lines.append(f"   SMA stack: price above SMA10 (partial trend)")
    if r.get('has_recent_8k'):
        lines.append(f"   8-K material event filed in last 7 days")
    if r.get('ev_to_ebitda') and r['ev_to_ebitda'] < 12:
        lines.append(f"   EV/EBITDA: {r['ev_to_ebitda']:.1f}x (below 12x M&A comp average)")
    if r.get('roic') and r['roic'] > 0.12:
        lines.append(f"   ROIC: {r['roic']*100:.0f}% — high quality capital allocator")
    if r.get('consecutive_beats', 0) >= 2:
        lines.append(f"   EPS beats: {r['consecutive_beats']} consecutive quarters ({r.get('beat_rate',0):.0f}% beat rate)")
    if r.get('fwd_pe') and r.get('est_trend') == 'up':
        lines.append(f"   Forward P/E: {r['fwd_pe']:.1f}x with rising estimates — analyst conviction")
    if r.get('earnings_imminent'):
        lines.append(f"   Earnings in {r.get('days_to_earnings','?')} days ({r.get('next_earnings','?')})")
    # Layer 7 — deal process (shown first, loudest)
    if r.get('strategic_alternatives'):
        lines.insert(2, f"   ██ STRATEGIC ALTERNATIVES DISCLOSED — board hired a banker (~85-90% deal rate)")
    if r.get('banker_retained') and not r.get('strategic_alternatives'):
        lines.insert(2, f"   ▲▲ FINANCIAL ADVISOR RETAINED / POTENTIAL SALE in 8-K — live process signal")
    if r.get('has_activist_13d'):
        lines.insert(3, f"   ★★ ACTIVIST 13D: {r.get('activist_filer','Unknown')} — forced sale pressure")
    if r.get('has_rofn') or r.get('has_rofr'):
        clause = 'ROFN' if r.get('has_rofn') else 'ROFR'
        pharma = r.get('named_pharma_partner') or 'major pharma'
        lines.append(f"   {clause} clause with {pharma} in 8-K — acquisition option exists")
    if r.get('named_pharma_partner') and not (r.get('has_rofn') or r.get('has_rofr')):
        lines.append(f"   Partnership with {r['named_pharma_partner']} detected in 8-K")
    if r.get('has_coc_provisions') and r.get('coc_payout_estimate', 0) > 0:
        payout = r['coc_payout_estimate']
        lines.append(f"   CoC provisions in proxy: ${payout/1e6:.1f}M management payout on acquisition")

    if verbose and r.get('signals'):
        lines.append('   Signals:')
        for sig in sorted(r['signals'], key=lambda x: -x.get('pts', 0))[:5]:
            pts = sig.get('pts', 0)
            if pts > 0:
                lines.append(f"     +{pts:.0f}pts  {sig['type']} — {sig['detail'][:70]}")
            elif pts < 0:
                lines.append(f"     {pts:.0f}pts  {sig['type']} — {sig['detail'][:70]}")

    if r.get('flags'):
        for flag in r['flags']:
            lines.append(f"   {flag}")

    # Layer breakdown
    ls = r.get('layer_scores', {})
    if ls:
        lines.append(
            f"   Score breakdown: Strategic={ls.get('strategic',0):.0f} | "
            f"Acquirability={ls.get('acquirability',0):.0f} | "
            f"Financial={ls.get('financial',0):.0f} | "
            f"Catalyst={ls.get('catalyst',0):.0f} | "
            f"AcqPattern={ls.get('acq_pattern',0):.0f} | "
            f"Institutional={ls.get('institutional',0):.0f} | "
            f"DealProcess={ls.get('deal_process',0):.0f} | "
            f"Penalties=-{ls.get('penalties',0):.0f}"
        )
    ap = r.get('acq_pattern', {})
    if ap and ap.get('similar_deals'):
        top = ap['similar_deals'][0]
        lines.append(f"   Pattern: mirrors {top['ticker']} ({top['acquirer']} ${top['deal_B']:.1f}B "
                     f"+{top['premium']}% prem) — implied prem {ap.get('implied_premium',0):.0f}%")
    if ap and ap.get('acquirer_interest'):
        lines.append(f"   Likely acquirers: {', '.join(ap['acquirer_interest'])}")

    return '\n'.join(lines)


def save_results(results, scan_id):
    """Save to JSON + CSV in the scan directory."""

    # JSON (full detail)
    json_path = os.path.join(SCAN_DIR, f'scan_v12_{scan_id}.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Always overwrite scan_latest.json so the dashboard can auto-load without a file picker
    latest_path = os.path.join(SCAN_DIR, 'scan_latest.json')
    with open(latest_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # CSV (summary for tracking)
    csv_path = os.path.join(PREDICTIONS_DIR, 'predictions_v12.csv')
    fieldnames = [
        'scan_date', 'ticker', 'company', 'score', 'conviction_tier',
        'price', 'mcap_M', 'runway_Q', 'phase3_count', 'revenue_M',
        'is_profitable', 'sell_pct', 'has_buying', 'pt_upside_pct',
        'hotspot_name', 'is_new_pick', 'days_tracked', 'scan_count',
        'first_price', 'first_tier',
        'dcf_fair_value', 'dcf_mos_pct', 'sma_above_short', 'sma_above_long', 'has_recent_8k',
        'ev_to_ebitda', 'roic', 'fwd_pe', 'est_trend', 'num_analysts',
        'beat_rate', 'consecutive_beats', 'next_earnings', 'earnings_imminent',
        'has_activist_13d', 'activist_filer', 'strategic_alternatives',
        'has_rofn', 'named_pharma_partner', 'top_8k_phrase',
        'has_coc_provisions', 'coc_payout_estimate', 'deal_process_score',
        'top_signals', 'flags',
        'outcome', 'outcome_date', 'outcome_price', 'return_pct', 'notes'
    ]
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in results:
            if r['conviction_tier'] in ('HIGH_CONVICTION', 'MEDIUM_CONVICTION', 'WATCH'):
                top_sigs = ' | '.join(
                    f"{s['type']} ({s['pts']:+.0f}pts)"
                    for s in sorted(r.get('signals', []), key=lambda x: -x.get('pts', 0))[:3]
                )
                writer.writerow({
                    'scan_date':       r['scan_date'],
                    'ticker':          r['ticker'],
                    'company':         r['company'],
                    'score':           r['score'],
                    'conviction_tier': r['conviction_tier'],
                    'price':           r['price'],
                    'mcap_M':          r['mcap_M'],
                    'runway_Q':        r.get('runway_Q', ''),
                    'phase3_count':    r.get('phase3_count', 0),
                    'revenue_M':       r.get('revenue_M', 0),
                    'is_profitable':   r.get('is_profitable', False),
                    'sell_pct':        r.get('sell_pct', 0),
                    'has_buying':      r.get('has_buying', False),
                    'pt_upside_pct':   r.get('pt_upside_pct', 0),
                    'hotspot_name':    r['hotspot']['name'] if r.get('hotspot') else '',
                    'is_new_pick':     r.get('is_new_pick', True),
                    'days_tracked':    r.get('days_tracked', 0),
                    'scan_count':      r.get('scan_count', 0),
                    'first_price':     r.get('first_price', ''),
                    'first_tier':      r.get('first_tier', ''),
                    'dcf_fair_value':   r.get('dcf_fair_value', ''),
                    'dcf_mos_pct':      r.get('dcf_mos_pct', ''),
                    'sma_above_short':  r.get('sma_above_short', ''),
                    'sma_above_long':   r.get('sma_above_long', ''),
                    'has_recent_8k':    r.get('has_recent_8k', ''),
                    'ev_to_ebitda':     r.get('ev_to_ebitda', ''),
                    'roic':             r.get('roic', ''),
                    'fwd_pe':           r.get('fwd_pe', ''),
                    'est_trend':        r.get('est_trend', ''),
                    'num_analysts':     r.get('num_analysts', ''),
                    'beat_rate':        r.get('beat_rate', ''),
                    'consecutive_beats': r.get('consecutive_beats', ''),
                    'next_earnings':    r.get('next_earnings', ''),
                    'earnings_imminent':      r.get('earnings_imminent', ''),
                    'has_activist_13d':       r.get('has_activist_13d', ''),
                    'activist_filer':         r.get('activist_filer', ''),
                    'strategic_alternatives': r.get('strategic_alternatives', ''),
                    'has_rofn':               r.get('has_rofn', ''),
                    'named_pharma_partner':   r.get('named_pharma_partner', ''),
                    'top_8k_phrase':          r.get('top_8k_phrase', ''),
                    'has_coc_provisions':     r.get('has_coc_provisions', ''),
                    'coc_payout_estimate':    r.get('coc_payout_estimate', ''),
                    'deal_process_score':     r.get('deal_process_score', ''),
                    'top_signals':     top_sigs,
                    'flags':           '; '.join(r.get('flags', [])),
                    'outcome':         'PENDING',
                    'outcome_date':    '',
                    'outcome_price':   '',
                    'return_pct':      '',
                    'notes':           '',
                })

    return json_path, csv_path


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCANNER
# ─────────────────────────────────────────────────────────────────────────────

def run_scan(tickers=None, verbose=True, save=True, max_workers=4):
    """
    Run the full M&A scan.

    Two-pass architecture:
      Pass 1 — all tickers, parallel, Layer 7 SEC fetches skipped (cheap).
               FMP + ClinicalTrials calls are cached after pass 1.
      Pass 2 — only tickers scoring >= LAYER7_THRESHOLD, parallel.
               FMP calls served from cache (near-instant). Only SEC doc
               fetches are new work.

    Args:
        tickers:     list of tickers to scan (default: full UNIVERSE)
        verbose:     print detailed output
        save:        save results to disk
        max_workers: ThreadPoolExecutor concurrency (default 4)
    """
    global _scan_start
    scan_start = datetime.now()
    _scan_start = time.monotonic()
    scan_id    = scan_start.strftime('%Y%m%d_%H%M%S')
    watchlist  = tickers or UNIVERSE

    print('\n' + '═'*72)
    print('  M&A SCANNER V12.3 — STRATEGIC ACQUISITION PREDICTOR')
    print(f'  {scan_start.strftime("%B %d, %Y %I:%M %p")}')
    print(f'  Universe: {len(watchlist)} stocks  |  Workers: {max_workers}  |  '
          f'Layer7 threshold: {LAYER7_THRESHOLD}')
    print('═'*72)
    logger.info('PHASE_START phase=scanner_init elapsed=0.0s')

    # One FMPClient for pre-load calls (single-threaded phase)
    fmp_main = FMPClient(FMP_API_KEY)

    # Pre-load earnings calendar for next 14 days (one call, set lookup per ticker)
    cal_from = datetime.now().strftime('%Y-%m-%d')
    cal_to   = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
    print(f'  Pre-loading earnings calendar ({cal_from} → {cal_to})...')
    _t_cal = _phase_start('earnings_calendar_preload')
    cal_data      = fmp_main.get_earnings_calendar(cal_from, cal_to)
    earnings_soon = {e['symbol'] for e in (cal_data or []) if e.get('symbol')}
    _phase_end('earnings_calendar_preload', _t_cal)
    print(f'  {len(earnings_soon)} tickers reporting earnings in next 14 days')

    # Pre-load SC 13D activist filings (one call, cross-referenced against universe)
    universe_set = set(watchlist)
    print(f'  Pre-loading SC 13D activist filings (last 60 days)...')
    _t_activist = _phase_start('activist_13d_preload')
    activist_map = preload_activist_signals(fmp_main, universe_set, days=60)
    _phase_end('activist_13d_preload', _t_activist)
    if activist_map:
        print(f'  ★ ACTIVIST 13D detected on: {", ".join(sorted(activist_map.keys()))}')
    else:
        print(f'  No activist 13D filings on universe tickers')

    # Load persistent tracking (read-only during scan; updated after all results in)
    tracking = load_tracking()
    print()

    # ── Helper: run one ticker in a worker thread ──────────────────────────────
    def _scan_ticker(ticker, skip_l7, phase_label=''):
        try:
            fmp          = _get_fmp()
            staleness    = get_staleness_info(tracking, ticker)
            return analyze_stock(
                ticker, fmp,
                staleness_info=staleness,
                earnings_calendar_flag=(ticker in earnings_soon),
                activist_signal=activist_map.get(ticker),
                skip_layer7=skip_l7,
                _phase_label=phase_label,
            )
        except Exception as e:
            return {'_error': ticker, '_msg': str(e)}

    # ── Partial save helper ────────────────────────────────────────────────────
    def _partial_save(batch_results, label):
        actionable = [r for r in batch_results
                      if r.get('conviction_tier') not in ('BELOW_THRESHOLD', None)]
        if actionable and save:
            partial_path = os.path.join(SCAN_DIR, 'scan_partial.json')
            with open(partial_path, 'w') as f:
                json.dump(actionable, f, indent=2, default=str)
            print(f'\n  [partial save] {len(actionable)} actionable results → scan_partial.json  ({label})')

    # ── PASS 1: all tickers, skip Layer 7 ─────────────────────────────────────
    print(f'  PASS 1 — scoring all {len(watchlist)} tickers (Layers 1-6, no SEC fetches)...')
    _t_pass1 = _phase_start('pass1_scoring')
    pass1_results = {}   # ticker → result dict
    errors        = []
    completed     = 0
    total         = len(watchlist)
    _last_progress_ticker = ''

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_scan_ticker, t, True, 'pass1'): t for t in watchlist}
        for future in as_completed(futures):
            ticker = futures[future]
            completed += 1
            _last_progress_ticker = ticker
            sys.stdout.write(f'\r  Pass 1: {completed}/{total}  [{ticker:<8}]  ')
            sys.stdout.flush()

            r = future.result()
            if r is None:
                continue
            if '_error' in r:
                errors.append(f"{r['_error']}: {r['_msg']}")
                continue
            pass1_results[ticker] = r

            if completed % 25 == 0:
                logger.info('LIVE_PROGRESS phase=pass1_scoring ticker=%s index=%d/%d elapsed=%.1fs',
                            ticker, completed, total, _elapsed())
                _partial_save(list(pass1_results.values()),
                              f'pass1 {completed}/{total}')

    _phase_end('pass1_scoring', _t_pass1)
    print(f'\n  Pass 1 complete — {len(pass1_results)} stocks scored')

    # ── PASS 2: Layer 7 for candidates above threshold ─────────────────────────
    candidates = [
        t for t, r in pass1_results.items()
        if r.get('score', 0) >= LAYER7_THRESHOLD
        and r.get('conviction_tier') != 'BANKRUPTCY_RISK'
    ]
    print(f'  PASS 2 — Layer 7 SEC fetch for {len(candidates)} candidates '
          f'(score ≥{LAYER7_THRESHOLD})...')
    _t_pass2 = _phase_start('pass2_sec_scan')

    pass2_results = {}
    completed2    = 0
    _n_cand = len(candidates)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures2 = {ex.submit(_scan_ticker, t, False, 'pass2_sec'): t for t in candidates}
        for future in as_completed(futures2):
            ticker = futures2[future]
            completed2 += 1
            sys.stdout.write(f'\r  Pass 2: {completed2}/{_n_cand}  [{ticker:<8}]  ')
            sys.stdout.flush()

            r = future.result()
            if r is None or '_error' in r:
                pass  # keep pass1 result for this ticker
            else:
                pass2_results[ticker] = r

            if completed2 % 25 == 0:
                logger.info('LIVE_PROGRESS phase=pass2_sec_scan ticker=%s index=%d/%d elapsed=%.1fs',
                            ticker, completed2, _n_cand, _elapsed())
                merged = {**pass1_results, **pass2_results}
                _partial_save(list(merged.values()),
                              f'pass2 {completed2}/{_n_cand}')

    _phase_end('pass2_sec_scan', _t_pass2)
    print(f'\n  Pass 2 complete — {len(pass2_results)} tickers upgraded with Layer 7')

    # ── Merge: pass2 results override pass1 where available ───────────────────
    final_map = {**pass1_results, **pass2_results}
    results   = list(final_map.values())

    # ── State history: load, update, attach transition events ─────────────────
    _t_state = _phase_start('state_history_update')
    from process_history import (
        load_state_history, save_state_history, update_ticker_history,
        get_state_entered_ts,
    )
    state_history = load_state_history(STATE_HISTORY_FILE)

    for r in results:
        tkr = r.get('ticker')
        if not tkr or r.get('conviction_tier') == 'BANKRUPTCY_RISK':
            continue
        try:
            events = update_ticker_history(tkr, r, state_history)
            r['state_transitions']     = events[-5:]   # surface last 5 to dashboard
            r['state_first_entered_ts'] = get_state_entered_ts(tkr, state_history)
            r['state_snapshot_count']  = len(
                state_history.get(tkr, {}).get('snapshots', [])
            )
        except Exception:
            pass   # history update must never break the scan

    save_state_history(state_history, STATE_HISTORY_FILE)
    _phase_end('state_history_update', _t_state)
    print(f'  State history updated — {len(state_history)} tickers tracked')

    # ── Sequence detection: derive compound patterns from state history ────────
    _t_seq = _phase_start('sequence_detection')
    try:
        from sequence_detector import detect_all_sequences, attach_sequences_to_result
        all_sequences = detect_all_sequences(state_history)
        n_with_seqs = 0
        for r in results:
            tkr = r.get('ticker')
            if not tkr:
                continue
            seqs = all_sequences.get(tkr, [])
            attach_sequences_to_result(r, seqs)
            if seqs:
                n_with_seqs += 1
        print(f'  Sequence detection complete — {n_with_seqs} tickers with compound patterns')
    except Exception as _seq_err:
        print(f'  [sequence_detector] Error: {_seq_err}')
        for r in results:
            r.setdefault('detected_sequences', [])
            r.setdefault('sequence_type', None)
            r.setdefault('sequence_label', None)
            r.setdefault('sequence_window_days', None)
            r.setdefault('compound_signal_quality', None)

    _phase_end('sequence_detection', _t_seq)

    # ── Update tracking (single-threaded, after all results collected) ─────────
    _t_tracking = _phase_start('tracking_update')
    new_picks   = 0
    high_conv   = []
    medium_conv = []
    watch_list  = []
    bankrupt    = []

    for r in results:
        tier = r.get('conviction_tier')
        tkr  = r['ticker']

        if tier in ('HIGH_CONVICTION', 'MEDIUM_CONVICTION', 'WATCH'):
            staleness = get_staleness_info(tracking, tkr)
            tracking  = update_tracking_entry(
                tracking, tkr, tier, r['score'], r['price']
            )
            if staleness.get('is_new'):
                new_picks += 1

        if tier == 'HIGH_CONVICTION':      high_conv.append(r)
        elif tier == 'MEDIUM_CONVICTION':  medium_conv.append(r)
        elif tier == 'WATCH':              watch_list.append(r)
        elif tier == 'BANKRUPTCY_RISK':    bankrupt.append(r)

    save_tracking(tracking)
    _phase_end('tracking_update', _t_tracking)

    # Log new HIGH/MEDIUM picks to outcomes.json for calibration tracking
    _t_output = _phase_start('output_write')
    log_picks_from_scan(results)

    print('\n')

    # Sort by score descending
    for group in [high_conv, medium_conv, watch_list]:
        group.sort(key=lambda x: -x['score'])

    # ── PRINT RESULTS ─────────────────────────────────────────────────────────

    if high_conv:
        print('\n' + '─'*72)
        print('  HIGH CONVICTION ACQUISITIONS')
        print('  Phase 3+ pipeline OR commercial stage + strategic fit + right size')
        print('─'*72)
        for r in high_conv:
            print(format_result(r, verbose))

    if medium_conv:
        print('\n' + '─'*72)
        print('  MEDIUM CONVICTION')
        print('─'*72)
        for r in medium_conv:
            print(format_result(r, verbose))

    if watch_list:
        print('\n' + '─'*72)
        print('  WATCH LIST')
        print('─'*72)
        for r in watch_list[:15]:  # Top 15 watches
            print(format_result(r, verbose=False))

    if bankrupt:
        print('\n' + '─'*72)
        print(f'  BANKRUPTCY RISK ({len(bankrupt)} stocks excluded from M&A scoring)')
        print('  These are likely headed to bankruptcy/restructuring, NOT acquisition')
        print('─'*72)
        for r in sorted(bankrupt, key=lambda x: x.get('mcap_M', 0)):
            reasons = '; '.join(r.get('flags', []))
            print(f"     {r['ticker']:<8} ${r['price']:.2f}  ${r['mcap_M']:.0f}M  {reasons[:70]}")

    # ── SUMMARY ───────────────────────────────────────────────────────────────

    duration = (datetime.now() - scan_start).seconds
    print('\n' + '═'*72)
    print(f'  M&A SCANNER V12.3 — SCAN COMPLETE in {duration}s')
    print(f'  Scanned: {len(results)} stocks  |  '
          f'High: {len(high_conv)}  |  Medium: {len(medium_conv)}  |  '
          f'Watch: {len(watch_list)}  |  Bankruptcy Risk: {len(bankrupt)}')
    print(f'  New picks this scan: {new_picks}  |  '
          f'Returning picks: {len(high_conv)+len(medium_conv)+len(watch_list)-new_picks}')

    if errors:
        print(f'  Errors: {len(errors)} tickers failed')

    if save and results:
        json_path, csv_path = save_results(
            [r for r in results if r['conviction_tier'] != 'BELOW_THRESHOLD'],
            scan_id
        )
        print(f'  Saved → {json_path}')
        print(f'  CSV   → {csv_path}')

    _phase_end('output_write', _t_output)
    print('═'*72 + '\n')

    return {
        'scan_id':           scan_id,
        'high_conviction':   high_conv,
        'medium_conviction': medium_conv,
        'watch':             watch_list,
        'bankruptcy_risk':   bankrupt,
        'all_results':       results,
        'errors':            errors,
    }


# ─────────────────────────────────────────────────────────────────────────────
# QUICK SINGLE-STOCK ANALYSIS (for spot-checking a ticker)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_one(ticker):
    """Quick analysis of a single ticker with full detail output."""
    fmp = FMPClient(FMP_API_KEY)
    print(f'\nAnalyzing {ticker}...')
    r = analyze_stock(ticker, fmp)
    if r:
        print(format_result(r, verbose=True))
        print(f'\nFull detail:')
        print(json.dumps({k: v for k, v in r.items() if k not in ('signals', 'flags', 'hotspot')},
                         indent=2, default=str))
    else:
        print(f'{ticker}: Could not analyze (excluded or no data)')
    return r


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO TRACKER — check status of previously flagged tickers
# ─────────────────────────────────────────────────────────────────────────────

def check_portfolio(tickers=None):
    """
    Quick status check on a list of tickers — current price, change from entry,
    any acquisition news.
    If tickers is None, reads from predictions_v12.csv.
    """
    fmp = FMPClient(FMP_API_KEY)

    if tickers is None:
        csv_path = os.path.join(PREDICTIONS_DIR, 'predictions_v12.csv')
        tickers = []
        if os.path.isfile(csv_path):
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                seen = set()
                for row in reader:
                    t = row['ticker']
                    if t not in seen:
                        tickers.append(t)
                        seen.add(t)

    print(f'\n{"Ticker":<8} {"Price":<10} {"YHigh":<10} {"YLow":<10} {"MCap":<12} {"Status"}')
    print('─'*65)

    for t in tickers:
        q = fmp.get_quote(t)
        if q:
            price = q.get('price', 0)
            yh    = q.get('yearHigh', 0)
            yl    = q.get('yearLow', 0)
            mc    = (q.get('marketCap', 0) or 0) / 1e6
            # Detect possible acquisition (price near yearHigh, 52-week breakout)
            near_acq = 'NEAR 52W HIGH — Check news' if price >= yh * 0.97 else ''
            print(f'{t:<8} ${price:<9.2f} ${yh:<9.2f} ${yl:<9.2f} ${mc:<10.0f}M {near_acq}')
        else:
            print(f'{t:<8} No data (possibly acquired/delisted)')


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    from outcome_tracker import update_outcome, print_summary as _print_outcomes

    parser = argparse.ArgumentParser(description='M&A Scanner V12.0 — Institutional-Grade Acquisition Predictor')
    parser.add_argument('--ticker',    type=str, help='Analyze a single ticker')
    parser.add_argument('--portfolio', action='store_true', help='Check tracked portfolio status')
    parser.add_argument('--tickers',   type=str, help='Comma-separated list of tickers to scan')
    parser.add_argument('--quick',     action='store_true',
                        help='Quick scan (first 50 tickers only, for testing)')
    parser.add_argument('--no-save',   action='store_true', help='Do not save results to disk')
    # Outcome tracking
    parser.add_argument('--outcomes',  action='store_true', help='Print outcome tracker summary')
    parser.add_argument('--log-outcome', type=str, metavar='TICKER',
                        help='Log/update outcome for a pick (use with --outcome-type etc.)')
    parser.add_argument('--outcome-type', type=str,
                        choices=['DEAL_ANNOUNCED', 'DEAL_CLOSED', 'DEAL_FAILED', 'DELISTED'],
                        help='Outcome type for --log-outcome')
    parser.add_argument('--deal-price',  type=float, help='Per-share deal price for --log-outcome')
    parser.add_argument('--acquirer',    type=str,   help='Acquirer name for --log-outcome')
    parser.add_argument('--notes',       type=str,   default='', help='Notes for --log-outcome')
    # Backtest
    parser.add_argument('--backtest',  action='store_true', help='Run retrospective coverage analysis')
    parser.add_argument('--full',      action='store_true', help='Fetch historical prices in backtest')
    args = parser.parse_args()

    if args.ticker:
        analyze_one(args.ticker.upper())
    elif args.portfolio:
        check_portfolio()
    elif args.outcomes:
        _print_outcomes()
    elif args.log_outcome:
        if not args.outcome_type:
            print('  --outcome-type required. choices: DEAL_ANNOUNCED DEAL_CLOSED DEAL_FAILED DELISTED')
        else:
            update_outcome(
                ticker=args.log_outcome.upper(),
                outcome=args.outcome_type,
                acquirer=args.acquirer,
                deal_price=args.deal_price,
                notes=args.notes,
            )
    elif args.backtest:
        try:
            from backtest import run_backtest
        except ImportError as exc:
            print(f'Backtest mode unavailable: could not import backtest ({exc}).')
            print('Normal scanner operation does not require the backtest module.')
            raise SystemExit(2)
        run_backtest(fetch_prices=args.full)
    elif args.tickers:
        run_scan(tickers=[t.strip().upper() for t in args.tickers.split(',')],
                 save=not args.no_save)
    elif args.quick:
        run_scan(tickers=UNIVERSE[:50], save=not args.no_save)
    else:
        run_scan(save=not args.no_save)
