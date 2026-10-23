# v0.36 — Assessment to Follow-up to Explainability (PUBLIC DEMO ONLY)

Design change: provide a clear, reactive and visually engaging workflow in the Doctor Portal. No person-level risk calculation, diagnosis, prognosis, treatment recommendation or unsupported explanation is permitted by this release.

- Patient assessment: entered observations are validated in the existing browser form and shown immediately in a live readout. Missing and structural skip responses are preserved. Entries are in memory only, lost when the page reloads. No network POST or records database exists.
- Follow-up: deliberate user click copies only valid BMI and PHQ-9 measurements into the temporary visit form, then date and Save are required; changes are shown descriptively from first/last dated visits for each outcome separately, requiring two nonmissing measurements. This is not an extrapolation.
- Model evidence: the technical charts formerly duplicated from Admin are replaced by an accessible animated five-step explanatory workflow. Pause/reduce motion and keyboard controls supported. The visualization is not model-specific XAI, as no individual prediction or fitted-model attribution is available.
- Private integrity verification remains read-only. The original case remains BLOCKED_FOR_NEW_ANALYSIS; no NHANES records, previously saved fitted models or target values are loaded or changed.
- Unlock criteria for a future governed runtime inference service: a designated purpose and population, audited source mapping (currently 3/14 predictors), prediction-index timing, approved fitting/inference, unchanged external evaluation protocol, calibration and subgroup assessment, privacy/access/logging, clinician review, authentic explanation tied to the exact fitted model and limits disclosure.

This is an educational software/UI improvement; it is not clinical validation or deployment approval.
