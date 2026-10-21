# FrailtyScope v0.12 — Decision Quality and Error Analysis

## Scope

The existing locally fitted v0.10 CatBoost general-purpose case model is the fixed object of evaluation. This release does **not** select or refit a new model, change preprocessing, or tune a decision threshold on the later NHANES cohort. The model and its data remain on the workstation. Public dashboard JSON is an explicitly screened set of aggregates.

## Scientific contract

- **Outcome:** Approximately five-year all-cause mortality in the CDC NHANES 2011–2014 linked public-use cohort, not frailty, cognitive decline or a clinical diagnostic endpoint.
- **Training and selection:** 873 training respondents and 292 development-validation respondents from 2011–2012. Keep the development-selected model and its operating threshold unchanged.
- **Evaluation:** 1,257 later-cycle respondents (2013–2014), 246 events. The later cycle has already been examined in preceding project releases; it cannot be called an untouched independent external test.
- **Threshold audit:** Evaluate a fixed grid of thresholds for sensitivity, specificity, false-positive rate, precision, F2 and **decision-curve net benefit**. These are descriptive sensitivity analyses, **not** threshold searches or clinical recommendations. Assumed risk-threshold odds weight the cost of false positives. No patient intervention utility model is validated.
- **Calibration:** Overall and by sex/age; age bands 65–69, 70–74, 75–79, and 80+ (public NHANES ages are top-coded). Within-group ranked probability bands are suppressed for small event or non-event cells. Missing groups are not fabricated.
- **Uncertainty:** 500 fixed-seed individual-IID bootstrap percentile draws for AUC, average precision, Brier, recall, and false-positive rate. These do **not** incorporate NHANES survey weights, strata or PSUs, and are not survey-design-valid inferential confidence intervals. Method names and limitations are retained in dashboard labels.
- **Specialist comparison:** Reuse prior published specialist CatBoost/Histogram-boosting aggregate results only when evaluation n=1,257 and outcome events=246 match. Different training/tuning protocols, missing paired predictions, and previous later-cycle inspection mean no paired difference test or formal superiority claim is possible. The strongest apparent AUC is not automatically the selected model.
- **Subgroup disclosure:** Only groups with n≥100 and ≥20 event and non-event observations are exported; within-group risk bands require n≥50 and ≥10 of each outcome. No respondent rows, IDs, fitted models, per-person scores, patient history or unreviewed data sources are exported.

## Reusability

`ml/case_decision_quality_v12.py` can evaluate any saved **binary classification** case compatible with the v0.10 manifest, without fitting a model. Input CSV paths must remain under project `data/`. Outputs remain under ignored project `artifacts/cases/<case_id>/`. Age and sex subgroup views appear only when those feature names exist; other assignment-specific strata require codebook-backed grouping definitions added and reviewed separately. Regression and time-to-event tasks require different metric contracts; never reuse the binary evaluation rules unchanged.

`export_decision_quality_v12.py` is intentionally *NHANES-only*, checking the approved data fingerprint, 1,257 evaluation records and 246 events before public publication. It must **not** be reused to publish a new case without a new privacy, license and scientific review.

## Release contract

Run `scripts/install_decision_quality_v12.sh` and inspect the real workstation results; then optionally run `scripts/publish_decision_quality_v12.sh`. The installer does not push. Both scripts enforce exact allowed files, real provenance, regression checks, isolated Next.js production build and dependency audit. No presentation scripts, new datasets, or Doctor Portal changes.
