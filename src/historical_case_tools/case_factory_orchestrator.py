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

    # Build command (source-evidence step uses exception-queue as its candidate input)
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
        cmd = [
            sys.executable, str(script),
            "--start", str(start),
            "--limit", str(limit),
            "--output", str(out_csv),
            "--report", str(out_report),
        ]

    print(f"Running step '{step}' for {label}...")
    print(f"  Script:  {script.name}")
    print(f"  Output:  {out_csv.name}")
    print(f"  Report:  {out_report.name}")
    print()

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

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
