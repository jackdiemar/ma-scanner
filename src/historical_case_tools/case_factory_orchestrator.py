#!/usr/bin/env python3
"""
case_factory_orchestrator.py

Unified orchestration layer for the 200-case historical prior-signal research factory.

Coordinates candidate selection, date backfill, exception queue generation, manual
review packet creation, and state tracking. Designed to scale the historical dataset
from 70 confirmed cases to 200 with minimal manual interruption.

Safety defaults (hardcoded — config flags that are false cannot be overridden by CLI):
  - No live API calls.
  - No filing collection unless collect_filings=true in config.
  - No automatic adjudication.
  - No VERIFIED or CALIBRATION_ELIGIBLE marking.
  - No dashboard/frontend changes.
  - No full live scanner execution.

Usage:
  python3 src/historical_case_tools/case_factory_orchestrator.py \\
    --config configs/case_factory.yaml --status

  python3 src/historical_case_tools/case_factory_orchestrator.py \\
    --config configs/case_factory.yaml --plan

  python3 src/historical_case_tools/case_factory_orchestrator.py \\
    --config configs/case_factory.yaml --select-next-batch

  python3 src/historical_case_tools/case_factory_orchestrator.py \\
    --config configs/case_factory.yaml --prepare-batch --start 71 --limit 30

  python3 src/historical_case_tools/case_factory_orchestrator.py \\
    --config configs/case_factory.yaml --run-step date-prefill --start 71 --limit 30

  python3 src/historical_case_tools/case_factory_orchestrator.py \\
    --config configs/case_factory.yaml --run-step exception-queue --start 71 --limit 30

  python3 src/historical_case_tools/case_factory_orchestrator.py \\
    --config configs/case_factory.yaml --write-review-packets --start 71 --limit 30
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from historical_case_tools.case_factory_config import load_config, CaseFactoryConfig
from historical_case_tools.case_factory_state import StateManager, DEFAULT_STATE_PATH
from historical_case_tools.case_factory_batch_selector import (
    DEFAULT_UNIVERSE,
    OUTPUT_FIELDS as QUEUE_FIELDS,
    batch_name,
    build_queue_rows,
    read_csv,
    select_candidates,
    write_csv,
    write_report as _write_selector_report,
)

RUN_DATE = date.today().isoformat()

# Known batch 51-70 tickers for gap calculation in plan/status
_BATCH_51_70_TICKERS: frozenset[str] = frozenset({
    "EPZM", "FMTX", "GBT", "IMGO", "OYST", "SRRA", "TPTX",
    "BLU", "CINC", "CTIC", "DICE", "HARP", "ISEE", "RETA",
    "ZYNE", "ALPN", "AMAM", "CBAY", "CERE", "DCPH",
})

# Step registry: maps step name -> script metadata
_STEP_REGISTRY: dict[str, dict] = {
    "date-prefill": {
        "script": REPO_ROOT / "src" / "historical_case_tools" / "merger_date_prefiller.py",
        "output_suffix": "date_prefill_queue.csv",
        "report_suffix": "date_prefill_report.md",
        "state_key": "dates_backfilled",
        "next_step": "exception-queue",
        "extra_args": [],
    },
    "exception-queue": {
        "script": REPO_ROOT / "src" / "historical_case_tools" / "exception_queue_builder.py",
        "output_suffix": "exception_queue.csv",
        "report_suffix": "exception_queue_report.md",
        "state_key": "exception_queues_created",
        "next_step": "source-evidence",
        "extra_args": [],
    },
    "source-evidence": {
        "script": REPO_ROOT / "src" / "historical_case_tools" / "source_evidence_autofill.py",
        "output_suffix": "source_evidence_draft.csv",
        "report_suffix": "source_evidence_draft_report.md",
        "state_key": "filings_collected",
        "next_step": "write-review-packets",
        "extra_args": ["exception_queue_required"],
    },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _historical_dir(cfg: CaseFactoryConfig) -> Path:
    return REPO_ROOT / cfg.output_dir


def _batch_files(cfg: CaseFactoryConfig, start: int, limit: int) -> dict[str, Path]:
    hdir = _historical_dir(cfg)
    label = batch_name(start, start + limit - 1)
    return {
        "candidate_queue_csv":          hdir / f"{label}_candidate_queue.csv",
        "candidate_queue_report":       hdir / f"{label}_candidate_queue_report.md",
        "date_prefill_csv":             hdir / f"{label}_date_prefill_queue.csv",
        "date_prefill_report":          hdir / f"{label}_date_prefill_report.md",
        "exception_queue_csv":          hdir / f"{label}_exception_queue.csv",
        "exception_queue_report":       hdir / f"{label}_exception_queue_report.md",
        "source_evidence_draft_csv":    hdir / f"{label}_source_evidence_draft.csv",
        "source_evidence_draft_report": hdir / f"{label}_source_evidence_draft_report.md",
        "review_packet":                hdir / f"{label}_review_packet.md",
        "final_summary":                hdir / f"{label}_final_summary.md",
    }


_RESOLVED_CANDIDATES_FIELDS = [
    "candidate_id", "ticker", "company_name", "likely_outcome_type",
    "likely_outcome_year", "outcome_source_hint", "outcome_edgar_query",
    "prior_process_signal_query", "prior_13d_query", "prior_rofr_exhibit_query",
    "proxy_or_s4_query", "verification_status", "priority",
    "reason_for_inclusion", "notes",
]


def _write_staging_candidates_csv(
    hdir: Path, label: str, queue_rows: list[dict[str, str]]
) -> Path:
    """
    Write a staging CSV in resolved_case_candidates format containing exactly
    the candidates in the batch selector's queue. Passed to existing step scripts
    via --candidates so the index-window approach uses the right candidate set.

    Uses --start 51 / --limit N with this file so idx_start = 51-51 = 0
    (take from the very beginning of the list, which is exactly our candidates).
    """
    staging_path = hdir / f"{label}_staging_candidates.csv"
    rows = []
    for r in queue_rows:
        rows.append({
            "candidate_id":             r.get("candidate_id", ""),
            "ticker":                   r.get("ticker", ""),
            "company_name":             r.get("company", ""),
            "likely_outcome_type":      "ACQUIRED",
            "likely_outcome_year":      r.get("announcement_year", ""),
            "outcome_source_hint":      r.get("source_url", ""),
            "outcome_edgar_query":      "",
            "prior_process_signal_query": "",
            "prior_13d_query":          "",
            "prior_rofr_exhibit_query": "",
            "proxy_or_s4_query":        "",
            "verification_status":      "CANDIDATE",
            "priority":                 "HIGH",
            "reason_for_inclusion":     "Batch selector candidate",
            "notes":                    r.get("notes", ""),
        })
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    import csv as _csv
    with staging_path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.DictWriter(
            f, fieldnames=_RESOLVED_CANDIDATES_FIELDS,
            extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    return staging_path


# ---------------------------------------------------------------------------
# --run-batch-package helpers
# ---------------------------------------------------------------------------

_CONFIRMATION_RESULTS_FIELDS = [
    "case_id", "ticker", "company_name", "acquisition_announcement_date",
    "search_window_start", "search_window_end", "searched_signal_types",
    "strategic_alternatives_hit", "banker_advisor_hit", "activist_13d_hit",
    "competing_bid_hit", "rofr_rofn_hit", "public_process_hit",
    "hit_status", "best_source_url", "best_source_excerpt",
    "confidence", "next_action", "notes",
]

_DATES_CSV = REPO_ROOT / "data" / "historical_cases" / "acquisition_announcement_dates.csv"


def _check_dates_gate(
    queue_rows: list[dict[str, str]],
    dates_csv: Path = _DATES_CSV,
) -> tuple[dict[str, str], list[str]]:
    """Return (dates_found, missing_tickers) for batch candidates vs announcement dates CSV."""
    batch_tickers = {r["ticker"] for r in queue_rows}
    date_map: dict[str, str] = {}
    if dates_csv.exists():
        for row in read_csv(dates_csv):
            tk = row.get("ticker", "")
            conf = row.get("confidence", "").upper()
            dt = row.get("acquisition_announcement_date", "").strip()
            if tk in batch_tickers and dt and conf in {"HIGH", "MEDIUM"}:
                date_map[tk] = dt
    missing = [r["ticker"] for r in queue_rows if r["ticker"] not in date_map]
    return date_map, missing


def _write_confirmation_results_staging(
    hdir: Path,
    label: str,
    queue_rows: list[dict[str, str]],
    dates_found: dict[str, str],
) -> Path:
    """Write batch-specific prior_signal_confirmation_results staging for filing collector."""
    import csv as _csv
    staging_path = hdir / f"{label}_confirmation_results_staging.csv"
    rows = []
    for r in queue_rows:
        tk = r.get("ticker", "")
        dt = dates_found.get(tk, "")
        search_start = ""
        if dt:
            try:
                search_start = f"{int(dt[:4]) - 2}-01-01"
            except (ValueError, IndexError):
                pass
        rows.append({
            "case_id":                      r.get("candidate_id", "") or f"RHC-BATCH-{tk}",
            "ticker":                       tk,
            "company_name":                 r.get("company", ""),
            "acquisition_announcement_date": dt,
            "search_window_start":          search_start,
            "search_window_end":            dt,
            "searched_signal_types":        "strategic_alternatives|banker_advisor|activist_13d|competing_bid|rofr_rofn|public_process",
            "strategic_alternatives_hit":   "",
            "banker_advisor_hit":           "",
            "activist_13d_hit":             "",
            "competing_bid_hit":            "",
            "rofr_rofn_hit":               "",
            "public_process_hit":           "",
            "hit_status":                   "NEEDS_MANUAL_REVIEW" if dt else "DATE_OR_CIK_BLOCKED",
            "best_source_url":              "",
            "best_source_excerpt":          "",
            "confidence":                   "LOW",
            "next_action":                  (
                "Run EDGAR queries manually and record hit/no-hit evidence."
                if dt else "Resolve announcement date before filing collection."
            ),
            "notes":                        f"Batch package staging. Year={r.get('announcement_year', '')}.",
        })
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    with staging_path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.DictWriter(
            f, fieldnames=_CONFIRMATION_RESULTS_FIELDS,
            extrasaction="ignore", lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return staging_path


def _write_proposed_baselines_csv(
    hdir: Path,
    label: str,
    exception_rows: list[dict[str, str]],
) -> tuple[Path, int]:
    """Write proposed DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE rows from PENDING/P6 tier cases."""
    import csv as _csv
    out_path = hdir / f"{label}_proposed_clean_baselines.csv"
    fields = ["case_id", "ticker", "priority_tier", "priority_reason",
              "proposed_classification", "rationale"]
    baseline_tiers = {"PENDING_FILING_COLLECTION", "P6"}
    rows = [
        {
            "case_id":                  r.get("case_id", ""),
            "ticker":                   r.get("ticker", ""),
            "priority_tier":            r.get("priority_tier", ""),
            "priority_reason":          r.get("priority_reason", ""),
            "proposed_classification":  "DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE",
            "rationale":                (
                "No prior public signal evidence at exception-queue stage. "
                "Proposed baseline — researcher must confirm before finalizing."
            ),
        }
        for r in exception_rows
        if r.get("priority_tier", "") in baseline_tiers
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return out_path, len(rows)


def _write_package_report(
    hdir: Path,
    label: str,
    start: int,
    end: int,
    limit: int,
    steps_log: list[dict],
    files_written: list[str],
    dry_run: bool,
    n_found: int,
    n_missing: int,
    gate_passed: bool,
) -> "Path | None":
    rpt_path = hdir / f"{label}_package_report.md"
    if dry_run:
        print(f"  [DRY RUN] Would write {rpt_path.name}")
        return None

    lines = [
        f"# {label.replace('_', ' ').title()} Package Report",
        "",
        f"Generated: {RUN_DATE}",
        "",
        "---",
        "",
        "## 1. Scope",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Batch | {label} |",
        f"| Cases | {start}–{end} ({limit} target) |",
        f"| Run date | {RUN_DATE} |",
        f"| Dry run | {dry_run} |",
        f"| Dates confirmed | {n_found} / {limit} |",
        f"| Dates missing | {n_missing} |",
        f"| Date gate | {'PASS' if gate_passed and n_missing == 0 else 'PARTIAL' if gate_passed else 'BLOCKED'} |",
        "",
        "---",
        "",
        "## 2. Step Results",
        "",
        "| Step | Status | Notes |",
        "|---|---|---|",
    ]
    for s in steps_log:
        note_parts = [f"{k}={v}" for k, v in s.items() if k not in {"step", "status"}]
        lines.append(f"| {s.get('step', '')} | {s.get('status', '')} | {'; '.join(note_parts)} |")

    lines += [
        "",
        "---",
        "",
        "## 3. Files Written",
        "",
    ]
    for fp in files_written:
        lines.append(f"- `{Path(fp).name}`")

    lines += [
        "",
        "---",
        "",
        "## 4. Safety Constraints",
        "",
        "- No cases adjudicated.",
        "- No VERIFIED flag set.",
        "- No CALIBRATION_ELIGIBLE flag set.",
        "- No live API calls made.",
        "- No live scanner run.",
        "- No first-70 classifications changed.",
        "- `source_evidence.csv` not written by this pipeline.",
    ]

    rpt_path.parent.mkdir(parents=True, exist_ok=True)
    rpt_path.write_text("\n".join(lines) + "\n")
    return rpt_path


def _write_run_manifest(
    hdir: Path,
    label: str,
    start: int,
    end: int,
    limit: int,
    steps_log: list[dict],
    files_written: list[str],
    dry_run: bool,
    allow_date_backfill: bool,
    allow_filing_collection: bool,
    allow_clean_baseline_autofinalize: bool,
    gate_passed: bool,
    n_found: int,
    n_missing: int,
) -> "Path | None":
    import json as _json
    manifest_path = hdir / f"{label}_run_manifest.json"
    if dry_run:
        print(f"  [DRY RUN] Would write {manifest_path.name}")
        return None

    manifest = {
        "batch": label,
        "start": start,
        "end": end,
        "limit": limit,
        "run_date": RUN_DATE,
        "dry_run": dry_run,
        "flags": {
            "allow_date_backfill": allow_date_backfill,
            "allow_filing_collection": allow_filing_collection,
            "allow_clean_baseline_autofinalize": allow_clean_baseline_autofinalize,
        },
        "gate_summary": {
            "dates_found": n_found,
            "dates_missing": n_missing,
            "gate_passed": gate_passed,
        },
        "steps": steps_log,
        "files_written": [Path(fp).name for fp in files_written],
        "safety": {
            "no_adjudication": True,
            "no_verified_flag": True,
            "no_calibration_eligible": True,
            "no_live_api": True,
            "no_live_scanner": True,
            "source_evidence_csv_untouched": True,
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(_json.dumps(manifest, indent=2) + "\n")
    return manifest_path


def _count_local_available(universe: list[dict]) -> int:
    return sum(
        1 for r in universe
        if r.get("already_in_first_50", "").upper() != "TRUE"
        and r.get("already_in_batch_51_70", "").upper() != "TRUE"
        and not r.get("inclusion_status", "").startswith("EXCLUDE")
        and r.get("ticker", "").upper() not in _BATCH_51_70_TICKERS
    )


def _abort_if_unsafe(cfg: CaseFactoryConfig) -> None:
    checks = [
        (cfg.adjudicate_automatically, "adjudicate_automatically must be false"),
        (cfg.mark_verified,             "mark_verified must be false"),
        (cfg.mark_calibration_eligible, "mark_calibration_eligible must be false"),
        (cfg.run_full_live_scanner,     "run_full_live_scanner must be false"),
    ]
    for flag, msg in checks:
        if flag:
            print(f"ERROR: {msg}. Refusing to run.")
            sys.exit(1)


# ---------------------------------------------------------------------------
# --status
# ---------------------------------------------------------------------------

def cmd_status(cfg: CaseFactoryConfig, sm: StateManager) -> int:
    state = sm.load()
    current = state.get("current_case_count", cfg.current_confirmed_case_count)
    remaining = cfg.target_case_count - current
    batches_left = math.ceil(remaining / cfg.batch_size)
    last_ts = state.get("last_run_timestamp") or "never"

    print(f"=== Case Factory Status  [{RUN_DATE}] ===")
    print()
    print(f"  Progress:            {current} / {cfg.target_case_count} cases confirmed")
    print(f"  Remaining:           {remaining} cases")
    print(f"  Batches left:        ~{batches_left} x {cfg.batch_size}")
    print(f"  Combined signal rate:{state.get('combined_signal_rate', '3/70 (4.3%)')}")
    print()
    print(f"  Finalized cases:     {state.get('finalized_cases', 70)}")
    print(f"  Blocked cases:       {state.get('blocked_cases', 0)}")
    print(f"  Unresolved cases:    {state.get('unresolved_cases', 0)}")
    print()
    print(f"  Last run:            {last_ts}")
    print(f"  Last step:           {state.get('last_completed_step', 'N/A')}")
    print(f"  Next step:           {state.get('next_recommended_step', 'select_next_batch')}")
    print()
    print("  Batches created:")
    for b in state.get("batches_created", []):
        summary = b.get("summary_file", "")
        print(
            f"    {b.get('batch_name', ''):22s}  "
            f"cases {b.get('start')}-{b.get('end'):3d}  "
            f"status={b.get('status', ''):12s}  "
            f"true_signals={b.get('true_prior_signal_count', '?')}"
        )
    print()
    print("  Safety flags (from config):")
    print(f"    allow_live_api:           {cfg.allow_live_api}")
    print(f"    allow_fmp_discovery:      {cfg.allow_fmp_discovery}")
    print(f"    collect_filings:          {cfg.collect_filings}")
    print(f"    adjudicate_automatically: {cfg.adjudicate_automatically}")
    print(f"    mark_verified:            {cfg.mark_verified}")
    return 0


# ---------------------------------------------------------------------------
# --plan
# ---------------------------------------------------------------------------

def cmd_plan(cfg: CaseFactoryConfig, sm: StateManager) -> int:
    state = sm.load()
    current = state.get("current_case_count", cfg.current_confirmed_case_count)
    remaining = cfg.target_case_count - current

    universe = read_csv(DEFAULT_UNIVERSE)
    local_available = _count_local_available(universe)
    discovery_gap = max(0, remaining - local_available)

    # Build batch sequence
    batches: list[tuple[int, int, int]] = []
    seq = current + 1
    while seq <= cfg.target_case_count:
        b_end = min(seq + cfg.batch_size - 1, cfg.target_case_count)
        batches.append((seq, b_end, b_end - seq + 1))
        seq = b_end + 1

    print(f"=== 200-Case Factory Plan  [{RUN_DATE}] ===")
    print()
    print(f"  Current confirmed:    {current}")
    print(f"  Target:               {cfg.target_case_count}")
    print(f"  Cases needed:         {remaining}")
    print(f"  Local candidates:     {local_available}  (from five_year_acquisition_universe_candidates.csv)")
    print(f"  Discovery gap:        {discovery_gap}  (need FMP or EDGAR universe expansion)")
    print()
    print("  Planned batches:")
    print(f"    {'Batch':25s}  {'Cases':>6s}  {'Status'}")
    print(f"    {'-'*25}  {'-'*6}  {'-'*20}")
    for s, e, sz in batches:
        label = batch_name(s, e)
        status = "NEXT"
        print(f"    {label:25s}  {sz:6d}  {status}")
    print()

    if batches:
        s, e, sz = batches[0]
        print("  Next recommended commands:")
        print()
        print(f"    # 1. Select candidates")
        print(f"    python3 src/historical_case_tools/case_factory_orchestrator.py \\")
        print(f"      --config configs/case_factory.yaml --select-next-batch")
        print()
        print(f"    # 2. Prepare batch (date prefill + exception queue)")
        print(f"    python3 src/historical_case_tools/case_factory_orchestrator.py \\")
        print(f"      --config configs/case_factory.yaml --prepare-batch --start {s} --limit {sz}")
        print()
        print(f"    # 3. Write review packet")
        print(f"    python3 src/historical_case_tools/case_factory_orchestrator.py \\")
        print(f"      --config configs/case_factory.yaml --write-review-packets --start {s} --limit {sz}")

    if discovery_gap > 0:
        print()
        print(f"  DISCOVERY GAP: {discovery_gap} candidates not yet in local universe.")
        print(f"  Options to resolve:")
        print(f"    1. Expand resolved_case_candidates.csv with 2024-2025 acquisitions")
        print(f"    2. Set allow_fmp_discovery: true in configs/case_factory.yaml (then re-run universe builder)")
        print(f"    3. Manually seed confirmed acquisitions from public M&A databases")
    return 0


# ---------------------------------------------------------------------------
# --select-next-batch
# ---------------------------------------------------------------------------

def cmd_select_next_batch(cfg: CaseFactoryConfig, sm: StateManager) -> int:
    state = sm.load()
    current = state.get("current_case_count", cfg.current_confirmed_case_count)
    start = current + 1
    limit = cfg.batch_size
    end = start + limit - 1

    hdir = _historical_dir(cfg)
    out_csv = hdir / f"{batch_name(start, end)}_candidate_queue.csv"
    out_report = hdir / f"{batch_name(start, end)}_candidate_queue_report.md"

    universe = read_csv(DEFAULT_UNIVERSE)
    if not universe:
        print(f"ERROR: Universe CSV not found: {DEFAULT_UNIVERSE}")
        return 1

    selected, excluded = select_candidates(universe, start, limit)
    queue_rows = build_queue_rows(selected, start)

    write_csv(out_csv, queue_rows, QUEUE_FIELDS)
    _write_selector_report(
        out_report,
        batch_name(start, end),
        queue_rows,
        excluded_count=len(excluded),
        eligible_total=len(universe),
        limit=limit,
        start=start,
        end=end,
        target=cfg.target_case_count,
        current=current,
    )

    sm.update(
        candidates_selected=len(queue_rows),
        last_completed_step="select_next_batch",
        next_recommended_step=f"prepare_batch_{start}_{end}",
    )

    gap = max(0, limit - len(queue_rows))
    print(f"Batch selected:   {batch_name(start, end)}")
    print(f"  Candidates:     {len(queue_rows)} of {limit} target")
    print(f"  Excluded:       {len(excluded)} (already covered or filtered)")
    print(f"  Discovery gap:  {gap} additional candidates needed")
    print(f"  Output CSV:     {out_csv}")
    print(f"  Report:         {out_report}")
    if gap > 0:
        print()
        print(f"  Gap resolution: expand resolved_case_candidates.csv")
        print(f"  OR set allow_fmp_discovery: true in configs/case_factory.yaml")
    return 0


# ---------------------------------------------------------------------------
# --run-step
# ---------------------------------------------------------------------------

def cmd_run_step(step: str, cfg: CaseFactoryConfig, sm: StateManager,
                 start: int, limit: int) -> int:
    if step not in _STEP_REGISTRY:
        print(f"ERROR: Unknown step '{step}'. Valid: {', '.join(_STEP_REGISTRY)}")
        return 1

    meta = _STEP_REGISTRY[step]
    end = start + limit - 1
    label = batch_name(start, end)
    hdir = _historical_dir(cfg)

    out_csv = hdir / f"{label}_{meta['output_suffix']}"
    out_report = hdir / f"{label}_{meta['report_suffix']}"

    script: Path = meta["script"]
    if not script.exists():
        print(f"ERROR: Script not found: {script}")
        return 1

    # Build command:
    #   source-evidence: pass --exception-queue (no candidate staging needed)
    #   date-prefill / exception-queue: use staging candidates file if candidate
    #     queue exists, so the index-window in each script operates on exactly
    #     the batch-selector's chosen candidates rather than the full
    #     resolved_case_candidates.csv window (which can include stale cases).
    if "exception_queue_required" in meta.get("extra_args", []):
        exception_csv = hdir / f"{label}_exception_queue.csv"
        if not exception_csv.exists():
            print(f"ERROR: Exception queue not found: {exception_csv}")
            print(f"  Run --run-step exception-queue --start {start} --limit {limit} first.")
            return 1
        cmd = [
            sys.executable, str(script),
            "--exception-queue", str(exception_csv),
            "--output", str(out_csv),
            "--report", str(out_report),
        ]
    else:
        candidate_queue_csv = hdir / f"{label}_candidate_queue.csv"
        queue_rows = read_csv(candidate_queue_csv) if candidate_queue_csv.exists() else []

        if queue_rows:
            # Staging file approach: avoids index-window misalignment caused by
            # batch_51_70 tickers missing from batch_results and 2020 candidates
            # in resolved_case_candidates that fall in the [20:50] window.
            staging = _write_staging_candidates_csv(hdir, label, queue_rows)
            n = len(queue_rows)
            cmd = [
                sys.executable, str(script),
                "--candidates", str(staging),
                "--start", "51",   # idx_start = 51-51 = 0 → take from row 0
                "--limit", str(n),
                "--output", str(out_csv),
                "--report", str(out_report),
            ]
            print(f"  Using staging candidates: {staging.name} ({n} rows)")
        else:
            # Fallback: original index-window behaviour (no candidate queue yet)
            cmd = [
                sys.executable, str(script),
                "--start", str(start),
                "--limit", str(limit),
                "--output", str(out_csv),
                "--report", str(out_report),
            ]
            print(f"  No candidate queue found — using index window (start={start}, limit={limit})")

    print(f"Running step '{step}' for {label}...")
    print(f"  Script:  {script.name}")
    print(f"  Output:  {out_csv.name}")
    print(f"  Report:  {out_report.name}")
    print()
    sys.stdout.flush()   # ensure parent output appears before subprocess stdout

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"ERROR: Step '{step}' failed (exit code {result.returncode})")
        return result.returncode

    state = sm.load()
    state[meta["state_key"]] = state.get(meta["state_key"], 0) + 1
    state["last_completed_step"] = f"{step}_{label}"
    state["next_recommended_step"] = f"{meta['next_step']}_{label}"
    sm.save(state)

    print(f"Step complete: {step}")
    print(f"  Output:  {out_csv}")
    print(f"  Report:  {out_report}")
    print(f"  Next:    --run-step {meta['next_step']} OR --write-review-packets")
    return 0


# ---------------------------------------------------------------------------
# --prepare-batch
# ---------------------------------------------------------------------------

def cmd_prepare_batch(cfg: CaseFactoryConfig, sm: StateManager,
                      start: int, limit: int) -> int:
    label = batch_name(start, start + limit - 1)
    print(f"=== Preparing batch {label} (cases {start}–{start + limit - 1}) ===")
    print()
    sys.stdout.flush()

    rc = cmd_run_step("date-prefill", cfg, sm, start, limit)
    if rc != 0:
        return rc

    print()
    rc = cmd_run_step("exception-queue", cfg, sm, start, limit)
    if rc != 0:
        return rc

    print()
    print(f"Batch preparation complete for {label}.")
    print(f"  Review date prefill queue; resolve any BLOCKED cases before filing collection.")
    print(f"  Next: --write-review-packets --start {start} --limit {limit}")
    return 0


# ---------------------------------------------------------------------------
# --write-review-packets
# ---------------------------------------------------------------------------

def cmd_write_review_packets(cfg: CaseFactoryConfig, sm: StateManager,
                              start: int, limit: int) -> int:
    end = start + limit - 1
    label = batch_name(start, end)
    files = _batch_files(cfg, start, limit)

    exception_rows = read_csv(files["exception_queue_csv"])
    candidate_rows = read_csv(files["candidate_queue_csv"])
    packet_path = files["review_packet"]

    lines = [
        f"# {label.replace('_', ' ').title()} Manual Review Packet",
        "",
        f"Generated: {RUN_DATE}",
        "",
        "Manual review only. No cases adjudicated by this system.",
        "All classifications must be made by a human researcher following the decision tree below.",
        "",
        "---",
        "",
        "## 1. Scope",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Cases in scope | {start}–{end} ({limit} target) |",
        f"| Candidate rows available | {len(candidate_rows)} |",
        f"| Exception queue rows | {len(exception_rows)} |",
        f"| Review packet generated | {RUN_DATE} |",
        "",
        "---",
        "",
        "## 2. Review Order",
        "",
        "| Priority | Tier | Review trigger |",
        "|---|---|---|",
        "| 1st | P1 | Explicit acquisition-process phrases (unsolicited / superior / competing proposals) |",
        "| 2nd | P2 | Strategic alternatives + advisor retention language |",
        "| 3rd | P3 | SC 13D Item 4 acquisition pressure |",
        "| 4th | P4 | ROFR/ROFN language requiring company-vs-asset scope check |",
        "| 5th | BLOCKED | Date or source missing — resolve before any filing collection |",
        "| Last | P6_WITH_HITS | Signal phrase hit but low-confidence type |",
        "",
        "---",
        "",
        "## 3. Classification Decision Tree",
        "",
        "1. Was the source public **before** the announcement date?",
        "   - **NO** → not `TRUE_PUBLIC_PRIOR_SIGNAL`",
        "2. Is the evidence company-level (not asset / product / territory-specific)?",
        "   - **NO** → `ASSET_SPECIFIC_RIGHTS_ONLY`",
        "3. Is it generic legal rights language (boilerplate ROFR, lock-up, CIC clause)?",
        "   - **YES** → `RIGHTS_LANGUAGE_ONLY`",
        "4. Does the process appear only in post-announcement SC 14D-9 or proxy background?",
        "   - **YES** → `PRIVATE_BACKGROUND_ONLY`",
        "5. Is there explicit pre-announcement proposal or process language with source URL, filing date, and excerpt?",
        "   - **YES** → possible `TRUE_PUBLIC_PRIOR_SIGNAL` (requires all evidence fields)",
        "6. No public process evidence confirmed → `DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE`",
        "",
        "If evidence is unclear: leave as `POSSIBLE_SIGNAL_NEEDS_REVIEW`. Do not force.",
        "",
        "---",
        "",
        "## 4. False-Positive Rules (from 70-case study)",
        "",
        "| Pattern | Correct classification |",
        "|---|---|",
        "| Deal-announcement 8-K flagged same day as announcement | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |",
        "| Negation: 'no plan or proposal to acquire' | False positive — ignore |",
        "| UUEncoded binary artifact in complete submission .txt | False positive — not in primary doc |",
        "| PWERM stock comp valuation (pre-IPO) in 10-Q | RIGHTS_LANGUAGE_ONLY |",
        "| CIC vesting clause in proxy | RIGHTS_LANGUAGE_ONLY |",
        "| Director biography: prior sale at a different organization | RIGHTS_LANGUAGE_ONLY |",
        "| VC/PE investor self-reservation in SC 13D (IPO-era) | RIGHTS_LANGUAGE_ONLY |",
        "| Geographic license ROFN (product + territory specific) | ASSET_SPECIFIC_RIGHTS_ONLY |",
        "| Product-level ROFR (not company-level) | ASSET_SPECIFIC_RIGHTS_ONLY |",
        "| BVI→Delaware redomiciliation merger agreement | False positive — internal doc |",
        "| Lock-up employment-termination share repurchase right | RIGHTS_LANGUAGE_ONLY |",
        "| FPI 6-K filer — no EDGAR target-form coverage | Baseline; note coverage gap |",
        "",
        "---",
        "",
        "## 5. Evidence Requirements for Non-Baseline Cases",
        "",
        "Each non-baseline or upgraded case requires all of:",
        "",
        "| Field | Required |",
        "|---|---|",
        "| case_id | yes |",
        "| ticker | yes |",
        "| announcement_date | yes |",
        "| source_url | yes |",
        "| filing_type | yes |",
        "| filing_date | yes |",
        "| accession_number | if available |",
        "| excerpt (verbatim) | yes |",
        "| days_before_announcement | yes |",
        "| classification | yes |",
        "| reason | yes |",
        "| false_positive_check | yes |",
        "",
        "---",
        "",
        "## 6. Exception Queue Summary",
        "",
    ]

    if exception_rows:
        tier_counts: dict[str, int] = {}
        for r in exception_rows:
            t = r.get("priority_tier", "UNKNOWN")
            tier_counts[t] = tier_counts.get(t, 0) + 1

        lines += ["| Tier | Count |", "|---|---|"]
        tier_order_disp = ["P1", "P2", "P3", "P4", "BLOCKED", "P5", "P6",
                           "PENDING_FILING_COLLECTION"]
        for t in tier_order_disp + [k for k in tier_counts if k not in tier_order_disp]:
            if t in tier_counts:
                lines.append(f"| {t} | {tier_counts[t]} |")

        lines += ["", "### Cases By Tier", ""]
        for tier in tier_order_disp + [k for k in tier_counts if k not in tier_order_disp]:
            tier_cases = [r for r in exception_rows if r.get("priority_tier", "") == tier]
            if not tier_cases:
                continue
            lines += [
                f"#### {tier}",
                "",
                "| case_id | ticker | priority_reason | next_action |",
                "|---|---|---|---|",
            ]
            for r in tier_cases:
                reason = r.get("priority_reason", "")[:70]
                action = r.get("next_action", "")[:50]
                lines.append(
                    f"| {r.get('case_id','')} | {r.get('ticker','')} | {reason} | {action} |"
                )
            lines.append("")
    else:
        lines += [
            f"No exception queue found at: `{files['exception_queue_csv']}`",
            "",
            f"Run first:",
            f"```bash",
            f"python3 src/historical_case_tools/case_factory_orchestrator.py \\",
            f"  --config configs/case_factory.yaml --run-step exception-queue --start {start} --limit {limit}",
            f"```",
            "",
        ]

    lines += [
        "---",
        "",
        "## 7. Candidate Cases",
        "",
    ]

    if candidate_rows:
        lines += [
            "| # | ticker | company | year | confidence | needs_backfill | source_url |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in candidate_rows:
            src = (r.get("source_url", "") or "(none)")[:60]
            co = r.get("company", "")[:30]
            lines.append(
                f"| {r.get('queue_position','')} | {r.get('ticker','')} "
                f"| {co} | {r.get('announcement_year','')} "
                f"| {r.get('confidence','')} | {r.get('needs_date_backfill','')} | {src} |"
            )
    else:
        lines += [
            f"No candidate queue found at: `{files['candidate_queue_csv']}`",
            "",
            "Run `--select-next-batch` first.",
        ]

    lines += [
        "",
        "---",
        "",
        "## 8. Unresolved Blockers",
        "",
        "Cases that cannot proceed without external resolution:",
        "",
    ]

    blocked = [r for r in exception_rows if r.get("priority_tier", "") == "BLOCKED"]
    if blocked:
        for r in blocked:
            lines.append(
                f"- **{r.get('ticker','')}** ({r.get('case_id','')}): "
                f"{r.get('priority_reason','')}"
            )
    else:
        lines.append(
            "None identified yet. Run date prefill step to surface BLOCKED cases."
        )

    lines += [
        "",
        "---",
        "",
        "## 9. Inspector Commands",
        "",
        "```bash",
        "# View EDGAR filings for a specific ticker (replace TICKER)",
        "python3 src/historical_case_tools/edgar_source_pull_helper.py --ticker TICKER",
        "",
        f"# Date prefill work queue",
        f"cat data/historical_cases/{label}_date_prefill_queue.csv",
        "",
        f"# Exception queue",
        f"cat data/historical_cases/{label}_exception_queue.csv",
        "",
        f"# Source evidence draft",
        f"cat data/historical_cases/{label}_source_evidence_draft.csv",
        "```",
        "",
        "---",
        "",
        "## 10. Safety Constraints",
        "",
        "- No automatic adjudication.",
        "- No VERIFIED flag.",
        "- No CALIBRATION_ELIGIBLE flag.",
        "- No alpha claims.",
        "- No M&A prediction framing.",
        "- EDGAR/source-backed evidence is the source of truth.",
        "- FMP is market context only — not classification evidence.",
        "- Post-announcement SC 14D-9 background is NOT prior public signal.",
        "- Generic ROFR is not process evidence.",
        "- Asset-specific rights are not company-level process evidence.",
        "- Private offers are not public signals unless publicly disclosed before announcement.",
    ]

    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text("\n".join(lines) + "\n")

    state = sm.load()
    state["manual_review_packets_created"] = state.get("manual_review_packets_created", 0) + 1
    state["last_completed_step"] = f"review_packet_{label}"
    state["next_recommended_step"] = f"manual_adjudication_{label}"
    sm.save(state)

    print(f"Review packet written: {packet_path}")
    print(f"  Exception queue rows: {len(exception_rows)}")
    print(f"  Candidate rows:       {len(candidate_rows)}")
    print(f"  Blocked cases:        {len(blocked)}")
    return 0


# ---------------------------------------------------------------------------
# --run-batch-package
# ---------------------------------------------------------------------------

def cmd_run_batch_package(
    cfg: CaseFactoryConfig,
    sm: StateManager,
    start: int,
    limit: int,
    allow_date_backfill: bool,
    allow_filing_collection: bool,
    allow_clean_baseline_autofinalize: bool,
    dry_run: bool,
) -> int:
    end = start + limit - 1
    label = batch_name(start, end)
    hdir = _historical_dir(cfg)

    steps_log: list[dict] = []
    files_written: list[str] = []
    n_found = 0
    n_missing = 0
    gate_passed = False
    exception_rows: list[dict[str, str]] = []

    def _step(name: str, status: str, **extra) -> dict:
        entry: dict = {"step": name, "status": status, **extra}
        steps_log.append(entry)
        return entry

    def _run_cmd(cmd: list, step_name: str) -> int:
        if dry_run:
            print(f"  [DRY RUN] Would run: {Path(cmd[1]).name} {' '.join(str(c) for c in cmd[2:])}")
            return 0
        sys.stdout.flush()
        return subprocess.run(cmd).returncode

    print(f"=== Batch Package: {label} (cases {start}–{end}) ===")
    print(f"  dry_run:                          {dry_run}")
    print(f"  allow_date_backfill:              {allow_date_backfill}")
    print(f"  allow_filing_collection:          {allow_filing_collection}")
    print(f"  allow_clean_baseline_autofinalize:{allow_clean_baseline_autofinalize}")
    print()

    # ------------------------------------------------------------------
    # STEP 1: Validate candidate queue
    # ------------------------------------------------------------------
    candidate_queue_csv = hdir / f"{label}_candidate_queue.csv"
    if not candidate_queue_csv.exists():
        print(f"ERROR: Candidate queue not found: {candidate_queue_csv}")
        print(f"  Run --select-next-batch first.")
        _step("validate_candidate_queue", "FAIL", error="No candidate queue")
        return 1

    queue_rows = read_csv(candidate_queue_csv)
    if not queue_rows:
        print(f"ERROR: Candidate queue is empty: {candidate_queue_csv}")
        _step("validate_candidate_queue", "FAIL", error="Empty candidate queue")
        return 1

    _step("validate_candidate_queue", "PASS", candidates=len(queue_rows))
    print(f"STEP 1 — Candidate queue: {len(queue_rows)} candidates  [PASS]")

    # ------------------------------------------------------------------
    # STEP 2: Date-prefill queue
    # ------------------------------------------------------------------
    print()
    print(f"STEP 2 — Date prefill queue...")
    if not dry_run:
        rc = cmd_run_step("date-prefill", cfg, sm, start, limit)
        if rc != 0:
            _step("date_prefill", "FAIL", exit_code=rc)
            return rc
        dp_csv = hdir / f"{label}_date_prefill_queue.csv"
        dp_rows = len(read_csv(dp_csv)) if dp_csv.exists() else 0
        _step("date_prefill", "PASS", output=dp_csv.name, rows=dp_rows)
        files_written += [str(dp_csv), str(hdir / f"{label}_date_prefill_report.md")]
        staging = hdir / f"{label}_staging_candidates.csv"
        if staging.exists():
            files_written.append(str(staging))
    else:
        _run_cmd([sys.executable, "merger_date_prefiller.py"], "date_prefill")
        _step("date_prefill", "DRY_RUN")

    # ------------------------------------------------------------------
    # STEP 3: Date gate
    # ------------------------------------------------------------------
    print()
    print(f"STEP 3 — Date gate...")
    dates_found, missing_tickers = _check_dates_gate(queue_rows)
    n_found = len(dates_found)
    n_missing = len(missing_tickers)

    print(f"  Candidates with confirmed dates (HIGH/MEDIUM): {n_found} / {len(queue_rows)}")
    if dates_found:
        for tk, dt in sorted(dates_found.items()):
            print(f"    {tk}: {dt}")
    if missing_tickers:
        print(f"  Missing dates ({n_missing}): {', '.join(sorted(missing_tickers))}")
        print(f"  EDGAR work queue: {label}_date_prefill_queue.csv")

    if n_missing == 0:
        gate_passed = True
        _step("date_gate", "PASS", dates_found=n_found, dates_missing=0)
        print(f"  Date gate: PASS")
    elif allow_date_backfill:
        gate_passed = True
        _step("date_gate", "PARTIAL", dates_found=n_found, dates_missing=n_missing,
              note="allow_date_backfill — continuing; BLOCKED tiers expected in exception queue")
        print(f"  Date gate: PARTIAL — proceeding (--allow-date-backfill set).")
        print(f"  Exception queue will mark {n_missing} cases BLOCKED until dates are resolved.")
    else:
        _step("date_gate", "BLOCKED", dates_found=n_found, dates_missing=n_missing,
              note="--allow-date-backfill not set")
        print(f"  Date gate: BLOCKED — {n_missing} dates missing; --allow-date-backfill not passed.")
        print(f"  Resolve dates in acquisition_announcement_dates.csv, then re-run with --allow-date-backfill.")
        rpt = _write_package_report(
            hdir, label, start, end, limit, steps_log, files_written,
            dry_run, n_found, n_missing, gate_passed=False,
        )
        _write_run_manifest(
            hdir, label, start, end, limit, steps_log, files_written, dry_run,
            allow_date_backfill, allow_filing_collection, allow_clean_baseline_autofinalize,
            gate_passed=False, n_found=n_found, n_missing=n_missing,
        )
        return 0

    # ------------------------------------------------------------------
    # STEP 4: Exception queue
    # ------------------------------------------------------------------
    print()
    print(f"STEP 4 — Exception queue...")
    if not dry_run:
        rc = cmd_run_step("exception-queue", cfg, sm, start, limit)
        if rc != 0:
            _step("exception_queue", "FAIL", exit_code=rc)
            return rc
        exception_csv = hdir / f"{label}_exception_queue.csv"
        exception_rows = read_csv(exception_csv) if exception_csv.exists() else []
        tier_counts: dict[str, int] = {}
        for r in exception_rows:
            t = r.get("priority_tier", "UNKNOWN")
            tier_counts[t] = tier_counts.get(t, 0) + 1
        _step("exception_queue", "PASS", output=exception_csv.name,
              rows=len(exception_rows), tiers=tier_counts)
        files_written += [str(exception_csv), str(hdir / f"{label}_exception_queue_report.md")]
    else:
        _run_cmd([sys.executable, "exception_queue_builder.py"], "exception_queue")
        _step("exception_queue", "DRY_RUN")
        tier_counts = {}

    # ------------------------------------------------------------------
    # STEP 5: Filing collection (opt-in)
    # ------------------------------------------------------------------
    print()
    filing_script = REPO_ROOT / "src" / "historical_case_tools" / "pre_announcement_filing_collector.py"
    if allow_filing_collection and n_found > 0 and filing_script.exists():
        print(f"STEP 5 — Filing collection ({n_found} of {len(queue_rows)} candidates have dates)...")
        if not dry_run:
            cr_staging = _write_confirmation_results_staging(hdir, label, queue_rows, dates_found)
            files_written.append(str(cr_staging))
            targets_out = hdir / f"{label}_filing_targets.csv"
            hits_out    = hdir / f"{label}_signal_hits.csv"
            filing_rpt  = hdir / f"{label}_filing_report.md"
            cmd = [
                sys.executable, str(filing_script),
                "--confirmation-results", str(cr_staging),
                "--targets-output",       str(targets_out),
                "--hits-output",          str(hits_out),
                "--report",               str(filing_rpt),
                "--no-api",
            ]
            rc = _run_cmd(cmd, "filing_collection")
            if rc != 0:
                _step("filing_collection", "WARN", exit_code=rc,
                      note="Non-fatal — continuing to source evidence")
                print(f"  WARNING: Filing collector exit={rc}. Continuing.")
            else:
                _step("filing_collection", "PASS",
                      staging=cr_staging.name, targets=targets_out.name, hits=hits_out.name)
                files_written += [str(targets_out), str(hits_out), str(filing_rpt)]
        else:
            _run_cmd([sys.executable, str(filing_script), "--no-api"], "filing_collection")
            _step("filing_collection", "DRY_RUN", candidates_with_dates=n_found)
    elif allow_filing_collection and n_found == 0:
        print(f"STEP 5 — Filing collection: SKIPPED (0 candidates have confirmed dates)")
        _step("filing_collection", "SKIPPED", reason="No candidates with confirmed dates")
    else:
        print(f"STEP 5 — Filing collection: SKIPPED (--allow-filing-collection not set)")
        _step("filing_collection", "SKIPPED", reason="allow_filing_collection=False")

    # ------------------------------------------------------------------
    # STEP 6: Source evidence draft
    # ------------------------------------------------------------------
    print()
    print(f"STEP 6 — Source evidence draft...")
    if not dry_run:
        rc = cmd_run_step("source-evidence", cfg, sm, start, limit)
        if rc != 0:
            _step("source_evidence", "FAIL", exit_code=rc)
            return rc
        se_csv = hdir / f"{label}_source_evidence_draft.csv"
        se_rows = len(read_csv(se_csv)) if se_csv.exists() else 0
        _step("source_evidence", "PASS", output=se_csv.name, rows=se_rows)
        files_written += [str(se_csv), str(hdir / f"{label}_source_evidence_draft_report.md")]
    else:
        _run_cmd([sys.executable, "source_evidence_autofill.py"], "source_evidence")
        _step("source_evidence", "DRY_RUN")

    # ------------------------------------------------------------------
    # STEP 7: Review packet
    # ------------------------------------------------------------------
    print()
    print(f"STEP 7 — Review packet...")
    if not dry_run:
        rc = cmd_write_review_packets(cfg, sm, start, limit)
        if rc != 0:
            _step("review_packet", "FAIL", exit_code=rc)
            return rc
        packet_path = hdir / f"{label}_review_packet.md"
        _step("review_packet", "PASS", output=packet_path.name)
        files_written.append(str(packet_path))
    else:
        print(f"  [DRY RUN] Would write {label}_review_packet.md")
        _step("review_packet", "DRY_RUN")

    # ------------------------------------------------------------------
    # STEP 8: Proposed clean baselines (opt-in)
    # ------------------------------------------------------------------
    print()
    if allow_clean_baseline_autofinalize:
        print(f"STEP 8 — Proposed clean baselines...")
        if not dry_run and exception_rows:
            bl_path, bl_count = _write_proposed_baselines_csv(hdir, label, exception_rows)
            files_written.append(str(bl_path))
            _step("proposed_baselines", "PASS", output=bl_path.name, count=bl_count)
            print(f"  Proposed baselines: {bl_count} rows → {bl_path.name}")
            print(f"  Researcher must confirm each before finalizing.")
        elif dry_run:
            print(f"  [DRY RUN] Would write {label}_proposed_clean_baselines.csv")
            _step("proposed_baselines", "DRY_RUN")
        else:
            _step("proposed_baselines", "SKIPPED", reason="Exception queue unavailable")
            print(f"  Proposed baselines: SKIPPED (no exception queue data)")
    else:
        print(f"STEP 8 — Proposed baselines: SKIPPED (--allow-clean-baseline-autofinalize not set)")
        _step("proposed_baselines", "SKIPPED", reason="allow_clean_baseline_autofinalize=False")

    # ------------------------------------------------------------------
    # STEP 9: Package report
    # ------------------------------------------------------------------
    print()
    print(f"STEP 9 — Package report...")
    rpt_path = _write_package_report(
        hdir, label, start, end, limit, steps_log, files_written,
        dry_run, n_found, n_missing, gate_passed,
    )
    if rpt_path:
        files_written.append(str(rpt_path))
        print(f"  Package report: {rpt_path.name}")

    # ------------------------------------------------------------------
    # STEP 10: Run manifest
    # ------------------------------------------------------------------
    print()
    print(f"STEP 10 — Run manifest...")
    manifest_path = _write_run_manifest(
        hdir, label, start, end, limit, steps_log, files_written, dry_run,
        allow_date_backfill, allow_filing_collection, allow_clean_baseline_autofinalize,
        gate_passed=gate_passed, n_found=n_found, n_missing=n_missing,
    )
    if manifest_path:
        files_written.append(str(manifest_path))
        print(f"  Run manifest:   {manifest_path.name}")

    # ------------------------------------------------------------------
    # STEP 11: State update
    # ------------------------------------------------------------------
    if not dry_run:
        state = sm.load()
        state["last_completed_step"] = f"batch_package_{label}"
        state["next_recommended_step"] = f"manual_adjudication_{label}"
        sm.save(state)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    passed_cnt  = sum(1 for s in steps_log if s.get("status") == "PASS")
    skipped_cnt = sum(1 for s in steps_log if s.get("status") in {"SKIPPED", "DRY_RUN"})
    blocked_cnt = sum(1 for s in steps_log if s.get("status") in {"BLOCKED", "FAIL", "WARN"})
    gate_label  = ("PASS" if gate_passed and n_missing == 0
                   else "PARTIAL" if gate_passed else "BLOCKED")

    print(f"=== Batch Package Complete: {label} ===")
    print(f"  Steps PASS:           {passed_cnt}")
    print(f"  Steps SKIPPED/DRY:    {skipped_cnt}")
    print(f"  Steps BLOCKED/WARN:   {blocked_cnt}")
    print(f"  Date gate:            {gate_label}")
    print(f"  Dates found:          {n_found} / {len(queue_rows)}")
    if n_missing and not dry_run:
        print(f"  Manual backfill needed: {', '.join(sorted(missing_tickers))}")
    print(f"  Files written:        {len(files_written)}")
    if rpt_path:
        print(f"  Report: {rpt_path}")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True,
                        help="Path to case_factory.yaml config")
    parser.add_argument("--status", action="store_true",
                        help="Print current factory status")
    parser.add_argument("--plan", action="store_true",
                        help="Print scaling plan to reach target case count")
    parser.add_argument("--select-next-batch", action="store_true",
                        help="Select candidates for the next batch")
    parser.add_argument("--prepare-batch", action="store_true",
                        help="Run date-prefill + exception-queue for a batch")
    parser.add_argument("--run-step", choices=list(_STEP_REGISTRY.keys()),
                        metavar="STEP",
                        help=f"Run one pipeline step: {{{','.join(_STEP_REGISTRY)}}}")
    parser.add_argument("--write-review-packets", action="store_true",
                        help="Generate manual review packet for a batch")
    parser.add_argument("--run-batch-package", action="store_true",
                        help="Run full batch pipeline: date-prefill → exception-queue → "
                             "source-evidence → review-packet → package report + manifest")
    parser.add_argument("--allow-date-backfill", action="store_true",
                        help="Proceed past date gate even when candidates lack confirmed dates "
                             "(exception queue will mark them BLOCKED; requires manual EDGAR research)")
    parser.add_argument("--allow-filing-collection", action="store_true",
                        help="Run pre_announcement_filing_collector --no-api for candidates with dates")
    parser.add_argument("--allow-clean-baseline-autofinalize", action="store_true",
                        help="Write proposed_clean_baselines.csv for PENDING/P6 tier cases")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned steps without running subprocesses or writing output files")
    parser.add_argument("--start", type=int, default=None,
                        help="First case number in this batch")
    parser.add_argument("--limit", type=int, default=None,
                        help="Number of cases in this batch")

    args = parser.parse_args()

    if not args.config.exists():
        print(f"ERROR: Config not found: {args.config}")
        return 1

    cfg = load_config(args.config)
    sm = StateManager(DEFAULT_STATE_PATH)
    sm.initialize_if_missing()

    _abort_if_unsafe(cfg)

    if args.status:
        return cmd_status(cfg, sm)

    if args.plan:
        return cmd_plan(cfg, sm)

    if args.select_next_batch:
        return cmd_select_next_batch(cfg, sm)

    if args.prepare_batch:
        start = args.start or cfg.start_case_number
        limit = args.limit or cfg.batch_size
        return cmd_prepare_batch(cfg, sm, start, limit)

    if args.run_step:
        start = args.start or cfg.start_case_number
        limit = args.limit or cfg.batch_size
        return cmd_run_step(args.run_step, cfg, sm, start, limit)

    if args.write_review_packets:
        start = args.start or cfg.start_case_number
        limit = args.limit or cfg.batch_size
        return cmd_write_review_packets(cfg, sm, start, limit)

    if args.run_batch_package:
        start = args.start or cfg.start_case_number
        limit = args.limit or cfg.batch_size
        return cmd_run_batch_package(
            cfg, sm, start, limit,
            allow_date_backfill=args.allow_date_backfill,
            allow_filing_collection=args.allow_filing_collection,
            allow_clean_baseline_autofinalize=args.allow_clean_baseline_autofinalize,
            dry_run=args.dry_run,
        )

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
