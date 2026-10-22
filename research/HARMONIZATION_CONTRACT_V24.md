# FrailtyScope v0.24 — source-semantic harmonization and data-processing contracts

## What this release **implements**

This is **part A** of advanced data preparation: a source-controlled, fail-closed harmonization contract, a pure in-memory semantic mapper, and a metadata-only command-line plan/audit. It does not claim full data engineering or any clinical model. No CLI in this release reads NHANES, HUNT, participant data, labels, predictions, or fitted models. It cannot authorize real-data execution.

- Exact observed-code maps (e.g., 1–4) are distinguished from refused, unknown, nonperformance, and documented structural skips. Raw special codes are not used as ordinal values.
- Blank answers without an explicitly documented reason fail; a structural skip must match a documented upstream questionnaire routing field. If an answer appears when the skip is active, the rule rejects it.
- Numeric source measurements can be mapped via a **source-approved** scale and offset; impossible values and nonfinite conversions are rejected, not silently imputed. This mapping requires explicit input and canonical units plus acceptable ranges.
- Different survey-wave mappings must target a consistent canonical type, unit, and (for categorical/ordinal values) canonical category set. This is basic syntactic consistency, **not evidence of measurement invariance or clinical equivalence**.
- The pure `harmonize_fixture(..., synthetic_fixture=True)` function is deliberately restricted to synthetic test fixtures for this release. It returns canonical values and separate `__status` columns, plus status counts, never automatically fitting a model.
- All source-defined predictors not yet covered are explicitly listed. The NHANES example maps only 2011–2012 PFQ061B/C/D after the raw v0.20 audit, and flags the other 11 as unmapped. No assumption that the 2013–2014 PFQ data are newly uninspected.

## What remains outside this first work package

- **Before fitting:** independent index-time availability verification, approved access and permitted compute, appropriate eligibility criteria, wave/site comparability review, patient/visit IDs, ranges and unit metadata, and confidentiality safeguards.
- **Inside training folds only:** imputation, learned scaling, encoders, feature selection, data-driven outlier thresholds, class resampling, measurement harmonization parameters inferred from data, target encoding and hyperparameter selection. None is fitted by v0.24.
- **Separate advanced tasks:** missing-data sensitivity, MAR/MNAR scenarios, multiple imputation with correct downstream pooling, longitudinal observation processes, sensor/device synchronization, cross-site transport, survey weights, and methods for censoring. These need case-specific methods and tests.
- **No universal automatic cleaner:** outliers may be true rare cases, structural missingness is not ordinary missing at random, units may be biologically non-equivalent across assay versions, and deletion or imputation is not benign by default.

## Future use in HUNT or other research

Start with the v0.23 dictionary for that **specific** assignment. Define a source map for each instrument and wave, a documented prediction index, intended outcome and relevant grouping. Use this blueprint to reject unreviewed coding differences **before** any authorized dataset is transformed. Clinical/statistical review must determine whether two waves measure the same construct, whether units are commensurable, and how missingness and follow-up should be modeled.

## Existing NHANES boundary

The 2011–2012 PFQ skip audit identified 279 B/C skips and specific response-5 counts; that evidence is instrument/cycle specific. The mortality target was internally reconciled, but public-use follow-up times can be disclosure-perturbed. The 2013–2014 cycle was already inspected in historical research; no fresh validation can be claimed. All 14 predictor timing checks remain pending in v0.23. This release keeps source semantics separate from a model training protocol.

## User commands

```bash
PYTHONPATH=. .venv/bin/python -m ml.case_harmonization_v24 --plan
PYTHONPATH=. .venv/bin/python -m ml.case_harmonization_v24 --audit
```

`--plan` reads source-controlled JSON only. `--audit` also checks the existing **private v0.23 metadata report**, saving a new immutable **private v0.24 report** under ignored `artifacts/`. Neither command opens real participant tables or fits anything. Never publish private reports.
