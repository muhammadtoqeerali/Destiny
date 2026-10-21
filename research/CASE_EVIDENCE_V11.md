# FrailtyScope v0.11 — Dataset-to-model evidence protocol

The **generic case engine** remains independent of NHANES. The NHANES-specific public workbench is an example of actual results in use, not a synthetic dataset. The code `ml/case_forensics_v11.py` reads the same case manifest used by v0.10; the public exporter deliberately supports *only the approved NHANES case*.

## Scientific workflow

1. **Input/data contract:** fixed task, case ID, source path, provenance, target, predictor roles, split strategy, objective, and allowed algorithms. Fail closed for ID/outcome leakage or mismatched dataset fingerprint.
2. **Dataset forensic audit:** per-column types, observed/missing counts, distinct values, quartiles, IQR outliers, privacy-screened distributions; training-only Spearman relationships; development/evaluation standardized mean differences and missingness shift; cohort counts.
3. **Actual fitted preprocessing:** source missingness; training median or mode; standardized training center and scale, categorical OHE outputs and resulting matrix width. Three quartiles are shown before/after as **summary values**, not fabricated records. Local audit separately contains actual de-identified before/after feature vectors for up to five training observations; never publish this file.
4. **Selection:** Optuna inside training folds; dummy and five trained families; validation Brier for selecting the candidate. Later-cycle evaluation must not determine hyperparameters or model family.
5. **Learning-curve and mechanics:** Training fractions (25%, 50%, 75%, 100%) are fit with the already-selected hyperparameters and evaluated on the development validation cohort for under-/over-fitting diagnostics. These are not new independent tests.
6. **Mechanics:** trained matrix construction, selected model parameters and validation permutation importance. Importance is not a causal effect.
7. **Enhancement:** one predefined validation-only candidate—Platt probability scaling—with 3-fold out-of-fold evaluation on the validation partition. Adopt only when OOF Brier gain is at least 0.002 *and* OOF ROC-AUC deterioration is no worse than 0.015. If rejected, retain raw model. The final later-cycle metrics are **descriptive evaluation only**.
8. **Final outcome:** confusion matrix, threshold, discrimination, probability error, calibration bins, and adequately sized age/sex strata. This remains exploratory and is not intended for clinical decisions or demographic fairness certification.

## Limits

- Public-use NHANES linked mortality times may be disclosure-modified. Five-year labels are approximate.
- Later survey cycle has been inspected repeatedly in prior research versions. It is not a virgin external validation cohort.
- NHANES survey design affects population inference; reported discriminative metrics are not survey-design-valid uncertainty estimates.
- Trial sample sizes are intentionally modest to support a generic runnable reference implementation; do not claim an exhaustive hyperparameter search or globally best model.
- Calibration crossfit removes direct calibrator self-evaluation bias but the original validation partition also selected the base model. A new independent external study is needed.
- The public dashboard contains no individual survey records, predictions, local fitted binaries or individual transformation examples.
- All per-person exploratory information stays in ignored workstation artifacts. Do not push local files.

## Supported new case tasks

The v0.11 forensic module supports classification and regression profiles from an existing v0.10 case manifest and trained artifact. The probability calibration enhancement is **binary-classification-only**. The NHANES public exporter is **not** a generic dataset publisher. For a new assignment, map its variables and licensed data on the workstation, run the case engine, and review a new disclosure policy before developing any public results.
