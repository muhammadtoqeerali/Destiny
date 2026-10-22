# FrailtyScope v0.26 — task-aware model comparison (synthetic-only)

## Purpose and current boundary

The v0.25 feature transformer is now attached to a reusable **development-only** candidate-comparison engine for **binary classification** and **continuous regression**. Source harmonization is still the fixed v0.24 step; train-learned preprocessing is fitted independently inside **each fold**. Models and outcomes are never fitted/scored by the `--plan` or `--audit` commands. In-memory evaluation requires deliberately invented fixtures and `synthetic_fixture=True`. The flag is **not a secure isolation boundary** and must never be used to pass real NHANES or HUNT records to this prototype.

**The current NHANES case remains blocked.** The index is provisional, only three mobility variables have v0.24 contracts, eleven are unmapped, and the later cycle was previously inspected. This release does not alter or replace the saved Random Forest and does not create a new benchmark claim.

## Implemented architecture

1. **Contract chain:** Load and validate v0.22 → v0.23 → v0.24 → v0.25 before validating the v0.26 source-controlled modeling protocol. Preserve `case_id`, inspection/exploration flags, predictor-index status, and v0.25 split policy. The private CLI audit opens only the immutable v0.25 **metadata review**, not data files.
2. **Task-specific candidate registry:** Classification supports `dummy_prior`, `logistic`, `random_forest`, `hist_gradient_boosting`. Regression supports `dummy_mean`, `ridge`, `random_forest`, `hist_gradient_boosting`. Each requires tightly bounded and prespecified parameters; no automatic broad hyperparameter search or dependency-heavy packages are added.
3. **Explicit task routing:** Binary classification and continuous regression use different outcomes and metrics. Survival and longitudinal route to `SPECIALIZED_ENGINE_REQUIRED`, with no model execution: censoring, competing risks, repeated visits, dynamic indexes, observation-process effects and appropriate scoring remain future specialist implementations.
4. **Partition-first design:** GroupKFold for person-disjoint partitions; TimeSeriesSplit over **distinct timestamps** for forward validation. `person_and_forward_time` additionally demands group disjointness. All folds, training sizes, outcome diversity and row/group/time boundaries are verified before the first fit; unsuitable splits fail closed. IDs, groups, timestamps and targets are never predictor columns.
5. **Fold-contained learning:** Every candidate/fold constructs a fresh `Pipeline(preprocessing=v0.25, estimator=...)` and fits only on training rows. Validation is transformed with the training-fitted preprocessor and predictions are scored without fitting on validation.
6. **Paired development comparison:** Same folds for every candidate. Classification computes Brier, log loss, ROC AUC and average precision. Regression computes MAE, RMSE and R². Model ordering uses the preregistered primary metric; candidate ordering remains exploratory because the very same CV data is used for comparing and choosing models. No independent confidence intervals, holdout results or clinical calibration claims.
7. **Reproducibility:** Seed and bounded estimator settings are explicit; the returned synthetic-only report includes a config SHA256 and scikit-learn/Python versions. No fitted models, sample predictions, target arrays or participant rows are serialized or exported.

## Important limitations

- This prototype **does not** use nested selection to provide unbiased performance after choosing the winner, nor external validation, survey-weighted estimands, grouped bootstrap uncertainty, class calibration/recalibration, threshold or clinical utility optimization.
- `GroupKFold` is not a full survey/cluster-design analysis. It may reject limited-group or imbalanced cohorts, and it does not automatically protect site clustering unless the grouping definition reflects site relationships. `person_and_forward_time` can be infeasible for participants observed across both windows; rejection is correct until a specialized protocol is defined.
- Time-based folds require a clinically meaningful, verified timestamp. The helper only checks declared chronological order; it does not infer when derived features become available.
- Prespecified candidates are **examples**, not a universal best-model choice. HistGradientBoosting can struggle on tiny folds; tests therefore emphasize finite outputs, guards and deterministic comparison, not optimal scores.
- Do not pass real participant records through the `evaluate_synthetic_candidates` API. The synthetic flag is documentary and not a technical protection against intentionally misusing it.
- No publication figures, manuscript generation or presentation work is part of this engineering milestone.

## Developer API

- `validate_design(config, v25_recipe, case_manifest=None)` validates the task, candidate registry, task-specific metric, documentation ancestry, split and no-real-execution boundary.
- `make_plan(config)` creates a documentary blocked plan without data access.
- `evaluate_synthetic_candidates(config, v25_recipe, frame, y, row_ids=..., groups=..., timestamps=..., synthetic_fixture=True)` performs **only fictional fixture development CV** with preprocessing learned inside each fold. It returns **aggregate results only** and never writes to disk.
- `--plan` verifies source-controlled predecessors; `--audit` verifies the **v0.25 private metadata ledger** and creates one immutable private v0.26 metadata review. Neither command fits a model.

**Later priorities:** targeted leakage attack tests, selection uncertainty and nested CV under new study protocols, regression diagnostics, evaluation with genuinely untouched datasets, survival/censoring and landmark modeling, longitudinal mixed/GEE/dynamic outcomes, survey design and privacy-conscious deployment boundaries.
