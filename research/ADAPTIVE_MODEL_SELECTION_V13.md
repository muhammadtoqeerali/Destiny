# FrailtyScope v0.13 — High-quality model-selection protocol

**Scope:** robust, reusable tabular binary classification and regression. Runs local only. This is a **new selection experiment**, not a demonstration that a higher ROC-AUC is achievable. No fitted models, clinical decisions, or individual records are published.

## Scientific and engineering rationale

1. Define the **estimand**, prediction index, predictors available at that time, outcome and horizon. For HUNT-like waves, do not treat repeated person-visits as IID: first derive a person-level landmark dataset or use a dedicated group- and time-aware longitudinal protocol. The v0.13 runner refuses repeated respondent IDs and unimplemented temporal splits.
2. Decide **primary metric before seeing results**: Brier for calibrated risk probabilities; ROC-AUC for pure discrimination; average precision when positives are rare; MAE/RMSE for continuous outcomes. Record the clinically meaningful secondary metrics and constraints separately.
3. **Holdout lock:** the later NHANES cycle was examined repeatedly in previous releases. It cannot be called untouched external validation. This protocol trains and selects only on the development period. The optional `--evaluate-once --acknowledge-holdout` is explicitly marked as a reused benchmark.
4. **Nested assessment:** each outer development fold runs the full family-screen/refine/selection procedure on its own inner folds. Only then is the winner evaluated on the untouched outer assessment fold. This estimates the procedure's internal performance instead of picking the best reported family score.
5. **Budgeted portfolio:** screen all declared candidates with a small number of Optuna trials; refine only top K families with a larger budget, then choose using the fixed primary loss. Very close candidates may be resolved by a declared simple-model preference, not by evaluation-set performance. This is a practical margin, not a statistical equivalence test.
6. Refit the winner on **development only** and derive a working classification threshold from development out-of-fold probabilities. This threshold is research-only and requires clinical utility evaluation before use.
7. Preserve **source and artifacts** separately: case JSON, protocol JSON, input hash, nested scores, chosen hyperparameters, fixed seeds, trained model binary in ignored `artifacts/`, and a separate one-time evaluation seal. Never release respondent-level scores.

## Model portfolio

The current local runner supports: regularized logistic/ridge, histogram gradient boosting, random forest, XGBoost and CatBoost through the existing tested case engine. It does NOT yet run LightGBM, TabPFN, AutoGluon, ensembling, deep learning, or competing-risk/survival models. Those may be added **behind the same protocol** after dependency, data governance and hardware review; their research reputation is not evidence they must win a particular task.

- Smaller tabular classification: evaluate CatBoost and XGBoost, logistic baseline, optionally TabPFN if conditions/license/hardware permit.
- Larger mixed-type data: consider LightGBM and CatBoost with native missing/categorical treatment, plus AutoML as an optional comparator.
- Time-to-event (mortality/falls with censoring): use penalized Cox, survival boosting/forests, survival-specific metrics, censoring and competing-risk rules. Do NOT convert censored observations to negative labels.
- Repeated waves: explicit index-date / prediction horizon and subject-wise + time-aware validation, longitudinal feature generation, attrition/missingness review. This is not silently handled by a random split.

## Workstation instructions

From the project root after installation:

```bash
# Schema, event prevalence, grouped leakage and missingness inspection only; no fitting
PYTHONPATH=. .venv/bin/python -m ml.case_strategy_v13 --plan

# Explicit costly development-only nested search on workstation; fits many temporary candidates
set -o pipefail
PYTHONPATH=. .venv/bin/python -m ml.case_strategy_v13 --search 2>&1 | tee ~/frailtyscope-v13-search.log

# Optional only after reviewing selected model, explicitly reuse the PREVIOUSLY INSPECTED NHANES later cycle.
# Do not interpret its metrics as unbiased untouched external validation.
PYTHONPATH=. .venv/bin/python -m ml.case_strategy_v13 --evaluate-once --acknowledge-holdout

# Source only; after reviewing search outputs
bash scripts/publish_strategy_v13.sh
```

For a new case, copy and edit both the v0.10 case manifest and `ADAPTIVE_STRATEGY_TEMPLATE_V13.json`. Update case ID, file path under ignored `data/`, feature roles, outcome and groups. Use a genuinely locked holdout if available and subject/time-based validation if the scientific task requires it. `--evaluate-once` is sealed against repeated runs for a given case and dataset.

**Reports and models remain local:**

`artifacts/cases/<case_id>/strategy_v13/selection.json`
`artifacts/cases/<case_id>/strategy_v13/winner_development_only.joblib`
`artifacts/cases/<case_id>/strategy_v13/evaluation_once.json` (only if explicitly opened)

**Sources for methodology and model portfolio**

- [scikit-learn: avoiding preprocessing leakage](https://scikit-learn.org/stable/common_pitfalls.html)
- [TRIPOD+AI (BMJ, 2024)](https://www.bmj.com/content/385/bmj-2023-078378)
- [PROBAST+AI (BMJ, 2025)](https://www.bmj.com/content/388/bmj-2024-082505)
- [TabPFN, Nature (2025)](https://www.nature.com/articles/s41586-024-08328-6)
- [Systematic real-world hospital benchmark, iScience (2026)](https://doi.org/10.1016/j.isci.2026.115654)
- [HUNT official Databank](https://hunt-db.medisin.ntnu.no/hunt-db/)

No model trained on the assistant's environment. Unit tests are structural and do not call `.fit()`.
