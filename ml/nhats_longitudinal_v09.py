"""Local-only NHATS wave import and transparent longitudinal-transition audit.

No data download, default mappings, trained model, or public export. Users
must register and independently verify variable names and response codes with
licensed NHATS codebooks before use. Never upload NHATS records to LLMs.
"""
from __future__ import annotations
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import pandas as pd

DOMAINS=('mobility','cognition','daily_function')
PLACEHOLDER='REPLACE_FROM_OFFICIAL_CODEBOOK'


def load_table(path:Path)->pd.DataFrame:
    suffix=path.suffix.lower()
    if suffix=='.csv':return pd.read_csv(path)
    if suffix=='.dta':return pd.read_stata(path,convert_categoricals=False)
    if suffix in ('.sas7bdat','.xpt'):return pd.read_sas(path,format='sas7bdat' if suffix=='.sas7bdat' else 'xport')
    raise ValueError('Expected extracted CSV, Stata DTA, SAS7BDAT, or XPT (no ZIP auto-extraction)')


def check_spec(spec:dict)->list[dict]:
    """Fail closed until every source column and code set is verified."""
    if spec.get('verified_against_nhats_codebooks') is not True:
        raise ValueError('Codebook verification not acknowledged')
    waves=spec.get('waves')
    if not isinstance(waves,list) or len(waves)<2:raise ValueError('At least two distinct waves required')
    if sorted(set(DOMAINS))!=sorted(spec.get('domains',[])):
        raise ValueError('Explicitly map all three domains; uninterpretable domains may use disabled=true')
    numbers=[];years=[]
    for w in waves:
        number=w.get('round');year=w.get('year');path=w.get('file');idcol=w.get('id_column')
        if not isinstance(number,int) or not isinstance(year,int) or year<2011 or number<1:
            raise ValueError('Verify round number and year')
        if not isinstance(path,str) or not path or path==PLACEHOLDER:
            raise ValueError('Wave file path missing')
        if not isinstance(idcol,str) or not idcol or idcol==PLACEHOLDER:
            raise ValueError('Wave participant ID column unverified')
        mapping=w.get('measures')
        if not isinstance(mapping,dict) or set(mapping)!=set(DOMAINS):
            raise ValueError('Each wave needs three explicit domain mappings')
        for domain,meta in mapping.items():
            if meta.get('disabled') is True:continue
            col=meta.get('column')
            positives=meta.get('positive_codes');negatives=meta.get('negative_codes')
            missing=meta.get('missing_codes')
            if not isinstance(col,str) or not col or col==PLACEHOLDER:
                raise ValueError('Unverified '+domain+' column')
            if (not isinstance(positives,list) or not positives or
                not isinstance(negatives,list) or not negatives or
                not isinstance(missing,list)):
                raise ValueError('Explicit positive, negative, missing codes required for '+domain)
            # Stringified canonical comparison to tolerate CSV numeric encodings.
            sets=[{canonical_code(x) for x in a} for a in (positives,negatives,missing)]
            if len(set.union(*sets))!=sum(len(s) for s in sets):
                raise ValueError('Overlapping status and missing codes')
            if any(len(s)!=len(a) for s,a in zip(sets,(positives,negatives,missing))):
                raise ValueError('Duplicate response codes')
        numbers.append(number);years.append(year)
    if numbers!=sorted(set(numbers)) or years!=sorted(set(years)):
        raise ValueError('Waves must have unique ascending rounds and years')
    return waves


def safe_path(project:Path,relative:str)->Path:
    project=project.resolve();restricted=(project/'data'/'nhats').resolve()
    path=(project/relative).resolve()
    if not path.is_relative_to(restricted):
        raise ValueError('NHATS inputs must remain within data/nhats/')
    if not path.is_file():raise FileNotFoundError(path)
    return path


def canonical_code(v):
    if isinstance(v,bool) or v is None:raise ValueError('Invalid response code')
    raw=str(v).strip()
    try:return format(Decimal(raw).normalize(),'f')
    except InvalidOperation:return raw

def normalized_status(value,meta:dict):
    if pd.isna(value):return None
    # Do not assume field numerical zero is a valid answer; only verified codes.
    code=canonical_code(value)
    sets=[{canonical_code(v) for v in meta[k]} for k in ('positive_codes','negative_codes','missing_codes')]
    if code in sets[0]:return 1
    if code in sets[1]:return 0
    if code in sets[2]:return None
    raise ValueError('Unexpected code in '+meta['column']+'; check file decoding and codebook')


def audit_rounds(frames:list[pd.DataFrame],spec:dict)->dict:
    waves=check_spec(spec)
    if len(frames)!=len(waves):raise ValueError('Frame/wave count mismatch')
    decoded=[];wave_counts=[]
    for raw,wave in zip(frames,waves):
        idcol=wave['id_column']
        mapped=[v['column'] for v in wave['measures'].values() if not v.get('disabled',False)]
        if not {idcol,*mapped}.issubset(raw.columns):
            raise ValueError('Missing mapped NHATS columns in round '+str(wave['round']))
        if raw[idcol].isna().any() or raw[idcol].duplicated().any():
            raise ValueError('Missing or duplicated participant key in a wave')
        if raw.empty:raise ValueError('Empty NHATS wave')
        d={}
        # IDs stay only in memory; report never includes identifiers or values.
        for domain,meta in wave['measures'].items():
            if meta.get('disabled') is True:continue
            statuses=[normalized_status(v,meta) for v in raw[meta['column']]]
            d[domain]=dict(zip(raw[idcol].tolist(),statuses))
        decoded.append(d)
        wave_counts.append({'round':wave['round'],'year':wave['year'],'n':int(len(raw)),
          'complete_by_domain':{domain:int(sum(v is not None for v in responses.values())) for domain,responses in d.items()}})
    transitions=[]
    for j in range(len(waves)-1):
        left=decoded[j];right=decoded[j+1]
        for domain in DOMAINS:
            if domain not in left or domain not in right:continue
            both=set(left[domain]).intersection(right[domain])
            pairs=[(left[domain][ident],right[domain][ident]) for ident in both]
            valid=[(before,after) for before,after in pairs if before is not None and after is not None]
            summary={'from_round':waves[j]['round'],'to_round':waves[j+1]['round'],
                'years_between':waves[j+1]['year']-waves[j]['year'],'domain':domain,
                'matched_respondents':len(both),'paired_observed_n':len(valid),
                'incident_difficulty_n':sum(a==0 and b==1 for a,b in valid),
                'recovery_n':sum(a==1 and b==0 for a,b in valid),
                'persistent_difficulty_n':sum(a==1 and b==1 for a,b in valid),
                'persistent_no_difficulty_n':sum(a==0 and b==0 for a,b in valid)}
            # Local report only, even when counts are very small.
            transitions.append(summary)
    return {'report_type':'NHATS_LOCAL_REGISTERED_SCHEMA_AND_TRANSITION_AUDIT',
            'status':'CODEBOOK_MAPPED_DESCRIPTIVE_ONLY_NO_PREDICTION',
            'rounds':wave_counts,'transitions':transitions,
            'limitations':['Registered NHATS data; no redistribution or public AI upload.',
                 'Mappings and recodes require independent verification with official codebooks.',
                 'Only observed consecutive provided waves; attrition, competing death and weights not yet handled.',
                 'Not incidence rates, frailty diagnosis, cognitive decline modeling or clinical predictions.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True)
    p.add_argument('--project-dir',default='.')
    p.add_argument('--output',default='artifacts/nhats/wave_audit_v09.json')
    a=p.parse_args(); project=Path(a.project_dir).resolve()
    config=safe_path(project,a.config)
    spec=json.loads(config.read_text())
    frames=[load_table(safe_path(project,w['file'])) for w in check_spec(spec)]
    result=audit_rounds(frames,spec)
    output=(project/a.output).resolve();private=(project/'artifacts'/'nhats').resolve()
    if not output.is_relative_to(private):raise ValueError('NHATS audit must stay in local artifacts/nhats/')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('NHATS LOCAL SUMMARY ONLY:',json.dumps({'waves':len(result['rounds']),
        'transition_domains':len(result['transitions']), 'report':str(output)}))
    print('Never publish NHATS records or this local report or upload NHATS data to public AI systems.')

if __name__=='__main__':main()
