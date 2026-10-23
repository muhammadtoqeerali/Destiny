# FrailtyScope v0.39 — Model Readiness Dossier and GitHub CI Reproducibility

This release **does not** use real NHANES/HUNT participant rows, retrain models, load private artifacts, serve an individual prognostic score, or claim clinical approval. It creates a reproducible public-only documentary status receipt for the original NHANES case and four **proposed** endpoints, adds Doctor-side model readiness evidence, and fixes GitHub browser QA root discovery.

## Historical mortality case: documentary facts only

- `research/cases/nhanes_workflow_v29.json`: `real_data_execution_permitted=false`, `clinical_use_permitted=false`, `model_fitting_permitted=false`, `holdout_scoring_permitted=false`, `public_export_permitted=false`; `models_saved=false`; `independent_validation=false`; `prediction_index_status=provisional`; `holdout_history=previously_inspected`.
- Earlier research review documented **3/14** source-mapped predictors; this release does not re-audit that mapping. Eleven remain unresolved in that prior review.
- A historic approximately 5-year **all-cause mortality** result is not authorization for scoring a new patient, and does not imply incident diabetes/stroke/heart-failure models.
- Diabetes, stroke and heart failure are **separate proposed outcomes** with no approved, suitably defined or validated incident-disease classifiers registered in this public demonstration.

## Added machine-readable evidence

`ml/inference_readiness_v39.py` reads **only the public v0.29 JSON contract**. It refuses unexpected evidence changes rather than granting a score; compare its deterministic receipt to `web/app/data/inference-readiness-v39.json` using:

```bash
PYTHONPATH=. .venv/bin/python -m ml.inference_readiness_v39 --check
```

`GET /api/inference/readiness` exposes this *public non-patient* documentary receipt with `Cache-Control: no-store`. POST refuses input (`405`) without reading its body; `/api/inference` remains a `403` block. The Doctor UI displays the four unavailable outcomes and the prerequisites for advancing scientific review. No Patient Assessment field is transmitted.

## Required real-model program (future, separately approved)

1. Approvals, authorized population and intended use; applicable regulatory assessment.
2. Define prediction timestamp, outcome-specific incidence and observable prediction horizon, competing risks, censoring and follow-up.
3. Complete feature mapping and handling of missingness/structural skips, measurement timing and transportability.
4. Independently validated, representative and calibrated model bundle with a versioned exact preprocessor, proven provenance, secure model registry and signed promotion reviews.
5. Evaluation for drift, discrimination, decision utility, calibration uncertainty and subgroups. Use an untouched independent cohort under an approved protocol; **previously inspected NHANES cycles do not become independent by rerunning tests**.
6. Authenticated, privacy-controlled patient-data infrastructure, clinician-in-the-loop use, audit, incident response and rollback.
7. Real feature-contribution explanations based on the actual fitted model, not coefficients in the fictional education studio.

**No single toggle, JSON change or registration in this release enables individual clinical inference.** Synthetic-only interactive scoring from v0.38 remains separate.

## CI root fix

The v0.38 GitHub Actions log confirmed Python/npm/build, Chrome 155 and npm audit passed. The browser QA runner then failed because its fallback root was a private workstation path. v0.39 resolves the runner root relative to the script, with `FRAILTYSCOPE_ROOT` available as an override, leaving tests real and mandatory. The GitHub-hosted workflow must be observed after publication before claiming a green CI run.
