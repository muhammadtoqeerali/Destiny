# FrailtyScope v0.46 — Study activation and reviewer action plan

**This release only coordinates evidence requests; it does not grant authorization.**

v0.44 supplied 25 blank evidence requests (14 predictors, four proposed outcomes, seven governance questions). v0.45 performs local CSV structure-only triage. v0.46 adds a deterministic, stage-ordered **action plan** that identifies the public owner role, request ID, dependency, claimed response status and next procedural action. It never shows offline ticket IDs, reviewer identities, evidence documents, paths or patient records. It never verifies signatures or approves modelling or clinical use.

## Suggested meeting order (not a substitute for independent scientific review)

1. **Authorization:** institutional data-controller / ethics determination for any future research work.
2. **Definitions:** freeze mortality prediction index and define genuinely incident diabetes, stroke and heart-failure outcomes; address competing events/censoring.
3. **Harmonization:** confirm all 14 variable provenance, survey cycles, missingness, source codes, physician-form equivalence and time availability. The three PFQ mappings are only partially source-verified; **zero** mappings have approved inference-time use.
4. **Model evidence:** only after appropriate authorization and feature approval, pursue provenance for a permitted fitted model and its exact preprocessor. No public/historical model is promoted here.
5. **Independent validation:** appropriately independent, untouched population; calibration, subgroup uncertainty and clinical utility. The historically inspected NHANES evaluation survey wave does not become independent validation again.
6. **Deployment governance:** authentication, privacy controls, clinical oversight, incident response, monitoring, regulatory assessment and rollback.

## Run locally (without any filled responses)

```bash
cd /mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
PYTHONPATH=. .venv/bin/python -m ml.study_activation_v46 --check-public-plan
PYTHONPATH=. .venv/bin/python -m ml.study_activation_v46 --template-plan --format markdown
```

## After receiving authorized responses outside the repository

```bash
PYTHONPATH=. .venv/bin/python -m ml.study_activation_v46 \
  --review-response /secure/outside/repo/responses.csv --format markdown
```

This tool validates the input with v0.45 triage first. It prints only the redacted action statuses and public request IDs; **redirect output only to a secured location** if retention is required. Any `APPROVED` CSV cell becomes `VERIFY_CLAIMED_SIGNOFF_INDEPENDENTLY`—never clinical approval. No private responses are bundled, exported or committed.

## What software cannot supply

Formal authority, baseline time approval, validated feature mapping, disease-specific target ascertainment, approved fitted real models, untouched external validation and secured clinical hosting require real institutional decisions and evidence. No real NHANES/HUNT data, private source reviews, pickled models or participant records are accessed by this release. `/api/inference` continues to block all patient inference.
