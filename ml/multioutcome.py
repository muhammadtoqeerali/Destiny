"""Synthetic MULTI-OUTCOME experiment; no data or parameters are learned from HUNT.

Each outcome is an invented binary event during 12-month follow-up. This is a
software demonstration, not an epidemiological or clinical risk model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from ml.simulate import generate

OUTCOMES = {
    'fall_within_12m': 'Falls',
    'fracture_within_12m': 'Fracture',
    'new_dependence_within_12m': 'New daily-life dependence',
    'cognitive_decline_within_12m': 'Cognitive deterioration',
    'hospital_admission_within_12m': 'Hospital admission',
}
DESCRIPTIONS = {
    'fall_within_12m': 'Invented fall event in the next 12 months',
    'fracture_within_12m': 'Invented new fracture within 12 months',
    'new_dependence_within_12m': 'Invented change in daily-life independence within 12 months',
    'cognitive_decline_within_12m': 'Invented cognitive deterioration within 12 months',
    'hospital_admission_within_12m': 'Invented hospital admission within 12 months',
}

def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(x, -25, 25)))


def make_synthetic_cohort(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    data = generate(n=n, seed=seed)
    rng = np.random.default_rng(seed+101)
    # Synthetic health-state generators depend on LATENT full measurements;
    # missingness was injected by `generate`. This is intentional for testing
    # robustness to incomplete records and does not emulate HUNT missingness.
    age = data.age.to_numpy()
    falls = data.fall_within_12m.to_numpy()
    medications = data.medication_count.to_numpy()
    comorb = data.comorbidity_count.to_numpy()
    gait = data.gait_speed_ms.fillna(.78).to_numpy()
    sppb = data.sppb_score.fillna(8).to_numpy()
    moca = data.moca_score.fillna(23).to_numpy()
    grip = data.grip_strength_kg.fillna(26).to_numpy()
    prev = data.previous_fall.to_numpy()
    fract = sigmoid(-3.25 + .042*(age-78) + .65*falls + .38*prev + .095*comorb - .20*(gait-.85))
    dependency = sigmoid(-2.55 + .051*(age-78) - .26*(sppb-8) - .60*(gait-.80) + .12*comorb + .27*falls)
    cognitive = sigmoid(-2.25 + .055*(age-78) - .105*(moca-24) + .080*comorb + .02*(medications-5))
    admission = sigmoid(-1.90 + .035*(age-78) + .145*comorb + .055*(medications-5) + .23*falls - .012*(grip-28))
    for key, probabilities in [
        ('fracture_within_12m', fract),
        ('new_dependence_within_12m',dependency),
        ('cognitive_decline_within_12m',cognitive),
        ('hospital_admission_within_12m',admission),
    ]:
        data[key] = rng.binomial(1,probabilities)
    data['baseline_date'] = '2018-06-01'
    data['last_observed_date'] = '2019-06-01'
    return data


def simulated_history(row: pd.Series, seed: int = 42) -> list[dict]:
    """An illustrative PRE-baseline progression; NEVER used as measured HUNT history."""
    import hashlib
    digest = hashlib.sha256((str(row['patient_id'])+':'+str(seed)).encode()).digest()
    r = np.random.default_rng(int.from_bytes(digest[:8], 'big'))
    gait = float(row.gait_speed_ms) if pd.notna(row.gait_speed_ms) else .76
    cognition = float(row.moca_score) if pd.notna(row.moca_score) else 23.
    sppb = float(row.sppb_score) if pd.notna(row.sppb_score) else 8.
    gait_change = r.uniform(-.09,.06)
    cognitive_change = r.uniform(-1.8,.7)
    sppb_change = r.uniform(-1.4,.5)
    return [
        {'period': label,
         'gait_ms': round(max(.12,gait + gait_change*(2-i)),2),
         'moca': round(np.clip(cognition + cognitive_change*(2-i),7,30),1),
         'sppb': round(np.clip(sppb + sppb_change*(2-i),0,12),1)}
        for i,label in enumerate(['2016 (simulated)','2017 (simulated)','2018 (baseline demo)'])
    ]
