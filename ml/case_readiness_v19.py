"""FrailtyScope v0.19 — read-only, case-independent data/endpoint/missingness gate.

NO fitting, scoring, prediction, sampling for training, model loading or public exports.
Reads an input under ignored data/ and uses ONLY development-cohort outcome values.
The holdout cohort is counted from its split label, never inspected for outcomes.
Missingness reasons MUST come from human-reviewed documentation; associations or
numeric sentinel values cannot identify skip patterns, MAR or MNAR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_DATA_READINESS_V19'
REPORT_SCHEMA = 'FRAILTYSCOPE_LOCAL_READINESS_V19'
KINDS = {'binary_fixed_horizon', 'continuous', 'time_to_event'}
GRAINS = {'one_record_per_person', 'repeated_visits'}
SPLITS = {'cohort', 'grouped', 'time'}
MISSING_STATUSES = {'unverified', 'reviewed_structural', 'reviewed_nonresponse',
                    'reviewed_mixed', 'reviewed_not_applicable'}
SUSPICIOUS_NAME = re.compile(r'(?:^|_)(?:death|mortality|outcome|target|label|followup|event|post_index|future)(?:_|$)', re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def validate_contract(cfg):
    """Pure validation; inspect no filesystem and load no research rows."""
    require(isinstance(cfg, dict) and cfg.get('schema') == SCHEMA, 'Invalid v0.19 case schema')
    case = cfg.get('case_id')
    require(isinstance(case,str) and re.fullmatch(r'[a-z][a-z0-9_]{2,70}',case),
            'Invalid case identifier')
    source = cfg.get('source')
    require(isinstance(source, dict) and isinstance(source.get('path'),str) and source['path'],
            'Missing data source path')
    sha = source.get('expected_sha256')
    require(sha is None or (isinstance(sha,str) and bool(re.fullmatch(r'[0-9a-f]{64}',sha))),
            'Expected SHA256 must be a 64-character lowercase hex digest or null')
    provenance=source.get('provenance')
    if provenance is not None:
        require(isinstance(provenance,dict) and isinstance(provenance.get('column'),str)
                and provenance['column'] and isinstance(provenance.get('value'),str)
                and provenance['value'], 'Source provenance requires column and expected value')
    features = cfg.get('features')
    require(isinstance(features,dict) and isinstance(features.get('numeric'),list)
            and isinstance(features.get('categorical'),list), 'Explicit feature types required')
    names = features['numeric'] + features['categorical']
    require(bool(names) and all(isinstance(n,str) and n and len(n)<=100 for n in names)
            and len(set(names))==len(names), 'Nonempty unique predictors required')
    ident = cfg.get('id_column');target=cfg.get('target')
    require(isinstance(ident,str) and ident and isinstance(target,str) and target
            and target != ident and ident not in names and target not in names,
            'Identifier/target must be distinct from predictors')
    split = cfg.get('split')
    require(isinstance(split,dict) and split.get('design') in SPLITS
            and isinstance(split.get('column'),str) and split['column']
            and split['column'] not in names and split['column'] not in (ident,target),
            'Explicit cohort/group/time split column required')
    require(type(split.get('development')) in (str,int) and type(split.get('holdout')) in (str,int)
            and str(split['development']) != str(split['holdout']), 'Different split values required')
    require(split.get('holdout_status') in ('locked_new','previously_inspected'),
            'Holdout inspection history must be declared')
    outcome = cfg.get('outcome');records = cfg.get('records')
    require(isinstance(outcome,dict) and outcome.get('type') in KINDS
            and isinstance(outcome.get('index_time'),str) and outcome['index_time']
            and isinstance(outcome.get('prediction_horizon'),str) and outcome['prediction_horizon'],
            'Explicit endpoint, index time and horizon required')
    require(isinstance(records,dict) and records.get('grain') in GRAINS,
            'Declare one-row-per-person or repeated visits')
    if outcome['type']=='binary_fixed_horizon':
        require(outcome.get('label_followup_status') in
                ('unverified','complete_horizon_verified','censoring_present'),
                'Declare fixed-horizon label completeness / censoring explicitly')
        proof=outcome.get('followup_evidence_reference','')
        require(isinstance(proof,str) and len(proof)<500,
                'Invalid follow-up verification reference')
        require(outcome['label_followup_status']!='complete_horizon_verified' or proof.strip(),
                'Verified complete follow-up requires supporting evidence')
    if outcome['type']=='time_to_event':
        require(all(isinstance(outcome.get(field),str) and outcome[field] for field in
                    ('duration_column','event_column')), 'Survival requires duration and event columns')
        require(outcome['duration_column'] != outcome['event_column'],
                'Survival duration and event columns cannot coincide')
    if records['grain']=='repeated_visits':
        require(isinstance(records.get('time_column'),str) and records['time_column'],
                'Repeated visits require a visit-time column')
    if split['design']=='grouped':
        require(isinstance(records.get('group_column'),str) and records['group_column'],
                'Grouped split requires a group/site column')
    if split['design']=='time':
        require(isinstance(records.get('time_column'),str) and records['time_column'],
                'Temporal split requires a time column')
    excluded = [split['column'], ident,target, records.get('time_column'),records.get('group_column'),
                outcome.get('duration_column'),outcome.get('event_column')]
    require(not set(names).intersection(e for e in excluded if e),
            'Identifier, outcome, follow-up, site and time columns cannot be predictors')
    post = cfg.get('post_index_columns')
    require(isinstance(post,list) and all(isinstance(z,str) for z in post)
            and len(set(post))==len(post), 'Declare post-index variables (possibly empty list)')
    require(not set(post).intersection(names), 'Post-index variable included in predictors')
    roles = cfg.get('missingness_semantics',{})
    require(isinstance(roles,dict) and set(roles).issubset(names),
            'Missingness semantics must refer only to declared predictors')
    for name,role in roles.items():
        require(isinstance(role,dict) and role.get('status') in MISSING_STATUSES,
                'Invalid missingness semantic status: '+name)
        evidence = role.get('evidence_reference','')
        require(isinstance(evidence,str) and len(evidence)<500, 'Invalid evidence reference')
        require(role['status']=='unverified' or bool(evidence.strip()),
                'Reviewed missingness status requires documentary evidence: '+name)
    constraints=cfg.get('numeric_bounds',{})
    require(isinstance(constraints,dict) and set(constraints).issubset(features['numeric']),
            'Numeric bounds must refer only to numeric predictors')
    for name,pair in constraints.items():
        require(isinstance(pair,list) and len(pair)==2 and
                all(type(v) in (int,float) and math.isfinite(v) for v in pair)
                and pair[0] < pair[1], 'Invalid numeric bounds: '+name)
    count=cfg.get('min_reporting_n',35)
    require(type(count) is int and 20<=count<=200, 'Minimum public-facing group size 20–200')
    flag=cfg.get('post_hoc_development_exploration')
    require(type(flag) is bool, 'Prior development inspection must be acknowledged')
    return cfg


def _safe_read(project, config):
    from ml.case_engine_v10 import safe_local_input,read_local_table,digest
    path=safe_local_input(project, config['source']['path'])
    fingerprint=digest(path)
    expected=config['source'].get('expected_sha256')
    require(expected is None or expected==fingerprint,
            'Source fingerprint changed: do not reuse prior evidence')
    table=read_local_table(path,config)
    require(len(set(table.columns))==len(table.columns), 'Duplicate source columns')
    provenance=config['source'].get('provenance')
    if provenance is not None:
        column=provenance['column']
        require(column in table.columns and table[column].notna().all() and
                set(table[column].astype(str).unique())=={provenance['value']},
                'Source contains missing or unexpected provenance entries')
    return table,fingerprint


def _development_subset(frame,cfg):
    """Select by source cohort ONLY; never access holdout target values."""
    import pandas as pd
    col=cfg['split']['column'];spec=cfg['split']
    required=set(cfg['features']['numeric']+cfg['features']['categorical'])
    required.update([cfg['id_column'],cfg['target'],col])
    if cfg['outcome']['type']=='time_to_event':
        required.update([cfg['outcome']['duration_column'],cfg['outcome']['event_column']])
    if cfg['records'].get('group_column'):required.add(cfg['records']['group_column'])
    if cfg['records'].get('time_column'):required.add(cfg['records']['time_column'])
    require(required.issubset(frame.columns),
            'Required columns absent: '+str(sorted(required-set(frame.columns))))
    cohort=frame[col].astype(str)
    a=cohort.eq(str(spec['development']));b=cohort.eq(str(spec['holdout']))
    require(int(a.sum())>0 and int(b.sum())>0 and (a|b).all(),
            'Unexpected/missing cohort labels: define a clean source before intake')
    # Reader loads the table, but NO holdout target values are analyzed.
    dev=frame.loc[a].copy()
    # checking identity is outcome-independent
    people_holdout=set(frame.loc[b,cfg['id_column']].dropna())
    people_dev=set(dev[cfg['id_column']].dropna())
    duplicate_dev=int(dev[cfg['id_column']].duplicated().sum())
    overlap=len(people_dev.intersection(people_holdout))
    return (dev,{'development_rows':int(a.sum()),'holdout_rows_unscored':int(b.sum()),
                'duplicate_person_rows_in_development':duplicate_dev,
                'person_overlap_between_cohorts':overlap,
                'missing_person_ids_in_development':int(dev[cfg['id_column']].isna().sum())},
            {'holdout_target_values_analyzed':False})


def _numeric_quality(dev,numeric,bounds):
    import numpy as np
    import pandas as pd
    rows=[]
    for c in numeric:
        raw=dev[c]
        as_num=pd.to_numeric(raw,errors='coerce')
        non_numeric=int((raw.notna() & as_num.isna()).sum())
        inf=int((as_num.notna() & ~np.isfinite(as_num.to_numpy(dtype=float))).sum())
        valid=as_num.dropna().to_numpy(dtype=float)
        out_of_range=None
        if c in bounds:
            lo,hi=bounds[c]
            out_of_range=int(((valid<lo)|(valid>hi)).sum())
        rows.append({'feature':c, 'non_numeric_nonmissing':non_numeric,
                     'nonfinite_numeric':inf,'outside_declared_bounds':out_of_range})
    return rows


def _missingness_profile(dev,cfg):
    import numpy as np
    feats=cfg['features']['numeric']+cfg['features']['categorical']
    n=len(dev)
    rows=[]
    for name in feats:
        missed=int(dev[name].isna().sum())
        role=cfg.get('missingness_semantics',{}).get(name,{'status':'unverified'})
        reviewed=role['status']!='unverified'
        rows.append({'feature':name,'n_development':n,'missing_n':missed,
                     'missing_percent':round(100*missed/n,3),
                     'documentation_status':role['status'],
                     'documentary_evidence_present':bool(role.get('evidence_reference','')),
                     'requires_codebook_review':bool(missed and not reviewed)})
    rows.sort(key=lambda x:(-x['missing_n'],x['feature']))
    names=[x['feature'] for x in rows if x['missing_n']>0]
    # Frequencies of missingness patterns are aggregates; suppress small patterns.
    patterns=Counter()
    if names:
        for row in dev[names].isna().itertuples(index=False,name=None):
            patterns[tuple(names[i] for i,flag in enumerate(row) if flag)]+=1
    minimum=cfg['min_reporting_n']
    patterns_out=[{'missing_features':list(key),'n':num}
                  for key,num in patterns.most_common() if num>=minimum][:12]
    suppressed=int(sum(num for key,num in patterns.items() if num<minimum))
    pairs=[]
    for i,left in enumerate(names):
        a=dev[left].isna().to_numpy()
        for right in names[i+1:]:
            b=dev[right].isna().to_numpy();both=int(np.sum(a & b))
            if both < minimum: continue
            union=int(np.sum(a|b))
            pairs.append({'feature_a':left,'feature_b':right,'both_missing_n':both,
                          'missing_union_n':union,
                          'missing_jaccard':round(both/union,4) if union else None})
    pairs.sort(key=lambda x:(-x['both_missing_n'],x['feature_a'],x['feature_b']))
    return rows,patterns_out,suppressed,pairs[:25]


def _dev_endpoint(dev,cfg):
    import numpy as np
    import pandas as pd
    kind=cfg['outcome']['type'];key=cfg['target']
    raw=dev[key]
    observed=int(raw.notna().sum())
    info={'type':kind,'development_target_observed_n':observed,
          'development_target_missing_n':int(len(dev)-observed),
          'holdout_target_examined':False,
          'prediction_horizon':cfg['outcome']['prediction_horizon'],
          'prediction_index_time':cfg['outcome']['index_time']}
    if kind=='binary_fixed_horizon':
        info['label_followup_status']=cfg['outcome']['label_followup_status']
        info['followup_documented']=bool(cfg['outcome'].get('followup_evidence_reference',''))
    if kind in ('binary_fixed_horizon','continuous'):
        target=pd.to_numeric(raw,errors='coerce')
        invalid=int((raw.notna()&target.isna()).sum())
        info['development_target_nonnumeric']=invalid
        if kind=='binary_fixed_horizon':
            info['development_binary_labels_valid']=bool(observed==len(dev) and
                invalid==0 and set(target.unique())=={0,1})
            info['development_event_n']=int((target==1).sum()) if invalid==0 else None
        else:
            info['development_continuous_target_valid']=bool(observed==len(dev) and invalid==0
                and np.isfinite(target.to_numpy(dtype=float)).all())
    else:
        duration=pd.to_numeric(dev[cfg['outcome']['duration_column']],errors='coerce')
        event=pd.to_numeric(dev[cfg['outcome']['event_column']],errors='coerce')
        info['development_duration_valid']=bool(duration.notna().all() and
             np.isfinite(duration.to_numpy(dtype=float)).all() and (duration>=0).all())
        info['development_event_indicator_valid']=bool(event.notna().all() and
             set(event.unique()).issubset({0,1}) and len(set(event.unique()))==2)
        info['censored_event_definition_requires_review']=True
    return info


def routing(cfg,identity,endpoint,quality,missing):
    outcome=cfg['outcome']['type'];records=cfg['records']
    hard=[];review=[]
    if identity['missing_person_ids_in_development']:
        hard.append('Missing development participant identifiers')
    if identity['person_overlap_between_cohorts']:
        hard.append('Same person appears in development and held-out cohort')
    if identity['duplicate_person_rows_in_development']:
        hard.append('Repeated-person rows: ordinary shuffled CV is unsafe')
    if records['grain']=='repeated_visits':
        hard.append('Longitudinal visits require landmark/group/time design')
    if cfg['split']['design']!='cohort':
        hard.append('Grouped/temporal intake recognized but must use design-specific splitter')
    if outcome=='time_to_event':
        hard.append('Censored survival endpoint: ordinary binary/regression runner prohibited')
        if not endpoint.get('development_duration_valid') or not endpoint.get('development_event_indicator_valid'):
            hard.append('Invalid development survival duration or event indicator')
    if outcome=='binary_fixed_horizon' and endpoint.get('label_followup_status')=='censoring_present':
        hard.append('Censoring declared for fixed-horizon binary labels: survival/IPCW design review required')
    if outcome=='binary_fixed_horizon' and endpoint.get('label_followup_status')=='unverified':
        review.append('Fixed-horizon follow-up and censoring not verified from source documentation')
    if outcome=='binary_fixed_horizon' and not endpoint.get('development_binary_labels_valid'):
        hard.append('Development binary endpoint is missing, nonbinary or invalid')
    if outcome=='continuous' and not endpoint.get('development_continuous_target_valid'):
        hard.append('Development continuous endpoint is incomplete or invalid')
    if any(z['non_numeric_nonmissing'] or z['nonfinite_numeric'] for z in quality):
        hard.append('Unparsed or nonfinite predictor measurements')
    if any(z['outside_declared_bounds'] for z in quality if z['outside_declared_bounds'] is not None):
        hard.append('Predictor values outside declared codebook bounds')
    if any(SUSPICIOUS_NAME.search(z) for z in cfg['features']['numeric']+cfg['features']['categorical']):
        hard.append('Suspicious outcome/future predictor name: manual leakage review required')
    for row in missing:
        if row['requires_codebook_review']:
            review.append(row['feature']+' missingness semantics unverified')
    if cfg['split']['holdout_status']=='previously_inspected':
        review.append('Holdout already inspected: no fresh independent validation claim')
    if cfg['post_hoc_development_exploration']:
        review.append('Development data already explored: subsequent comparisons are post hoc')
    if records.get('group_column') and cfg['split']['design']=='cohort':
        review.append('Group/site column declared: verify grouped validation compatibility')
    review.append('Verify all predictors were measurable at the declared prediction index time')
    engine=('SPECIALIZED_SURVIVAL_REQUIRED' if outcome=='time_to_event'
            else 'SPECIALIZED_LONGITUDINAL_REQUIRED' if records['grain']=='repeated_visits'
            else 'SPECIALIZED_SPLITTER_REQUIRED' if cfg['split']['design']!='cohort'
            else 'GENERIC_TABULAR_POSSIBLE')
    return {'status':'BLOCKED_FOR_CURRENT_ENGINE' if hard else
                     ('EXPLORATORY_REVIEW_REQUIRED' if review else 'EXPLORATORY_READY'),
            'suggested_engine':engine,
            'generic_tabular_training_permitted':not hard,
            'holdout_declared_uninspected':cfg['split']['holdout_status']=='locked_new',
            'clinical_deployment_permitted':False,
            'blocking_findings':hard,'review_findings':review}


def audit_table(frame,cfg,sha='test_fixture'):
    """Main pure audit: no model fitting and no holdout outcome access."""
    validate_contract(cfg)
    dev,identity,privacy=_development_subset(frame,cfg)
    numeric=_numeric_quality(dev,cfg['features']['numeric'],cfg.get('numeric_bounds',{}))
    missing,patterns,suppressed,overlap=_missingness_profile(dev,cfg)
    endpoint=_dev_endpoint(dev,cfg)
    routes=routing(cfg,identity,endpoint,numeric,missing)
    return {'schema':REPORT_SCHEMA,'report_type':'LOCAL_DATA_READINESS_NO_MODEL_FITTING',
            'case_id':cfg['case_id'],'config_sha256':canonical_hash(cfg),
            'dataset_sha256':sha,'source':{'format':Path(cfg['source']['path']).suffix.lower()},
            'identity_and_splits':identity,'endpoint_contract':endpoint,
            'numeric_quality':numeric,'missingness':missing,
            'reported_missingness_patterns':patterns,
            'suppressed_small_missingness_patterns_total':suppressed,
            'missingness_pair_overlaps':overlap,
            'route':routes,
            'no_holdout_target_analysis':privacy['holdout_target_values_analyzed'] is False,
            'n_model_fits':0,'n_model_scores':0,
            'public_export':False,'local_only':True,
            'methodology':[
                'Source table is read locally; the holdout split label and person-ID set are used only to detect overlap.',
                'The source file is read as a whole; holdout outcome values are not analyzed, summarized or scored.',
                'Observed/missing associations and co-occurrence do not establish MAR, MNAR or questionnaire skip reasons.',
                'Codebook or instrument review is required before marking structural skip or nonresponse.',
                'One-row-per-person and cohort split are required for generic tabular training.',
                'Time-to-event, repeated visits and group/time splits must use specialized protocols.',
                'This is a readiness audit, not fitted model validation or clinical deployment evidence.'
            ]}


def validate_report(cfg,report):
    require(isinstance(report,dict) and report.get('schema')==REPORT_SCHEMA
            and report.get('report_type')=='LOCAL_DATA_READINESS_NO_MODEL_FITTING'
            and report.get('case_id')==cfg.get('case_id')
            and report.get('config_sha256')==canonical_hash(cfg),
            'Local intake schema or contract mismatch')
    require(report.get('no_holdout_target_analysis') is True and
            report.get('n_model_fits')==0 and report.get('n_model_scores')==0 and
            report.get('public_export') is False and report.get('local_only') is True,
            'Holdout, model or publication boundary violated')
    require(isinstance(report.get('route'),dict)
            and report['route'].get('clinical_deployment_permitted') is False,
            'Readiness report cannot authorize deployment')
    return {'case_id':cfg['case_id'],'status':report['route']['status'],
            'n_development':report['identity_and_splits']['development_rows'],
            'holdout_scored':False,'models_fitted':0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true',help='Read-only dataset audit; do not save')
    mode.add_argument('--audit',action='store_true',help='Read-only dataset audit; save PRIVATE aggregate report')
    p.add_argument('--project',default='.')
    p.add_argument('--config',default='research/cases/nhanes_readiness_v19.json')
    a=p.parse_args();project=Path(a.project).resolve();root=(project/'research').resolve()
    cfg_file=(project/a.config).resolve()
    require(cfg_file.is_relative_to(root) and cfg_file.is_file(),
            'Intake configuration must be inside research/')
    cfg=validate_contract(json.loads(cfg_file.read_text()))
    frame,sha=_safe_read(project,cfg)
    result=audit_table(frame,cfg,sha)
    out=(project/'artifacts'/'cases'/cfg['case_id']/'readiness_v19'/
         canonical_hash(cfg)[:12]/'readiness_audit.json').resolve()
    require(out.is_relative_to((project/'artifacts'/'cases').resolve()),
            'Private report output path escaped artifacts/')
    print('V19 DATA READINESS:',json.dumps({'case_id':cfg['case_id'],
        'source_sha256':sha,
        'development_n':result['identity_and_splits']['development_rows'],
        'holdout_n_not_scored':result['identity_and_splits']['holdout_rows_unscored'],
        'endpoint':result['endpoint_contract']['type'],
        'route':result['route'],
        'highest_missingness':result['missingness'][:6],
        'n_model_fits':0},indent=2))
    if a.audit:
        require(not out.exists(), 'Existing versioned readiness report: refuse overwrite')
        validate_report(cfg,result)
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x') as fh:json.dump(result,fh,indent=2,allow_nan=False);fh.write('\n')
        print('PRIVATE READINESS REPORT:',out)
    else:
        print('PLAN ONLY. No report saved.')
    print('No model fitting, holdout outcome analysis, patient-level export, or GitHub push.')


if __name__=='__main__':main()
