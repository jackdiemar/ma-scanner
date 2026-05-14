# Acquisition Prior-Signal Mini-Study

Generated: 2026-05-12

## Scope

This mini-study summarizes the first 15 acquired historical cases reviewed through the prior-public-signal workflow:

MDVN, CPXX, RLYP, VTAE, CLCD, DMTX, AVXS, CASC, RXDX, ALDR, ARRY, CMTA, LOXO, NITE, ONCE.

The workflow used acquisition announcement dates, pre-announcement filing collection, collector audit, and source-text adjudication for possible hits. It does not mark any case `VERIFIED` or `CALIBRATION_ELIGIBLE`.

## Results

- Cases reviewed: 15
- Confirmed true prior public signal cases: 2
- Confirmed no-hit / false-positive cases: 2
- Still requiring manual EDGAR hit/no-hit confirmation: 11
- Adjudicated possible-hit rows: 16
- True prior public signal rows: 13
- False-positive rows: 3

## True Prior Public Signal Cases

| case_id | ticker | signal pattern | conservative read |
| --- | --- | --- | --- |
| RHC-0006-ACQUIRED-MDVN | MDVN | Public unsolicited proposal, competing bid pressure, board response, public process language | Strong MDVN-like case. The public signal existed before the Pfizer acquisition announcement. |
| RHC-0012-ACQUIRED-DMTX | DMTX | Public unsolicited proposal, superior proposal language, advisor/legal consultation, matching-right waiver context | Strong MDVN-like case beyond MDVN. The public signal existed before the Ultragenyx acquisition announcement. |

## Deal-Announcement Baseline Cases

Confirmed no-hit / false-positive baselines:

- CPXX: collector hit was generic rights language, not a whole-company process signal.
- ARRY: collector hits were asset/subsidiary-specific rights, not whole-company process evidence.

Likely no-hit candidates pending manual confirmation:

- RLYP
- VTAE
- CLCD
- AVXS
- CASC
- RXDX
- ALDR
- CMTA
- LOXO
- NITE
- ONCE

These 11 should remain `NEEDS_MANUAL_REVIEW` until EDGAR hit/no-hit work is source-backed.

## False-Positive Cases

| case_id | ticker | adjudication | rule learned |
| --- | --- | --- | --- |
| RHC-0005-ACQUIRED-CPXX | CPXX | RIGHTS_LANGUAGE_ONLY | Generic securities representations using "right of first refusal" are not process evidence. |
| RHC-0020-ACQUIRED-ARRY | ARRY | ASSET_SPECIFIC_RIGHTS_ONLY | Product, asset, subsidiary, or note-conversion rights are not whole-company sale process evidence unless the source clearly connects them to a company sale pathway. |

## Signal Types Found

The first true cases were not subtle ROFR cases. They were public contest/process cases:

- Public unsolicited acquisition proposal.
- Public rejected proposal.
- Competing bid or superior proposal.
- Board response after consultation with financial or legal advisors.
- Public process pressure through consent solicitation or matching-right waiver context.

No confirmed activist 13D sale-pressure case was found in this first 15-case batch.

## What The Scanner Could Have Caught

The scanner could plausibly have caught MDVN and DMTX if it had been running at the time with strong pre-announcement filing detection:

- MDVN: multiple 8-K and 10-Q filings before the final acquisition announcement contained public proposal and process language.
- DMTX: several 8-K filings before the final acquisition announcement contained unsolicited proposal, superior proposal, advisor, and matching-right context.

The scanner should have routed these as high-quality public process signals, not as score-only acquisition candidates.

## What The Scanner Could Not Have Caught

The scanner should not treat later proxy-only background negotiations as prior public signals. If a process only appears later in a merger proxy or Schedule 14D-9 background section, that is not a pre-announcement public signal.

The scanner also should not count:

- Generic securities-rights language.
- Routine collaboration, license, or asset rights.
- Product-specific ROFR/ROFN language unless tied to a company-level sale pathway.
- Final merger announcement language as if it were a prior signal.
- Private talks later disclosed after the deal announcement.

## Implications For Future Case Verification

1. Adjudication needs source filing text, not short collector excerpts alone.
2. Public competing-bid language is a high-confidence true signal when dated before the final acquisition announcement.
3. ROFR/ROFN hits require scope classification before they can affect a case-level prior-signal label.
4. `LIKELY_NO_HIT` is a workflow label only. It should not become `CONFIRMED_NO_HIT` without enough searched filings or manual EDGAR confirmation.
5. Case packets should show adjudication status directly so false positives are not re-promoted in later verification work.

## Next Verification Batch

Prioritize these pending cases for manual EDGAR hit/no-hit confirmation:

1. RLYP
2. VTAE
3. CLCD
4. AVXS
5. CASC

Rationale: they are inside the first 15 MDVN-like target set, still require manual confirmation, and have acquisition dates available. The next pass should record source-backed no-hit evidence or promote only public pre-announcement filing hits.

## Current Packet Fields Added

Case packets and `case_packet_index.csv` now include:

- `prior_signal_hit_status`
- `prior_signal_adjudication_status`
- `true_prior_signal_rows`
- `false_positive_rows`
- Packet-level prior signal adjudication section with source URLs, filing dates, classifications, and notes.
