# FrailtyScope v0.21 — Source-aware physical-function representations

## Hypothesis and evidence

The locally executed v0.20 PFQ_G reconciliation established that 279 of 303 missing walking responses and 279 of 292 missing stairs responses were the documented `PFQ054=1` skip. The remaining 24 walking and 13 stairs responses were raw code `5` ("do not do this activity"). All 35 processed stooping missing values were also raw code `5`. **The original processed missingness has complete provenance within these three features for the analyzed 2011–2012 development cohort**, with no linked raw/processed disagreement.

CDC 2011–2012 codebook: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/PFQ_G.htm . The CAPI `PFQ054` skip applies to PFQ061B/C, **not PFQ061D**. Codes 1–4 are ordinal difficulty, code 5 is not an ordinal severity, and codes 7/9 mean refused/don't know. The current development cohort has none of 7/9 in these three variables; v0.21 fails closed if unreviewed codes arise.

## Workstation-only comparison (post-hoc)

One fixed Random Forest recipe from the already completed v0.16 joint selection is held constant. Across exactly matched development-only stratified folds, test these three **representations**, without retuning family/hyperparameters:

1. `legacy_missing_indicators`: existing numeric values 1–4 + median imputation and indicators for missing numeric fields.
2. `source_status_augmented`: baseline numerical values + explicit categorical *REPORTED / SKIP_PFQ054 / DO_NOT_DO_ACTIVITY* per mobility measurement.
3. `source_categories`: replace the three mobility numeric predictors with a one-hot nominal representation of ordered response levels 1–4, questionnaire skip, and code 5. All other numeric predictors still receive the same imputation and indicator logic. This is an **alternative representation**, not a clinical severity ordering of categories.

The three representations are compared with identical development folds in three repeats, using Brier as primary and ROC-AUC, average precision and log loss as descriptive secondary measures. Fold-specific imputers and encoders are refitted inside each fold. The actual experiment is triggered **only** by `--run` on the researcher's workstation. The report contains aggregate results only, with no identifiers, predictions, fitted models or clinical thresholds.

This is not a new nested model-family search and is not independent confirmation: previous research choices have already used these development participants. Any apparent benefit is a hypothesis to carry into a **future genuinely new cohort and appropriately designed nested comparison**; do not use the already-inspected later NHANES cycle to choose a representation.

## Privacy and operational guardrails

- Validates exact processed + raw PFQ source SHA256 fingerprints and the completed private v0.20 lineage report.
- Links raw PFQ responses to the 2011–2012 development participants **only**, in memory; does not export person-level data.
- Reads development mortality labels from the CSV only after checking the cohort identifier. The 2013–2014 target cells are never accessed by the script.
- Requires unique matching SEQN and perfect reconciliation for reported codes, structural skips and code 5. Any unexplained missing data or code 7/9 stops the experiment.
- Reuses v0.16 model family/parameters, but **does not deserialize** the previously fitted model or overwrite its files.
- Installation and CI tests are synthetic only; no NHANES fitting during installation. Output is immutable and remains ignored under `artifacts/`.
- Release scripts whitelist source code only and require uppercase `YES` before GitHub publication.
- The module is **NHANES PFQ-specific**. For HUNT or other data, adapt the source-evidence mapping after reviewing each instrument's codebook and eligibility rules; do not reuse the PFQ rule outside its context.

## Commands

```bash
PYTHONPATH=. .venv/bin/python -m ml.case_source_semantics_v21 --plan
PYTHONPATH=. .venv/bin/python -m ml.case_source_semantics_v21 --run
```

A positive Brier improvement means lower development OOF Brier for a representation, **not evidence of clinical superiority, causality, or cross-dataset transportability**.
