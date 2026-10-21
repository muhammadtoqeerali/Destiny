# FrailtyScope: real HUNT integration and multidimensional outcome plan

## What is REAL today, and what is NOT

- **REAL published HUNT figures:** HUNT4 70+ original catchment area **9,956** participants (2017–2019); HUNT4 Trondheim 70+ **1,743** additional participants (2018–2019). Source: Skjellegrind et al., *International Journal of Epidemiology*, published 19 February 2026, https://academic.oup.com/ije/article/55/2/dyag011/8490101
- **REAL HUNT research resources:** publicly browsable metadata and questionnaire/measurement catalog. https://hunt-db.medisin.ntnu.no/hunt-db/
- **NOT AVAILABLE HERE:** row-level HUNT participant records, linked register events, authorized repeated clinical examinations, target labels. No actual HUNT patient was used to fit any FrailtyScope classifier or calculate model accuracy.
- **SYNTHETIC research demo:** 6,000 fictional participants, 14 illustrative features, five independent fabricated future-event labels, four algorithms each (20 fits), three-way random patient split. These results do not establish healthcare prediction utility.

## Authorization and protected execution

Contact the NTNU/Digi-FrailCare team to identify the principal investigator, the approved protocol, purpose, REK approval and HUNT DAC decision, signed agreement, authorized data delivery and computing environment. International collaborators require an eligible Norwegian PI. Registry linkages and any additional outcomes require their own permissions. Never retrieve row-level HUNT data from unofficial sites or copy extracts onto a personal workstation without institutional authorization.

- Official HUNT access: https://www.ntnu.edu/hunt/dataaccess
- HUNT databank: https://www.ntnu.edu/hunt/databank
- Digi-FrailCare objectives: https://www.ntnu.edu/digitalfrailcare

**No protected HUNT extracts, event dates, row-level predictions, linked pseudonyms, models trained on restricted data, or private statistics may be copied into `web/`, Vercel, GitHub or chats.**

## Outcomes and exact label definitions to agree with clinicians

The labels below are **PROPOSED**, not evidence of released fields:

| Domain | Draft outcome | Preferred evidence | Challenges |
|---|---|---|---|
| Falls | First new fall within 365 days of baseline | Dated prospectively ascertained fall event | Recall/ascertainment, recurrence |
| Fracture | New fracture within 365 days | Approved fracture registry linkage | Trauma coding, competing death |
| Dependence | New ADL/IADL dependence | Repeated validated ADL measures | Availability/timing |
| Cognition | Cognitive deterioration | Repeated validated cognitive scores and/or a clinically agreed decline definition | Practice effects, missingness, measurement invariance |
| Hospitalization | Any acute hospital admission | Approved hospitalization records | Admission type, access and coding |
| Mortality (future extension) | Time to death | Approved Cause of Death Registry | Competing risks, survival modeling |
| Frailty progression (future extension) | Transition between prespecified frailty states | Prospective assessments, agreed frailty phenotype/index | Leakage when the same indicators define the target |

For each outcome, define an index time, at-risk cohort, prior-event washout, event definition, first event/repeated events, death as competing event, loss to follow-up, time horizon, censoring and clinical acceptability. Prediction of “what disease a patient will get” is **not** supported without dated, ascertained disease endpoints; avoid claiming this.

## Approved data import contract (NOT HUNT original variable codes)

`ml/approved_hunt_adapter.py` accepts already authorized, pseudonymized and mapped CSV extracts inside an institutional secure environment:

- baseline file: `participant_id`, `baseline_date` (YYYY-MM-DD), plus the 14 standardized feature names in `ml/schema.py`.
- follow-up file: `participant_id`, `last_observed_date`, optional `death_date` and **approved and accurately defined** `first_fall_date`, `first_fracture_date`, `first_new_dependence_date`, `first_cognitive_decline_date`, `first_hospital_admission_date`.
- One baseline row and one follow-up row per pseudonym. The 14 standardized names are illustrative research contracts and do **not** claim HUNT field equivalence. Mapping from delivered actual variable IDs must be reviewed by investigators.
- Negative (`0`) is assigned only with ≥365 days of verified follow-up; if follow-up ends earlier and no event is observed, the label is unresolved (`NA`). Death truncates follow-up for non-death outcomes. Recorded events after death or inconsistent dates require data review.

These simple 12-month binary labels are **not** substitutes for survival analysis with competing risks or repeated event modeling. More advanced longitudinal time-varying features and right-censoring methods should be selected after reviewing what is actually measured.

### Local data-readiness command — only in the approved research environment

```bash
python -m ml.approved_hunt_adapter \
  --baseline /institutional/approved/baseline_mapped.csv \
  --followup /institutional/approved/followup_mapped.csv \
  --acknowledge-approved-environment
```

### Local restricted benchmark — only in approved research environment

```bash
python -m ml.advanced_multitarget \
  --mode approved-local \
  --baseline /institutional/approved/baseline_mapped.csv \
  --followup /institutional/approved/followup_mapped.csv \
  --acknowledge-approved-environment
```

The adapter does not send, export, persist or publish patient-level results. The real-data prototype currently requires at least three distinct baseline dates for a simple temporal split, with enough eligible events in all partitions; if the approved HUNT subset has a single baseline wave, the model deliberately refuses to substitute a random split. A scientifically justified design must then be chosen with NTNU researchers. Do not interpret the code as regulatory approval or production clinical readiness.

## Modeling roadmap with real data

1. Validate data rights, variable mapping, quality, known missingness mechanisms and risk-set definition.
2. Compare regularized regression, gradient boosting, XGBoost and CatBoost using train-only preprocessing. Evaluate calibration, ROC-AUC, PR-AUC/average precision, sensitivity, specificity and decision curves.
3. Use repeated visits and suitable time-to-event models (Cox/penalized Cox, survival forests, competing-risk approaches) where observation windows and censoring permit. No post-outcome features at baseline.
4. Evaluate bootstrapped confidence intervals, fairness across age/sex/availability groups, transportability, external cohorts, temporal drift, missingness sensitivity, proper model cards, and clinical utility before considering deployment.
5. Obtain clinician input and institutional information-security, data-protection and clinical governance review. Real patient dashboards must run within approved systems, **not** public Vercel.
