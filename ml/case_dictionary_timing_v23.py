"""FrailtyScope v0.23: source-only feature dictionary and prediction-index gate.

Never loads CSV/XPT/person records, outcomes, trained models or predictions. --audit
reads only the already saved PRIVATE v0.22 metadata ledger and writes one immutable
private summary. A documentary gate is NOT permission to run a clinical model.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 'FRAILTYSCOPE_FEATURE_TIMING_PROTOCOL_V23'
REPORT_SCHEMA = 'FRAILTYSCOPE_PRIVATE_FEATURE_TIMING_V23'
PHASES = {'household_interview', 'mec_private_interview', 'mec_examination',
          'derived_multiple_sources', 'clinical_record', 'register_linkage',
          'wearable', 'unknown', 'other'}
AVAILABILITY = {'verified_at_or_before_index', 'pending_index_review',
                'known_after_index', 'unavailable_at_inference', 'unknown'}
KINDS = {'numeric', 'ordinal', 'binary', 'categorical', 'derived_numeric'}
DANGEROUS_SOURCE_COLUMNS = {'seqn','patient_id','person_id','outcome_5yr',
                            'mortstat','permth_exm','permth_int','eligstat',
                            'duration','event','death_date'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',', ':'),
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def local_path(root:Path, name:str, folder:str)->Path:
    require(isinstance(name,str) and name and '\\' not in name,
            'Expected safe relative path')
    p=Path(name)
    require(not p.is_absolute() and '..' not in p.parts and p.parts[0]==folder,
            'File must be a relative path under '+folder+'/')
    target=(root/name).resolve()
    require(target.is_relative_to((root/folder).resolve()) and target.is_file(),
            'Expected existing source file under '+folder+'/')
    return target


def evidence_ref(ref:str):
    require(isinstance(ref,str) and 10<=len(ref)<=500 and '\n' not in ref and '\r' not in ref,
            'Evidence reference must be a short one-line path or HTTPS URL')
    if ref.startswith('https://'):
        require(not any(x in ref.lower() for x in ('@','localhost','127.0.0.1')),
                'Unsafe evidence URL')
        return
    p=Path(ref)
    require(not p.is_absolute() and '..' not in p.parts and len(p.parts)>=2 and
            p.parts[0] in ('ml','research','tests','scripts') and '\\' not in ref,
            'Evidence must be source code or HTTPS documentation, never raw data')


def validate_protocol(cfg:dict, manifest:dict, prior:dict)->dict:
    require(isinstance(cfg,dict) and cfg.get('schema')==SCHEMA,'Incorrect v0.23 protocol schema')
    require(cfg.get('case_id')==manifest.get('case_id')==prior.get('case_id'),
            'Mismatch with existing case identity')
    require(prior.get('holdout_history')==cfg.get('holdout_history') and
            prior.get('prior_exploration')==cfg.get('prior_exploration'),
            'Do not reset previously inspected holdout/development reuse')
    require(cfg.get('holdout_history') in ('previously_inspected','locked_new','not_applicable')
            and type(cfg.get('prior_exploration')) is bool,'Invalid validation boundary')
    require(cfg.get('allow_model_fitting') is False and
            cfg.get('allow_heldout_scoring') is False and
            cfg.get('allow_clinical_inference') is False,
            'A documentary feature audit cannot authorize fitting, scoring, or clinical use')
    require(cfg.get('case_manifest')=='research/cases/nhanes_mortality_v10.json' or
            isinstance(cfg.get('case_manifest'),str), 'Missing case manifest reference')
    anchor=cfg.get('prediction_index')
    require(isinstance(anchor,dict) and
            anchor.get('definition_status') in ('provisional','operationally_verified'),
            'Prediction index requires explicit evidence status')
    require(isinstance(anchor.get('event'),str) and len(anchor['event'])>=12 and
            isinstance(anchor.get('population'),str) and len(anchor['population'])>=8,
            'Index event and intended prediction population required')
    refs=anchor.get('evidence',[])
    require(isinstance(refs,list) and len(refs)>0 and len(refs)<=6,
            'Index source/documentary evidence required')
    for ref in refs:evidence_ref(ref)
    require(anchor.get('approved_by_study_team') in (True,False) and
            type(anchor['approved_by_study_team']) is bool,
            'Study team index signoff must be explicit')
    if anchor['definition_status']=='operationally_verified':
        require(anchor['approved_by_study_team'] is True,
                'Index cannot be verified without study-team signoff')
    features=manifest.get('features',{})
    expected=features.get('numeric',[])+features.get('categorical',[])
    require(expected and len(set(expected))==len(expected),'Duplicate/empty manifest features')
    specs=cfg.get('predictors')
    require(isinstance(specs,dict) and set(specs)==set(expected),
            'Dictionary must cover EXACTLY all predictors (no silent omissions)')
    names={manifest.get('id_column'),manifest.get('target')}
    require(not names.intersection(specs),'Identifiers/target cannot be predictors')
    for field,spec in specs.items():
        require(isinstance(spec,dict),'Invalid predictor spec: '+field)
        require(spec.get('kind') in KINDS, 'Missing or unrecognized type: '+field)
        require(spec.get('measurement_phase') in PHASES,
                'Unknown measurement source/phase: '+field)
        require(spec.get('availability_status') in AVAILABILITY,
                'Missing temporal availability classification: '+field)
        require(isinstance(spec.get('source_file'),str) and
                re.fullmatch(r'[A-Za-z0-9_.-]{3,70}',spec['source_file']),
                'Use simple descriptive source file name: '+field)
        raw=spec.get('source_variables')
        require(isinstance(raw,list) and len(raw)>0 and len(raw)<=30 and
                len(set(raw))==len(raw) and all(isinstance(x,str) and
                re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{1,40}',x) for x in raw),
                'Source variable names required: '+field)
        require(not any(x.casefold() in DANGEROUS_SOURCE_COLUMNS for x in raw),
                'Outcome, leakage, or ID source variable listed as predictor: '+field)
        require(isinstance(spec.get('units'),str) and spec['units'] and
                len(spec['units'])<65, 'Units/status required: '+field)
        require(isinstance(spec.get('transformation'),str) and
                len(spec['transformation'])>=8 and len(spec['transformation'])<=320,
                'Document derived value and recoding: '+field)
        require(isinstance(spec.get('missing_semantics'),str) and
                8<=len(spec['missing_semantics'])<=340,
                'Explicit missingness semantics needed: '+field)
        require(isinstance(spec.get('timing_rationale'),str) and
                8<=len(spec['timing_rationale'])<=350,
                'Why feature is or is not available at index: '+field)
        docs=spec.get('evidence')
        require(isinstance(docs,list) and 1<=len(docs)<=5 and len(docs)==len(set(docs)),
                'Codebook/reference required: '+field)
        for ref in docs:evidence_ref(ref)
        if spec['availability_status']=='verified_at_or_before_index':
            require(anchor['definition_status']=='operationally_verified' and
                    anchor['approved_by_study_team'] is True,
                    'No feature may be certified before the index is independently approved')
            require(spec.get('source_timing_verified_by_study_team') is True,
                    'Verified timing requires separate per-predictor review')
        else:
            require(spec.get('source_timing_verified_by_study_team') is False,
                    'Pending/unsafe predictor cannot have verified flag')
    return cfg


def make_plan(cfg:dict)->dict:
    status=Counter(row['availability_status'] for row in cfg['predictors'].values())
    groups={state:sorted(k for k,v in cfg['predictors'].items()
                         if v['availability_status']==state)
            for state in sorted(AVAILABILITY)}
    problematic=sorted([key for key,value in cfg['predictors'].items()
                        if value['availability_status']!='verified_at_or_before_index'])
    blocked=bool(problematic or cfg['prediction_index']['definition_status']!='operationally_verified')
    blocked=blocked or cfg['holdout_history']=='previously_inspected'
    return {
        'schema':REPORT_SCHEMA,'case_id':cfg['case_id'],
        'protocol_sha256':digest(cfg),'prediction_index':cfg['prediction_index']['event'],
        'index_status':cfg['prediction_index']['definition_status'],
        'features_total':len(cfg['predictors']),'availability_counts':dict(sorted(status.items())),
        'feature_groups':groups,'unresolved_predictors':problematic,
        'holdout_history':cfg['holdout_history'], 'prior_exploration':cfg['prior_exploration'],
        'route':'BLOCKED_FOR_PREDICTION_PROTOCOL_REVIEW' if blocked else 'DOCUMENTARY_REVIEW_ONLY',
        'review_actions':[
            'Confirm prediction timestamp and prediction setting with study team',
            'For each predictor, verify collection vs exam/index time, source module, and inferential availability',
            'Confirm original source codes, skip routing, units and derived transforms',
            'Review outcome-derived proxies, target leakage and repeated-visit grouping',
            'Preserve previously inspected holdout history; do not convert this to independent validation'
        ],
        'no_data_rows_opened':True,'no_models_fitted':True,'no_predictions_generated':True,
        'no_holdout_targets_accessed':True,'clinical_use_permitted':False,'public_export':False,
        'limitations':[
            'Codebook collection phase does not establish the exact availability time at deployment.',
            'Documentary index/predictor review is not a data integrity or patient-level chronology audit.',
            'Previously inspected NHANES later wave is not a pristine evaluation set.',
            'A future clinical or HUNT case must independently define its index, rights, predictor sources and validation.'
        ]}


def verify_prior_ledger(cfg, root:Path, prior:dict)->dict:
    rel=cfg.get('related_private_v22_ledger')
    path=local_path(root,rel,'artifacts')
    require(path.suffix=='.json' and path.stat().st_size<250_000,'Unsafe aggregate report')
    obj=json.loads(path.read_text())
    from ml.case_governance_v22 import validate_ledger
    result=validate_ledger(prior,obj)
    require(obj.get('case_id')==cfg['case_id'] and obj.get('public_export') is False
            and obj.get('no_models_fitted') is True and
            obj.get('no_holdout_outcomes_analyzed') is True,
            'v0.22 ledger cannot support this source-only review')
    require(result['controls']==33,'Wrong prior evidence checklist')
    return {'source':'v22_private_metadata_only','prior_route':obj['route'],
            'ledger_metadata_valid':True,'n_prior_checks':len(obj.get('local_evidence_checks',[]))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    selection=parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--plan',action='store_true')
    selection.add_argument('--audit',action='store_true')
    parser.add_argument('--project',default='.')
    parser.add_argument('--config',default='research/cases/nhanes_dictionary_timing_v23.json')
    args=parser.parse_args()
    root=Path(args.project).resolve()
    conf=local_path(root,args.config,'research')
    cfg=json.loads(conf.read_text())
    manifest=json.loads(local_path(root,cfg['case_manifest'],'research').read_text())
    prior=json.loads(local_path(root,cfg['related_v22_protocol'],'research').read_text())
    from ml.case_governance_v22 import validate_protocol as validate_v22
    validate_v22(prior)
    validate_protocol(cfg,manifest,prior)
    report=make_plan(cfg)
    if args.audit:
        report['previous_private_ledger_metadata']=verify_prior_ledger(cfg,root,prior)
    else:
        report['previous_private_ledger_metadata']=None
    print('V23 SOURCE DICTIONARY AND INDEX PLAN:',json.dumps({
          key:report[key] for key in ('case_id','route','prediction_index','index_status',
                                     'features_total','availability_counts',
                                     'unresolved_predictors','holdout_history')},indent=2))
    if args.audit:
        target=(root/'artifacts/cases'/cfg['case_id']/'field_timing_v23'/
                digest(cfg)[:12]/'dictionary_timing_audit.json').resolve()
        require(target.is_relative_to((root/'artifacts/cases').resolve()),
                'Unsafe report output')
        require(not target.exists(), 'Immutable private v0.23 report exists; refuse overwrite')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False)
        print('PRIVATE SOURCE-ONLY TIMING LEDGER:',target)
    else:print('PLAN ONLY. No private reports or data opened; nothing written.')
    print('No participant records, models, labels or predictions loaded or exported.')

if __name__=='__main__':main()
