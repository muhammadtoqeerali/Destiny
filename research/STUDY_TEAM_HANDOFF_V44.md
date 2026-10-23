# FrailtyScope v0.44 — Research-team decision and evidence handoff

**Status: not authorized to run new analysis or individual prognosis.** This release is not a claim that new evidence was obtained. It does not load NHANES/HUNT rows, evaluate model binaries, alter existing public aggregates, collect health records, assign reviewer identities or make an approval decision.

## Why this handoff is the next blocker

The v0.23 candidate dictionary lists 14 possible feature source references, but **candidate references are not approved runtime transforms**. The v0.24 public harmonization contract partially verifies three PFQ mobility mappings for **2011–2012 only**. The remaining **11 mappings are unresolved**. The index and measurement availability have not been approved for any of the 14 predictors. For the historical approximately five-year all-cause mortality case, the 2013–2014 evaluation cycle was previously inspected, not untouched independent validation. No approved clinical model has been registered.

## Deliverables requiring actual study-team action

1. **Ethics/data-controller decision:** document intended use, jurisdiction, permissible cohort/data handling, data access basis, privacy and medical-device assessment. Keep approvals in a suitably controlled private institutional system; do not upload signatures or participant material to GitHub.
2. **Baseline and endpoint timing:** approve the exact prediction-time event, sample eligibility, predictor availability, follow-up and baseline ascertainment, using a prospective protocol. Review look-ahead bias and structural skips.
3. **14-field crosswalk:** have the questionnaire/data-curation team adjudicate candidate codebook references, wave coverage, raw category semantics, missingness, unit conversions, differences in Doctor form and source top-coding. The CSV request template lists all 14; no source mapping is automatically approved.
4. **Disease-specific targets:** approximately five-year all-cause mortality is the *only* existing historical NHANES classification case. Incident diabetes, incident stroke and incident heart failure require distinct event definitions, baseline prevalent-disease exclusion, dated outcomes and longitudinal ascertainment. Prevalence questionnaire items do **not** establish future events.
5. **Independent model evaluation:** after written authorization, create a new analysis protocol in a restricted environment; fit/register exact preprocessing with provenance and conduct genuinely independent holdout validation with discrimination, calibration, subgroup uncertainty and clinical net benefit as appropriate. A previously inspected cycle cannot become untouched by rerunning the same analysis.
6. **Controlled clinical deployment:** require separate model promotion, secure authorization, consent/legal basis, auditability, clinician oversight, rollback and monitoring. The public demo is not a patient data service.

## What's provided

- `web/app/data/study-handoff-v44.json`: deterministic read-only summary of missing evidence, source hashes, 14 predictor questions, four outcome design requests and seven organizational gates.
- `research/templates/STUDY_TEAM_EVIDENCE_REQUEST_V44.csv`: **blank** 25-item review request matrix; approval cells deliberately say `NOT_RECEIVED`. Do not commit a completed confidential copy.
- `GET /api/inference/handoff`: public no-store source evidence; rejects query parameters and write methods.
- Doctor Portal *Model evidence*: browse the open questions without transmitting any patient inputs.

Read-only check:

```bash
PYTHONPATH=. .venv/bin/python -m ml.study_handoff_v44 --check
```

The CLI has a release-author-only `--write-public-bundle` that regenerates the *blank public packet* from safe inputs; this is **not** a research audit, approval workflow or private evidence loader.

## Stop condition

New real-data fitting, holdout scoring, clinical serving and individual probability calculations remain `BLOCKED_FOR_NEW_ANALYSIS` / unavailable. No metadata file or green software test can change this. The next real scientific decision belongs to the data controller, clinical investigators and independent validation group.
