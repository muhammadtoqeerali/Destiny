# FrailtyScope v0.30 — source integrity, synthetic reproducibility and chart resilience

**Engineering status:** synthetic-only development verification. This release is NOT a new NHANES or HUNT analysis and it neither upgrades research permissions nor validates a clinical instrument.

## What is implemented

- Validate the existing v0.22–v0.29 source-contract chain using v0.29's established validation, then assemble a deterministic byte- and canonical-JSON SHA-256 ledger for all eight relevant source configs. Source files alone are read by `--plan`.
- In `--smoke`, internally generate 72 **invented** questionnaire rows for 36 fictional people, run the v0.29 synthetic-only workflow twice and require identical digest of aggregate diagnostics. The output is an integrity receipt, never row predictions or saved models. Seeds, source chain and aggregate hash are tracked.
- Preserve v0.29's participant-disjoint OOF mapping, shared train/validation folds, training-only preprocessing and prefit leakage guards; expand v0.30 negative tests for tampered source list, ambiguous JSON, nonfinite output and immutable audit overwrites.
- `--audit` validates the existing immutable v0.29 documentary metadata review, records the source integrity ledger under ignored `artifacts/cases/.../integrity_v30/.../integrity_review.json` with exclusive creation, and opens no participant data or fitted models. `--verify` checks ledger vs *current* source files and the preexisting private review, without writing.
- Replace the earlier Decision quality Recharts threshold plot with a data-checked responsive native SVG that remains visible across tab/threshold changes without depending on ResizeObserver layout. The existing **historically published aggregate** JSON is unchanged; the chosen threshold is highlighted. This is a public visualization-only correction, not a reanalysis.

## Limitations and compliance

- `synthetic_fixture=True` is **not** an access-control mechanism. Only `--smoke`'s internally generated toy fixture may be used here. No new study can be enabled by editing this package.
- The previously inspected NHANES 2013–2014 cohort is **not** pristine independent validation. The 2011–2012 development records are repeatedly used; no new scores, selection, RF replacement or population estimates are made.
- The three source-reviewed PFQ mappings remain the only supported NHANES subset; the 11 unmapped predictors and provisional index still block research analysis.
- Source SHA-256 hashes detect changes relative to the *created private review*, not cryptographic attestation by a third party. The ledger does not prove source inputs are scientifically appropriate.
- The synthetic comparison checks determinism within a machine/software environment; cross-platform bitwise equivalence depends on package versions and numeric implementations. No refitting-aware uncertainty, study-level transport inference, nested-selection uncertainty, complex survey estimation, or clinical clearance is supplied.
- No participant-level exports, model artifacts or updated `web/public/data/` files are created by this release.

## CLI

```bash
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --plan
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --smoke
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --audit
PYTHONPATH=. .venv/bin/python -m ml.case_integrity_v30 --verify
```

`--audit` MUST run only once for unchanged source/configuration; audit files are immutable. After that, `--verify` is the repeatable read-only check.
