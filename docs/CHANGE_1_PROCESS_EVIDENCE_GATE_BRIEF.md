# Change #1: Process Evidence Score Cap

Implemented PM feedback:

> Binary Gate for Process Evidence: If there is no real process signal, max score capped at 80.

## Files Changed

- `PRODUCTION_SCANNER_V12.py`
- `PROCESS_EVIDENCE_CAP_CHANGELOG.md`
- `CHANGE_1_PROCESS_EVIDENCE_GATE_BRIEF.md`

## Function Changed

- `calculate_ma_score`

## Function Added

- `has_real_process_evidence`

## Logic Added

The scanner still calculates the normal M&A attractiveness score first. After that, it checks whether the company has real process evidence. If not, the final score is capped at 80.

```python
PROCESS_EVIDENCE_SCORE_CAP = 80

real_process_evidence = has_real_process_evidence(
    activist_signal=activist_signal,
    text_signals=text_signals,
)

if not real_process_evidence and final_score > PROCESS_EVIDENCE_SCORE_CAP:
    final_score = PROCESS_EVIDENCE_SCORE_CAP
```

## Real Process Evidence

These qualify:

- Strategic alternatives / formal review language
- Activist SC 13D or clear activist sale pressure
- ROFN / ROFR / ROFO clause creating a specific acquisition pathway
- Explicit merger agreement language

These do not qualify:

- Analyst upside
- Change-of-control provisions
- Insider buying
- Valuation discount
- Strategic fit
- Platform attractiveness
- Acquirer need
- General M&A speculation
- Acquisition-pattern matching alone

## Verification

Ran:

```bash
python3 -m py_compile PRODUCTION_SCANNER_V12.py
```

Result: passed.

Also checked helper behavior for activist signal, strategic alternatives, ROFR, and CoC-only cases.

## Assumptions

- `PRODUCTION_SCANNER_V12.py` is the active V12.3 production scanner.
- Existing Layer 7 filing detection is the source of truth for process evidence.
- Change-of-control provisions remain visible as a signal, but do not satisfy the new gate by themselves.

## Future Improvements

Not implemented:

- Dedicated banker/advisor-hired parser
- Unit tests with fixture-based filing signals
- Optional `real_process_evidence` field in scan JSON
