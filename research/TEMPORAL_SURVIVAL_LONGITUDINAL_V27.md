# FrailtyScope v0.27 — Survival and Longitudinal Foundations

**Boundary.** Research engineering code for **invented synthetic fixtures only**. The source-only `--plan` and `--audit` entrypoints never load participant CSV/XPT files, targets, existing model objects, or prediction outputs. Passing `synthetic_fixture=True` is **not** a security sandbox: never pass real HUNT/NHANES records into these prototype APIs. The existing NHANES case retains **classification**, a **provisional index**, three PFQ mappings with 11 missing, and **previously inspected** holdout history. This release neither changes the outcome nor scores the later cycle.

## A. Right-censored survival foundation

**Input:** Synthetic canonical v0.25 predictor/status frame; positive time since prediction index; binary `event` (1=observed event, 0=right-censored); row and participant IDs separately; an explicit positive horizon. A person appears in **one** partition only. Features are learned from the *training* subset only.

**Candidates:** Kaplan–Meier population reference and ridge-penalized Cox proportional hazards, with Breslow tie handling. Cox partial likelihood uses a bounded optimizer and a development-fitted baseline cumulative hazard. No Cox claim is made without checking PH assumptions, covariate functional form, dependent censoring, baseline time origin, and competing event definitions in a future authorized study.

**Validation metrics:** Strictly comparable-pair Harrell C (equal follow-up times excluded; ties in risk given half credit) and horizon-specific **IPCW Brier**. Censoring survival for IPCW is estimated **only from each training fold** using reverse Kaplan–Meier. Early-censored validation individuals are not mistakenly labeled as event-free. Reject folds with insufficient events, censoring, horizon follow-up, or censoring support. Harrell C can be biased under censoring, and IPCW assumes a defensible censoring model and independent censoring; these are demonstration calculations, not proven population-inference methods. No competing risks, left truncation, time-varying exposures, independent test evaluation, or clinical model certification.

## B. Longitudinal foundation

**Input:** One synthetic transition per `(person, current visit)` with the **current-visit** canonical feature/status values and an observed `previous_outcome` at that same index visit. The `next_outcome` and next observed visit timestamp are **targets/metadata**, never features. Checks demand `index_time < target_time`, consistent consecutive visit chains within each person and agreement between a past transition's outcome and the next visit's lagged outcome.

**Candidates:** last-observed value reference and Ridge regression over current-visit features plus lagged outcome. Every model/scale/imputation is re-fitted inside **participant-disjoint folds**; report exploratory MAE and RMSE. This predicts the value at the **next observed visit**: its time interval varies; visit scheduling, selective participation, dropout, intervening death, informative observation process and fixed-horizon trajectory modeling are **not** handled. Use mixed effects, GEE, joint models, landmarking, inverse-visit weighting, and specialized outcome processes in later versions after task-specific design.

## Engineering safeguards

- Full documentary chain v0.22 → v0.23 → v0.24 → v0.25 → v0.26 → v0.27, with case identity and previously-inspected holdout history unchanged.
- Exact predictor/status frame schema; IDs, event indicators, durations, visit times, survey weights and outcomes stay outside predictors.
- All synthetic development folds and split boundaries validated before model training. No hyperparameter tuning, no trained-model export, no private group/individual predictions.
- `--plan` reads approved source protocol JSON only; `--audit` additionally reads the immutable **v0.26 metadata JSON**, verifies its identity and no-real-work claims and creates a new immutable private v0.27 metadata review under ignored `artifacts/`.
- No paper, slides, clinical deployment, survey-weighted inference, calibrated external performance, independent validation, or ethical/access clearance claimed.

## Proposed next milestone

Test task-specific censoring calibration and uncertainty, PH diagnostics, participant-level resampling, interval-specific landmark prediction, dropout and death sensitivity, study-defined horizons, and finite-sample limits. Expand beyond synthetic cases **only** after a new study-specific governance, index, dictionary, and privacy review; the currently inspected NHANES later cycle cannot be made pristine.
