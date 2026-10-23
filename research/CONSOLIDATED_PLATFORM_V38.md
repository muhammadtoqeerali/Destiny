# FrailtyScope v0.38 — Consolidated platform engineering, NOT a clinical release

## Delivered together

1. **Repair hosted browser QA** without Playwright CDN downloads: GitHub's Ubuntu image includes Google Chrome. CI checks `/usr/bin/google-chrome`, and `FRAILTYSCOPE_QA_CHROMIUM` opts the v0.34–v0.38 local-loopback browser suites into the system browser. Local developer machines retain bundled Playwright Chromium by default. Browser QA is never skipped.
2. **Runtime inference architecture:** `/api/inference` is a real server route that returns HTTP 403 and a stable structured denial for all GET/POST/PUT requests. It never reads a body, stores values, loads fitted clinical artifacts, or pretends a model is approved. This is a fail-closed *interface contract*, not activated clinical serving.
3. **Reproducibly fitted multi-output synthetic ML:** `scripts/build_fictional_models_v38.py` creates 1,200 entirely invented training/test records and fits 3 independent logistic classifiers with deterministic batch gradient descent. 960 invented records used to fit, 240 invented examples reserved, not independent clinical validation. Generated JSON under `web/app/data` (not the historical public NHANES aggregates); exact reproduction checked on every test run.
4. **Interactive explainability:** browser-only fictional inputs drive all three outputs simultaneously. The selected outcome shows exact additive terms on the fitted classifier's log-odds scale and the sigmoid output. Neither SHAP nor causality nor real patient explanations is claimed. Patient Assessment values are never passed to synthetic scoring, and no network POST is sent.
5. **Outcome-specific readiness:** four named requested *real* endpoints displayed separately: historical 5-year all-cause mortality, new diabetes, stroke, heart failure. All are unavailable, each for a genuine missing clinical model/validation reason. Historical NHANES mortality model results do NOT establish models for incident diabetes, stroke or heart failure.

## Scientific and privacy boundaries

`nhanes_mortality_v10` remains `BLOCKED_FOR_NEW_ANALYSIS`. v0.29 governance explicitly sets `real_data_execution_permitted=false`, `model_fitting_permitted=false`, `holdout_scoring_permitted=false`, `clinical_use_permitted=false`, `models_saved=false`. Current prediction index is provisional, 11/14 predictor source mappings are not reviewed, and the later cycle has been inspected. No newly untouched external test cohort and no approved clinical model package is registered. The historical endpoint is approximately 5-year all-cause mortality, **not** prediction of all future illnesses.

No participant-level NHANES/HUNT tables, holdout targets, saved models, private review audits or real patient records are read. The artificial coefficients *are learned from generated pseudo-data*, not the historical NHANES participants. Even when displayed as percentages, these scores are simulated outputs unrelated to disease incidence, frailty progression or actual mortality. Do not enter identifiable patient data into this public portal. Any clinical endpoint will require its own authorized model and independent evaluation.

## What is still needed for true patient-specific predictive use

- Named prediction outcome and time horizon, pre-specified prediction index, source variable timing, complete input and missingness mapping, consent and legal/ethical authorization.
- A model trained/registered under an explicitly authorized research protocol, immutable preprocessor/version/hashes, calibration and meaningful independent external validation, uncertainties and subgroup performance.
- Secure authenticated and audited patient-data flows, access control, retention policy, monitoring and rollback; appropriate medical-device evaluation, supervision and clinician oversight.
- For each *new disease outcome*, its own incident label, time-at-risk and follow-up, competing events handling where relevant, trained model, independent validation and outcome-specific explanations. Reusing a mortality classifier does not create these models.

## Release check

Full fixture/privacy tests, exact regenerated synthetic registry, immutable v0.30 integrity `--verify` only, CSS PostCSS, Next.js types/build, all v0.34–v0.38 Chromium desktop/mobile suites. Approved source paths only; backup/rollback on installer failure; fresh uppercase YES for publisher. Prior unrelated untracked interview-brief files untouched. GitHub Actions outcome unknown until new workflow runs; preinstalled Chrome may have compatibility issues and these must be fixed rather than skipping tests.
