# FrailtyScope v0.29 — Integrated reproducible development workflow

**Scope: software engineering only, invented synthetic data only.** This module connects earlier source contracts (v0.22–v0.24), v0.24 fixed-source mapping, v0.25 training-fold preprocessing, v0.26 task-model comparison machinery, and v0.28 fixed-OOF reliability diagnostics. It fits synthetic classification/regression models *in memory*; its source-only `--plan` and private metadata-only `--audit` do not fit anything. `synthetic_fixture=True` is a caller promise, **not** an access-control sandbox. Never supply real participant records to this prototype.

## Implemented connected path

1. **Source-only validation:** `--plan` follows and verifies v0.22 → v0.23 → v0.24 → v0.25 → v0.26 → v0.27 → v0.28 → v0.29 contracts. The study's `case_id`, original task, inspected holdout history, exploratory reuse and prediction-index status are preserved; no approval is inferred.
2. **Fixed source semantics:** `run_synthetic_workflow(...,source_fixture=True,synthetic_fixture=True)` optionally maps *invented* raw questionnaire codes according to the documented v0.24 wave. Extra raw fields are rejected, rather than discarded. The alternative is an exact canonical feature + `__status` frame. Both paths require the **same three** source-mapped predictor definitions.
3. **Partition-first checks:** v0.26 constructs identical participant-disjoint development folds, and v0.25 validates train/validation IDs and participant grouping. `run_synthetic_workflow` adds participant-disjoint checks even for otherwise looser policies. In the current chain, the v0.27 protocol confines this illustration to `person_disjoint`, not prospective or individual-trajectory validation.
4. **Strictly fold-fitted preprocessing/models:** On each training fold, a fresh v0.25 preprocessing pipeline and v0.26 registered estimator are fitted; its validation fold is only transformed and predicted. The example candidates (`dummy_prior`, `logistic`) are pre-registered and shared with v0.28; regression with appropriate `dummy_mean`/`ridge` contracts is tested on invented data.
5. **Reliability from *actual synthetic out-of-fold predictions*:** The integrated runner creates aligned, held-out fold records itself, then feeds them to v0.28, returning pooled performance, descriptive calibration or regression residuals, participant-cluster paired fixed-prediction intervals, and toy score perturbation results. It discards per-row fold records instead of saving them.
6. **Documentary audit:** `--audit` checks the existing, **private, immutable v0.28 metadata-only** review and saves a new immutable v0.29 metadata-only review in ignored `artifacts/`. No CSV/XPT, predictions, research labels or model binaries are opened by the CLI. The CLI's `no_models_fitted` refers to its metadata-only audit; the explicit synthetic API demonstrably fits synthetic toy models.

## Status and scientific limitations

- **NHANES remains `BLOCKED_FOR_NEW_ANALYSIS`.** Its original task is binary five-year mortality classification, the prediction index is provisional, only **3 of 14** features have v0.24 verified source mappings, and the 2013–2014 later cycle was previously inspected. No new NHANES experiment, result, independent validation, or clinical score is created.
- The synthetic integrated demo performs **development CV only**. It does not tune or select a winner, perform nested CV, or estimate performance after selection. Pooled out-of-fold predictions from this repeatedly used development population are not independent confirmation.
- v0.28 cluster bootstrap uncertainty is **conditional on fixed predictions** and does not resample the full fit/selection pipeline. Calibration slopes are descriptive diagnostics, not learned or applied calibrators.
- v0.27 toy survival/next-observed-visit examples are **not yet connected** to integrated reliability or general-purpose censoring-aware and longitudinal validation. Competing risks, informative observation/dropout, fixed future horizons, entry time, sites and survey design require specialist engineering.
- No automatic clinical thresholds, claims of generalization, survey-design confidence intervals, external transport validation, saved model binaries, participant predictions, manuscript/slide production, or deployment authorization.
- Fitted model artifact loading (including `joblib`) should remain disabled for untrusted files. New research datasets require approved source dictionaries, time-index evidence, governance and a genuine independent assessment plan.

## API

`validate_workflow(cfg,v28,v27,v26,v25,v24)` validates the source contract chain and reproducibility safeguards.

`run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,frame,y,row_ids=...,groups=...,source_fixture=True|False,synthetic_fixture=True)` runs the invented fixture through the integrated path and returns **aggregate synthetic metrics only**, no fitted models or row-level predictions. Test only with invented toy records.

`python -m ml.case_workflow_v29 --plan` reads source JSON only. `--audit` checks only the private prior metadata JSON and writes an immutable ignored review. Neither mode touches participant-level data.

Official methodological background: https://scikit-learn.org/stable/common_pitfalls.html and https://scikit-learn.org/stable/modules/cross_validation.html
