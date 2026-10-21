"""Generate privacy-conscious NHANES descriptive cohorts, never respondent rows."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

HEALTH={
 'heart_failure':'Heart failure','coronary_disease':'Coronary heart disease',
 'stroke':'Stroke','cancer':'History of cancer','diabetes':'Diabetes',
 'hypertension':'Hypertension','ever_smoked':'Ever smoked',
}
MOBILITY={'walking_difficulty':'Walking','stairs_difficulty':'Stairs','stooping_difficulty':'Stooping'}
AGE_LABELS=[('65–69',65,69),('70–74',70,74),('75–79',75,79),('80+',80,120)]
MIN_DENOMINATOR=50
MIN_EVENT=20


def binary_prevalence(df:pd.DataFrame,col:str,group:str)->dict|None:
    values=pd.to_numeric(df[col],errors='coerce')
    mask=values.isin([0,1])
    n=int(mask.sum());num=int((values[mask]==1).sum())
    if n<MIN_DENOMINATOR or num<MIN_EVENT or n-num<MIN_EVENT:return None
    w=pd.to_numeric(df.loc[mask,'survey_weight'],errors='coerce')
    if w.notna().sum()!=n or not np.isfinite(w.to_numpy()).all() or (w<=0).any():raise ValueError('Invalid survey weights')
    weighted=float(np.average(values[mask],weights=w))
    return {'group':group,'label':HEALTH.get(col,col),'n_observed':n,
      'percent':round(100*num/n,1),'weighted_percent':round(100*weighted,1)}


def build_profile(df:pd.DataFrame,quality:dict|None=None)->dict:
    required={'SEQN','cycle','data_origin','survey_weight','sex','age','bmi',*HEALTH,*MOBILITY}
    if not required.issubset(df.columns):raise ValueError('Missing profile fields: '+str(required-set(df.columns)))
    if len(df)<1000 or set(df.data_origin)!={'NHANES_PUBLIC_2019_LMF'}:raise ValueError('Expected real cohort')
    if df.SEQN.duplicated().any():raise ValueError('Repeated respondent')
    frames={'All 65+':df}
    for label,lo,hi in AGE_LABELS:frames[label]=df.loc[df.age.between(lo,hi)]
    for label in ('Female','Male'):frames[label]=df.loc[df.sex.eq(label)]
    out=[]
    for group,subset in frames.items():
        if len(subset)<MIN_DENOMINATOR:continue
        conditions=[binary_prevalence(subset,key,group) for key in HEALTH]
        mobility=[]
        for key,label in MOBILITY.items():
            x=pd.to_numeric(subset[key],errors='coerce')
            known=x.isin([1,2,3,4]);n=int(known.sum());pos=int(x[known].ge(2).sum())
            if n<MIN_DENOMINATOR or min(pos,n-pos)<MIN_EVENT:continue
            w=pd.to_numeric(subset.loc[known,'survey_weight'],errors='coerce')
            if not np.isfinite(w).all() or (w<=0).any():raise ValueError('Invalid weights')
            mobility.append({'label':label,'group':group,'n_observed':n,
               'percent':round(100*pos/n,1),'weighted_percent':round(100*float(np.average(x[known].ge(2).astype(float),weights=w)),1)})
        bmi=pd.to_numeric(subset.bmi,errors='coerce');good=bmi.between(12,70)
        bmi_mean=round(float(np.average(bmi[good],weights=subset.loc[good,'survey_weight'])),1) if good.sum()>=MIN_DENOMINATOR else None
        out.append({'name':group,'n':len(subset),'mean_bmi_weighted':bmi_mean,
            'conditions':[v for v in conditions if v is not None],'mobility':mobility})
    flags=[]
    if quality and quality.get('phq9_flag')=='LOW_COVERAGE_REVIEW':flags=['PHQ-9 excluded from descriptive profiles pending raw-data completeness review']
    return {'provenance':'REAL_NHANES_AGGREGATE_ONLY','dataset':'NHANES 2011–2014',
            'source':'CDC/NCHS','population':'Participants 65+ with eligible linked-mortality follow-up',
            'groups':out,'method':'Survey-weighted descriptive percentages; no design-based uncertainty estimates',
            'notes':flags,'small_cell_rule':'Only variables with ≥50 observed records and ≥20 per category are reported'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',default='data/processed/nhanes_5yr_local.csv');p.add_argument('--quality',default='artifacts/realdata_nhanes/quality_v08.json');p.add_argument('--output',default='web/public/data/nhanes-cohort-profile.json');a=p.parse_args()
    quality=json.loads(Path(a.quality).read_text()) if Path(a.quality).exists() else None
    profile=build_profile(pd.read_csv(a.input),quality)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(profile,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print('PUBLIC aggregate cohort profile generated:',out,'groups',len(profile['groups']))
if __name__=='__main__':main()
