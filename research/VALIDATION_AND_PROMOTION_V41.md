# FrailtyScope v0.41 — Science, Validation Rehearsal & Promotion Gate

## What is new

This is a **source-only scientific and release-readiness** improvement, not an approved patient-risk engine. It produces one deterministic public receipt based on the published NHANES v0.10/v0.23/v0.24/v0.29 documentary contracts, and scores **three fictional classifiers** (v0.38) on **240 invented held-aside examples**. A strict read-only public endpoint and an explanation panel show the evidence, with full source/browser/privacy regressions. No external dataset or private model is opened.

### Historical mortality case: 14 predictor documentary review

- v0.10 case manifest defines exactly 14 named predictor fields. The v0.24 **partial blueprint**, specifically for NHANES 2011–12, names `walking_difficulty`, `stairs_difficulty`, `stooping_difficulty` as *source-verified in that partial blueprint*. The remaining 11 are **unmapped in that blueprint**. This does **not** imply which features have been clinically validated.
- v0.23 dictionary enumerates proposed codebooks and measurement phases but all 14 have `availability_status=pending_index_review` and `source_timing_verified_by_study_team=false`; index approval is false.
- v0.29 prohibits new real-data processing/fitting/scoring, new holdout scoring, public export and clinical inference. Previously inspected 2013–14 evaluation is not untouched external validation. Selection was not performed; models were not saved in the v0.29 integrated workflow.
- Real all-cause mortality at approximately five years is **not equivalent** to future incident diabetes, stroke or heart failure. New disease outcomes require explicit baseline exclusions, operational incidence definitions, follow-up ascertainment, right-censoring/competing-death policies, defined horizon, representative development and untouched validation.

### Added reproducible synthetic-only rehearsal

`PYTHONPATH=. .venv/bin/python -m ml.research_validation_v41 --check` reads only the **public** v0.10/v0.23/v0.24/v0.29 case JSON files, synthetic fitted v0.38 registry, and the deterministic `generated()` invented fixture. The classifier is evaluated on the final 240 records, not the first 960 invented fitting records; that is an out-of-fit check **within the same fictional generator**, never independent clinical validation.

For three **invented labels** A/B/C, calculate ROC-AUC (tie-aware rank statistic), Brier loss, five-bin absolute calibration gap, calibration bin counts, and deterministic 150-replicate bootstrap intervals for **invented-row Brier loss only**. All outputs are non-patient, synthetic metrics and provide no estimate of real disease risk or uncertainty.

The full report is `web/app/data/validation-readiness-v41.json`, reproducible via the command above; it is shown in Doctor's educational Model Evidence section and exposed via `GET /api/inference/validation`. No arbitrary request input is accepted; every write verb returns 405. `GET /api/inference` remains 403. No participant feature, private data, model artifact, target or prediction crosses that boundary.

### Genuine clinical model promotion remains unavailable

For each **separately defined** disease/mortality outcome, the new receipt explicitly records the following fields as **not approved**: clinical index and endpoint definition; prevalent-case exclusion; horizon; censoring/competing outcomes; source mapping and exact preprocessing; authorized and cryptographically tracked fitted model; representative untouched independent evaluation with calibration/subgroup uncertainty; clinician oversight, privacy/access control, data-controller/ethics/legal and medical-device assessment; rollback/monitoring and model-specific explanations. Do not turn on patient-level inference by editing a flag, committing a model binary or reusing fictional coefficients.

**If and only if** the study team independently approves real-data access and analysis, execute a separately reviewed study protocol in a secure environment, documenting model provenance, temporal transportability, subgroup calibration, safeguards, consent/legal basis and scope. Do not treat publication as approval. No v0.41 release command exercises private data or the v0.30 `--audit` path; integrity uses only `--verify`.

### Release checklist

1. Verify exact published v0.40 SHA and clean tracked tree (two unrelated interview-brief files can remain untracked).
2. Confirm package SHA256 checks, source-only file allowlist, no private or historical aggregate edits.
3. Regenerate/check the deterministic public receipt, run 754+ synthetic/privacy/source tests and read-only immutable integrity check.
4. Parse CSS, Next.js TypeScript check and production build, run all v0.34–v0.41 desktop/mobile Chromium suites.
5. Inspect 15 reviewed paths; type uppercase `YES` to commit/push. Confirm GitHub Actions, Vercel and active endpoint after publication. Never claim CI success before the run concludes.
