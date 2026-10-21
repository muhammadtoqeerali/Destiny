# FrailtyScope v0.3 — Two-workspace interview demonstration

## Research & Developer workspace

Access from the first two entries on the left navigation (default view: Developer studio).

1. **Data exploration:** 6,000 synthetic records summary, test cohort age distribution, artificial model-score distribution, and feature completeness.
2. **Preprocessing:** exact 60/20/20 stratified split, train-fitted numeric and categorical branches, imputation/encoding/scaling diagram and leakage-controls checklist.
3. **Model architecture:** interactive selection of regularized logistic regression, random forest and histogram gradient boosting, with high-level flow and actual configuration settings. Clinical versus expanded feature groups shown separately.
4. **Performance:** held-out metrics and bootstrap interval, six validation candidates, calibration view, subgroup table and plain-language metric definitions.

## Clinical review workspace

- A **fictional patient directory** with ID/age/sex search, risk-band filters, and case selection.
- Patient-at-a-glance with a clearly labeled **illustrative** fall-event model score and measurement cards.
- Non-additive one-variable model response contrasts (NOT SHAP, causal attribution or diagnosis).
- Clinician-friendly interpretation notes and clinical-use limitations.

## How the numbers were produced

The browser consumes `web/public/data/demo.json` created by `python -m ml.train` from simulated records. It does **not** send patient data to a service or perform new inference in-browser. All plots and patient cases are generated from the same public synthetic dataset. No HUNT patient-level data are used.

## Security / deployment notes

`web/package.json` now includes an npm override requesting PostCSS >=8.5.23 to address publicly reported vulnerabilities in the transitive PostCSS dependency. **This does not itself prove remediation.** Before pushing, regenerate and commit the dependency lockfile using `npm install`, run `npm audit --omit=dev`, `npm run lint`, and `npm run build`. Do not use `npm audit fix --force`. An old Next.js *vendored* PostCSS may not respond to overrides, so review the final audit report and migrate to a patched framework version with compatibility testing if necessary.

The repository and public Vercel application should contain only approved source code and synthetic records; never upload HUNT records or model files trained on HUNT.

## Not implemented or verified yet

- HUNT variable mapping, approved secure data access, outcome-linkage or temporal survival modeling
- Real-world diagnosis, disease forecasts, clinician recommendations, external validation or deployment for patient care
- Full production build on the target workstation (syntax/CSS parsing and seven Python tests passed in the build sandbox; npm packages are unavailable in the sandbox)
