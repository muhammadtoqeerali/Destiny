# Research brief: HUNT4 70+ and Digi-FrailCare

Prepared 20 October 2026. The claims below refer to public documentation; they do not describe any approved project-specific extract.

## Position alignment

NTNU vacancy "Postdoctoral Fellow in Machine Learning and Digital Health Services for Frail Older People" seeks work with HUNT epidemiology, relevant registries and wearable activity data, within interdisciplinary GeMS-R. Digi-FrailCare explicitly lists transparent ML prediction of falls, fall-related fractures and dependence as a research aim.

Sources: [vacancy copy](https://jobbsafari.no/jobb/postdoctoral-fellow-in-machine-learning-and-digital-health-services-for-frail-older-people-473812), [Digi-FrailCare](https://www.ntnu.edu/digitalfrailcare).

## Key cohorts

- HUNT1 (1984–1986), HUNT2 (1995–1997), HUNT3 (2006–2008), HUNT4 (2017–2019) are longitudinal waves; different instruments and selection between waves.
- The HUNT4 70+ cohort paper (published 19 February 2026) describes **9,956** people from the historical HUNT area and **1,743** additional Trondheim participants. Do not combine automatically without checking recruitment, missingness, measures and compatibility.
- HUNT4 70+ data types: nutrition/weight loss, exhaustion, SPPB/gait/strength, MoCA/CERAD, oral health, activity monitors, physiological measurements, and more.
- Some measurements are **subcohort-specific**: ROAG-J coverage differs dramatically between cohorts; HUNT4 Trondheim 70+ did not collect the same laboratory and biological materials as the main 70+ cohort.
- HUNT may be linked to registers (with appropriate approvals) for actual later outcomes. Public materials do not constitute access to linked falls, fractures or ADL follow-up labels.

Sources: [2026 cohort profile](https://academic.oup.com/ije/article/55/2/dyag011/8490101), [HUNT variable browser](https://hunt-db.medisin.ntnu.no/hunt-db/), [data access](https://www.ntnu.edu/hunt/data).

## Proposed primary task, pending team approval

**Aim:** Predict a genuinely future clinically defined adverse event among eligible adults ≥70, e.g. an incident fall-related fracture within 24 months or prospectively ascertained falls within 12 months, conditional on *the actual linked labels and time stamps being available*. These cannot be inferred from the public catalog.

**Design:** cohort index date at completion of HUNT4 baseline, predictors known strictly at or before index; remove prevalent conditions or first-event cases according to endpoint. Capture censoring, death as competing risk where relevant, and register follow-up.

**Development/validation:** first train an interpretable logistic regression or Cox cause-specific hazards baseline as appropriate. Compare gradient-boosted trees and survival models, nested tuning, bootstrap CIs, Brier / C-index / time-dependent AUC, PR-AUC, calibration, decision curves and clinically defensible thresholds. Handle participant and household clustering if necessary; avoid leakage from follow-up values. External/temporal holdout if available.

**Missingness:** describe cohort flow and missingness by feature, cohort, outcome, and availability of oral and sensor subsets. Avoid complete-case-only selection by default; compare missingness strategies and imputation within folds. Wearable-only analyses are a selection-sensitive sub-study.

**Explanations:** global and local feature attributions, calibrated risk with absolute horizon, subgroup calibration, threshold provenance and intervention disclaimers. Feature influence is associative, not causal; no suggestion that changing a feature necessarily changes risk.

**Human-centered design:** avoid diagnoses, automation bias and unvalidated interventions. Conduct usability evaluation with geriatric clinicians; show missingness and uncertainty; avoid definitive future-health predictions.

**Reporting:** TRIPOD+AI checklist, model card, data dictionary, ethics/data security plan, and audit trail.

## Required before restricted-data work

1. PI's approved REK/HUNT application scope, secure-compute requirements, linkage and export policy.
2. Actual HUNT study waves/subcohorts, precise Databank variable codes, coding of missing values and units.
3. Approved outcomes/definitions, event and measurement dates, censoring/competing risks.
4. Authorized baseline feature availability, subgroup definitions and patient-reported outcomes if any.
5. Clarification whether any Helseplattformen care data or wearables are in project scope.

## Security and publication

HUNT requires ethics approval, DAC project authorization and data agreement. Do not publish row-level data, trained confidential model artifacts or patient IDs in public GitHub or Vercel. The software demo uses synthetic data only and must label synthetic evaluation scores prominently.
