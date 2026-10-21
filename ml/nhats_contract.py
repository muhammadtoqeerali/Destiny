"""NHATS local-only, codebook-confirmed cross-wave schema adapter.
No NHATS data, credentials, participant rows or unverified mappings are bundled.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd

PLACEHOLDER='REPLACE_FROM_OFFICIAL_CODEBOOK'

def validate_rounds(rounds:list[pd.DataFrame],spec:dict)->dict:
    idname=spec.get('participant_key')
    waves=spec.get('waves')
    if not idname or idname==PLACEHOLDER or not isinstance(waves,list) or len(waves)<2:raise ValueError('Two verified waves and participant key required')
    if len(rounds)!=len(waves):raise ValueError('File/wave mismatch')
    mapped=spec.get('variables')
    if not isinstance(mapped,dict) or not mapped or any(not v or v==PLACEHOLDER for v in mapped.values()):raise ValueError('Verify variable mapping against NHATS codebooks')
    if not spec.get('outcome_definition_verified',False):raise ValueError('Outcome definition requires codebook review')
    counts=[];idsets=[]
    for frame,wave in zip(rounds,waves):
        if not set([idname,*mapped.values()]).issubset(frame.columns):raise ValueError('Wave does not contain mapped variables')
        if frame[idname].isna().any() or frame[idname].duplicated().any():raise ValueError('Invalid participant keys')
        ids=set(frame[idname]);idsets.append(ids)
        counts.append({'wave':str(wave),'n':len(frame),'variables_with_data':{k:int(frame[col].notna().sum()) for k,col in mapped.items()}})
    overlap=len(set.intersection(*idsets))
    return {'wave_counts':counts,'overlap_n':overlap,'n_waves':len(waves),'status':'SCHEMA_CHECK_ONLY_NO_MODEL_TRAINING'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--files',nargs='+',required=True);p.add_argument('--output',default='artifacts/nhats/schema_audit.json');a=p.parse_args()
    conf=json.loads(Path(a.config).read_text())
    if any(not str(x).startswith(('data/','/')) for x in a.files):raise ValueError('Use local protected data files')
    frames=[]
    for name in a.files:
        path=Path(name)
        if not path.is_file():raise FileNotFoundError(path)
        if path.suffix.lower()=='.csv':frames.append(pd.read_csv(path))
        elif path.suffix.lower()=='.dta':frames.append(pd.read_stata(path))
        else:raise ValueError('Only CSV or Stata DTA files supported')
    result=validate_rounds(frames,conf)
    dest=Path(a.output)
    if not str(dest).startswith('artifacts/') and not str(dest).startswith('/'):raise ValueError('Only local artifact reports')
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n')
    print('Local NHATS schema assessment saved. Do NOT send NHATS files, record-level outputs or credentials to this chat.')
if __name__=='__main__':main()
