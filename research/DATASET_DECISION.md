# Real dataset decision for FrailtyScope

**Now: CDC NHANES 2011–2014 baseline measurements joined to 2019 public-use linked mortality**. The observations are real public survey records; vital status was not perturbed, but *some public-use follow-up times/cause variables were synthetically substituted* for confidentiality. A fixed 60-month event label is therefore approximate. NHANES is primarily repeated cross-sectional surveys, not repeat visits to the same people. The prototype trains a **single real longitudinally linked outcome (mortality)**, not falls or cognitive progression. No clinical deployment.

**Next, with account registration: National Health and Aging Trends Study (NHATS)**. US adults 65+ followed in annual rounds with relevant mobility, daily function, and cognition domains, allowing proper time-stamped outcome definitions subject to the instrument codebooks and missingness. Public-use files require registration and CONDITIONS OF USE prohibit uploading data to public LLM systems or redistributing to third parties. Keep all rows and models local; only non-disclosive, permitted aggregate outputs could be shared/published.

**Alternative: Health and Retirement Study (HRS)**. More waves and outcomes but registered access and use restrictions.

**Ultimate target: NTNU HUNT4 70+ and approved linked registry outcomes**. Requires NTNU-approved extract, PI, and ethical/legal approvals. Variables are not plug-and-play interchangeable: mapping, harmonizing units, timing, outcome validity, and permissions are essential before training.

## Important NHANES study limitations

- The 2011–2012 development cohort is randomly divided for training/validation; the 2013–2014 cycle is a later-cycle held-out evaluation. This is **not external-site validation**.
- Mortality follow-up in public files ends 31 December 2019. Labeling uses 60 months with censored cases excluded. A death at 60 months counts as an event.
- Because some follow-up times are perturbed, this horizon-specific mortality outcome is not perfectly measured; results are exploratory only.
- Age 80+ is top-coded at 80 in the public-use dataset; no granular age trends past age 80.
- Interviews self-report several clinical conditions; physical functioning may be missing by routing, not missing at random.
- We use an MEC-linked BMI measurement, but this benchmark does **not yet** incorporate full multistage-survey design variance, propensity adjustments, or survey-aware model selection.
- Baseline questionnaire variables are not HUNT measures, and comparisons across countries may not generalize.
- Treat protected HUNT/NHATS records separately under their licenses; keep them away from public app, GitHub, assistants, and automated public export.

## Authoritative source links

- NHATS access: https://www.nhats.org/data-access
- NHATS registration conditions: https://www.nhats.org/data-access/nhats
- HRS registration: https://hrsdata.isr.umich.edu/data-products/public-survey-data
- CDC NHANES questionnaire files: https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component=Questionnaire&CycleBeginYear=2011
- CDC NHANES demographics: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/DEMO_G.htm
- CDC linked mortality: https://www.cdc.gov/nchs/linked-data/mortality-files/
- CDC public linked mortality FTP: https://ftp.cdc.gov/pub/health_statistics/NCHS/datalinkage/linked_mortality/
