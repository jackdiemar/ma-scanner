#!/usr/bin/env python3
"""
pipeline_scraper.py - Get Phase 3 trials and FDA status from ClinicalTrials.gov
Free API, no key required
"""

import requests
import json
import time

CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/v2/studies"

def get_company_trials(company_name, ticker):
    """Get clinical trials for a company"""
    try:
        # Search for trials by company name
        params = {
            'query.lead': company_name,
            'filter.overallStatus': 'RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION',
            'pageSize': 100,
            'format': 'json'
        }
        
        response = requests.get(CLINICAL_TRIALS_API, params=params, timeout=15)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        studies = data.get('studies', [])
        
        if not studies:
            return None
        
        # Count by phase
        phase_counts = {
            'phase1': 0,
            'phase2': 0,
            'phase3': 0,
            'phase4': 0
        }
        
        breakthrough = False
        orphan = False
        
        for study in studies:
            protocol = study.get('protocolSection', {})
            design = protocol.get('designModule', {})
            phases = design.get('phases', [])
            
            for phase in phases:
                if 'PHASE1' in phase:
                    phase_counts['phase1'] += 1
                elif 'PHASE2' in phase:
                    phase_counts['phase2'] += 1
                elif 'PHASE3' in phase:
                    phase_counts['phase3'] += 1
                elif 'PHASE4' in phase:
                    phase_counts['phase4'] += 1
            
            # Check for designations
            conditions = protocol.get('conditionsModule', {})
            keywords = conditions.get('keywords', [])
            
            if any('breakthrough' in str(k).lower() for k in keywords):
                breakthrough = True
            if any('orphan' in str(k).lower() for k in keywords):
                orphan = True
        
        return {
            'ticker': ticker,
            'phase3_count': phase_counts['phase3'],
            'phase2_count': phase_counts['phase2'],
            'total_trials': len(studies),
            'has_breakthrough': breakthrough,
            'has_orphan': orphan
        }
        
    except Exception as e:
        print(f"Error getting trials for {ticker}: {e}")
        return None

def get_fda_approvals(ticker, company_name):
    """Check for recent FDA approvals - simplified version"""
    # Would integrate with FDA API or scrape FDA.gov
    # For now, returning placeholder
    return {
        'recent_approval': False,
        'approval_date': None
    }

def enrich_with_pipeline_data(ticker, company_name=None):
    """Main function to get all pipeline data for a ticker"""
    
    if not company_name:
        # Try to get company name from ticker
        # Would integrate with FMP or yfinance
        company_name = ticker
    
    pipeline_data = get_company_trials(company_name, ticker)
    fda_data = get_fda_approvals(ticker, company_name)
    
    if pipeline_data:
        pipeline_data.update(fda_data)
        return pipeline_data
    
    return {
        'ticker': ticker,
        'phase3_count': 0,
        'phase2_count': 0,
        'total_trials': 0,
        'has_breakthrough': False,
        'has_orphan': False,
        'recent_approval': False
    }

if __name__ == "__main__":
    # Test
    test_companies = [
        ('KALA', 'Kala Pharmaceuticals'),
        ('DTIL', 'Precision BioSciences'),
        ('CRBU', 'Caribou Biosciences')
    ]
    
    for ticker, company in test_companies:
        print(f"\n{ticker} ({company}):")
        data = enrich_with_pipeline_data(ticker, company)
        print(json.dumps(data, indent=2))
        time.sleep(2)  # Rate limit
