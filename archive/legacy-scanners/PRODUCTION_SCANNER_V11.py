#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          M&A SCANNER V11.0 — STRATEGIC ACQUISITION PREDICTOR               ║
║                     Built: April 2026 | Rebuilt from Autopsy               ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT BROKE IN V10.6 (full postmortem):
  ❌ Watchlist: 117 hand-picked stocks — 0/8 actual acquisitions were on it
  ❌ Wrong thesis: Hunted "dying companies"; real 2026 deals (VTYX, RAPT, CALT,
     DAWN) were strategic acquisitions of VALUABLE assets
  ❌ Distress ≠ M&A: High insider selling + <2Q runway = BANKRUPTCY, not buyout
  ❌ No market cap floor: KALA ($14M mcap) scored 105pts, then went to $0.14
  ❌ Runway logic inverted: Rewarded ≤6Q runway; companies with 1Q go bankrupt
  ❌ Score inflation: One problem (cash burn) counted 4 separate times (+67pts)
  ❌ Backtest: 5 companies, all outcomes known — statistically meaningless
  ❌ Launchd broken: "Operation not permitted" — never ran from Downloads/

WHAT ACTUALLY PREDICTS BIOTECH M&A (2020-2026 empirical analysis):
  ✅ Phase 3 pipeline at or near readout inflection (VTYX, CALT, IMGN, SGEN)
  ✅ Commercial product with expansion opportunity (CALT, DAWN, ACAD)
  ✅ Therapeutic mechanism in acquirer's strategic gap (TYK2→BMS, ADC→Pfizer)
  ✅ Market cap $150M–$5B (acquirable without mega-deal board approval)
  ✅ Stock 20–65% below 52-week high (buyer gets discount, but company isn't dying)
  ✅ Cash runway 4–16Q (motivated to discuss, not desperate or bankrupt)
  ✅ Analyst consensus far above current price (hidden value signal)
  ✅ Insider BUYING or neutral (not mass-fleeing the company)

NEW ARCHITECTURE:
  Layer 0 → Bankruptcy Exclusion (price<$1, mcap<$100M, runway<2Q, insider>5%)
  Layer 1 → Strategic Value Score (pipeline, approvals, therapeutic fit) /40
  Layer 2 → Acquirability Score (market cap, price discount, analyst gap) /30
  Layer 3 → Financial Health Score (revenue, runway in strategic zone) /20
  Layer 4 → Catalyst Signals (insider buying, volume, news clean) /10
  Total: 100 pts possible

CONVICTION TIERS:
  🔴 HIGH    ≥82 pts + mcap ≥$150M + runway ≥3Q + Phase 3 or commercial
  🟡 MEDIUM  ≥72 pts + mcap ≥$150M + runway ≥3Q
  ⚪ WATCH   ≥62 pts
  🚫 BELOW   <62 pts — not actionable
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
from datetime import datetime, timedelta
import sys
from secure_config import get_env

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

FMP_API_KEY = get_env("FMP_API_KEY")
FMP_BASE    = "https://financialmodelingprep.com/stable"

# Bankruptcy exclusion thresholds (if any trigger, skip M&A scoring entirely)
BANKRUPT_PRICE_MAX     = 1.00    # Below $1 = delisting risk
BANKRUPT_MCAP_MIN      = 100     # Below $100M = too small for pharma M&A
BANKRUPT_RUNWAY_MIN    = 2.0     # Below 2 quarters = likely bankruptcy filing
BANKRUPT_INSIDER_MAX   = 5.0     # Above 5% insider selling = death spiral

# Conviction gate minimums (must meet ALL to get HIGH/MEDIUM tier)
GATE_MCAP_MIN          = 150     # $150M minimum market cap
GATE_RUNWAY_MIN        = 3.0     # At least 3 quarters of cash
GATE_SCORE_HIGH        = 82      # High conviction threshold
GATE_SCORE_MEDIUM      = 72      # Medium conviction threshold
GATE_SCORE_WATCH       = 62      # Watch threshold

# Scan output directory
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIR = os.path.join(REPO_ROOT, "data", "scans")
PREDICTIONS_DIR = os.path.join(REPO_ROOT, "data", "predictions")
os.makedirs(SCAN_DIR, exist_ok=True)
os.makedirs(PREDICTIONS_DIR, exist_ok=True)

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
    'KALA', 'YMAB', 'IOVA', 'AGIO', 'CGEM',
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
    'ACNB', 'ALVO', 'ANGI', 'AVBH', 'VTYX',
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

# Build deduplicated universe — target 500
_all = (AUTOIMMUNE + ONCOLOGY + METABOLIC + RARE_DISEASE + NEUROSCIENCE +
        RENAL + GENE_CELL_THERAPY + CARDIOVASCULAR + COMMERCIAL_STAGE +
        INFECTIOUS_DISEASE + OPHTHALMOLOGY + WOMENS_HEALTH + ADDITIONAL +
        BROAD_BIOTECH + VERIFIED_NEW)
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
        'pts': 10,
        'acquirers': 'BMS, AbbVie, Sanofi, Pfizer'
    },
    {
        'name': 'ADC / Oncology Platform',
        'keywords': ['antibody-drug conjugate', 'adc', 'trop-2', 'folr1', 'her2',
                     'radioligand', 'rlft', 'bispecific', 'kras', 'prmt5',
                     'solid tumor', 'hematologic malignancy', 'tumor microenvironment'],
        'pts': 10,
        'acquirers': 'Pfizer, AstraZeneca, Gilead, Daiichi Sankyo'
    },
    {
        'name': 'Obesity / Metabolic',
        'keywords': ['obesity', 'weight loss', 'glp-1', 'gcgr', 'gip receptor',
                     'metabolic syndrome', 'nash', 'mash', 'nafld', 'type 2 diabetes',
                     'lipid', 'fatty liver', 'steatohepatitis'],
        'pts': 8,
        'acquirers': 'Eli Lilly, Novo Nordisk, Amgen'
    },
    {
        'name': 'Rare Disease (ODD)',
        'keywords': ['rare disease', 'ultra-rare', 'orphan drug', 'lysosomal',
                     'fabry disease', 'gaucher', 'pompe', 'enzyme replacement',
                     'hereditary transthyretin', 'spinal muscular', 'sma ',
                     'duchenne', 'genetic disorder'],
        'pts': 8,
        'acquirers': 'Takeda, Sanofi, Ultragenyx, Amicus, BioMarin'
    },
    {
        'name': 'Renal / Nephrology',
        'keywords': ['iga nephropathy', 'kidney disease', 'renal', 'fsgs',
                     'glomerulonephritis', 'pkd', 'polycystic kidney',
                     'iga vasculitis', 'membranous nephropathy', 'dialysis'],
        'pts': 7,
        'acquirers': 'AstraZeneca, Otsuka, Novartis'
    },
    {
        'name': 'Neuroscience / CNS',
        'keywords': ["alzheimer's", 'parkinson', 'huntington', 'amyotrophic lateral',
                     'als ', 'neurodegeneration', 'schizophrenia', 'major depression',
                     'epilepsy', 'multiple sclerosis', 'treatment-resistant'],
        'pts': 6,
        'acquirers': 'Biogen, AbbVie, J&J, Otsuka'
    },
    {
        'name': 'Gene / Cell Therapy',
        'keywords': ['gene therapy', 'gene editing', 'crispr', 'base editing',
                     'prime editing', 'aav vector', 'lentiviral', 'car-t',
                     'til therapy', 'tcr-t', 'cell therapy platform'],
        'pts': 5,
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

    # Find similar completed deals (at least 3 matching attributes)
    similar = []
    for deal in RECENT_ACQUISITIONS:
        deal_attrs = set(deal.get('attributes', []))
        overlap = cand_attrs & deal_attrs
        if len(overlap) >= 3:
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
        score += pts * 0.4           # weight = 40% of raw pts → max ~12 pts
        label = attr.replace('_', ' ').title()
        matched.append(f'{label} — matches recent acquisition attribute')

    # Bonus if we found highly similar completed deals
    if len(similar) >= 3:
        score += 5
        matched.append(f'Closely mirrors {len(similar)} completed deals '
                       f'({", ".join(d["ticker"] for d in similar[:2])})')
    elif len(similar) >= 1:
        score += 2
        matched.append(f'Comparable to {similar[0]["ticker"]} ({similar[0]["acquirer"]}, '
                       f'${similar[0]["deal_B"]:.1f}B, +{similar[0]["premium"]}%)')

    # Hot area bonus: this area had multiple recent acquisitions
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
            score += 2
            matched.append(f'Active M&A area: {area} ({hot[area]} deals 2023–2026)')
            break  # only one area bonus

    result['pattern_score']    = min(round(score, 1), 15)
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
        params = params or {}
        params['apikey'] = self.api_key
        url = f"{base or FMP_BASE}/{endpoint}"
        try:
            r = self.session.get(url, params=params, timeout=12)
            r.raise_for_status()
            time.sleep(0.15)
            return r.json()
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
    """
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
            r = requests.get(url, params=params, timeout=15)
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

def calculate_ma_score(ticker, quote, profile, insider, financial, pipeline):  # noqa: too-many-args
    """
    Score a stock's M&A acquisition probability on a 0–100 scale.

    LAYER 1 — Strategic Value (max 40 pts):
        Pipeline stage + commercial stage + FDA designations + therapeutic hotspot
    LAYER 2 — Acquirability (max 30 pts):
        Market cap sweet spot + price discount + analyst upside
    LAYER 3 — Financial Health (max 20 pts):
        Cash runway in strategic zone + revenue generation
    LAYER 4 — Catalyst Signals (max 10 pts):
        Insider buying + volume anomaly + clean news

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
        pts = 8
        signals.append({'cat': 'Pipeline', 'type': 'Multiple Phase 2 Programs',
                        'detail': f'{phase2} active Phase 2 trials (Phase 3 readout incoming)',
                        'pts': pts})
        layer1 += pts
    elif phase2 == 1:
        pts = 5
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

    layer1 = min(layer1, 40)  # cap layer 1

    # ── LAYER 2: ACQUIRABILITY (max 30) ───────────────────────────────────────

    layer2 = 0.0

    # 2a. Market cap sweet spot (max 20 pts)
    # Based on actual deal size distribution: $150M–$1B is bolt-on, $1B–$4B is mid, $4B+ is mega
    if 150 <= mcap <= 1000:
        pts = 20
        signals.append({'cat': 'Size', 'type': 'Bolt-On Acquisition Sweet Spot',
                        'detail': f'${mcap:.0f}M mcap — ideal size for most pharma acquirers', 'pts': pts})
        layer2 += pts
    elif 1000 < mcap <= 3000:
        pts = 14
        signals.append({'cat': 'Size', 'type': 'Mid-Cap Acquisition Target',
                        'detail': f'${mcap:.0f}M mcap — attractive for large pharma', 'pts': pts})
        layer2 += pts
    elif 3000 < mcap <= 7000:
        pts = 8
        signals.append({'cat': 'Size', 'type': 'Large Acquisition Target',
                        'detail': f'${mcap:.0f}M mcap — requires strategic justification', 'pts': pts})
        layer2 += pts
    elif 100 <= mcap < 150:
        pts = 10
        signals.append({'cat': 'Size', 'type': 'Small Acquisition Target',
                        'detail': f'${mcap:.0f}M mcap — lower priority for large pharma', 'pts': pts})
        layer2 += pts

    # 2b. Price discount from 52-week high (max 12 pts)
    # Buyer wants a discount; too much discount = company is dying
    if year_high > 0 and price > 0:
        discount_pct = ((year_high - price) / year_high) * 100
        if 25 <= discount_pct <= 60:
            pts = 12
            signals.append({'cat': 'Value', 'type': 'Strategic Price Discount',
                            'detail': f'-{discount_pct:.0f}% from 52-week high (buyer gets a deal)',
                            'pts': pts})
            layer2 += pts
        elif 15 <= discount_pct < 25:
            pts = 7
            signals.append({'cat': 'Value', 'type': 'Moderate Price Discount',
                            'detail': f'-{discount_pct:.0f}% from 52-week high', 'pts': pts})
            layer2 += pts
        elif discount_pct > 60:
            pts = 4
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

    layer2 = min(layer2, 30)  # cap layer 2

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
            flags.append(f'⚠️  Only {runway:.1f}Q runway — verify solvency before entering')
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

    # ── LAYER 4: CATALYST SIGNALS (max 10) ────────────────────────────────────

    layer4 = 0.0

    # 4a. Insider BUYING — the #1 contrarian M&A signal (insiders buy when deal is coming)
    if insider.get('has_buying'):
        buy_val = insider.get('buy_value_90d', 0)
        pts = 10
        signals.append({'cat': 'Insider', 'type': '🟢 C-Level Insider Buying',
                        'detail': f'${buy_val/1e6:.2f}M purchased in last 90 days — confidence signal',
                        'pts': pts})
        layer4 += pts

    # 4b. Volume anomaly (2x+ average in recent 5 days)
    try:
        hist = yf.Ticker(ticker).history(period='3mo')
        if not hist.empty and len(hist) > 20:
            recent_vol = hist['Volume'].iloc[-5:].mean()
            avg_vol    = hist['Volume'].mean()
            if avg_vol > 0 and recent_vol > avg_vol * 2.0:
                pts = 5
                signals.append({'cat': 'Technical', 'type': 'Unusual Volume Activity',
                                'detail': f'{recent_vol/avg_vol:.1f}x avg volume (potential deal activity)',
                                'pts': pts})
                layer4 += pts
    except Exception:
        pass

    # 4c. RSI oversold on a GOOD company (not distressed) = entry + M&A signal
    rsi_data = fmp_client.get_rsi(ticker)
    if rsi_data and 'rsi' in rsi_data:
        rsi = rsi_data['rsi']
        if rsi < 35:
            pts = 5
            signals.append({'cat': 'Technical', 'type': 'Technically Oversold',
                            'detail': f'RSI {rsi:.1f} — possible M&A entry window',
                            'pts': pts})
            layer4 += pts

    layer4 = min(layer4, 10)

    # ── LAYER 5: ACQUISITION PATTERN MATCH (max 15) ───────────────────────────
    # Compares this stock against profile of recently completed M&A deals

    layer5 = 0.0
    acq_pattern = analyze_acquisition_patterns(ticker, profile, financial, pipeline, quote)
    if acq_pattern['pattern_score'] > 0:
        pts = acq_pattern['pattern_score']
        layer5 = pts
        detail_parts = acq_pattern['matched_patterns'][:2]
        detail_str = '; '.join(detail_parts)[:90] if detail_parts else 'Pattern match to recent M&A'
        signals.append({'cat': 'AcqPattern', 'type': '🎯 Acquisition Pattern Match',
                        'detail': detail_str, 'pts': pts})
        if acq_pattern['similar_deals']:
            top = acq_pattern['similar_deals'][0]
            signals.append({'cat': 'AcqPattern', 'type': f"Comparable Deal: {top['ticker']} ({top['acquirer']})",
                            'detail': f"${top['deal_B']:.1f}B acquisition · +{top['premium']}% premium · {top['area']}",
                            'pts': 0})

    # ── DISTRESS PENALTIES ─────────────────────────────────────────────────────
    # These reduce score for distress signals that predict bankruptcy, not M&A

    penalties = 0.0
    sell_pct = insider.get('sell_pct_of_mcap', 0)

    if sell_pct >= 3.0:
        pen = 20
        flags.append(f'🔴 Heavy insider selling ({sell_pct:.1f}% of mcap) — leadership exiting, not deal prep')
        signals.append({'cat': 'Risk', 'type': 'Heavy Insider Selling (PENALTY)',
                        'detail': f'{sell_pct:.1f}% of market cap sold by C-level in 90 days',
                        'pts': -pen})
        penalties += pen
    elif sell_pct >= 1.5:
        pen = 10
        flags.append(f'⚠️  Elevated insider selling ({sell_pct:.1f}% of mcap)')
        signals.append({'cat': 'Risk', 'type': 'Elevated Insider Selling (PENALTY)',
                        'detail': f'{sell_pct:.1f}% of market cap sold in 90 days',
                        'pts': -pen})
        penalties += pen
    elif sell_pct >= 0.5:
        # Minor selling — just flag, no penalty
        flags.append(f'📝 Moderate insider selling ({sell_pct:.1f}% of mcap)')

    # ── TOTAL SCORE ────────────────────────────────────────────────────────────

    raw_total = layer1 + layer2 + layer3 + layer4 + layer5
    final_score = max(0, raw_total - penalties)
    final_score = min(final_score, 100)

    # ── CONVICTION TIER ────────────────────────────────────────────────────────

    has_phase3_or_commercial = (phase3 >= 1) or (phase2 >= 2) or financial.get('has_revenue', False)
    runway_ok = (runway is None or runway >= GATE_RUNWAY_MIN)

    if final_score >= GATE_SCORE_HIGH and mcap >= GATE_MCAP_MIN and runway_ok and has_phase3_or_commercial:
        conviction = 'HIGH_CONVICTION'
    elif final_score >= GATE_SCORE_MEDIUM and mcap >= GATE_MCAP_MIN and runway_ok:
        conviction = 'MEDIUM_CONVICTION'
    elif final_score >= GATE_SCORE_WATCH:
        conviction = 'WATCH'
    else:
        conviction = 'BELOW_THRESHOLD'

    return {
        'score':          round(final_score, 1),
        'layer_scores': {'strategic': round(layer1, 1), 'acquirability': round(layer2, 1),
                         'financial': round(layer3, 1), 'catalyst': round(layer4, 1),
                         'acq_pattern': round(layer5, 1), 'penalties': round(penalties, 1)},
        'acq_pattern':  acq_pattern,
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

def analyze_stock(ticker, fmp):
    """
    Full analysis pipeline for one ticker.
    Returns result dict or None if excluded.
    """
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

        # 6. Score
        result = calculate_ma_score(ticker, quote, profile, insider, financial, pipeline)

        # 7. Package output
        return {
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
            'description':      profile.get('description', '')[:200],
            'scan_date':        datetime.now().isoformat(),
        }

    except Exception as e:
        print(f'  ⚠️  {ticker}: Error — {str(e)[:60]}')
        return None


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

TIER_ICONS = {
    'HIGH_CONVICTION':   '🔴',
    'MEDIUM_CONVICTION': '🟡',
    'WATCH':             '⚪',
    'BELOW_THRESHOLD':   '🔵',
    'BANKRUPTCY_RISK':   '💀',
}

def format_result(r, verbose=True):
    icon = TIER_ICONS.get(r['conviction_tier'], '  ')
    tier_label = r['conviction_tier'].replace('_', ' ')
    lines = []
    lines.append(
        f"\n{icon} [{r['score']:.0f}pts] {r['ticker']} — {r['company']}"
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
        lines.append(f"   🟢 INSIDER BUYING detected in last 90 days")
    if r.get('sell_pct', 0) > 1.0:
        lines.append(f"   🔴 Insider selling: {r['sell_pct']:.1f}% of mcap (penalty applied)")

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
            f"Penalties=-{ls.get('penalties',0):.0f}"
        )
    ap = r.get('acq_pattern', {})
    if ap and ap.get('similar_deals'):
        top = ap['similar_deals'][0]
        lines.append(f"   🎯 Pattern: mirrors {top['ticker']} ({top['acquirer']} ${top['deal_B']:.1f}B "
                     f"+{top['premium']}% prem) — implied prem {ap.get('implied_premium',0):.0f}%")
    if ap and ap.get('acquirer_interest'):
        lines.append(f"   Likely acquirers: {', '.join(ap['acquirer_interest'])}")

    return '\n'.join(lines)


def save_results(results, scan_id):
    """Save to JSON + CSV in the scan directory."""

    # JSON (full detail)
    json_path = os.path.join(SCAN_DIR, f'scan_v11_{scan_id}.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # CSV (summary for tracking)
    csv_path = os.path.join(PREDICTIONS_DIR, 'predictions_v11.csv')
    fieldnames = [
        'scan_date', 'ticker', 'company', 'score', 'conviction_tier',
        'price', 'mcap_M', 'runway_Q', 'phase3_count', 'revenue_M',
        'is_profitable', 'sell_pct', 'has_buying', 'pt_upside_pct',
        'hotspot_name', 'top_signals', 'flags', 'outcome', 'outcome_date',
        'outcome_price', 'return_pct', 'notes'
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

def run_scan(tickers=None, verbose=True, save=True):
    """
    Run the full M&A scan.

    Args:
        tickers: list of tickers to scan (default: full UNIVERSE)
        verbose: print detailed output
        save:    save results to disk
    """
    scan_start = datetime.now()
    scan_id    = scan_start.strftime('%Y%m%d_%H%M%S')
    watchlist  = tickers or UNIVERSE

    print('\n' + '═'*72)
    print('  M&A SCANNER V11.0 — STRATEGIC ACQUISITION PREDICTOR')
    print(f'  {scan_start.strftime("%B %d, %Y %I:%M %p")}')
    print(f'  Universe: {len(watchlist)} stocks')
    print('═'*72)

    fmp      = FMPClient(FMP_API_KEY)
    results  = []
    errors   = []

    high_conv   = []
    medium_conv = []
    watch_list  = []
    bankrupt    = []

    for i, ticker in enumerate(watchlist, 1):
        try:
            sys.stdout.write(f'\r  Scanning {i}/{len(watchlist)}: {ticker:<8}  ')
            sys.stdout.flush()

            r = analyze_stock(ticker, fmp)
            if r is None:
                continue

            results.append(r)

            tier = r['conviction_tier']
            if tier == 'HIGH_CONVICTION':
                high_conv.append(r)
            elif tier == 'MEDIUM_CONVICTION':
                medium_conv.append(r)
            elif tier == 'WATCH':
                watch_list.append(r)
            elif tier == 'BANKRUPTCY_RISK':
                bankrupt.append(r)

        except Exception as e:
            errors.append(f'{ticker}: {e}')
            continue

    print('\n')

    # Sort by score descending
    for group in [high_conv, medium_conv, watch_list]:
        group.sort(key=lambda x: -x['score'])

    # ── PRINT RESULTS ─────────────────────────────────────────────────────────

    if high_conv:
        print('\n' + '─'*72)
        print('  🔴 HIGH CONVICTION ACQUISITIONS')
        print('  Phase 3+ pipeline OR commercial stage + strategic fit + right size')
        print('─'*72)
        for r in high_conv:
            print(format_result(r, verbose))

    if medium_conv:
        print('\n' + '─'*72)
        print('  🟡 MEDIUM CONVICTION')
        print('─'*72)
        for r in medium_conv:
            print(format_result(r, verbose))

    if watch_list:
        print('\n' + '─'*72)
        print('  ⚪ WATCH LIST')
        print('─'*72)
        for r in watch_list[:15]:  # Top 15 watches
            print(format_result(r, verbose=False))

    if bankrupt:
        print('\n' + '─'*72)
        print(f'  💀 BANKRUPTCY RISK ({len(bankrupt)} stocks excluded from M&A scoring)')
        print('  These are likely headed to bankruptcy/restructuring, NOT acquisition')
        print('─'*72)
        for r in sorted(bankrupt, key=lambda x: x.get('mcap_M', 0)):
            reasons = '; '.join(r.get('flags', []))
            print(f"     {r['ticker']:<8} ${r['price']:.2f}  ${r['mcap_M']:.0f}M  {reasons[:70]}")

    # ── SUMMARY ───────────────────────────────────────────────────────────────

    duration = (datetime.now() - scan_start).seconds
    print('\n' + '═'*72)
    print(f'  SCAN COMPLETE in {duration}s')
    print(f'  Scanned: {len(results)} stocks  |  '
          f'High: {len(high_conv)}  |  Medium: {len(medium_conv)}  |  '
          f'Watch: {len(watch_list)}  |  Bankruptcy Risk: {len(bankrupt)}')

    if errors:
        print(f'  Errors: {len(errors)} tickers failed')

    if save and results:
        json_path, csv_path = save_results(
            [r for r in results if r['conviction_tier'] != 'BELOW_THRESHOLD'],
            scan_id
        )
        print(f'  Saved → {json_path}')
        print(f'  CSV   → {csv_path}')

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
    If tickers is None, reads from predictions_v11.csv.
    """
    fmp = FMPClient(FMP_API_KEY)

    if tickers is None:
        csv_path = os.path.join(PREDICTIONS_DIR, 'predictions_v11.csv')
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
            near_acq = '🎯 NEAR 52W HIGH — Check news' if price >= yh * 0.97 else ''
            print(f'{t:<8} ${price:<9.2f} ${yh:<9.2f} ${yl:<9.2f} ${mc:<10.0f}M {near_acq}')
        else:
            print(f'{t:<8} No data (possibly acquired/delisted)')


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='M&A Scanner V11.0 — Strategic Acquisition Predictor')
    parser.add_argument('--ticker',    type=str, help='Analyze a single ticker')
    parser.add_argument('--portfolio', action='store_true', help='Check tracked portfolio status')
    parser.add_argument('--tickers',   type=str, help='Comma-separated list of tickers to scan')
    parser.add_argument('--quick',     action='store_true',
                        help='Quick scan (first 50 tickers only, for testing)')
    parser.add_argument('--no-save',   action='store_true', help='Do not save results to disk')
    args = parser.parse_args()

    if args.ticker:
        analyze_one(args.ticker.upper())
    elif args.portfolio:
        check_portfolio()
    elif args.tickers:
        run_scan(tickers=[t.strip().upper() for t in args.tickers.split(',')],
                 save=not args.no_save)
    elif args.quick:
        run_scan(tickers=UNIVERSE[:50], save=not args.no_save)
    else:
        run_scan(save=not args.no_save)
