# FrailtyScope v0.17 — development selection stability and reliability

## Scientific purpose

The v0.16 model-family and preprocessing selector was assessed using one outer-CV repeat. This protocol examines the sensitivity of the **entire** predeclared staged/nested selection method to different folds, its out-of-fold probability calibration, and how often input-feature permutation matters in assessment folds. It compares the joint selector with an **independently tuned, fold-matched** logistic/ridge reference.

This is a **local research development diagnostic**, not new independent validation. The NHANES 2011–2012 participants have been inspected in previous iterations. Repeating their partitions does not create additional independent participants. The 2013–2014 evaluation records remain unscored by this study.

## Workflow

1. **Plan:** `PYTHONPATH=. .venv/bin/python -m ml.case_stability_v17 --plan`. Verifies the case manifest, current v0.16 protocol fingerprint, previously completed source-only report, saved local model file's existence, and fold-fitting budget. No model loading, fitting, or inference.
2. **Run:** `PYTHONPATH=. .venv/bin/python -m ml.case_stability_v17 --run`. Explicitly starts training and evaluation of development-fold models on **your workstation only**. Runs the same v0.16 screening/refinement and tuned reference inside every outer training fold. Each corresponding outer assessment fold is scored exactly once for that repeat. The existing v0.16 development winner remains unchanged.
3. **Review:** Read `artifacts/cases/<case_id>/stability_v17/<config-sha-prefix>/selection_stability.json` locally. This report contains **aggregate only**: pair selection counts, paired per-repeat metrics, calibration bins, and held-out-fold permutation-importance summaries. No participant predictions, participant identifiers or fitted model binaries.
4. **Publish (optional):** `bash scripts/publish_stability_v17.sh` requires an explicit uppercase `YES`. Only approved code, tests, protocols and documentation are published. Reports and real model artifacts are never staged.

## Metrics and interpretation

- **Selection stability:** Number of outer folds selecting each model/preprocessing pair. Descriptive frequency across overlapping resamples, **not** a probability of external generalization.
- **Paired reference comparison:** Per-repeat Brier, ROC-AUC and average precision for binary classification, or RMSE/MAE for regression. Both methods use identical outer assessment rows.
- **Calibration:** For binary classification, equal-frequency development OOF probability bins (minimum 40 observations by default), descriptive expected calibration error, and mean predicted risk minus event prevalence. The report **does not fit or accept a new calibrator**, and does not select a clinical threshold.
- **Importance stability:** Permutation importance on each outer assessment fold, with negative Brier (or negative squared error) as score, mean score decrease and how frequently a feature appears in the top five. Permuting correlated predictors can conceal their combined value. Features absent from a selected recipe are explicitly marked as **not assessed**.

## Boundaries and reuse

- Input table stays under ignored `data/`. All actual training, Optuna studies and prediction calls run on the workstation only.
- The report is written immutably under ignored `artifacts/`. Reruns refuse overwrite; change the versioned protocol and use a distinct output hash if necessary.
- No public JSON asset or dashboard is changed. No v0.16 model is replaced or loaded during installation.
- New assignments can reuse the same runner after defining the v0.10 case manifest, v0.13 strategy, v0.16 joint-selection protocol, running their **own** v0.16 development search, and generating a new v0.17 protocol with its own matching `v16_protocol_sha256`. They do **not** need to reproduce historical NHANES v0.13–v0.15 experiments.
- For repeated visits, site grouping, censoring, time-varying predictors, or longitudinal outcomes, use dedicated valid group/time/survival protocols; do not force this shuffled tabular CV design.

## Evidence limitations

These computations are post-selection exploratory because earlier NHANES analyses motivated the candidate portfolio. Results lack complex survey variance adjustments, independent site validation, and clinical decision utility evaluation. They must not be represented as superiority proof or patient-specific medical guidance.
