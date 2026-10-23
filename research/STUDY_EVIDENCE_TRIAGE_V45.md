# FrailtyScope v0.45 — Private evidence-intake triage (no approval authority)

The 25-item v0.44 handoff is now actionable **outside the public GitHub repository**.
This stage tests only the completeness and consistency of a **CSV response sheet**;
it **does not** authenticate a reviewer, inspect supporting documents, establish source mappings, authorize data processing, validate a trained model, or approve clinical inference.

## Study-team procedure

1. Copy `research/templates/STUDY_TEAM_EVIDENCE_REQUEST_V44.csv` into a restricted study-team location **outside the git checkout**. Never edit or commit the public template.
2. Only edit `approval_status` and `evidence_reference_to_be_supplied_offline`. Preserve all other six columns and all 25 row IDs/order. Permitted statuses: `NOT_RECEIVED`, `IN_REVIEW`, `EVIDENCE_RECEIVED`, `CHANGES_REQUESTED`, `REJECTED`, `APPROVED`. A claimed `APPROVED` is **not independently verified**.
3. If evidence is claimed received or approved, provide an opaque, non-sensitive ticket such as `OFFLINE-REVIEW_000001`. Never paste document contents, paths, URLs, names, dates of birth, participant identifiers, signatures, keys or clinical notes. The ticket should resolve only within the approved private process.
4. Run the triage locally. Output contains only counts and the already-public request IDs; it does not include tickets or the original CSV values. Retain the response sheet and supporting evidence exclusively in the restricted institutional system.

```bash
cd /mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
PYTHONPATH=. .venv/bin/python -m ml.study_evidence_triage_v45 --check-template

# After the team completes an offline COPY outside the repository:
PYTHONPATH=. .venv/bin/python -m ml.study_evidence_triage_v45 \
  --review-response /path/outside/repository/study_team_responses.csv
```

The CLI refuses unknown columns, renamed/duplicate/reordered/missing requests, modified evidence questions, non-opaque references, incomplete received-status references, paths inside the repo, symlinked files and unexpectedly large/non-UTF8 inputs. It never dereferences offline tickets. Nothing is written to disk by the triage command.

## Next gates (must be independently resolved)

- **Research authority:** written data-controller/ethics determination, intended-use and legal review.
- **Index and mapping:** freeze prediction timestamp; resolve 11 unverified source mappings and 14 index-time/form transformation approvals, including source-wave effects and missing codes.
- **Endpoints:** the old NHANES case is approximately five-year all-cause mortality; incident diabetes, stroke and heart failure each require longitudinal new-event ascertainment, prediction horizon, censoring, competing-risks strategy and separate model programs.
- **Artifact and validation:** approved fitted model and exact preprocessor; independent, untouched evaluation and calibration, relevant subgroup/uncertainty and clinical-utility review; reviewer-signed provenance.
- **Deployment:** secure authenticated patient handling, clinical oversight, monitoring, incident response and rollback, and applicable medical-device/privacy assessment.

**This release is not an approval or certification engine.** No filled responses, reviewer evidence, participant-level records, historic model binaries, secrets or real probabilities belong in GitHub, the Doctor Portal or this ZIP. `/api/inference` stays `403`.
