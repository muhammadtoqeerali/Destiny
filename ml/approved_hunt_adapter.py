"""LOCAL-ONLY label builder for authorized, already mapped/approved HUNT extracts.

This module does NOT fetch HUNT data, does NOT transfer data, and does not export
patient-level records to the public Next.js application. The named files here
are a research *contract*, not a representation of released HUNT field codes.

Input: pseudonymized baseline table (participant_id, baseline_date, and feature
columns mapped according to an institutionally approved feature dictionary), and an approved follow-up table
(participant_id, last_observed_date, date columns defined in ENDPOINT_DATE_FIELDS).
An outcome is eligible when an observed event occurs during the horizon or
follow-up is long enough to establish its absence. Short follow-up is NA,
NEVER a negative. Death can truncate follow-up for non-death outcomes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

ENDPOINT_DATE_FIELDS = {
 'fall_within_12m': 'first_fall_date',
 'fracture_within_12m': 'first_fracture_date',
 'new_dependence_within_12m': 'first_new_dependence_date',
 'cognitive_decline_within_12m': 'first_cognitive_decline_date',
 'hospital_admission_within_12m': 'first_hospital_admission_date',
}
HORIZON_DAYS=365


def make_labels(baseline:pd.DataFrame, followup:pd.DataFrame, horizon_days:int=HORIZON_DAYS)->pd.DataFrame:
    required_base={'participant_id','baseline_date'}
    required_follow={'participant_id','last_observed_date'}
    if not required_base <= set(baseline) or not required_follow <= set(followup):
        raise ValueError('participant_id / baseline_date / last_observed_date required')
    if any(x in baseline.columns or x in followup.columns for x in ['national_identity_number','fødselsnummer','ssn']):
        raise ValueError('Direct identifiers are prohibited in this adapter')
    if baseline.participant_id.duplicated().any() or followup.participant_id.duplicated().any():
        raise ValueError('Input must have one baseline/follow-up record per pseudonym; aggregate before use')
    both = baseline.merge(followup,on='participant_id',validate='one_to_one',how='left',indicator=True)
    if (both['_merge']!='both').any():
        raise ValueError('Some participants lack a follow-up row')
    both=both.drop(columns='_merge')
    start=pd.to_datetime(both.baseline_date,errors='coerce')
    last=pd.to_datetime(both.last_observed_date,errors='coerce')
    if start.isna().any() or last.isna().any() or (last<start).any():
        raise ValueError('Invalid baseline or follow-up dates')
    death=pd.to_datetime(both['death_date'],errors='coerce') if 'death_date' in both else pd.Series(pd.NaT,index=both.index)
    if ((death.notna()) & (death<start)).any():
        raise ValueError('Death before baseline is not eligible')
    # For nonmortality targets, a death stops the observation window rather
    # than magically providing evidence of no event after death.
    effective_last = last.where(death.isna() | (last<=death),death)
    horizon=start+pd.to_timedelta(horizon_days,unit='D')
    for target,col in ENDPOINT_DATE_FIELDS.items():
        if col not in both.columns:
            both[target]=pd.array([pd.NA]*len(both),dtype='Int64')
            continue
        event=pd.to_datetime(both[col],errors='coerce')
        if ((event.notna()) & ((event < start) | (event > last))).any():
            raise ValueError(f'Inconsistent event date in {col}; check ascertainment and lookback')
        event_within = event.notna() & (event <= horizon) & (event <= effective_last)
        fully_observed = effective_last >= horizon
        labels = np.where(event_within, 1, np.where(fully_observed,0,np.nan))
        both[target] = pd.array(labels,dtype='Int64')
    return both


def describe_labels(df:pd.DataFrame)->dict:
    return {t:{'eligible':int(df[t].notna().sum()),'events':int(df[t].fillna(0).sum()),
               'unresolved_censored':int(df[t].isna().sum())} for t in ENDPOINT_DATE_FIELDS}


def cli():
    parser=argparse.ArgumentParser(description='Inspect AUTHORIZED, mapped HUNT extracts in an approved environment; never public export')
    parser.add_argument('--baseline',required=True)
    parser.add_argument('--followup',required=True)
    parser.add_argument('--acknowledge-approved-environment',action='store_true')
    args=parser.parse_args()
    if not args.acknowledge_approved_environment:
        parser.error('Use only inside institutionally approved data environment with valid authorizations.')
    for path in [args.baseline,args.followup]:
        if not Path(path).is_file():parser.error('File not found: '+path)
    df=make_labels(pd.read_csv(args.baseline),pd.read_csv(args.followup))
    # Output only NON-DISCLOSIVE local counts to caller; small-cell suppression
    # for publication still requires the approved institutional policy.
    print('PRIVATE DIAGNOSTICS ONLY — DO NOT COPY THESE RESULTS TO PUBLIC DASHBOARD')
    print('Mapped columns accepted. Defined outcomes:',len(ENDPOINT_DATE_FIELDS))
    for k,v in describe_labels(df).items():print(k,v)

if __name__=='__main__':cli()
