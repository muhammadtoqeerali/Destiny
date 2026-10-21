# Upgrade from Phase 1 → Phase 2

Keep the repository named **Destiny**; the visible dashboard is now **FrailtyScope**.

## On your Linux workstation

1. Stop the old Next.js `npm run dev` process with **Ctrl+C** in its terminal. Leave the Windows PowerShell SSH tunnel active.
2. Copy files from this release into the existing NTNU workspace. Use plain `cp -R`, **not** `cp -a` (the older command produced permission-preservation warnings on your mounted drive).
3. Run `bash scripts/phase2_upgrade.sh 2>&1 | tee phase2-run.log` from the workspace root.
4. Verify six configurations, seven passing tests, and a successful Next.js build.
5. Run `cd web && npm run dev -- -p 3001` and refresh `http://127.0.0.1:13001` in the Windows browser (existing SSH port tunnel).

## Expected outputs

- `web/public/data/demo.json`: synthetic-only public dashboard dataset
- `artifacts/synthetic_model.joblib`: local, ignored generated model
- `artifacts/experiment_report.json`: local, ignored run report
- `web/app/page.tsx`: visible FrailtyScope branding + data readiness/uncertainty tabs
- `.github/workflows/ci.yml`: GitHub actions checks

## GitHub safety

Run `git status` and `git diff --stat` before pushing. `.gitignore` excludes synthetic raw data, model artifacts, credentials, virtual environments, protected HUNT datasets and frontend build caches. Review the staged diff anyway. Do not ever add actual HUNT participant-level records or a real-data model to this repository.

## Scope

All performance measurements concern invented outcomes on artificial records. The run cannot show empirical fall-risk accuracy or actual HUNT effect sizes. Model explanations are one-feature sensitivity contrasts, **not SHAP**. The chart of thresholds is an educational calculation on synthetic data and not a treatment recommendation.
