"""Schema checks for future *approved* wave-level NHATS/HUNT extracts.

DO NOT apply this to live health data outside the dataset's approved environment.
This is a contract validator, not a magic converter between survey instruments.
"""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class OutcomeSpec:
    name:str
    baseline_date_col:str
    event_date_col:str
    followup_end_col:str


def check_panel(data:pd.DataFrame,id_col='person_id',date_col='assessment_date')->dict:
    needed={id_col,date_col,'data_origin'}
    if not needed.issubset(data.columns):raise ValueError(f'Missing {sorted(needed-set(data.columns))}')
    if data[id_col].isna().any():raise ValueError('Missing person_id')
    date=pd.to_datetime(data[date_col],errors='coerce')
    if date.isna().any():raise ValueError('Invalid assessment dates')
    if data.duplicated([id_col,date_col]).any():raise ValueError('Duplicated person/wave')
    return {'n_people':int(data[id_col].nunique()),'n_assessments':int(len(data)),
            'waves_per_person_min':int(data.groupby(id_col).size().min()),
            'waves_per_person_max':int(data.groupby(id_col).size().max())}


def label_at_horizon(df:pd.DataFrame,spec:OutcomeSpec,days:int=365)->pd.Series:
    """1=event in horizon, 0=observed beyond horizon without event, NA=censored.
    This is only appropriate when dates are measured/defined consistently.
    """
    base=pd.to_datetime(df[spec.baseline_date_col],errors='coerce')
    event=pd.to_datetime(df[spec.event_date_col],errors='coerce')
    end=pd.to_datetime(df[spec.followup_end_col],errors='coerce')
    horizon=base+pd.to_timedelta(days,unit='D')
    labels=pd.Series(pd.NA,index=df.index,dtype='Int64')
    valid=base.notna()&end.notna()&(end>=base)&(event.isna()|(event>=base))
    happened=valid&event.notna()&(event<=horizon)&(event<=end)
    no_event=valid&~happened&(end>=horizon)
    labels.loc[happened]=1
    labels.loc[no_event]=0
    return labels
