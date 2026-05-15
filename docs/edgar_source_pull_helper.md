# EDGAR Source Pull Helper

`src/historical_case_tools/edgar_source_pull_helper.py` is a lightweight utility for historical acquisition case review. It pulls SEC filing source text into a local cache, normalizes the text for manual review, saves metadata, and can print snippets around process-signal phrases.

It is support material for review. The cache is not final classification evidence by itself.

## Why It Exists

Batch 51-70 and future acquisition batches require repeated source-text review. The recurring friction is finding a filing, downloading the text, cleaning SEC HTML, and searching for phrases such as "unsolicited proposal", "superior proposal", "strategic alternatives", or "tender offer".

This helper standardizes that step without changing classifications, source evidence, case packets, or batch outputs.

## Output Location

Files are saved under:

`data/historical_cases/source_text_cache/`

For each filing, the helper writes:

- `{case_id}_{ticker}_{filing_type}_{accession}.txt`
- `{case_id}_{ticker}_{filing_type}_{accession}.json`

The cache directory is ignored by git because downloaded filing text can become large and should be committed only when intentionally promoted into source evidence or a research artifact.

## Metadata Fields

The JSON sidecar includes:

- `case_id`
- `ticker`
- `filing_type`
- `source_url`
- `accession_number`
- `pulled_at`
- `text_length`
- `normalized_text_path`
- `notes`

## Example: Pull A Filing URL

```bash
python3 src/historical_case_tools/edgar_source_pull_helper.py \
  --url "https://www.sec.gov/Archives/edgar/data/899866/000110465920056508/tm2018594d2_ex99-1.htm" \
  --case-id "RHC-0042-ACQUIRED-PTLA" \
  --ticker "PTLA" \
  --filing-type "8-K"
```

## Example: Search Process Phrases

```bash
python3 src/historical_case_tools/edgar_source_pull_helper.py \
  --url "SEC_ARCHIVE_URL" \
  --case-id "RHC-XXXX" \
  --ticker "TICKER" \
  --filing-type "8-K" \
  --find "unsolicited proposal" \
  --find "superior proposal" \
  --find "strategic alternatives"
```

`--find` prints readable snippets around each match. It is designed for quick triage before deciding whether a filing belongs in `source_evidence.csv` or an adjudication queue.

## Example: Build URL From CIK And Accession

```bash
python3 src/historical_case_tools/edgar_source_pull_helper.py \
  --cik "899866" \
  --accession-number "0001104659-20-056508" \
  --primary-document "tm2018594d2_ex99-1.htm" \
  --case-id "RHC-0042-ACQUIRED-PTLA" \
  --ticker "PTLA" \
  --filing-type "8-K"
```

## Example: Normalize A Local File

```bash
python3 src/historical_case_tools/edgar_source_pull_helper.py \
  --input-file "/path/to/filing.html" \
  --case-id "RHC-XXXX" \
  --ticker "TICKER" \
  --filing-type "SC 14D-9" \
  --find "background of the merger"
```

## Notes For Batch 51-70

Use this helper after announcement dates are backfilled and before adjudication. Pull the merger announcement filing, Schedule 14D-9, proxy, or relevant pre-announcement filing into the local cache. Then use `--find` to identify process phrases and copy only source-backed excerpts into formal evidence files when needed.

Do not treat the cached text as a classification decision. It is a workbench for finding and preserving source text.
