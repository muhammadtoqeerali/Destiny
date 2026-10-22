# FrailtyScope v0.25 — fold-safe preprocessing contracts

**Purpose:** A reusable, sklearn-compatible, **synthetic-only** prototype connecting source-backed v0.24 harmonization with train-fitted data transformations. This release **does not** authorize reading real participant datasets, fitting real NHANES/HUNT models, using a previously inspected evaluation cycle, clinical use, or publishing research artifacts. A `synthetic_fixture=True` parameter is a documented execution condition, **not a data-security sandbox**; only synthetic inputs are permitted in v0.25.

## Two strictly separate transformations

**Source contract (fixed, v0.24):** Apply only reviewed codebooks, approved units and routing rules. Preserve `feature` and `feature__status` (observed, structural skip, refusal, unknown, does not do activity, etc.). Never call raw code 5 a severity score or infer a questionnaire skip without routing evidence.

**Learned preprocessing (this release):** Build a fresh `sklearn.pipeline.Pipeline` per **training fold**. Numeric features use fold-trained median imputation, optional StandardScaler/RobustScaler, plus a *fixed-shape* missingness indicator. Categorical/ordinal/binary features are one-hot represented, with approved codebook categories fixed in the protocol or inferred **from training only**. Missing source statuses always receive separately defined one-hot columns; they are never flattened into generic NaN. Unseen, undeclared source status is an error. Unseen ordinary categories error by default; `ignore` must be explicitly configured for open-vocabulary categorical inputs. All-missing training columns are rejected. No automatic outlier deletion, target encoding, scaling before splitting, or full-dataset feature selection.

### Safe sequence for a future authorized assignment

1. Establish authorized data access and a signed study definition. Verify prediction index, outcome, task type, eligible population, source dictionary, and complete feature harmonization; do not bypass v0.22–v0.24 readiness findings.
2. Choose evaluation strategy **before** preprocessing: disjoint persons/sites, prospective time split, or a documented combination. Keep participant/site IDs, visit timestamps, outcomes, censoring/event information and survey weights *outside* predictor columns. `validate_partition()` or `prepare_synthetic_fold()` checks a proposed split; it does not manufacture a statistically valid split.
3. Within each training fold: fit source-compatible imputation, encoding, scaling and (later) feature selection **only on the training subset**. Transform validation with the same fitted objects, without refitting or updating statistics. Tune hyperparameters/preprocessing within development folds only.
4. Use the resulting matrix with appropriately validated downstream estimators: classification and regression can use `make_model_pipeline()`; survival models need separate censorship/event logic and time-dependent scoring; longitudinal models need visit-history and outcome-time semantics. This release implements the *shared predictor transformer*, **not** generic survival/longitudinal model fitters.
5. Keep one genuinely untouched independent evaluation dataset for a new study; the NHANES 2013–2014 cohort was inspected previously and is not such a dataset.

## Implemented API (synthetic fixtures only)

- `validate_recipe(config, dictionary, harmonization)` checks identity and predecessor research boundaries, exact mapped feature coverage and v0.24 codebooks/statuses.
- `build_preprocessor(recipe, synthetic_fixture=True)` returns **unfitted** sklearn Pipeline for predictor transformation only.
- `make_model_pipeline(recipe, estimator, synthetic_fixture=True)` returns **unfitted** sklearn Pipeline composed of preprocessing and a supplied classifier or regressor. This is demonstrated solely on invented toy examples.
- `validate_partition(train_ids, valid_ids, policy=..., train_groups=..., valid_groups=..., train_time=..., valid_time=...)` rejects repeated row IDs, overlapping groups when required, and non-forward timestamps when required; group/time variables must not be in predictor features.
- `prepare_synthetic_fold(...)` checks partition boundaries **before** it fits the preprocessor on training-only data and transforms validation.
- `--plan` validates **source-controlled metadata only**; `--audit` checks only immutable v0.24 private **aggregate metadata**, then saves an immutable private metadata-only review. Neither CLI mode opens participant records or creates models.

## Explicit limitations and next engineering steps

- The current NHANES contract contains **only 3 verified PFQ mobility fields**, with the remaining 11 predictors unmapped and the prediction index provisional; it is **blocked for new real analysis**.
- The v0.25 numeric logic exists as a generic tested API with invented numeric fixtures. The actual NHANES v0.24 mapped subset is *ordinal one-hot*; this release does not claim complete numeric source coverage.
- Feature-type and codebook validation are programmatic contracts, not independent medical verification. `unknown='ignore'` in open-vocabulary categoricals can hide drift: log/quantify unknown levels in future approved deployments.
- No group-level or survey-design valid uncertainty, no rare-event handling, no dynamic/landmark survival engineering, no longitudinal outcome leakage proof, and no automatic intervention/casual analysis.
- The partition validator is a developer tool, not a guarantee that all cross-validation libraries are used correctly. A future approved executor must enforce group/time split construction end to end.
- Joblib deserialization is unsafe for untrusted model files; future persistence must require local trusted artifacts and checksums. Synthetic round-trip testing is **not** approval to deserialize external binaries.
- No real-data scoring, clinical performance evidence, calibration, transportability or clinical-use authorization is claimed.

Official sklearn leakage/pipeline guidance: https://scikit-learn.org/stable/common_pitfalls.html
Official OneHotEncoder reference: https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html
