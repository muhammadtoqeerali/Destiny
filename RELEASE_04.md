# FrailtyScope v0.4: Doctor & Admin portals

## What changed

- Only two top-level header destinations: **Doctor Portal** and **Admin Portal**.
- Removed the global left sidebar; application opens in Doctor Portal.
- Doctor portal: illustrated patient directory, search, risk-band filtering, paginated case selection; separate Overview, Measurements and Score explanation tabs. All 14 variables are available with missingness clearly signposted.
- Admin portal: demonstration password sign-in, server-verified signed HttpOnly cookie and sign-out. Inside it, four horizontal stages: Data exploration, Preprocessing, Model architecture and Performance. Existing research data and metrics preserved.
- More spacious visual design: readable typography, larger charts, less crowded content, responsive layouts.

## Demonstration password

**admin123** is the default password for synthetic demo purposes ONLY. This is intentionally weak, public, and **must never be used to protect health records, real HUNT data, sensitive metrics or operational clinical services**. Do not interpret the login UI as compliance with Norwegian health data security standards.

For better (still prototype-level) access control, set environment variables in Vercel Project -> Settings -> Environment Variables, then redeploy:

- `ADMIN_PORTAL_PASSWORD`: replace demo default with your own strong password (do not commit it).
- `ADMIN_SESSION_SECRET`: long random value (e.g., generated using `openssl rand -hex 32` on your workstation; paste only into Vercel).

Session cookies are HttpOnly, SameSite=Lax, signed by a server-side HMAC, and expire after eight hours. The demo does **not** implement identity-based authentication, rate limiting, auditing, MFA, or clinical privacy controls. Synthetic data in `/public/data/demo.json` remain public and are not made private by this portal.

For true patient data, use institutionally approved restricted infrastructure and real authentication / RBAC with independent security review. Never deploy real records or individual HUNT data to this public Vercel demo.

## Paths

- `/` redirects to `/doctor`
- `/doctor` - public synthetic demo
- `/admin` - signed-in developer workspace, redirects unauthenticated requests to `/admin/login`
- `/admin/login` - server-side credential check

## Release workflow

From Linux workstation:

```bash
unzip -oq ~/Downloads/FrailtyScope_v04_Two_Portals.zip -d /tmp/frailtyscope-v04
bash /tmp/frailtyscope-v04/frailtyscope_v04_release/scripts/publish_v04.sh 2>&1 | tee ~/frailtyscope-v04.log
```

The publishing script validates origin, `main`, and clean local app changes, then builds and audits dependencies **in a separate temporary directory**, allowing the workstation's live app to keep running untouched. It pushes only approved source paths after successful verification. Vercel then deploys `main` automatically.

## Research integrity

All displayed individual cases, 12-month fall-event labels, evaluation scores and model-response explanations arise from **artificial synthetic data**. Neither actual HUNT data nor clinical outcomes are available to the demo. This platform is **not** for clinical use.
