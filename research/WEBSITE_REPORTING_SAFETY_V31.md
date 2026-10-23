# FrailtyScope v0.31 — Historical website reporting and authentication correction

**Scope:** website/source/test corrections only, not new NHANES/HUNT research.

## Verified inputs and scientific boundary

- The v0.30 source-only publication was confirmed at Git SHA `a50bc58b4a36dd7e441e2b29ffba6ed992ac34b4`. GitHub CI succeeded, but source publication alone does not prove Vercel production deployment identity.
- User screenshots of the current admin website show the v0.30 SVG threshold chart with values for 0.22: sensitivity 74.4%, false-positive rate 30.0%, precision 37.7%, 486 flags. These reproduce existing public aggregate metrics to rounding. Do not replace that fixed SVG.
- The 2,422 historical participants comprise 1,165 earlier-cycle development and 1,257 later-cycle participants; the later cycle contains 246 observed events. These are historical *unweighted benchmark* counts, not an approved clinical cohort or HUNT evidence.
- Historical published model results are from multiple distinct protocols: specialist CatBoost (AUC 0.8033/Brier 0.1232), specialist HistGB (0.8006/0.1228), general-purpose CatBoost (0.791758/0.129447). They must not be represented as a single model or new independent external validation.

## Source-only remediation

1. Initialize Decision Quality threshold selection using the actual closest grid value. The original `locked_threshold` is stored in floating-point as `0.21999999999999997`, while the displayed option is 0.22.
2. Add a persistent historical/research-readiness notice to both portals and clarify misleading references to pristine independent evaluation, particularly in Deep Analysis and Decision Quality.
3. Fail closed if production admin credentials/session signing secret are absent or inadequately configured. **Set BOTH** Vercel environment variables `ADMIN_PORTAL_PASSWORD` (minimum 16 characters) and `ADMIN_SESSION_SECRET` (minimum 32 characters, independently generated, different from the password) in a secure Vercel environment. Never place their values into code, a terminal transcript, or chat. Redeploy and verify sign-in under an authorized session.
4. Keep nonperformance, structural skips, refusal and unknown mobility statuses separate from graded difficulty; reject out-of-range or noninteger age/PHQ-9 from the descriptive completion count. Still no individual prognosis is computed or stored.
5. Add public-aggregate internal arithmetic regressions and source-level privacy guard checks to CI; no participant-level datasets or model files are opened.

## Important limitations

- These corrections do **not** establish that the historical fitted models were scientifically valid, that all real measurements have been reconciled to original questionnaires, or that a deployment is currently live at a specific Git SHA.
- The NHANES case remains `BLOCKED_FOR_NEW_ANALYSIS`: the prediction index is provisional, eleven of fourteen predictors are unmapped, and 2013–2014 has already been inspected.
- No changes to `web/public/data`, `artifacts/`, or `data/` are allowed in this release. Existing fitted Random Forest models remain untouched.
- Browser E2E testing (including responsive layout, blank-chart regressions, protected auth, and every tab) must be performed on an authorized deployment after successful build. No automated sign-in or admin bypass is included.
- The admin password endpoint should additionally be protected by Vercel/platform rate limiting and monitoring; this patch alone does not implement distributed rate limiting.

## Publication

Only the USER may run the reviewed workstation publisher and type a fresh uppercase `YES`. Installation does not push. Source-only staging must be inspected and GitHub commit verified after the user push.
