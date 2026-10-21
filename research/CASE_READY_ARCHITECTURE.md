# FrailtyScope: case-assignment-ready architecture (v0.10)

## Goal

Retain a reproducible, inspectable scientific pipeline rather than guessing the content of an unreceived assignment. **No additional dataset access or NHATS registration is required for this release.** The existing NHANES 2011–14 plus 2019 linked mortality benchmark is the verified working reference, not a stand-in for an unspecified assignment.

## Implemented layers and their contracts

| Layer | Source | Inputs | Outputs | Guard |
|---|---|---|---|---|
| Source validation | `ml/case_engine_v10.py` | Local CSV/XLSX/Parquet/Stata/SAS + JSON manifest | Verified dataframe and SHA-256 fingerprint | Files under ignored `data/`; ID uniqueness; target validation; optional provenance check |
| Split strategy | `ml/case_engine_v10.py` | Cohort or random split | Training / validation / reserved evaluation | No overlapping partitions; no target/identifier as features; stable random seed |
| Feature pipeline | scikit-learn ColumnTransformer | Named numeric/categorical feature lists | Numeric imputation + scaling, categorical imputation + one-hot encoding | Fitted separately inside CV training folds and on final training set, never test |
| Model registry | `model_for()` | Task type + algorithm + parameters | Binary classification or regression model | No implicit clinical interpretation, no forced GPU |
| Optimisation | Optuna TPE | Training partition only | CV-loss-optimised candidates (Brier / 1−AUC / RMSE / MAE by configured metric) | Model choice and threshold on validation, not evaluation |
| Evaluation | `calculate_metrics()` | Selected model + later cohort | Classification: ROC-AUC, AP, Brier, precision, recall, F1 and confusion; regression: RMSE, MAE, R² | Dummy baseline, disclosed threshold, aggregate-only output |
| Explainability | Permutation importance + existing NHANES SHAP | Validation outcomes and chosen model | Ranked feature reliance | Explanation ≠ causation; no individual SHAP exported |
| Experiment record | `artifacts/cases/<case_id>/` | Config / fingerprint / model summary | `metrics.json`, `experiment_summary.md`, selected fitted `best_model.joblib` (training partition only) | Local ignored artifacts only; no patient rows / IDs / predictions |
| Admin portal | `Benchmark` tab | Current baseline/refined NHANES public aggregates | Model choice and error trade-offs | Displays only implemented, aggregate results |
| Doctor portal | Existing v0.8 interface | Current real cohort aggregates + user-entered session measurements | Health profiles, assessment and visits | No NHANES row-level records in public app |
| Survival engine | Existing `ml/nhanes_survival_v09.py` | NHANES linkages | Local Cox benchmark report | Time-to-event benchmark separate from classification |
| Longitudinal validation | Existing `ml/nhats_longitudinal_v09.py` | Official registered wave files, verified codes | Local transition audit | No assumption NHATS files exist; registration/access separate |

## How to adapt when assignment arrives

1. Capture exact target question, cohort, index date, prediction horizon, available features and allowed data uses.
2. Select task family: binary classification or regression via the case runner; time-to-event via v0.9 Cox; genuinely longitudinal outcomes via validated wave mapping. **Multilabel, competing risks, trajectory forecasting, causal effects and external validation are NOT implemented generically yet.** Only claim them if actually completed.
3. Copy `research/cases/CASE_ASSIGNMENT_TEMPLATE.json` to a new checked-in *source-only* manifest after replacing every placeholder with verified source columns and outcome definitions; put actual data only in ignored `data/`.
4. Choose split design based on assignment: cohort/time where meaningful, else random; account for site/patient grouping if repeated observations. The v0.10 tabular runner rejects repeated record IDs and is not a group-aware longitudinal training engine.
5. Run dry-run validation, then train. Review the report, baseline, missingness, threshold and expected error consequences before making claims.
6. Provide a coherent evidence story in the Admin view and a clinician-friendly interpretation in the Doctor view, using only implemented outcomes. Do not display internal task-planning text on the website.
7. Keep evaluation data fixed and treat results on repeatedly inspected cohorts as exploratory, not fresh external validation.

## What v0.10 explicitly does NOT claim

- Best possible performance, universal state-of-the-art, clinical safety, prospective validity, or causal interpretation.
- Generic survival API inside `case_engine_v10.py` (use separate existing survival module).
- Imported NHATS participants, real repeated clinical visits, or ready-to-use HUNT data.
- Production multi-user authentication, encrypted healthcare-record storage, regulatory clearance, or EHR integration.
- All-model SHAP parity or GPU acceleration; existing NHANES experiment has SHAP aggregates, new case runner uses permutation importance.

## Privacy and publication

The default repo ignores `data/` and `artifacts/`. Never put registered datasets, participant rows, IDs, individual predictions or model binaries in GitHub, Vercel, chat files or public CI artifacts. Only reviewed aggregate reporting that complies with source terms may be published. This release's publishing script stages **code, tests, manifest templates, documentation and the Admin portal source only**, not new JSON data or results.
