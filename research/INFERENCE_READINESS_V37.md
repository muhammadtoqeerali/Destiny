# FrailtyScope v0.37 — Inference readiness and synthetic scoring demonstration

## Purpose

The v0.36 Doctor Portal records *temporary* fictional/de-identified observations but cannot produce a patient prognosis. v0.37 adds a visible fail-closed inference readiness panel to the assessment and a self-contained, fictional scoring laboratory to the explanation page.

## Exact scientific boundary

- Original `nhanes_mortality_v10`: `BLOCKED_FOR_NEW_ANALYSIS` (v0.29); no clinical inference, model fitting or public export authorized.
- Provisional prediction index and only 3/14 source-reviewed predictor mappings.
- Previously inspected 2013–14 later-cycle evaluation, so no fresh independent external validation.
- The historical work focuses on **approximately five-year all-cause mortality**, not multiple new diagnoses, clinical trajectories, or treatment recommendations.
- Historical AUC/Brier scores do not establish that any historical saved model is approved, safely calibrated or suitable for live new-person scoring.
- v0.29 synthetic integration did not select or save a fitted model.

## What the user sees

1. The Patient Assessment checks basic field completion and clearly states clinical inference unavailable. No prediction is calculated.
2. The education page contains a **synthetic-only** logistic teaching function, with invented coefficients (`intercept=-0.55`, `age=0.035`, `BMI=0.08`, categorical movement signals `[-0.4,0.15,0.65]`). These are **not fitted NHANES coefficients** and do not imply associations or causation.
3. Visitors may adjust **fictional** inputs and inspect exact formula contributions and a class-1 output for an invented binary label. **That output is not patient mortality risk**. Patient Assessment state never flows to this model.
4. No inference API, new training data, model weights, saved records, browser persistence, network call or private data handling is added.

## Preconditions before a real clinical feature

Obtain documented legal/ethical authority and data-controller approval; freeze clinically meaningful prediction index and data contract; fully map/verify every needed source variable, statuses and timing; register an approved model with exact preprocessor and hash; independently validate/calibrate on suitable representative data; document intended population and subgroup drift/uncertainty; build authenticated secure patient-data flows, clinical human oversight, audit/monitoring, incident rollback and model-specific explanation methods. Assess applicable medical-device regulation before deployment. Until then: **no clinical inference**.

## QA and release

Full existing Python privacy fixtures and read-only v0.30 verify; web types/build; PostCSS parse; original v0.34–36 browser runs; new v0.37 local Chromium checks on desktop/mobile for no POST requests, no live patient prediction, deterministic synthetic arithmetic and exact coefficient explanations. Source-only 12-path allowlist, fresh uppercase YES before push. Leave unrelated untracked interview brief files untouched.
