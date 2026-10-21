"""Local exploratory Kaplan-Meier audit of REAL NHANES linked-mortality follow-up.
Times in public-use linked mortality are disclosure-perturbed. This is not a
clinical survival model, and results are never exported to the public portal.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from ml.realdata_nhanes import CYCLES,download_xpt,download_mortality,read_mortality


def kaplan_meier(time,observed,months=(12,24,36,48,60)):
    t=np.asarray(time,dtype=float);e=np.asarray(observed,dtype=int)
    if len(t)!=len(e) or len(t)<2 or not np.isfinite(t).all() or (t<0).any() or not set(e).issubset({0,1}):raise ValueError('Invalid time-to-event data')
    times=np.unique(t[e==1]);survival=1.0;rows=[];idx=0
    for end in months:
        while idx<len(times) and times[idx]<=end:
            date=times[idx];at_risk=int((t>=date).sum());events=int(((t==date)&(e==1)).sum())
            if at_risk<events or at_risk<=0:raise ValueError('Invalid risk set')
            survival*=1-events/at_risk;idx+=1
        rows.append({'month':int(end),'survival':round(survival,4),'number_at_risk':int((t>=end).sum())})
    return rows


def audit(raw_dir:Path):
    frames=[]
    for cycle in CYCLES:
        demo=pd.read_sas(download_xpt(cycle,'DEMO',raw_dir),format='xport')
        ages=demo[['SEQN','RIDAGEYR']]
        mortality=read_mortality(download_mortality(cycle,raw_dir))
        z=ages.merge(mortality,on='SEQN',how='inner',validate='one_to_one')
        z=z.loc[z.RIDAGEYR.ge(65)&z.ELIGSTAT.eq(1)&z.MORTSTAT.isin([0,1])&z.PERMTH_EXM.notna()&z.PERMTH_EXM.ge(0)].copy()
        z['cycle']=cycle;frames.append(z)
    d=pd.concat(frames,ignore_index=True)
    if len(d)<1000:raise ValueError('Unexpectedly small survival cohort')
    return {'dataset':'REAL NHANES linked mortality; public times may be perturbed',
       'n':len(d),'observed_deaths':int(d.MORTSTAT.sum()),
       'all_ages':kaplan_meier(d.PERMTH_EXM,d.MORTSTAT),
       'interpretation':'Local descriptive Kaplan-Meier; unweighted and no survey-design variance'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',default='data/raw/nhanes');p.add_argument('--output',default='artifacts/realdata_nhanes/km_audit_v08.json');a=p.parse_args()
    out=audit(Path(a.raw_dir));dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
