#!/usr/bin/env python3
"""
case_factory_config.py

Load and validate case_factory.yaml configuration for the historical case factory.
No external dependencies — uses a built-in YAML-subset parser for the config format.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "case_factory.yaml"


def _parse_yaml(text: str) -> dict[str, Any]:
    """
    Parse the case_factory.yaml subset (scalars + simple top-level lists).
    Handles: str, int, bool, and single-level '  - item' lists.
    Comments (#) and blank lines are skipped.
    """
    result: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        # Skip blanks and comments
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item (must come before key detection)
        if current_list_key is not None and line.startswith("  - "):
            result[current_list_key].append(line[4:].strip())
            continue

        # Key: value or Key: (start of list)
        if ":" in line:
            key, _, raw_val = line.partition(":")
            key = key.strip()
            val = raw_val.strip()

            if not val or val.startswith("#"):
                current_list_key = key
                result[key] = []
            else:
                current_list_key = None
                # Strip inline comment
                if " #" in val:
                    val = val[: val.index(" #")].strip()
                result[key] = _coerce(val)
        else:
            current_list_key = None

    return result


def _coerce(val: str) -> Any:
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~", "none"):
        return None
    if val.lstrip("-").isdigit():
        return int(val)
    return val


@dataclass
class CaseFactoryConfig:
    target_case_count: int = 200
    current_confirmed_case_count: int = 70
    batch_size: int = 30
    start_case_number: int = 71
    end_case_number: int = 200
    lookback_years: int = 5
    require_source_backed_dates: bool = True
    require_edgar_or_source_url: bool = True
    allow_fmp_discovery: bool = False
    allow_live_api: bool = False
    collect_filings: bool = False
    adjudicate_automatically: bool = False
    mark_verified: bool = False
    mark_calibration_eligible: bool = False
    run_full_live_scanner: bool = False
    output_dir: str = "data/historical_cases"
    cache_dir: str = "~/.ma_scanner_cache"
    max_filings_per_case: int = 50
    eight_k_scan_depth: int = 8
    manual_review_required_tiers: list[str] = field(
        default_factory=lambda: ["P1", "P2", "P3", "P4", "P6_WITH_HITS"]
    )

    @property
    def output_path(self) -> Path:
        return REPO_ROOT / self.output_dir

    @property
    def remaining_cases_needed(self) -> int:
        return self.target_case_count - self.current_confirmed_case_count

    @property
    def batches_remaining(self) -> int:
        return math.ceil(self.remaining_cases_needed / self.batch_size)


def load_config(path: Path = DEFAULT_CONFIG) -> CaseFactoryConfig:
    """Load config from YAML; fall back to defaults for unknown keys."""
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    raw = _parse_yaml(path.read_text())
    cfg = CaseFactoryConfig()
    for key, val in raw.items():
        if hasattr(cfg, key):
            setattr(cfg, key, val)
    return cfg


if __name__ == "__main__":
    cfg = load_config()
    print(f"target_case_count:            {cfg.target_case_count}")
    print(f"current_confirmed_case_count: {cfg.current_confirmed_case_count}")
    print(f"remaining_cases_needed:       {cfg.remaining_cases_needed}")
    print(f"batches_remaining:            {cfg.batches_remaining}")
    print(f"batch_size:                   {cfg.batch_size}")
    print(f"allow_live_api:               {cfg.allow_live_api}")
    print(f"collect_filings:              {cfg.collect_filings}")
    print(f"adjudicate_automatically:     {cfg.adjudicate_automatically}")
    print(f"manual_review_required_tiers: {cfg.manual_review_required_tiers}")
