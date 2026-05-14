# Acquisition Prior-Signal Batch Report

Generated: 2026-05-14

## Summary

- Cases processed: 50
- True prior public signals: 3
- Baseline candidates: 15
- False positives: 7
- Needs manual review: 0
- Blockers: 25
- No cases were marked `VERIFIED` or `CALIBRATION_ELIGIBLE`.

## Counts By Adjudication Status

- DATE_MISSING: 25
- DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE: 15
- PRIVATE_BACKGROUND_ONLY: 5
- TRUE_PUBLIC_PRIOR_SIGNAL: 3
- RIGHTS_LANGUAGE_ONLY: 1
- ASSET_SPECIFIC_RIGHTS_ONLY: 1

## True Prior Public Signal Candidates

| case_id | ticker | announcement_date | adjudication_status | confidence | packet_path |
| --- | --- | --- | --- | --- | --- |
| RHC-0006-ACQUIRED-MDVN | MDVN | 2016-08-22 | TRUE_PUBLIC_PRIOR_SIGNAL | HIGH | data/historical_cases/case_packets/RHC-0006-ACQUIRED-MDVN_MDVN.md |
| RHC-0012-ACQUIRED-DMTX | DMTX | 2017-10-03 | TRUE_PUBLIC_PRIOR_SIGNAL | HIGH | data/historical_cases/case_packets/RHC-0012-ACQUIRED-DMTX_DMTX.md |
| RHC-0025-ACQUIRED-TSRO | TSRO | 2018-12-03 | TRUE_PUBLIC_PRIOR_SIGNAL | MEDIUM | data/historical_cases/case_packets/RHC-0025-ACQUIRED-TSRO_TSRO.md |

## False Positives

| case_id | ticker | adjudication_status | confidence | next_action |
| --- | --- | --- | --- | --- |
| RHC-0005-ACQUIRED-CPXX | CPXX | RIGHTS_LANGUAGE_ONLY | LOW | Keep out of true prior-signal counts unless separate public whole-company process evidence is found. |
| RHC-0008-ACQUIRED-TBRA | TBRA | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. |
| RHC-0010-ACQUIRED-ARIA | ARIA | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. |
| RHC-0013-ACQUIRED-KITE | KITE | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. |
| RHC-0015-ACQUIRED-BIVV | BIVV | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. |
| RHC-0017-ACQUIRED-JUNO | JUNO | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. |
| RHC-0020-ACQUIRED-ARRY | ARRY | ASSET_SPECIFIC_RIGHTS_ONLY | LOW | Keep out of true prior-signal counts unless separate public whole-company process evidence is found. |

## Baseline Candidates

| case_id | ticker | announcement_date | filings_checked_count | adjudication_status | confidence |
| --- | --- | --- | --- | --- | --- |
| RHC-0001-ACQUIRED-NPSP | NPSP | 2015-01-12 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0002-ACQUIRED-PCYC | PCYC | 2015-03-06 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0003-ACQUIRED-ZSPH | ZSPH | 2015-11-06 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0004-ACQUIRED-ANAC | ANAC | 2016-05-16 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0007-ACQUIRED-RLYP | RLYP | 2016-07-21 | 38 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0009-ACQUIRED-VTAE | VTAE | 2016-09-14 | 18 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0011-ACQUIRED-CLCD | CLCD | 2017-01-18 | 7 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0014-ACQUIRED-AVXS | AVXS | 2018-04-09 | 43 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0016-ACQUIRED-CASC | CASC | 2018-01-31 | 33 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0018-ACQUIRED-RXDX | RXDX | 2017-12-22 | 37 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0019-ACQUIRED-ALDR | ALDR | 2019-09-16 | 36 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0021-ACQUIRED-CMTA | CMTA | 2019-02-25 | 3 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0022-ACQUIRED-LOXO | LOXO | 2019-01-07 | 34 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0023-ACQUIRED-NITE | NITE | 2019-03-04 | 2 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |
| RHC-0024-ACQUIRED-ONCE | ONCE | 2019-02-25 | 26 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM |

## Blockers

| case_id | ticker | adjudication_status | next_action |
| --- | --- | --- | --- |
| RHC-0026-ACQUIRED-ACHN | ACHN | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0027-ACQUIRED-BOLD | BOLD | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0028-ACQUIRED-DERM | DERM | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0029-ACQUIRED-FTSV | FTSV | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0030-ACQUIRED-MNTA | MNTA | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0031-ACQUIRED-MYOK | MYOK | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0032-ACQUIRED-PGNX | PGNX | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0033-ACQUIRED-PRNB | PRNB | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0034-ACQUIRED-PRVL | PRVL | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0035-ACQUIRED-ADMS | ADMS | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0036-ACQUIRED-DOVA | DOVA | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0037-ACQUIRED-DRNA | DRNA | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0038-ACQUIRED-FLXN | FLXN | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0039-ACQUIRED-FPRX | FPRX | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0040-ACQUIRED-GWPH | GWPH | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0041-ACQUIRED-PAND | PAND | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0042-ACQUIRED-PTLA | PTLA | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0043-ACQUIRED-TRIL | TRIL | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0044-ACQUIRED-VIE | VIE | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0045-ACQUIRED-XLRN | XLRN | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0046-ACQUIRED-ATRS | ATRS | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0047-ACQUIRED-AVEO | AVEO | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0048-ACQUIRED-BHVN | BHVN | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0049-ACQUIRED-CCXI | CCXI | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0050-ACQUIRED-CMPI | CMPI | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |

## Next 10 Manual Reviews

| case_id | ticker | announcement_date | filings_checked_count | possible_hits_count | adjudication_status | next_action |
| --- | --- | --- | --- | --- | --- | --- |
| RHC-0026-ACQUIRED-ACHN | ACHN |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0027-ACQUIRED-BOLD | BOLD |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0028-ACQUIRED-DERM | DERM |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0029-ACQUIRED-FTSV | FTSV |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0030-ACQUIRED-MNTA | MNTA |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0031-ACQUIRED-MYOK | MYOK |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0032-ACQUIRED-PGNX | PGNX |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0033-ACQUIRED-PRNB | PRNB |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0034-ACQUIRED-PRVL | PRVL |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |
| RHC-0035-ACQUIRED-ADMS | ADMS |  | 0 | 0 | DATE_MISSING | Backfill exact acquisition announcement date before prior-signal review. |

## All Batch Results

| case_id | ticker | company_name | announcement_date | announcement_date_confidence | filings_checked_count | possible_hits_count | adjudication_status | confidence | next_action | packet_path | completeness_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RHC-0001-ACQUIRED-NPSP | NPSP | NPS Pharmaceuticals, Inc. | 2015-01-12 | HIGH | 0 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Source evidence indicates no public prior process signal; keep as baseline candidate pending final hit/no-hit confirmation. | data/historical_cases/case_packets/RHC-0001-ACQUIRED-NPSP_NPSP.md | 80 |
| RHC-0002-ACQUIRED-PCYC | PCYC | Pharmacyclics, Inc. | 2015-03-06 | HIGH | 0 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Source evidence indicates no public prior process signal; keep as baseline candidate pending final hit/no-hit confirmation. | data/historical_cases/case_packets/RHC-0002-ACQUIRED-PCYC_PCYC.md | 80 |
| RHC-0003-ACQUIRED-ZSPH | ZSPH | ZS Pharma, Inc. | 2015-11-06 | HIGH | 0 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Source evidence indicates no public prior process signal; keep as baseline candidate pending final hit/no-hit confirmation. | data/historical_cases/case_packets/RHC-0003-ACQUIRED-ZSPH_ZSPH.md | 80 |
| RHC-0004-ACQUIRED-ANAC | ANAC | Anacor Pharmaceuticals, Inc. | 2016-05-16 | HIGH | 0 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Source evidence indicates no public prior process signal; keep as baseline candidate pending final hit/no-hit confirmation. | data/historical_cases/case_packets/RHC-0004-ACQUIRED-ANAC_ANAC.md | 80 |
| RHC-0005-ACQUIRED-CPXX | CPXX | Celator Pharmaceuticals, Inc. | 2016-05-31 | MEDIUM | 23 | 1 | RIGHTS_LANGUAGE_ONLY | LOW | Keep out of true prior-signal counts unless separate public whole-company process evidence is found. | data/historical_cases/case_packets/RHC-0005-ACQUIRED-CPXX_CPXX.md | 5 |
| RHC-0006-ACQUIRED-MDVN | MDVN | Medivation, Inc. | 2016-08-22 | HIGH | 54 | 9 | TRUE_PUBLIC_PRIOR_SIGNAL | HIGH | Reused adjudicated true prior public signal; do not mark VERIFIED without independent review. | data/historical_cases/case_packets/RHC-0006-ACQUIRED-MDVN_MDVN.md | 80 |
| RHC-0007-ACQUIRED-RLYP | RLYP | Relypsa, Inc. | 2016-07-21 | HIGH | 38 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0007-ACQUIRED-RLYP_RLYP.md | 5 |
| RHC-0008-ACQUIRED-TBRA | TBRA | Tobira Therapeutics, Inc. | 2016-09-20 | HIGH | 0 | 0 | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. | data/historical_cases/case_packets/RHC-0008-ACQUIRED-TBRA_TBRA.md | 80 |
| RHC-0009-ACQUIRED-VTAE | VTAE | Vitae Pharmaceuticals, Inc. | 2016-09-14 | HIGH | 18 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0009-ACQUIRED-VTAE_VTAE.md | 5 |
| RHC-0010-ACQUIRED-ARIA | ARIA | ARIAD Pharmaceuticals, Inc. | 2017-01-09 | HIGH | 0 | 0 | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. | data/historical_cases/case_packets/RHC-0010-ACQUIRED-ARIA_ARIA.md | 80 |
| RHC-0011-ACQUIRED-CLCD | CLCD | CoLucid Pharmaceuticals, Inc. | 2017-01-18 | HIGH | 7 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0011-ACQUIRED-CLCD_CLCD.md | 5 |
| RHC-0012-ACQUIRED-DMTX | DMTX | Dimension Therapeutics, Inc. | 2017-10-03 | HIGH | 27 | 4 | TRUE_PUBLIC_PRIOR_SIGNAL | HIGH | Reused adjudicated true prior public signal; do not mark VERIFIED without independent review. | data/historical_cases/case_packets/RHC-0012-ACQUIRED-DMTX_DMTX.md | 5 |
| RHC-0013-ACQUIRED-KITE | KITE | Kite Pharma, Inc. | 2017-08-28 | HIGH | 0 | 0 | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. | data/historical_cases/case_packets/RHC-0013-ACQUIRED-KITE_KITE.md | 80 |
| RHC-0014-ACQUIRED-AVXS | AVXS | AveXis, Inc. | 2018-04-09 | HIGH | 43 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0014-ACQUIRED-AVXS_AVXS.md | 5 |
| RHC-0015-ACQUIRED-BIVV | BIVV | Bioverativ Inc. | 2018-01-22 | HIGH | 0 | 0 | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. | data/historical_cases/case_packets/RHC-0015-ACQUIRED-BIVV_BIVV.md | 80 |
| RHC-0016-ACQUIRED-CASC | CASC | Cascadian Therapeutics, Inc. | 2018-01-31 | HIGH | 33 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0016-ACQUIRED-CASC_CASC.md | 5 |
| RHC-0017-ACQUIRED-JUNO | JUNO | Juno Therapeutics, Inc. | 2018-01-22 | HIGH | 0 | 0 | PRIVATE_BACKGROUND_ONLY | MEDIUM | Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found. | data/historical_cases/case_packets/RHC-0017-ACQUIRED-JUNO_JUNO.md | 80 |
| RHC-0018-ACQUIRED-RXDX | RXDX | Ignyta, Inc. | 2017-12-22 | HIGH | 37 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0018-ACQUIRED-RXDX_RXDX.md | 5 |
| RHC-0019-ACQUIRED-ALDR | ALDR | Alder BioPharmaceuticals | 2019-09-16 | HIGH | 36 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0019-ACQUIRED-ALDR_ALDR.md | 5 |
| RHC-0020-ACQUIRED-ARRY | ARRY | Array BioPharma Inc. | 2019-06-17 | HIGH | 30 | 2 | ASSET_SPECIFIC_RIGHTS_ONLY | LOW | Keep out of true prior-signal counts unless separate public whole-company process evidence is found. | data/historical_cases/case_packets/RHC-0020-ACQUIRED-ARRY_ARRY.md | 5 |
| RHC-0021-ACQUIRED-CMTA | CMTA | Clementia Pharmaceuticals Inc. | 2019-02-25 | HIGH | 3 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0021-ACQUIRED-CMTA_CMTA.md | 5 |
| RHC-0022-ACQUIRED-LOXO | LOXO | Loxo Oncology, Inc. | 2019-01-07 | HIGH | 34 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0022-ACQUIRED-LOXO_LOXO.md | 5 |
| RHC-0023-ACQUIRED-NITE | NITE | Nightstar Therapeutics plc | 2019-03-04 | HIGH | 2 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0023-ACQUIRED-NITE_NITE.md | 5 |
| RHC-0024-ACQUIRED-ONCE | ONCE | Spark Therapeutics, Inc. | 2019-02-25 | HIGH | 26 | 0 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | MEDIUM | Use as baseline candidate after final manual EDGAR hit/no-hit spot check. | data/historical_cases/case_packets/RHC-0024-ACQUIRED-ONCE_ONCE.md | 5 |
| RHC-0025-ACQUIRED-TSRO | TSRO | TESARO, Inc. | 2018-12-03 | HIGH | 0 | 0 | TRUE_PUBLIC_PRIOR_SIGNAL | MEDIUM | Reused adjudicated true prior public signal; do not mark VERIFIED without independent review. | data/historical_cases/case_packets/RHC-0025-ACQUIRED-TSRO_TSRO.md | 40 |
| RHC-0026-ACQUIRED-ACHN | ACHN | Achillion Pharmaceuticals |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0026-ACQUIRED-ACHN_ACHN.md | 5 |
| RHC-0027-ACQUIRED-BOLD | BOLD | Audentes Therapeutics, Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0027-ACQUIRED-BOLD_BOLD.md | 5 |
| RHC-0028-ACQUIRED-DERM | DERM | Dermira |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0028-ACQUIRED-DERM_DERM.md | 5 |
| RHC-0029-ACQUIRED-FTSV | FTSV | Forty Seven, Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0029-ACQUIRED-FTSV_FTSV.md | 5 |
| RHC-0030-ACQUIRED-MNTA | MNTA | Momenta Pharmaceuticals, Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0030-ACQUIRED-MNTA_MNTA.md | 5 |
| RHC-0031-ACQUIRED-MYOK | MYOK | MyoKardia, Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0031-ACQUIRED-MYOK_MYOK.md | 5 |
| RHC-0032-ACQUIRED-PGNX | PGNX | Progenics Pharmaceuticals |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0032-ACQUIRED-PGNX_PGNX.md | 5 |
| RHC-0033-ACQUIRED-PRNB | PRNB | Principia Biopharma Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0033-ACQUIRED-PRNB_PRNB.md | 5 |
| RHC-0034-ACQUIRED-PRVL | PRVL | Prevail Therapeutics Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0034-ACQUIRED-PRVL_PRVL.md | 5 |
| RHC-0035-ACQUIRED-ADMS | ADMS | Adamas Pharmaceuticals |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0035-ACQUIRED-ADMS_ADMS.md | 5 |
| RHC-0036-ACQUIRED-DOVA | DOVA | Dova Pharmaceuticals |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0036-ACQUIRED-DOVA_DOVA.md | 5 |
| RHC-0037-ACQUIRED-DRNA | DRNA | Dicerna Pharmaceuticals, Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0037-ACQUIRED-DRNA_DRNA.md | 5 |
| RHC-0038-ACQUIRED-FLXN | FLXN | Flexion Therapeutics |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0038-ACQUIRED-FLXN_FLXN.md | 5 |
| RHC-0039-ACQUIRED-FPRX | FPRX | Five Prime Therapeutics, Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0039-ACQUIRED-FPRX_FPRX.md | 5 |
| RHC-0040-ACQUIRED-GWPH | GWPH | GW Pharmaceuticals plc |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0040-ACQUIRED-GWPH_GWPH.md | 5 |
| RHC-0041-ACQUIRED-PAND | PAND | Pandion Therapeutics |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0041-ACQUIRED-PAND_PAND.md | 5 |
| RHC-0042-ACQUIRED-PTLA | PTLA | Portola Pharmaceuticals |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0042-ACQUIRED-PTLA_PTLA.md | 5 |
| RHC-0043-ACQUIRED-TRIL | TRIL | Trillium Therapeutics Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0043-ACQUIRED-TRIL_TRIL.md | 5 |
| RHC-0044-ACQUIRED-VIE | VIE | Viela Bio, Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0044-ACQUIRED-VIE_VIE.md | 5 |
| RHC-0045-ACQUIRED-XLRN | XLRN | Acceleron Pharma Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0045-ACQUIRED-XLRN_XLRN.md | 5 |
| RHC-0046-ACQUIRED-ATRS | ATRS | Antares Pharma |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0046-ACQUIRED-ATRS_ATRS.md | 5 |
| RHC-0047-ACQUIRED-AVEO | AVEO | AVEO Oncology |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0047-ACQUIRED-AVEO_AVEO.md | 5 |
| RHC-0048-ACQUIRED-BHVN | BHVN | Biohaven Pharmaceutical Holding Company Ltd. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0048-ACQUIRED-BHVN_BHVN.md | 5 |
| RHC-0049-ACQUIRED-CCXI | CCXI | ChemoCentryx, Inc. |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0049-ACQUIRED-CCXI_CCXI.md | 5 |
| RHC-0050-ACQUIRED-CMPI | CMPI | Checkmate Pharmaceuticals |  |  | 0 | 0 | DATE_MISSING | LOW | Backfill exact acquisition announcement date before prior-signal review. | data/historical_cases/case_packets/RHC-0050-ACQUIRED-CMPI_CMPI.md | 5 |
