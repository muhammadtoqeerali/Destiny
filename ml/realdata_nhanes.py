"""CDC NHANES 2011-14 public-use baseline + 2019 linked mortality.

Actual public research records; NEVER export individual-level records to Vercel/GitHub.
The CDC has perturbed some public-use follow-up times. No clinical prediction.
"""
from __future__ import annotations
import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

CYCLES = {'2011-2012':'G','2013-2014':'H'}
COMPONENTS = ('DEMO','BMX','PFQ','MCQ','DIQ','BPQ','DPQ','SMQ')
RENAMES = {
    'RIDAGEYR':'age', 'RIAGENDR':'sex', 'BMXBMI':'bmi',
    'PFQ061B':'walking_difficulty', 'PFQ061C':'stairs_difficulty',
    'PFQ061D':'stooping_difficulty', 'MCQ160B':'heart_failure',
    'MCQ160C':'coronary_disease', 'MCQ160F':'stroke', 'MCQ220':'cancer',
    'DIQ010':'diabetes', 'BPQ020':'hypertension','SMQ020':'ever_smoked',
}
PHQ = [f'DPQ0{x}' for x in ('10','20','30','40','50','60','70','80','90')]
BASE_FEATURES = ['age','sex','bmi','walking_difficulty','stairs_difficulty',
                 'stooping_difficulty','heart_failure','coronary_disease','stroke',
                 'cancer','diabetes','hypertension','ever_smoked','phq9_score']
ONE_TWO = {'heart_failure','coronary_disease','stroke','cancer','diabetes','hypertension','ever_smoked'}
MORT_BASE='https://ftp.cdc.gov/pub/health_statistics/NCHS/datalinkage/linked_mortality'


def get(urls: list[str], target: Path, force:bool=False)->Path:
    if target.exists() and not force and target.stat().st_size>100:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    errors=[]
    for url in urls:
        try:
            req=urllib.request.Request(url, headers={'User-Agent':'FrailtyScopeResearch/0.1 (CDC public-use study; browser compatible)'})
            with urllib.request.urlopen(req, timeout=90) as r:
                data=r.read()
            if len(data)<1000 or b'<html' in data[:300].lower() or b'<!doctype' in data[:300].lower():
                raise RuntimeError(f'Unexpected downloaded format ({len(data)} bytes)')
            target.write_bytes(data)
            print(f'DOWNLOADED {target.name} ({len(data):,} bytes)')
            return target
        except Exception as exc:
            errors.append(f'{url}: {type(exc).__name__} {exc}')
    raise RuntimeError(f'Could not download {target.name}. If your network blocks CDC, manually download from official CDC sources to {target}; diagnostics: '+ ' | '.join(errors))


def download_xpt(cycle:str, component:str, raw_dir:Path)->Path:
    suffix=CYCLES[cycle]
    first=cycle.split('-')[0]
    fname=f'{component}_{suffix}.XPT'
    urls=[f'https://wwwn.cdc.gov/Nchs/Nhanes/{cycle}/{fname}',
          f'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{first}/DataFiles/{fname}']
    return get(urls, raw_dir/cycle/fname)


def download_mortality(cycle:str,raw_dir:Path)->Path:
    filename=f'NHANES_{cycle.replace("-","_")}_MORT_2019_PUBLIC.dat'
    return get([f'{MORT_BASE}/{filename}'],raw_dir/cycle/filename)


def read_mortality(path:Path)->pd.DataFrame:
    """2019 NHANES public-use fixed width, 0-indexed half-open positions.
    See CDC 2019 LMF R/SAS sample readers, not the NHANES III schema.
    """
    m=pd.read_fwf(path,colspecs=[(0,6),(14,15),(15,16),(45,48)],
                names=['SEQN','ELIGSTAT','MORTSTAT','PERMTH_EXM'],dtype='float64',
                na_values=['.',''])
    if len(m)<10: raise ValueError('Mortality file unexpectedly small')
    m['SEQN']=pd.to_numeric(m.SEQN,errors='coerce').astype('Int64')
    if not set(m.ELIGSTAT.dropna().unique()).issubset({1,2,3}):
        raise ValueError('Mortality ELIGSTAT parsing failed: check 2019 layout')
    if not set(m.MORTSTAT.dropna().unique()).issubset({0,1}):
        raise ValueError('Mortality MORTSTAT parsing failed: check 2019 layout')
    return m


def recode_yes_no(s:pd.Series)->pd.Series:
    return pd.to_numeric(s,errors='coerce').map({1:1.0,2:0.0})


def recode_function(s:pd.Series)->pd.Series:
    # PFQ 1=no difficulty, 2=some, 3=much, 4=unable. 5=no activity, 7/9 unknown.
    return pd.to_numeric(s,errors='coerce').where(lambda x:x.isin([1,2,3,4]))


def construct_five_year_label(m:pd.DataFrame,months:int=60)->pd.DataFrame:
    """Fixed follow-up horizon. Status 0 if alive beyond horizon OR death after.
    Censored alive before horizon is unknown, not treated as a negative.
    """
    z=m.copy()
    valid=(z.ELIGSTAT.eq(1)&z.MORTSTAT.isin([0,1])&z.PERMTH_EXM.notna())
    t=z.PERMTH_EXM
    status=z.MORTSTAT
    eligible=valid&((status.eq(1)&t.le(months))|t.ge(months))
    z['outcome_5yr']=np.nan
    z.loc[eligible,'outcome_5yr']=((status.eq(1)&t.le(months))&eligible).loc[eligible].astype(int)
    # For an event at exactly 60 months, count as an event.
    return z


def as_features(raw:pd.DataFrame)->pd.DataFrame:
    df=raw.copy()
    for column in RENAMES:
        if column not in df: df[column]=np.nan
    df=df.rename(columns=RENAMES)
    for key in ONE_TWO:
        df[key]=recode_yes_no(df[key])
    for key in ['walking_difficulty','stairs_difficulty','stooping_difficulty']:
        df[key]=recode_function(df[key])
    df['sex']=pd.to_numeric(df['sex'],errors='coerce').map({1:'Male',2:'Female'})
    df['age']=pd.to_numeric(df['age'],errors='coerce')
    df['bmi']=pd.to_numeric(df['bmi'],errors='coerce').where(lambda x:x.between(12,70))
    for key in PHQ:
        if key not in df:df[key]=np.nan
        df[key]=pd.to_numeric(df[key],errors='coerce').where(lambda x:x.isin([0,1,2,3]))
    # PHQ-9 total only when all nine scores were recorded; avoids treating absent as zero.
    df['phq9_score']=df[PHQ].sum(axis=1,min_count=9)
    return df


def load_cycle(cycle:str, raw_dir:Path)->pd.DataFrame:
    tables=[]
    for comp in COMPONENTS:
        file=download_xpt(cycle,comp,raw_dir)
        try:
            df=pd.read_sas(file,format='xport')
        except Exception as exc:
            raise RuntimeError(f'Invalid XPT {file}. Remove the corrupt cache file and retry.') from exc
        if 'SEQN' not in df.columns:raise ValueError(f'{file} lacks SEQN')
        df['SEQN']=pd.to_numeric(df.SEQN,errors='coerce').astype('Int64')
        if df.SEQN.duplicated().any():raise ValueError(f'Duplicate respondent in {file}')
        tables.append(df)
    d=tables[0]
    for table in tables[1:]:
        d=d.merge(table,on='SEQN',how='left',validate='one_to_one')
    d=as_features(d)
    d=d[d.age.ge(65)&d.age.notna()].copy()
    m=construct_five_year_label(read_mortality(download_mortality(cycle,raw_dir)))
    d=d.merge(m[['SEQN','ELIGSTAT','MORTSTAT','PERMTH_EXM','outcome_5yr']],
              on='SEQN',how='inner',validate='one_to_one')
    d=d[d.outcome_5yr.isin([0,1])].copy()
    d['cycle']=cycle
    d['data_origin']='NHANES_PUBLIC_2019_LMF'
    d['survey_weight']=pd.to_numeric(d['WTMEC2YR'],errors='coerce')/len(CYCLES)
    d['outcome_5yr']=d['outcome_5yr'].astype(int)
    if len(d)<150:raise ValueError(f'Unexpectedly few usable records in {cycle}: {len(d)}')
    # Never include linked identifiers or outcome timing as prediction features.
    return d[['SEQN','cycle','data_origin','survey_weight','outcome_5yr']+BASE_FEATURES]


def build(raw_dir:Path,output:Path)->dict:
    frames=[load_cycle(c,raw_dir) for c in CYCLES]
    frame=pd.concat(frames,ignore_index=True)
    if frame.duplicated(['SEQN','cycle']).any():raise ValueError('Duplicate joined respondent-cycle keys')
    output.parent.mkdir(parents=True,exist_ok=True)
    frame.to_csv(output,index=False)
    stats={'dataset':'NHANES 2011–2014 public survey + 2019 public-use linked mortality',
           'source':'CDC/NCHS','n':len(frame),'cycles':{c:int((frame.cycle==c).sum()) for c in CYCLES},
           'events':int(frame.outcome_5yr.sum()),'fraction_events':float(frame.outcome_5yr.mean()),
           'data_origin':'REAL_PUBLIC_USE','target':'approximately five-year mortality (public-use timing may be perturbed)',
           'age_topcoded_at_80':True,'individual_records_publication':'PROHIBITED_IN_THIS_PROJECT'}
    print('REAL NHANES merged summary:',json.dumps(stats,indent=2))
    print('Local-only data saved:',output)
    return stats


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',default='data/raw/nhanes')
    parser.add_argument('--output',default='data/processed/nhanes_5yr_local.csv')
    a=parser.parse_args()
    build(Path(a.cache),Path(a.output))
if __name__=='__main__':main()
