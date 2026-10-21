# FrailtyScope v0.6 — Real-data-only activation

**Primary source:** CDC NHANES public-use survey data for 2011–2014 + the 2019 linked-mortality public-use release.

**Workstation source of truth:** `artifacts/realdata_nhanes/report.json`, generated on your own workstation. This report is aggregate only. Raw participant rows and local model assets are **never** exported.

### What is removed

- Synthetic patient directory, fictional case histories, synthetic score explanations, and five invented-outcome views.
- Three published synthetic JSON assets: `demo.json`, `multioutcome-demo.json`, `shap-summary-demo.json`.
- Active artificial generators and training modules, and legacy synthetic-only test files.
- CI instructions for generating artificial data.

Git history and historical Vercel deployments are not erased by this change. The production branch and current deployment no longer include the synthetic resources after successful activation. No force push or Git history rewrite is performed.

### What remains

- Real NHANES ingestion and real-data training code.
- Local-only HUNT adapter and longitudinal endpoint contract.
- Real-data source code tests (small artificial *test fixtures* still used for software unit testing, never for deployed research models).
- Admin research portal showing NHANES data collection, preprocessing, model comparison, and evaluation.
- Doctor portal showing only population-level research interpretation. No personal clinical decisions or forecasts.

### Scientific limitations

The current NHANES outcome is **approximately five-year all-cause mortality**. The CDC has perturbed public-use timing for selected records; this should not be presented as an exact five-year risk model. The headline numbers are unweighted, from a restricted eligible sample; complex survey design corrections and validation are still required. The 2013–2014 cycle is a time-separated test cohort, not an external hospital validation.

### To publish

Run `bash scripts/activate_real_only.sh` from the unpacked release directory, then review `git diff --cached --stat` and the generated public JSON. The script verifies an existing real-data report, runs tests and an isolated production build, and only then commits/pushes the explicitly allowlisted changes. It refuses to modify the repository if unexpected source modifications exist. The Vercel site deploys automatically from GitHub `main`.
