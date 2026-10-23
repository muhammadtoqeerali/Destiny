# FrailtyScope v0.43 — Synthetic Artifact Acceptance & Clinical Promotion Denial

**Scope:** Source-only acceptance rehearsal. Explicitly forbidden: reading any private NHANES/HUNT files, pickle/joblib deserialization, fitting or reloading historical clinical models, patient submissions, new outcome modelling, and clinical promotion.

## What this adds

- A fixed public *fictional model candidate manifest* under `research/cases/`, referencing the v0.38 synthetic JSON coefficient registry and v0.41 invented holdback receipt by exact SHA256.
- A deterministic, read-only `ml.artifact_acceptance_v43 --check` verifier: validates the bundle identity, ordered six-feature schema, exact synthetic preprocessing version, generated-data provenance, fit/holdback size, and the continued v0.29/v0.39/v0.41/v0.42 denial contracts.
- A public `web/app/data/artifact-acceptance-v43.json` receipt and GET-only `/api/inference/artifacts` documentary route. All write methods return 405; GET is permanently denied if its bundled status ever claims clinical promotion.
- A Doctor Portal acceptance checklist (synthetic digest, six ordered artificial signals, inventory of three fictional outcomes, ten checks, four blocked clinical outcomes).
- Tamper rejection tests for modified registry hash, altered feature order, fake signatures, clinical toggle, external file path and fake clinical model inventory; full browser checks and CI checks.

## Evidence: not a permission grant

This is a **metadata consistency check**, not a signature verification service, not an artifact store, and not a secure patient serving service. Comparing a public SHA256 with a public JSON source does not authenticate a clinical model or establish approval. There are still **zero** approved real clinical models and **zero** prediction-time feature approvals; historical 2013–14 evaluation was previously inspected and cannot serve as fresh independent validation.

The historical NHANES task is *approximately five-year all-cause mortality*. Incident diabetes, stroke and heart failure require separately defined endpoint ascertainment, fitting, and independent validation. Do not infer those outcomes from a mortality classifier or from the fictional model outputs.

## Future restricted-environment deliverables

1. Written controller/ethics approvals, explicit intended use, device/privacy risk assessment and a locked prediction index for each outcome.
2. Complete 14-feature cross-wave mapping, time ordering, structural-skip and measurement equivalence review, exact trained preprocessing.
3. Approved source datasets and separate outcome-specific target definitions under a restricted study environment; no public release of people-level data.
4. A signed, identity-verified model promotion decision; immutable hashes of exact fitted model and preprocessor; safe loading policy that does not execute untrusted serialized code.
5. Untouched representative external validation, uncertainty/calibration/subgroup/decision analysis and a monitoring/rollback protocol.
6. Authenticated clinician-facing infrastructure with consent, least-privilege access, auditing and incident response. Public `/api/inference` must remain a 403 until a separately reviewed deployment exists.

Run `PYTHONPATH=. .venv/bin/python -m ml.artifact_acceptance_v43 --check` to check the public receipt; it never accesses private files or runs a model.
