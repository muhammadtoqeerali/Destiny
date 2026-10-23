# FrailtyScope v0.33 — Engine Studio redesign & discreet demonstration sign-in

## Purpose

Improve the **public-aggregate-only interview demonstration** without changing historic NHANES research results, fitted model files, source contracts, immutable audit records, or model permissions. Target source baseline: v0.32 commit `399b9c100089d4eca5e6de60d2f31a1cfbe740d5`.

## Changes

1. Remove both visible passcode banners from the Admin Login and Admin Dashboard. Keep the separate, unchanged public-demo route for **already public aggregate views only**. Its fixed passcode is still discoverable from source and its cookie still grants no genuine security. NEVER attach private records, server-side ML execution, privileged mutations or research actions to `canViewPublicDashboard()` or `hasPublicDemoSession()`. Genuine private routes must use `hasAdminSession()` with strong credentials.
2. Replace the earlier v0.32 guided-documentation presentation with four interactive views: Mission Control (workflow and cohort figures), Pipeline Explorer (seven selectable stages, train/validation schematic and fold-safe boundary), Model Evidence (responsive zero-baseline charts from three **separate** historical published aggregates), and Quality & Lineage (synthetic SHA-256 receipts, test/readiness indicators, transparent restrictions).
3. All changed charts and interactions are browser-side visualizations of **existing historical aggregates and documented synthetic engineering evidence**, not live Python model fitting, new clinical prediction, fresh validation, or optimization of the repeatedly inspected NHANES holdout.
4. Preserve the current historical dashboard tabs, v0.31 disclaimer, v0.30 verified immutable audit, v0.29 execution guard, and unchanged `web/public/data` JSON. No private artifacts are copied.
5. Responsive custom styling is scoped to the new component, with semantic buttons, disabled-state controls, focus outlines and reduced-motion handling.

## Boundaries

- The only confirmed executable integrated modeling pathway remains synthetic-only. No claim of state-of-the-art validated NHANES performance, HUNT clearance or Norwegian clinical deployment.
- The original NHANES case remains `BLOCKED_FOR_NEW_ANALYSIS`, with a provisional prediction index, 11 unmapped source predictors and previously inspected 2013–2014 cycle.
- The displayed 708 passed / 1 skipped count is the v0.32 workstation-reported baseline and may differ from the later v0.33 suite.
- The v0.30 hashes refer to the original published synthetic execution receipt, not to the current v0.33 source revision or live model fitting.
- Removing a publicly displayed password does not make a hard-coded demonstration passcode confidential or secure.

## Review gates

1. Run the source-only installer, backed up and rollback guarded.
2. All synthetic/privacy tests, private v0.30 `--verify` **read-only**, TypeScript compile and Next.js production build must pass before any release.
3. Source-only publisher whitelists exactly 13 paths, lists them and requires the human to type uppercase `YES` before GitHub commit/push.
4. Independently verify GitHub main/CI and actual Vercel deployment. Manually inspect all Engine Studio views on desktop and mobile, verify keyboard controls and zero-baseline chart, and verify no on-screen passcode. Test authenticated access to the existing read-only aggregate portal; do not test private data paths.
5. Keep Doctor Portal redesign as a separate later phase.
