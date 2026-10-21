# FrailtyScope fitted-model artifact contract

## Training stays on the workstation

`ml/case_engine_v10.py` reads the case manifest, fits candidate models, and saves the selected pipeline under ignored `artifacts/cases/<case_id>/best_model.joblib`. Run it **locally**, never as part of the public Next.js deployment or on a chat assistant's machine. Persist `metrics.json` from the same run, including input file fingerprint, split configuration, selected model, threshold, and evaluation metrics. Keep the original data and fitted models out of Git and Vercel.

## Stable class identity is essential

A model fitted by `python -m ml.case_engine_v10` must use classes imported from **`ml.case_engine_v10`**, not classes defined by the transient `__main__` module. The command entrypoint calls its canonical imported module `main()` to preserve this identity. Never patch `sys.modules['__main__']` permanently to make a pickle load.

## Recover an existing trusted artifact

`ml.case_model_io_v11` invokes an independent Python process for a fresh model reload. Only the known old `__main__.CatBoostClassifierAdapter`/`CatBoostRegressorAdapter` issue qualifies for migration. For that case it:

1. Loads the known locally created model with a temporary, limited alias.
2. Recomputes the exact saved evaluation metrics and confusion matrix on the workstation (no training).
3. Writes a new temporary joblib in the ignored local artifacts directory.
4. Reloads that file in another Python process without aliases and re-verifies the results.
5. Backs up the old file and atomically replaces it only when all checks pass.

A successful *in-process* `joblib.load()` alone is **not** evidence of portable serialization. Modules responsible for later diagnostics (`case_forensics_v11` and `case_enhancement_v11`) share the same strict loader. For new case assignments use separate case IDs and manifest files to avoid overwriting reproducibility evidence.

**Security:** joblib/pickle deserialization can execute code. Use this only with trusted artifacts produced on the same workstation. Never load downloaded, emailed, or user-submitted pickle/joblib files. The fresh-process check improves compatibility testing, **not** pickle security isolation.

## Research release rule

Only audited source code, tests, documentation and allowlisted aggregate statistics may go to GitHub/Vercel. Do not publish `data/`, `artifacts/`, fitted models, participant records, per-person predictions, or the local forensic report. The public Admin Portal must display actual reviewed aggregate values, not generated demo metrics.
