"""
acquisition_case_schema.py — Schema and enum constants for completed acquisition learning cases.

Used by:
  - acquisition_case_library.py (load/validate/query)
  - acquisition_situation_classifier.py (scoring)
  - acquisition_probability_engine.py (probability computation)
"""
from __future__ import annotations

from typing import Optional


# ── Enum constants ────────────────────────────────────────────────────────────

ACQUISITION_SITUATION_TYPES: list[str] = [
    "ACTIVE_PUBLIC_SALE_PROCESS",
    "PUBLIC_UNSOLICITED_PROPOSAL",
    "COMPETING_BID_OR_SUPERIOR_PROPOSAL",
    "MEDIA_REPORTED_SALE_PROCESS",
    "STRATEGIC_REVIEW_OR_ALTERNATIVES",
    "DISTRESSED_OR_CASH_RUNWAY_SALE",
    "PIPELINE_CATALYST_DRIVEN_TAKEOUT",
    "SINGLE_ASSET_STRATEGIC_FIT",
    "PLATFORM_STRATEGIC_FIT",
    "PARTNERSHIP_RIGHTS_CONVERTED_TO_ACQUISITION",
    "ACTIVIST_PRESSURE_OR_13D",
    "ALREADY_ANNOUNCED_DEAL",
    "PRIVATE_BACKGROUND_ONLY",
    "NO_PUBLIC_PRIOR_SIGNAL",
    "FALSE_POSITIVE_ONLY",
    "INSUFFICIENT_EVIDENCE",
]

PUBLIC_SIGNAL_CATEGORIES: list[str] = [
    "TRUE_PUBLIC_PRIOR_SIGNAL",
    "SETUP_SIGNAL_NOT_PROCESS_SIGNAL",
    "PRIVATE_ONLY",
    "POST_ANNOUNCEMENT_ONLY",
    "FALSE_POSITIVE",
    "NO_VISIBLE_SIGNAL",
    "NEEDS_VERIFICATION",
]

PUBLIC_CATCHABILITY: list[str] = ["HIGH", "MEDIUM", "LOW", "NONE", "UNKNOWN"]

VERIFICATION_STATUSES: list[str] = [
    "VERIFIED",
    "NEEDS_VERIFICATION",
    "TEMPLATE",
    "INFERRED_FROM_PUBLIC_SUMMARY",
]

PROBABILITY_BUCKETS: list[str] = [
    "P0_NO_ACTION_FALSE_POSITIVE",
    "P1_DISCARD_ALREADY_ANNOUNCED",
    "P2_MONITOR_ONLY",
    "P3_WATCHLIST_SETUP",
    "P4_RESEARCH_PRIORITY",
    "P5_HIGH_PRIORITY_PROCESS_SIGNAL",
]


# ── Required fields for case validation ──────────────────────────────────────

REQUIRED_CASE_FIELDS: set[str] = {
    "case_id",
    "ticker",
    "company_name",
    "public_signal_category",
    "acquisition_situation_type",
    "public_catchability",
    "verification_status",
}


# ── Schema reference (TypedDict-style, for documentation) ─────────────────────

class AcquisitionCase:
    """
    Represents a completed acquisition learning case.
    All fields are documented here; runtime uses plain dicts.
    """
    case_id: str
    ticker: str
    company_name: str
    acquirer: Optional[str]
    announcement_date: Optional[str]
    deal_value: Optional[str]
    premium_if_available: Optional[str]
    sector: Optional[str]
    modality_or_therapeutic_area: Optional[str]
    company_stage: Optional[str]
    market_cap_prior: Optional[str]
    cash_runway_context: Optional[str]
    lead_asset_context: Optional[str]
    key_assets: list  # list[str]
    public_signal_category: str  # PUBLIC_SIGNAL_CATEGORIES
    acquisition_situation_type: str  # ACQUISITION_SITUATION_TYPES
    pre_announcement_public_evidence: list  # list[str]
    post_announcement_background: Optional[str]
    private_background_only: bool
    source_documents: list  # list[str]
    source_quotes: list  # list[str]
    source_urls: list  # list[str]
    signal_start_date: Optional[str]
    days_before_announcement: Optional[int]
    public_catchability: str  # PUBLIC_CATCHABILITY
    was_publicly_catchable_before_announcement: Optional[bool]
    why_catchable_or_not: Optional[str]
    visible_setup_traits: list  # list[str]
    invisible_setup_traits: list  # list[str]
    buyer_strategic_rationale: Optional[str]
    target_strategic_rationale: Optional[str]
    catalyst_context: Optional[str]
    valuation_context: Optional[str]
    price_reaction_context: Optional[str]
    competing_bid_context: Optional[str]
    activist_context: Optional[str]
    banker_or_advisor_context: Optional[str]
    partnership_or_rights_context: Optional[str]
    asset_specific_vs_company_level: Optional[str]
    false_positive_lessons: list  # list[str]
    true_signal_lessons: list  # list[str]
    operator_lesson: Optional[str]
    model_training_summary: Optional[str]
    tags: list  # list[str]
    verification_status: str  # VERIFICATION_STATUSES


def make_empty_case(case_id: str, ticker: str, company_name: str) -> dict:
    """Return a minimal valid case dict with all list/optional fields initialized."""
    return {
        "case_id": case_id,
        "ticker": ticker,
        "company_name": company_name,
        "acquirer": None,
        "announcement_date": None,
        "deal_value": None,
        "premium_if_available": None,
        "sector": "Biotech",
        "modality_or_therapeutic_area": None,
        "company_stage": None,
        "market_cap_prior": None,
        "cash_runway_context": None,
        "lead_asset_context": None,
        "key_assets": [],
        "public_signal_category": "NEEDS_VERIFICATION",
        "acquisition_situation_type": "INSUFFICIENT_EVIDENCE",
        "pre_announcement_public_evidence": [],
        "post_announcement_background": None,
        "private_background_only": False,
        "source_documents": [],
        "source_quotes": [],
        "source_urls": [],
        "signal_start_date": None,
        "days_before_announcement": None,
        "public_catchability": "UNKNOWN",
        "was_publicly_catchable_before_announcement": None,
        "why_catchable_or_not": None,
        "visible_setup_traits": [],
        "invisible_setup_traits": [],
        "buyer_strategic_rationale": None,
        "target_strategic_rationale": None,
        "catalyst_context": None,
        "valuation_context": None,
        "price_reaction_context": None,
        "competing_bid_context": None,
        "activist_context": None,
        "banker_or_advisor_context": None,
        "partnership_or_rights_context": None,
        "asset_specific_vs_company_level": None,
        "false_positive_lessons": [],
        "true_signal_lessons": [],
        "operator_lesson": None,
        "model_training_summary": None,
        "tags": [],
        "verification_status": "TEMPLATE",
    }
