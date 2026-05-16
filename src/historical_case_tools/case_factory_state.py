#!/usr/bin/env python3
"""
case_factory_state.py

Read and write case_factory_state.json for the historical case factory.
Tracks progress toward 200-case target across batches and steps.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "historical_cases" / "case_factory_state.json"

INITIAL_STATE: dict[str, Any] = {
    "target_case_count": 200,
    "current_case_count": 70,
    "batches_created": [
        {
            "batch_name": "first_50",
            "start": 1,
            "end": 50,
            "status": "finalized",
            "finalized_date": "2026-05-14",
            "true_prior_signal_count": 3,
            "combined_signal_rate": "3/50 (6%)",
            "summary_file": "data/historical_cases/biotech_prior_signal_50_case_final_summary.md",
        },
        {
            "batch_name": "batch_51_70",
            "start": 51,
            "end": 70,
            "status": "finalized",
            "finalized_date": "2026-05-15",
            "true_prior_signal_count": 0,
            "combined_signal_rate": "0/20 (0%)",
            "summary_file": "data/historical_cases/batch_51_70_final_summary.md",
        },
    ],
    "last_completed_case_number": 70,
    "candidates_selected": 0,
    "dates_backfilled": 0,
    "filings_collected": 0,
    "exception_queues_created": 0,
    "manual_review_packets_created": 0,
    "finalized_cases": 70,
    "blocked_cases": 0,
    "unresolved_cases": 0,
    "combined_true_prior_signal_count": 3,
    "combined_signal_rate": "3/70 (4.3%)",
    "latest_reports": {
        "50_case_summary": "data/historical_cases/biotech_prior_signal_50_case_final_summary.md",
        "batch_51_70_summary": "data/historical_cases/batch_51_70_final_summary.md",
        "universe_report": "data/historical_cases/five_year_acquisition_universe_report.md",
    },
    "last_run_timestamp": None,
    "last_completed_step": "batch_51_70_finalized",
    "next_recommended_step": "select_next_batch",
}


class StateManager:
    def __init__(self, path: Path = DEFAULT_STATE_PATH) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if self.path.exists():
            with self.path.open() as f:
                return json.load(f)
        return dict(INITIAL_STATE)

    def save(self, state: dict[str, Any]) -> None:
        state["last_run_timestamp"] = datetime.now(tz=timezone.utc).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")

    def update(self, **kwargs: Any) -> dict[str, Any]:
        state = self.load()
        state.update(kwargs)
        self.save(state)
        return state

    def add_batch(self, batch_record: dict[str, Any]) -> dict[str, Any]:
        """Append or replace a batch record (matched by batch_name)."""
        state = self.load()
        batches = state.setdefault("batches_created", [])
        name = batch_record.get("batch_name", "")
        state["batches_created"] = [b for b in batches if b.get("batch_name") != name]
        state["batches_created"].append(batch_record)
        self.save(state)
        return state

    def initialize_if_missing(self) -> dict[str, Any]:
        """Write initial state to disk if no state file exists."""
        if not self.path.exists():
            state = dict(INITIAL_STATE)
            self.save(state)
            return state
        return self.load()


if __name__ == "__main__":
    sm = StateManager()
    state = sm.initialize_if_missing()
    print(f"State file: {sm.path}")
    print(f"  current_case_count:    {state.get('current_case_count')}")
    print(f"  target_case_count:     {state.get('target_case_count')}")
    print(f"  last_completed_step:   {state.get('last_completed_step')}")
    print(f"  next_recommended_step: {state.get('next_recommended_step')}")
    print(f"  combined_signal_rate:  {state.get('combined_signal_rate')}")
    print(f"  batches_created:       {len(state.get('batches_created', []))}")
