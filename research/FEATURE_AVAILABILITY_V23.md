# FrailtyScope v0.23 — Data dictionary, predictor chronology and leakage gate

**Scope:** scientific/engineering groundwork for future health-data assignments: study index, predictor meaning, source lineage, response semantics, input availability and leakage prevention. This is **not** presentation/manuscript automation, a universal predictor optimizer, a clinical certification, or approval to train.

## Why this is a distinct work package

The v0.22 33-control evidence ledger has `predictor_availability` as a blocking **pending** item. A model can be mathematically well cross-validated yet invalid if variables become known only after the prediction instant, if an outcome proxy leaks into features, or if instrument codes and missing values are misinterpreted.

The first step is to **declare a prediction index operationally** (e.g. exactly after MEC exam, during admission, at enrollment, at each visit) and an intended deployment setting. Merely identifying a NHANES data component as an interview/MEC measure **does not** verify observation time or availability to an eventual prediction service. The v0.23 gate therefore fails closed until study-team evidence/signoff is supplied. This can take place in a future case; do not 'approve' NHANES purely to clear a checklist.

## Source-backed NHANES development metadata

`research/cases/nhanes_dictionary_timing_v23.json` supplies entries for all 14 existing predictors, with source names, component, transformation, missing semantics, modality and candidate collection phase. Every predictor remains `pending_index_review` until the *actual measurement chronology* is established for an explicitly defined index.

- **Household interview**: PFQ_G physical functioning was asked using household CAPI. This explains structural PFQ054 routing and the non-ordinal raw PFQ code 5. Sources: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/PFQ_G.htm and `ml/realdata_nhanes.py`. v0.20 verified development skip/code-5 provenance; v0.21 development-only source-category representations were exploratory.
- **MEC private interview**: DPQ_G PHQ-9 questions were collected in MEC private CAPI; raw 0–3 codes, nine complete items required for a total. Source: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/DPQ_G.htm .
- **MEC examination**: BMX_G BMI was measured at examination, not assumed available in a household-only decision context. Source: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/BMX_G.htm .
- Chronic conditions, blood pressure awareness, diabetes, and smoking are **self-reported questionnaire indicators**, not confirmed measurements of diagnoses. Source files MCQ_G, BPQ_G, DIQ_G and SMQ_G have their respective CDC codebooks.
- Outcome `outcome_5yr` and mortality linkage `MORTSTAT` / `PERMTH_EXM` are explicitly excluded from the predictor dictionary. Source-derived features must not use these fields, even if renamed.

**Important distinction:** official source documentation can establish that a survey phase was household or MEC. It does not independently establish the exact time the *processed* value existed, whether it would be available to a deployment operator, or whether an index date can be reconstructed for every participant. Those remain pending.

## Correct pre-model workflow for future HUNT-like cases

1. Define cohort membership, governance/approved use and prediction index (time zero). Resolve repeated visits, site/family identity, censoring and outcome horizon separately.
2. Create one dictionary entry per candidate predictor: name and definition, raw source file/field(s), units, recode, valid range, missing and special-code meaning, measurement source/phase, measurement time and access time, signoff/evidence.
3. Fail closed for unknown, after-index or inference-unavailable fields. Seek an alternative dataset/landmark/design rather than leaking post-index information or simply relabeling fields as safe.
4. Check upstream transformations for hidden outcome use, label-derived features, identifiers, target-dependent missingness, cross-visit joins or learned features fitted before data partitioning.
5. Only after appropriate data, study-design and governance gates pass, prepare fold-safe transformations and trial the model families suitable for the outcome. Do not certify classification if there is material early censoring; use survival methodology as appropriate.
6. For validation, use untouched groups, sites and/or time periods as defined before looking at outcomes. Do not call the previously inspected NHANES 2013–2014 group a new external holdout.

## CLI behavior and privacy

`PYTHONPATH=. .venv/bin/python -m ml.case_dictionary_timing_v23 --plan` validates source-controlled JSON only; no private files.

`PYTHONPATH=. .venv/bin/python -m ml.case_dictionary_timing_v23 --audit` additionally reads **only** the immutable v0.22 private aggregate metadata ledger and writes a v0.23 private source-only ledger under `artifacts/cases/.../field_timing_v23`. It never opens CSV/XPT, NHANES labels, HUNT tables, fitted models, predictions or evaluation cohort records. The report contains field names and documentary statuses, not patient records.

The protocol is deliberately `BLOCKED_FOR_PREDICTION_PROTOCOL_REVIEW`; this does not invalidate existing exploratory model comparisons. A user may publish the **software source** even with an incomplete protocol; never publish private ledgers or interpret source checks as clinical validation.

`research/cases/FEATURE_DICTIONARY_TEMPLATE_V23.json` is a non-executable starting template: replace every placeholder to match a new approved case before using it. Do not copy NHANES PFQ skip rules, time anchors or categorical meanings to HUNT by assumption.

## Test philosophy

Fixture-only unit tests cover: complete dictionary coverage, metadata validity, outcome/ID leakage, unsafe paths, index timing signoff, after-index safeguards, previously inspected holdout history, and source-only output. No real data fitting or data processing occurs in source tests.

**Remaining next steps**: operationally verified predictor timestamps and measurement availability for a *specific* research assignment; source-code integration of dictionary fields with actual fold-safe preprocessing; generalized repeated-visit, survival, site-group and censoring-aware routes; independent evaluation. The checkpoint explicitly does not solve these by itself.
