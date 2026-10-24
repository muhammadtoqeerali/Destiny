# FrailtyScope — NTNU Postdoc Interview Reset (three focused phases)

## Purpose
Demonstrate strong machine-learning reasoning and executable skills for the NTNU Postdoctoral Fellow in Machine Learning and Digital Health Services for Frail Older People interview. This is an interview research demonstrator, not a hospital information system or approved medical device.

## What changes now
* Primary interview questions: Is there a suitable older-person cohort? How would we define frailty or later functional decline without leakage? How do we handle repeated visits, missingness and survey bias? Which candidate model performs best on the chosen real dataset under a fair evaluation? Can a nontechnical clinician understand observed measurements and limitations?
* Keep `/doctor` and `/admin` intact as **legacy advanced research workspaces**. New `/interview` is the concise public entrypoint and `/admin/interview` is a protected, dataset-specific ML evidence view. The old features are retained but no longer lead the interview narrative.
* Never claim an invented benchmark validates HUNT or patient outcomes. The generated cohort deliberately tests pipeline and UI integration only.
* No manual patient entry, visit editing or care-system integration is needed for the immediate assignment.

## Preferred dataset sequence
1. **NHATS** (US): longitudinal older adults, mobility, functional limitations, ageing-related outcomes. Registration required; its variables/outcome coding must be verified before training.
2. **SHARE** (Europe): repeated ageing survey waves, scientific-use after individual registration. Strong alternative if access is faster.
3. **HRS**: longitudinal older-age research, registered download. Backup or separate replication dataset.
4. **Historical NHANES**: preserve as its own ~five-year mortality benchmark; `BLOCKED_FOR_NEW_ANALYSIS` means no new fits or holdout scoring on this historical case.
5. **HUNT4 70+**: scientific target and interview context, *not accessible for model fitting* without project-specific authorization. Study-specific HUNT variable definitions are never inferred from generated data.

HUNT4 70+ published methods include a Fried phenotype and a HUNT 35-item frailty index; this is *not* the training target implemented by our generated fixture. Citation sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC11387435/ and https://www.ntnu.edu/hunt/data

## Phase I — honest executable foundation (this release)
* An artificial older-adult tabular cohort with documented generator and invented future ADL-decline label.
* Identical baseline features and person-disjoint 60/20/20 train/validation/test for Dummy, logistic regression, random forest and histogram gradient boosting.
* All transformations fitted on train only; compare validation Brier, AUC and AP; choose one algorithm by validation Brier alone; evaluate on synthetic heldout set only once; report calibration bands and sparsity.
* A doctor-focused fictional person explorer and protected admin dataset selector that explicitly separates synthetic, historical NHANES and unavailable datasets.
* Old research dashboards preserved; no real participant examples on Vercel.

## Phase II — the main scientific work, after dataset access
* Inspect actual wave-by-wave codebooks, frailty phenotype/ADL target definitions, missingness/structural skips, units, sample design and permitted usage.
* Freeze ONE prospective outcome, relevant population, index time, follow-up and allowable features. Compare strong baselines and hyperparameter-tuned tree ensembles including XGBoost/CatBoost only if justified by available columns and training size.
* Group by person, preserve chronology where possible, nested/internal validation without touching held-out evaluation, report AUROC and PR-AUC, Brier and calibration, confidence intervals with appropriate resampling, fairness/subgroups, missingness sensitivity and leakage audit. Pre-register selection criteria rather than cherry-pick highest AUC.
* Attribution: global permutation/shap with appropriate background assumptions; per-example explanation only for legally permitted deidentified research examples, and check stability. No causal language.
* Each dataset remains isolated. Do not compare scores from different endpoints/cohort sizes as a fair head-to-head ranking. Survey weights and selection biases require explicit analysis.

## Phase III — interview presentation and handoff
* Doctor front page: clear available cohort summary, conditions/function, annotated longitudinal trajectory, explained validated *research* predictions only if permissible; otherwise clearly synthetic examples.
* Admin front page: dataset selector, input dictionary, preprocessing and splits, full comparable model leaderboard, calibration/uncertainty, error-analysis and source citation. Move advanced diagnostics into expandable secondary pages.
* Five-minute narrative: study question → cohort and leakage safeguards → model choices and why → honest results and limitations → how it could transfer to a future HUNT assignment.

## Important limits
No model is universally 'best'. Selection is relative to the dataset, target and metric, and must use the same split. Synthetic generator performance cannot establish real-world accuracy. HUNT/SHARE/NHATS individual records or licensed data must never be shipped to GitHub/Vercel. No clinical patient scoring is permitted in the current repository; `/api/inference` remains blocked.

## Reproduce phase I

```bash
PYTHONPATH=. .venv/bin/python -m ml.interview_benchmark_v47 --check
```

All synthetic results live in `web/app/data/interview-benchmark-v47.json` and are regenerated using only `ml/interview_benchmark_v47.py`. No real NHANES model, participants or artifacts were touched.
