# NHATS — registered longitudinal data (private-workstation procedure)

The National Health and Aging Trends Study offers annual observations for older adults. Official access: https://www.nhats.org/data-access and https://www.nhats.org/data-access/nhats . Round 1 is 2011; Round 14 is 2024 as listed on the official website in October 2026.

**Register personally.** Public-use annual files require each user to register. The conditions, updated April 6, 2026, prohibit sharing downloaded public-use files with other people, even supervised staff. The January 22, 2026 conditions explicitly prohibit uploading NHATS/NSOC records to publicly hosted AI/LLM systems. https://www.nhats.org/conditions-of-use . Do not put NHATS participant rows, IDs, files, or authenticated downloads in this chat, GitHub, Vercel or third-party services. Do not share account credentials. Review the terms again when registering.

## First wave mapping (no guessed codes)

1. Log in through the official NHATS data-access site and download two or more approved public-use annual files **directly to your workstation**. Use official Stata `.dta` or SAS `.sas7bdat` / XPT formats. Extract ZIP locally. Read documentation and verify variable names and allowable response codes for EACH round.
2. Save the files under this repository's ignored `data/nhats/` directory. Use the ignored path `data/nhats/nhats_mapping_v09.json` for your private configuration; **do not commit any private mapping that contains sensitive metadata**.
3. Copy the *template* `research/NHATS_MAPPING_V09.json` into the ignored directory. For each wave, supply actual `file`, `id_column`, and `measures` fields from the codebooks. Positive codes mean a **defined difficulty/deficit**; negative codes mean its absence; missing codes are explicit. For unavailable domains use `{"disabled":true}` and do not fabricate measurements. Map the same clinical construct consistently across waves, not merely similarly named variables.
4. After verifying codes, set `verified_against_nhats_codebooks` to `true`, then run:

```bash
cd /mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
PYTHONPATH=. .venv/bin/python -m ml.nhats_longitudinal_v09 \
  --project-dir . \
  --config data/nhats/nhats_mapping_v09.json \
  --output artifacts/nhats/wave_audit_v09.json
```

This validates repeat respondent identifiers, annual joins, missing-code logic, and cross-wave status transitions. Its local-only output contains aggregate transition counts, not identifiers or individual predictions. **This is a schema and descriptive longitudinal audit, NOT an incidence-rate estimator, competing-risk model, clinical prediction tool, or frailty diagnosis.** Attrition, nonresponse, survey weights and endpoint definitions need further work before any model training. Never copy the resulting NHATS report to the public site without an explicit disclosure and licensing review.

## NHANES benchmark compared to NHATS

- NHANES v0.9 is an *exploratory Cox proportional-hazards analysis* of NHANES 2011–2014 baseline measurements and 2019 public-use linked mortality, including early-censored observations. It remains local-only, because some public-use follow-up times are synthetically substituted to protect confidentiality. It does not provide survey-design-valid confidence intervals and has not passed PH assumption tests.
- NHATS adds repeated annual respondent measurements once registered files have been obtained and independently harmonized. It is not available in the project yet. No NHATS-trained model, patient-level prediction or public NHATS dashboard is claimed.

## Publication boundary

`bash scripts/publish_research_v09.sh` pushes **only code, tests, documentation, and GitHub CI changes**, never NHANES raw rows, local survival reports, registered NHATS records, or new unvalidated frontend claims. This keeps the existing Doctor and Admin portals unchanged until scientific validation and necessary disclosure screening are complete.
