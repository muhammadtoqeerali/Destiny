# FrailtyScope v0.32 — public aggregate demo access and ML Engine Studio

## Aim

A clear, responsive interview demonstration that separates **historical public-use NHANES aggregate results** from **synthetic-only runnable ML engineering**. No new NHANES participant data is loaded, fitted, scored, copied, exported, or published. This is not an approved HUNT adapter or a clinical risk service.

## Implemented in v0.32

1. **Public demonstration passcode `admin123`**, restricted to the pre-existing public-aggregate Admin dashboard. The passcode is *intentionally public*, not secure administrator authentication. It creates a separately named demonstration cookie that is not used for secure admin authorization. The v0.31 secure password/session-secret check remains intact and fail-closed; a future private route MUST use strict `hasAdminSession()`, never `hasPublicDemoSession()` or `canViewPublicDashboard()`. No personal data, private APIs, file uploads or server-based model fitting may be added behind this demo view. When the interview ends, remove this demo passcode path.
2. **Engine Studio** as the first Admin tab, with seven selectable engineering gates: protocol → source harmonization → participant-disjoint split → fold-only preprocessing → toy candidate fits → synthetic OOF reliability → source integrity. Clear limits, source evidence and reproducibility identifiers remain visible.
3. **Visual validation design** showing an illustrative three-fold partition (not records or actual per-person assignment), implemented/prototype/blocked capabilities, and the immutable v0.30 synthetic receipt.
4. **Separate historical evidence** showing three published model experiments with different protocols; not a re-ranked winner or new independent study. The original five public JSON aggregates are unmodified.
5. **Source and privacy regression tests, TypeScript and Next.js production build, immutable v0.30 metadata verification**. An HTTP-only post-deployment health check is supplied; live user interaction still requires browser tests.

## Evidence and scientific boundaries

- Existing v0.30 user-confirmed smoke output: internally invented 72 rows / 36 fictional people, 3 group-disjoint development folds, 2 candidates and 6 fitted toy models. Seed 1701; source SHA-256 `85a346ced199a6f00b53232aec01cc3f99720e6a467ee0ab4db58631a0e458a1`, synthetic-aggregate SHA-256 `deb79398b4f62c49801b127c7a0e0f8cd045cf9dc61f3a7d87b140b9e5dab4b7`.
- The Engine Studio is a **guided, evidence-linked browser visualization of the previously run Python synthetic engine**, not a browser server endpoint for Python fitting and not a new synthetic execution. The underlying executable engine remains in `ml/` and the private immutable review remains under gitignored `artifacts/` on the workstation.
- The original NHANES five-year mortality task remains `BLOCKED_FOR_NEW_ANALYSIS`: provisional prediction index, 11 of 14 predictors unmapped, 2013–2014 previously inspected and no longer a clean independent holdout. Don't reuse it to select a better model. The existing saved Random Forest is not touched.
- v0.27 survival/longitudinal educational prototypes and v0.28 conditional fixed-prediction uncertainty remain appropriately limited. There is no general clinical validation, complex-survey inference, independent generalization claim or best model for future NTNU studies.
- Admin `admin123` is only a **demonstration access convenience** and can be forged. It is *not security*. Server code must never infer access to private material from its cookie. Admin interactive workspace displays historical public aggregate JSON only.

## Verification and release order

1. Validate installer base SHA and package checksum; install with source backup and strict rollback on failure.
2. Full fixture/privacy Python tests, `ml.case_integrity_v30 --verify` read-only, TypeScript `npm run lint`, and `npm run build`.
3. Personally inspect the publisher's staged source allowlist, decline if any data/artifacts/public results are present, type a fresh **YES** on the workstation only if approved.
4. Inspect GitHub commit and Vercel production SHA separately. Sign in with `admin123` to **public demo only**; browse all admin tabs; test Engine Studio 7-stage controls/width; confirm historical values and notice. Run the optional HTTP health script for route availability. No Vercel account credentials or research data are required for the demo access path.
5. After interview: disable/remove public-demo passcode and perform a separate Norway-inspired Doctor Portal design/accessibility phase. Base on Norway's Designsystemet and WCAG accessibility principles; do not claim to be an official Norwegian or NTNU service.

## Out of scope for this release

- No tuning, retraining, or new NHANES modeling in the assistant environment or on the workstation.
- No change to Doctor Portal, historical public aggregates, persisted models or research approval status.
- No fully automated Playwright interaction test or deployed-Vercel verification before access to an authorized browser/project is available.
- No change to complex-survey methods, selection-aware inference or study-specific real-data clearance.
