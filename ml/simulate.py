"""Generate entirely synthetic, non-HUNT, illustrative records and outcomes.

The synthetic relationships are invented for software demonstrations; their
magnitudes are not estimates from HUNT or valid clinical evidence.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def generate(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    if n < 100:
        raise ValueError('Generate at least 100 synthetic patients for experiments.')
    rng = np.random.default_rng(seed)
    age = np.clip(rng.normal(78.8, 7.2, n), 70, 103).round(0).astype(int)
    sex = rng.choice(['Female', 'Male'], size=n, p=[0.54, 0.46])
    prev = rng.binomial(1, np.clip(0.18 + 0.009 * (age - 78), .08, .45))
    comorb = np.clip(rng.poisson(np.maximum(0.6, 1.5 + .07 * (age - 75))), 0, 8)
    medication = np.clip(rng.poisson(2.5 + .75 * comorb), 0, 20)
    gait = np.clip(rng.normal(1.05 - .018 * (age - 75) - .06 * prev - .025 * comorb, .20), .12, 1.65)
    grip = np.clip(rng.normal(37 - 12 * (sex == 'Female') - .32 * (age - 75) - .75 * comorb, 7.2), 5, 62)
    sppb = np.clip(np.rint(10.9 + 5.0 * (gait - 1) - .055 * (age - 75) + rng.normal(0, 1.9, n)), 0, 12)
    moca = np.clip(np.rint(rng.normal(25.1 - .15 * (age - 75) - .25 * comorb, 3.3, n)), 7, 30)
    bmi = np.clip(rng.normal(27.1 - .025 * (age - 78), 4.3, n), 16, 44)
    weight_loss = rng.binomial(1, np.clip(.10 + .014 * (age - 75) + .020 * comorb, .03, .50))
    exhaustion = rng.binomial(1, np.clip(.13 + .010 * (age - 75) + .025 * comorb, .06, .52))
    oral = rng.binomial(1, np.clip(.20 + .008 * (age - 75) + .025 * comorb, .08, .70)).astype(float)
    activity = np.clip(rng.normal(110 - 2.3 * (age - 75) + 42 * (gait - 1) - 6 * comorb, 40), 3, 220)

    # Entirely artificial 12-month prospective-event label with no HUNT linkage.
    linear = (-1.85 + .040 * (age - 78) + .76 * prev + .080 * (medication - 5)
              - 1.1 * (gait - .9) - .025 * (grip - 28) - .09 * (sppb - 9)
              - .024 * (moca - 24) + .19 * weight_loss + .25 * exhaustion
              + .11 * (comorb - 2) - .0025 * (activity - 70))
    prob = 1 / (1 + np.exp(-linear))
    fall = rng.binomial(1, prob)
    frame = pd.DataFrame({
        'patient_id': [f'SYN-{i:05d}' for i in range(1, n + 1)],
        'data_origin': 'SYNTHETIC',
        'baseline_year': 2018,
        'age': age, 'sex': sex, 'bmi': np.round(bmi, 1),
        'grip_strength_kg': np.round(grip, 1),
        'gait_speed_ms': np.round(gait, 2),
        'sppb_score': sppb.astype(float), 'moca_score': moca.astype(float),
        'weight_loss': weight_loss.astype(float), 'exhaustion': exhaustion.astype(float),
        'medication_count': medication.astype(float),
        'oral_health_problem': oral,
        'activity_minutes_day': np.round(activity, 0),
        'previous_fall': prev.astype(float),
        'comorbidity_count': comorb.astype(float),
        'fall_within_12m': fall,
    })
    # Realistic field availability *patterns* for testing missing-data handling,
    # not estimates of actual HUNT missingness processes.
    for col, miss in {
        'bmi': .06, 'grip_strength_kg': .07, 'gait_speed_ms': .09,
        'sppb_score': .09, 'moca_score': .11, 'weight_loss': .14,
        'exhaustion': .20, 'oral_health_problem': .45,
        'activity_minutes_day': .51,
    }.items():
        frame.loc[rng.random(n) < miss, col] = np.nan
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description='Create a synthetic demo cohort (no HUNT data).')
    parser.add_argument('--n', type=int, default=6000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', default='data/synthetic_cohort.csv')
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = generate(args.n, args.seed)
    frame.to_csv(output, index=False)
    print(f'Generated {len(frame):,} SYNTHETIC records: {output}')
    print(f'Artificial event fraction: {frame.fall_within_12m.mean():.1%}. Not a HUNT estimate.')


if __name__ == '__main__':
    main()
