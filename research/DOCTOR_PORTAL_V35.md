# FrailtyScope v0.35.1 — Doctor Portal, Norwegian-inspired research presentation

**Intent:** Improve visual hierarchy, accessibility and communication for the existing public aggregate research / fictional form demo. This is an independent site and is **not** an official Norwegian government, Helsenorge or NTNU clinical service.

## Engineering scope

- New responsive Doctor Portal hero and evidence card driven **only** by existing `web/public/data/nhanes-aggregate.json`. Development 2011–2012 (1,165) and later-cycle 2013–2014 (1,257) are distinct participants, not a temporal trajectory; the later cycle includes 246 historical recorded events. Any proportions in the new bars are simply ratios of existing, disclosed public aggregate counts.
- A sober five-section navigation, with explicit current-page semantics and 44px+ input/interaction targets.
- A compact visible non-clinical status with a keyboard-operated disclosure for the existing full research-boundary notice.
- Improved card spacing, typography, color contrast, mobile layout and visible keyboard focus; presentation is scoped to `.v35-doctor` and does not restyle the Admin Portal.
- Numeric assessment inputs now include programmatic `aria-invalid` states. Existing completion counts additionally have a semantic progressbar. These are descriptive, **not** clinical scores.
- The existing 5 Doctor functional pages and all patient/visit form values, ranges, response-status distinctions, disposable local memory and no-server storage behavior remain unchanged. No real clinical visit data, patient identifiers, name or risk outputs are permitted.
- Existing v0.34 browser QA continues to run, followed by additional Doctor-specific desktop/mobile Chromium checks from the same loopback-only server.

## Design basis

Independent implementation inspired by public guidance from Norway's Designsystemet (https://designsystemet.no/en/intro/accessibility and https://designsystemet.no/en/intro/about-the-design-system/) and Helsenorge's published universal-design discussion (https://www.helsenorge.no/en/accessibility-on-helsenorge/). We use native React and CSS, not their logos, branding or components. No implied Norwegian public-sector partnership.

## Research boundaries and release safety

- `nhanes_mortality_v10` remains `BLOCKED_FOR_NEW_ANALYSIS`; prediction index provisional, 11/14 predictors unmapped, later-cycle cohort previously inspected. **No new NHANES/HUNT fitting, data import, holdout reuse or model ranking**.
- Public historical aggregate JSON files, saved fitted Random Forest, private review artifacts, participant tables, and immutable v0.30 audit remain unchanged. Verifying previous immutable audit uses `--verify` only; never run `--audit` again.
- The new public view intentionally does not calculate a prediction, save patient details, or substitute for clinical decision-making. The demonstration `admin123` path continues to serve only public aggregates and is not secure authorization.
- v0.35 publisher stages exactly 13 reviewed paths, runs Python fixture/privacy tests, immutable private read-only verification, production TS/Next.js build, mandatory local desktop/mobile Playwright QA, and requires fresh uppercase `YES` before any `git push`.
- Unrelated untracked interview brief scripts remain untouched; no general-purpose `git add .`.

## Follow-up work, not silently claimed here

This release does **not** establish independent WCAG conformance testing, screen-reader certification, clinical usability studies, Norwegian translation, HL7/FHIR connectivity, electronic health record integration, clinical risk validation or HUNT study authorization. Those require separate scope, review and resources.

## v0.35.1 compatibility hotfix

The initial v0.35 local install stopped and rolled back when `tests/test_demo_qa_v34.py` still expected the old `--with-deps chromium` CI command. v0.35.1 changes only that outdated string assertion in the prior test while retaining an explicit positive test for the new CI command, and adds that tracked test file to baseline SHA verification, rollback and publication allowlists. Local full regression, Next.js and Chromium tests are still required.

## Prior v0.34 GitHub Actions failure

Verified 2026-10-23: v0.34 run https://github.com/muhammadtoqeerali/Destiny/actions/runs/39926669998 failed **at Playwright's `install --with-deps chromium` step** after Python tests, public-payload validation, Node build, and `npm audit` passed. The precise apt/download error is unavailable through the connected job metadata. v0.35 changes the installation to `playwright install chromium`, omitting the runner-level Linux OS package installation request; it **does not bypass the browser QA** step. GitHub CI for v0.35 must be checked after publication; the change is a candidate fix, not yet verified in Actions.

## v0.35.3 compatibility regression

The v0.34 browser QA had ambiguous Doctor navigation selectors after the new hero introduced a second button whose name contains “Health profiles”. Keep the hero shortcut, but scope original browser test clicks to the `Doctor workspace` navigation and request exact names. Both desktop/mobile original browser QA and new Doctor-specific browser QA remain mandatory. `tests/browser_qa_v34.py` is now an exact allowlisted 14th source path with Git blob guard and rollback.
