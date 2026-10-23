# v0.40 — Synthetic server-side model execution, explainability and hard inference boundary

## What this release actually enables

An end-to-end Next.js **GET-only** demonstration of three previously fitted synthetic logistic models. The new route `/api/inference/synthetic?fixture=<allowlisted_id>` accepts only exactly one of three literal invented fixture IDs. It rejects arbitrary features and extra query parameters; other HTTP methods return 405 without reading bodies. Model parameters come from the existing versioned `fictional-model-registry-v38.json`, trained on deterministic generated rows. Outputs include exact model intercept, six normalized signal values, coefficients, additive log-odds contributions, logit, and sigmoid probability of an invented binary label. The Doctor's nontechnical explanation area gains a live server demonstration, independent of Patient Assessment.

This is a *technical inference service* and *mathematically exact explanation of synthetic model coefficients*. It is not an NHANES/HUNT fitted model, not a patient risk estimate, not a disease classifier and not a clinically validated result. The percentages have no clinical interpretation. The browser UI only requests enumerated fictional fixtures and does not transmit assessment inputs. The route always returns a no-store response, and independently checks the v0.38 synthetic registry and v0.39 blocked clinical contract on every request.

## Real clinical models remain blocked

`/api/inference` continues to reject all methods (403), while `/api/inference/readiness` reports the original blocked case. v0.29 remains `clinical_use_permitted=false`, `real_data_execution_permitted=false`, `models_saved=false`, `independent_validation=false`, `prediction_index_status=provisional`, `holdout_history=previously_inspected`. The historical v0.39 review only documented 3 of 14 predictors as mapped. The proposed incident diabetes, stroke and heart failure targets are not trained/validated; no set of synthetic coefficients can infer their risks.

## Genuine real-person inference prerequisites (separate program)

1. Obtain legal, ethical, data-controller, and clinical-use authority; specify intended-use population and regulatory classification.
2. Freeze prediction timestamp, horizon, inclusion/exclusion, and separately defined outcomes. For incident diseases address baseline prevalent disease, censoring and surveillance.
3. Resolve all source predictor mappings, missingness/status categories, timing/transportability, and exact fitted preprocessors.
4. Register an approved artifact with hashes/provenance and separate restricted secure-serving process, without committing binaries or patient data to the public repo.
5. Evaluate independent external data, calibration, subgroup uncertainty and drift; maintain clinical monitoring and human oversight.
6. Produce explanations bound to the exact approved model and input transform, not the fictional demo.

## Verification

Includes source-only tests, real browser GET/POST/invalid-fixture checks, cross-outcome coefficient math, unchanged clinical API block and no browser patient-data transmission. The install/publish scripts verify source hashes, checksums, immutable private review **read-only**, full Python tests, Next.js production build and all prior desktop/mobile browser suites. Approval of publication does not authorize patient scoring.

## v0.40.1 compatibility correction
The existing v0.37 browser suite was built when any `/api/inference` request was forbidden. The v0.40 fictional GET route made that over-broad assertion fail, despite the clinical inference endpoint remaining closed. The updated contract permits precisely the static `GET /api/inference/synthetic?fixture=fictional_reference` scenario during the older browser test, with no patient parameters, no POST/PUT, and no inference to the clinical route. The fix is covered by source tests and the full replay of all browser suites. CSS `flex-start` replaces `start` to avoid Autoprefixer portability warnings.
