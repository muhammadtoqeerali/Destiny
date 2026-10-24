# FrailtyScope NTNU interview — final phase (v0.49)

## Fixed three-phase objective

**Position:** NTNU Postdoctoral Fellow in Machine Learning and Digital Health Services for Frail Older People.

**Phase 1 (v0.47):** concise Doctor/Admin interview-facing software and executable fictional ageing cohort; completed and published.

**Phase 2 (v0.48 + preprocessing corrections):** actual no-registration CDC NHANES 2015–2016 and 2017–2018 public-use records, a separate, reproducible *cross-sectional, current quarter-mile walking difficulty* classification study. CatBoost selected using 2015–2016 validation Brier. Earlier 2011–2014 mortality historical case remains frozen/blocked and is NOT pooled. Source published at fd8b099, real records remain outside Git.

**Phase 3 (v0.49):** present the reviewed real **aggregate-only** NHANES metrics alongside clearly separate fictional person examples. Do not show or serve real patient rows, trained models or person-level scores. When installed, tested and published, the agreed three-phase interview software deliverable is complete.

## 5-minute interview demonstration (practise aloud)

**0:00–0:40 — Research motivation.** "For an NTNU/HUNT-oriented ML workflow I demonstrated a full tabular research experiment on public older-adult NHANES data. HUNT data are not used. I chose a valid current self-reported mobility outcome to avoid inventing longitudinal events."

**0:40–1:25 — Source variables and preprocessing.** CDC 2015–2016 development, 2017–2018 later survey; age 65+. Merge six questionnaire/exam modules by SEQN locally; correctly distinguish PFQ054 skip logic from negative outcomes; correct pandas SAS XPORT numeric-zero artifact exactly; require nine valid DPQ items to sum PHQ-9. Exclude leakage-prone PFQ predictors. Use only eight permitted features: age, BMI, PHQ-9, arthritis, heart failure, stroke, diabetes, sex. Report missingness and age 80+ top-code; train-only preprocessing.

**1:25–2:25 — Fair model selection.** 788 earlier-cycle training and 197 earlier-cycle validation. Six model families (dummy, logistic, forest, histogram boosting, XGBoost, CatBoost); 3-fold CV where applied. Lowest validation Brier selected CatBoost (0.15070), with logistic regression close (0.15377) and stronger cross-validation Brier (0.16627 against CatBoost 0.17675). No universal-best claim.

**2:25–3:25 — Later-cycle results.** 1,032 later-cycle records, 278 currently reporting walking difficulty. Exploratory *previously inspected* ROC-AUC 0.732, AP 0.475, Brier 0.174; row-bootstrap AUC interval 0.701–0.768 **not survey-design adjusted**. Sensitivity at arbitrary 0.5 cutoff only 17.3%; calibration 20–40% band underpredicts (28.2% vs 35.3% observed). A better threshold requires a purpose-defined decision analysis. This is a repeated exploratory evaluation, not fresh independent validation.

**3:25–4:20 — Interpretability.** Validation permutation importance shows arthritis and PHQ-9 as top model reliance features, followed by BMI, diabetes, stroke, heart failure. This is *not* causal effect or real-person SHAP. The Doctor page provides fictional records with separately trained fictional logistic explanations; those probabilities are not from the NHANES model.

**4:20–5:00 — Transfer to HUNT research.** Explain how cohort eligibility, visit linkage, harmonization, missingness, participant-disjoint split, survey/time design, calibration, prospective endpoint definition, frailty outcome mapping, robust validation and explainability must be adapted once HUNT protocol and legitimate access are specified. Do **not** claim actual HUNT model performance, future-disease prediction, patient risk estimates or clinical readiness.

## Demo URLs

- `/interview`: simple clinician research snapshot **plus explicitly fictional example profiles**. This is not a patient portal or a predictor for individuals.
- `/admin/interview`: select **NHANES 2015–2018 mobility** (default) for six-model comparison and aggregate results; select artificial cohort or historic mortality separately. Existing `/doctor` and `/admin` advanced workflows remain unchanged.
- Admin research preview uses the existing public static-aggregate demo access, **not a security mechanism for private data**.

## Data and provenance protection

`web/app/data/real-mobility-summary-v49.json` is a hand-curated **small aggregate-only** presentation derived from the user's printed real-data report. `python -m ml.interview_results_v49 --verify-local PATH` compares its entire numerical content to the previously generated local **aggregate-only** report before release. It never opens XPT/person records or model artifacts, never publishes the local report, never writes outside the public reviewed summary, and never relaxes `/api/inference` (403). Private aggregate source fingerprints are NOT copied into the public bundle.

The local 2017–2018 evaluation was previously scored under v0.48 before fixing PHQ decoding; rerun is exploratory repeat sensitivity, not a newly untouched test. Complex survey-design uncertainty is not available and any population-generalizable claims require suitable survey-design methods. Data privacy and NHANES/HUNT provenance are never conflated.

## Completion criterion

When v0.49's exact-source installer, aggregate verification, all Python source/privacy regressions, the production Next.js build and desktop/mobile Playwright suites pass, followed by the exact-source guarded publisher and hosted CI, **the agreed three-phase NTNU interview project is complete.** Do not add more synthetic dashboards, model families, PHI forms or new dataset downloads.
