# FrailtyScope v0.34 — executable browser QA and deployment identity

**Release boundary:** engineering-only QA. It does not retrain the saved RF/CatBoost/HGB models, read private research data, change public aggregate JSON, open NHANES participant files, approve new analysis, or create clinical scores.

## Implemented

1. `GET /api/status`: minimal public release marker (`v0.34`), optional Vercel Git commit SHA only if syntactically valid, research-execution boundary, cache disabled. Does **not** expose any password, secret, private experiment ID or source participant data. If Vercel does not provide SHA, return `null`, never invent identity.
2. Engine Studio status strip: displays the server's stated release and Git prefix if provided. `Not available from this deployment` is deliberately distinct from a verified SHA. The source's outdated `708 passed` counter is removed; the only repeated-run number comes from the documented v0.30 synthetic receipt.
3. **Actual Chromium E2E checks**, desktop 1440 × 900 and mobile 390 × 844: /doctor navigation; numeric validity; distinction between activity nonperformance and difficulty; temporary visit; /admin unauthenticated redirect, wrong password and aggregate-only demo login; Engine Studio views; all eight historical admin sections; threshold 0.22 initial value, 0.35 selector, sensitivity and decision-benefit chart geometry. Browser exceptions fail the gate.
4. Standalone local-server runner starts the built Next.js application on a random 127.0.0.1 port, probes /api/status, executes Chromium, then stops its own server. It cannot target a remote clinical endpoint by accident.
5. CI gains a Chromium browser gate alongside existing full synthetic/privacy Python checks, public aggregate disclosure guards, Next build and production dependency audit. The publisher additionally requires Chromium QA **before** allowing consent/push.

## Dependencies and workstation checks

After installing the ZIP package and passing Python/Next build, install browser QA tooling **in the same workstation venv** (not the Vercel service):

```
.venv/bin/python -m pip install 'playwright==1.56.0'
.venv/bin/python -m playwright install chromium
bash scripts/run_browser_qa_v34.sh
```

If the browser lacks required Linux libraries, install the supported Playwright OS dependencies through the package manager using appropriate system administration policies. The installer intentionally does not mutate the Python environment or automatically install system libraries. The GitHub Ubuntu CI job runs `python -m playwright install --with-deps chromium`.

The E2E test uses only **fictional** form values (age 75, BMI 26.5, visit date 2026-01-15) and the existing public `admin123` aggregate-only demo path. This passcode is *not security*, and the public dashboard must never expose private APIs or participant data. E2E does not call model fitting, download private artifacts, or serialize participant records. No screenshot/trace is uploaded or committed.

## How to interpret validation

- Python unit/source tests + Next build validate source, not a browser deployment.
- Local Chromium QA validates the built site on that workstation. It is **not** evidence of which SHA a Vercel URL currently serves.
- Vercel release identity must be confirmed with a live `/api/status` response; if the Git SHA is null, compare Vercel deployment metadata in the authorized account.
- Historical NHANES 2013–2014 is previously inspected, not independent external validation; outcomes are approximately five-year **mortality**, not frailty or clinical risk.
- The source-only integrity receipt is documentary evidence of synthetic repeatability, not clinical approval or best-model performance.

## Next phase

After publishing v0.34, inspect the production release receipt and test it in a browser. Then progress to the separate Norwegian-design-principles Doctor Portal redesign, retaining the same safe data boundaries and avoiding false official Norwegian/NTNU branding.
