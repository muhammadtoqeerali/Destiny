"""Local NHANES data-quality checks. Never exports respondent rows or identifiers."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from ml.realdata_nhanes import normalize_xport_zero

PHQ_ITEMS=[f'DPQ{i:03d}' for i in range(10,100,10)]
CYCLES={'2011-2012':'G','2013-2014':'H'}


def phq_diagnostics(raw:pd.DataFrame,processed:pd.DataFrame)->dict:
    """Cross-check the official nine DPQ items against processed PHQ-9 totals by SEQN."""
    required={'SEQN',*PHQ_ITEMS}
    if not required.issubset(raw.columns):
        raise ValueError('Missing official DPQ columns: '+str(sorted(required-set(raw.columns))))
    if not {'SEQN','phq9_score'}.issubset(processed.columns):raise ValueError('Missing processed PHQ fields')
    if raw.SEQN.duplicated().any() or processed.SEQN.duplicated().any():raise ValueError('Duplicate respondent IDs')
    raw=raw[['SEQN']+PHQ_ITEMS].copy()
    raw['SEQN']=pd.to_numeric(raw.SEQN,errors='coerce').astype('Int64')
    proc=processed[['SEQN','phq9_score']].copy()
    proc['SEQN']=pd.to_numeric(proc.SEQN,errors='coerce').astype('Int64')
    merged=proc.merge(raw,on='SEQN',how='left',validate='one_to_one',indicator=True)
    if merged['_merge'].eq('left_only').any():raise ValueError('Processed participants missing from raw DPQ file')
    items=merged[PHQ_ITEMS].apply(pd.to_numeric,errors='coerce')
    zero_alias=(items.notna() & items.ne(0) & items.abs().lt(1e-70))
    normalized=items.apply(normalize_xport_zero)
    valid=normalized.where(normalized.isin([0,1,2,3]))
    reconstructed=valid.sum(axis=1,min_count=9)
    proc_tot=pd.to_numeric(merged.phq9_score,errors='coerce')
    mismatch=~((reconstructed.eq(proc_tot)) | (reconstructed.isna()&proc_tot.isna()))
    stats={
       'n':len(merged),
       'raw_nine_complete':int(reconstructed.notna().sum()),
       'processed_complete':int(proc_tot.notna().sum()),
       'mismatch_count':int(mismatch.sum()),
       'xport_zero_alias_values_corrected':int(zero_alias.to_numpy().sum()),
       'raw_complete_percent':round(100*float(reconstructed.notna().mean()),2),
       'item_valid_percent':{key:round(100*float(valid[key].notna().mean()),2) for key in PHQ_ITEMS},
    }
    if stats['mismatch_count']:
        raise ValueError('PHQ-9 ingestion mismatch; investigate before publishing. Counts: '+json.dumps(stats))
    return stats


def audit(processed_path:Path,raw_dir:Path)->dict:
    processed=pd.read_csv(processed_path)
    needed={'cycle','SEQN','phq9_score','data_origin'}
    if not needed.issubset(processed.columns):raise ValueError('Processed schema incomplete')
    if set(processed.data_origin)!={'NHANES_PUBLIC_2019_LMF'}:raise ValueError('Real NHANES provenance required')
    out={'provenance':'NHANES_PUBLIC_2019_LMF','sample_size':len(processed),'phq9_by_cycle':{}}
    for cycle,suffix in CYCLES.items():
        sub=processed.loc[processed.cycle.eq(cycle)]
        if sub.empty:raise ValueError('Missing cycle '+cycle)
        xpt=raw_dir/cycle/f'DPQ_{suffix}.XPT'
        if not xpt.is_file():raise FileNotFoundError(f'CDC DPQ source not cached: {xpt}')
        out['phq9_by_cycle'][cycle]=phq_diagnostics(pd.read_sas(xpt,format='xport'),sub)
    out['phq9_complete_percent']=round(100*float(processed.phq9_score.notna().mean()),2)
    out['phq9_flag']=('LOW_COVERAGE_REVIEW' if out['phq9_complete_percent']<50 else 'COVERAGE_OK')
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--processed',default='data/processed/nhanes_5yr_local.csv');p.add_argument('--raw-dir',default='data/raw/nhanes');p.add_argument('--report',default='artifacts/realdata_nhanes/quality_v08.json');a=p.parse_args()
    out=audit(Path(a.processed),Path(a.raw_dir))
    dest=Path(a.report);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps(out,indent=2))
    if out['phq9_flag']!='COVERAGE_OK':
        print('IMPORTANT: PHQ-9 completeness is below 50%; existing PHQ-9 model contribution needs review.')
if __name__=='__main__':main()
