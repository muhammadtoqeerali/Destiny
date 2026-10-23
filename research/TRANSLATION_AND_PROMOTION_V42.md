# FrailtyScope v0.42 — Source-to-form translation and clinical promotion gates

**Scope:** Public documentary sources, no real participant records, no NHANES/HUNT private reviews, no fitted models, no individual predictions. Real-data analysis remains `BLOCKED_FOR_NEW_ANALYSIS`.

## Findings documented, not clinical approvals

The 14 predictors in the `nhanes_mortality_v10` manifest have *candidate source dictionary references* in the public v0.23 codebook/timing protocol. However, only **three** (walking, stairs and stooping difficulty) have source-verified **partial 2011–12 harmonization** mappings in the public v0.24 blueprint. The other 11 are unmapped in that blueprint. All 14 prediction-time approvals remain pending, and the prediction index is provisional. A candidate survey variable name is **not** an approved runtime transform.

The Doctor Portal currently accepts an **assessment entry form**, not raw NHANES survey codes. Important known translation gaps that require research review:

- Age: NHANES public-use `RIDAGEYR` is top-coded at 80, whereas the form allows age 65–110. This is not fixable by silently equating 80 to actual ages of 81–110.
- BMI: the source function documented in v0.23 retains values between 12–70 while the form accepts 10–70. This difference must be resolved in the preprocessing contract, not handled as if equivalent.
- Mobility: PFQ difficulty codes 1–4, code 5 nonperformance, refusals, unknown responses and PFQ054 routing/structural skip semantics differ from human-readable form options. The PFQ054 skip for walking/stairs does not apply to stooping.
- PHQ-9: the NHANES derived total is based on all nine DPQ questionnaire responses, each validated at the source; a manually entered total does not establish equivalent provenance.
- Sex and binary health-history fields: source-code semantics, statuses, timing, population and encoding remain subject to explicit review.

## Four separately governed proposed outcomes

The historic case is **approximately five-year all-cause mortality**; it is not a diagnosis predictor. Incident diabetes, stroke and heart failure require separately defined new-onset outcome targets, baseline exclusion, prediction horizons, follow-up/censoring, external validation and permitted training. The source-only registry contains **zero approved clinical models**. The `POST /api/inference` block continues to deny patient inputs.

## Technical components

- `ml/model_translation_v42.py`: public-contract-only deterministic review, 14-row candidate ledger, source-to-form gap notes and four **DENIED** promotion decisions. `--check` read-only; `--write-public` only generates a non-person public receipt.
- `web/app/data/model-translation-v42.json`: generated source-only report, no participants, fitted models or individual predictions.
- `GET /api/inference/translation`: returns public report with `no-store`; rejects non-GET requests; denies service if any clinical flag unexpectedly changes.
- Doctor `Model evidence` tab: accessible source-to-form crosswalk with 14 fields, unresolved/partial filters, exact source-variable candidates, and unmatched input semantics. No patient input is transmitted to it.
- Installer/publisher: exact v0.41 baseline, verified checksums, source allowlists, backup/rollback, full pytest, TypeScript production build, Chromium desktop/mobile QA, separate uppercase `YES` before Git publication.

## Required external actions before actual inference

The project owners must secure written ethics/data-controller approvals and intended clinical-use definition; approve index timing; independently map every predictor across waves and point-of-care input meanings; obtain an authorized, version-locked model **with exact fitted preprocessing**, provenance and artifact hash from a restricted environment; evaluate on representative untouched independent cohorts (including calibration, uncertainty, subgroup and drift checks); fulfill consent, privacy, clinician oversight, and any medical-device requirements; and check model-specific explanations against the actual fitted preprocessor/model.

**This release neither grants those approvals nor performs new real-person inference.** The already-published synthetic fixture-only serving examples remain separate.

## v0.42.1 backward-compatible release correction

The v0.41 regression checks exact source insertions, including its original Python CI test command.
A v0.42 draft extended that line and thereby broke the historical source-contract test.
The corrected release preserves that command and adds new CI steps before the v0.41 verification block (preserving its adjacency to the public-payload check), including a separate mandatory pytest step for
`tests/test_translation_v42.py`. This runs the new coverage without weakening older tests.
A review-only cleanup tool is bundled for explicitly verified failed-installation files;
it never removes unrelated interview-brief files or changes the blocked clinical inference gate.
