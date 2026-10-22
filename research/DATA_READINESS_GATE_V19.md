# FrailtyScope v0.19 — dataset and endpoint readiness before fitting

## Why this exists

FrailtyScope v0.13–v0.18 explored model selection, preprocessing, stability and calibration on a single public-use NHANES binary mortality case. Its performance comparisons are exploratory, because the same development participants informed earlier candidate choices. The published pipeline supports ordinary tabular binary classification and regression only. That is **not sufficient** to automatically handle repeated HUNT visits, censoring, landmark prediction, site effects, or survey questionnaire skip patterns.

Version 0.19 adds a **case-independent, no-training** data-intake gate before any model search. It reads a local dataset into memory, inspects only development-cohort target values, and emits a local aggregate and explicit route. It neither runs Optuna nor deserializes any model. The source file is read as a whole; the holdout cohort is counted using cohort labels and inspected for participant-ID overlap **without computing with held-out outcomes**. The v0.18 fitted model and any prior artifacts remain unchanged.

## Commands on the workstation

```bash
PYTHONPATH=. .venv/bin/python -m ml.case_readiness_v19 --plan
PYTHONPATH=. .venv/bin/python -m ml.case_readiness_v19 --audit
```

`--plan` prints aggregate readiness diagnostics without saving. `--audit` writes an immutable, private, source-hashed readiness report under `artifacts/cases/<case_id>/readiness_v19/<config-sha-prefix>/readiness_audit.json`. Never commit this report or a source dataset. A different case uses `--config research/cases/YOUR_CASE.json`; no previous NHANES models or v0.13–v0.18 runs are required.

## Required case contract

- **Data input**: relative path under ignored `data/`, optional SHA256 pin and exact source-provenance check; CSV/XLSX/Parquet/Stata/SAS format supported by existing v0.10 readers.
- **Explicit roles**: person identifier, target, numeric/categorical predictors, development/holdout split, declared previously-inspected vs locked-new holdout.
- **Clinical prediction time**: declared index time and prediction horizon; outcome type `binary_fixed_horizon`, `continuous`, or `time_to_event`. A fixed-horizon binary endpoint must declare verified complete follow-up, unverified follow-up, or observed censoring; claiming verified follow-up requires a documented source. Declared censoring blocks the ordinary classifier until an appropriate outcome/survival protocol is chosen. A survival endpoint must declare duration/event columns.
- **Record design**: `one_record_per_person` vs `repeated_visits`, optional group and visit-time columns. Generic v0.16 runner is blocked for repeated records, survival outcomes, and designs requiring group/temporal split handling.
- **Missingness semantics**: per-feature `unverified` until a **human-reviewed** source instrument/codebook provides evidence for `reviewed_structural`, `reviewed_nonresponse`, `reviewed_mixed`, or `reviewed_not_applicable`. No status is inferred from predictive performance, correlations, codes such as 7/9, or observed missingness.
- **Leakage**: declared post-index predictors are prohibited, as are target/time/follow-up/site/ID columns inside the predictor list. Suspicious names trigger manual review; chronology must still be checked substantively.

## Interpret the status

- `BLOCKED_FOR_CURRENT_ENGINE`: a hard schema, chronology/identity, range, endpoint or design risk means **do not use** the ordinary tabular selection workflow; correct the contract or use a specialized group/time/landmark/survival workflow.
- `EXPLORATORY_REVIEW_REQUIRED`: ordinary cohort-tabular model search may be technically possible, but unverified missingness reasons, predictor timing or prior holdout inspection require substantive review. **Not clinical deployment** and not independent confirmation.
- `EXPLORATORY_READY`: initial mechanical contracts passed; human assessment and independent validation are still required.

A direct result of the 2011–2012 NHANES data is expected to flag walking/stair/PHQ-9 missingness for **codebook review**. Do not interpret a strong missingness indicator as proof of a survey skip or MNAR. Study event-rate associations from v0.18 are observational only.

## Scientific standards and source documentation

- CDC NHANES FAQs, questionnaire skips and missing codes: https://wwwn.cdc.gov/nchs/nhanes/ContinuousNhanes/faq.aspx
- CDC NHANES Datasets and Documentation Tutorial: https://wwwn.cdc.gov/nchs/nhanes/tutorials/Datasets.aspx
- TRIPOD+AI (2024): https://doi.org/10.1136/bmj-2023-078378
- PROBAST+AI (2025): https://doi.org/10.1136/bmj-2024-082505

These sources motivate documentation, outcome/predictor timing, missingness review, leakage control, and appropriate validation **but do not certify** a result of this software.

## What the audit does NOT do

It cannot infer the missingness mechanism from data alone; it does not create a valid survival target, confirm a clinical time horizon, provide NHANES design-based standard errors, inspect source instruments, harmonize waves, or implement repeated-measurement/grouped/temporal CV. A flag for a particular route is a **stop/redirect**, not an implementation of that training protocol.

Once the actual assignment is defined, establish these contracts, then run a design-compatible nested model comparison (and consider survival/multistate methods when appropriate). Validation must be independent of prior feature/model exploration before claiming transportability or superiority.
