# Research protocol — decision log before HUNT access

**Status:** methodology proposal. No access to person-level HUNT data claimed.

## Question and outcome

- Main use case: new falls / fractures / dependence after a well-defined baseline among at-risk older adults. Outcome, verification source, and date must be signed off with clinicians/data custodians.
- Prediction moment `t0`: first eligible assessment / approved index visit, strictly before any included outcome.
- Determine whether recurrent events, interval-censoring and death as a competing event require survival or competing-risks methods. A 12-month binary toy target is NOT the default for real research.

## Data dictionary and mapping

- Capture raw variable ID, survey/questionnaire wave, question wording, categories, unit, valid ranges, measured timestamp, assessment modality, missing/not-applicable codes and data permissions.
- Map separately for original HUNT region vs Trondheim 70+ because instrument coverage and participation differ.
- Wearables: verify raw vs derived accelerometer availability, minimum recording time, nonwear rules, and temporal relationship to outcomes.
- Establish outcome linkage date window and ethics scope before merging external registry files.

## Leakage and eligibility

- Reject measurements after prediction time.
- Prevent person/family/visit overlap across folds and institutions; avoid repeated measures crossing boundaries.
- Pre-specify missingness analysis, nonresponse mechanism, imputation folds and representation of missingness.
- Split by geography / enrollment year / health system to test transportability where justified, not simply random row-wise splitting.
- Handle censoring, follow-up time, competing mortality, and event ascertainment bias explicitly.

## Benchmark analysis

- Start with regularized logistic / Cox models as transparent comparators, depending on endpoint and censoring.
- Strong tabular competitors: gradient boosting and CatBoost, with nested or held-out tuning and model-selection accounting.
- Calibration intercept/slope, discrimination with uncertainty, net benefit, age/sex/functional-status subgroup checks, missingness and wearable/oral-health ablations.
- Quantify risks of measurement error, missing-not-at-random and geographic shifts; report TRIPOD+AI information and risk-of-bias assessment.

## Clinical decision support

- Never imply a synthetic estimate is a real risk score. Reasons presented by SHAP/perturbation are model associations, not causes.
- Show absolute time horizon, confidence/uncertainty and data provenance. Co-design information architecture with clinicians and physiotherapists.
- No automatic treatment decisions or public app with real patients; conduct relevant legal/security, human factors and prospective validation.

## Interview demo

1. Explain actual data access and cohort constraints.
2. Demonstrate 6-algorithm-feature-set experiments on synthetic records and independent holdout.
3. Show feature availability, partial dependence limitations and patient-level model sensitivity.
4. Explain which claims cannot yet be made (no clinically valid predictions, no real effect sizes).
5. Propose adaptation plan with HUNT team and evaluation design.
