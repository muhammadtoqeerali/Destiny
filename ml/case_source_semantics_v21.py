"""FrailtyScope v0.21 — local NHANES PFQ semantic-encoding *diagnostic*.

--plan audits provenance and creates no model. --run fits only development-fold
models on researcher's workstation. This is post-hoc, not new validation.
Never reads evaluation outcome values, overwrites an existing model, or exports rows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_SOURCE_SEMANTICS_V21'
REPORT_SCHEMA = 'FRAILTYSCOPE_LOCAL_SOURCE_SEMANTICS_V21'
FEATURE_MAP = {'walking_difficulty':'PFQ061B',
               'stairs_difficulty':'PFQ061C',
               'stooping_difficulty':'PFQ061D'}
POLICIES = ('legacy_missing_indicators','source_status_augmented','source_categories')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False).encode()).hexdigest()


def sha_file(path):
    h=hashlib.sha256()
    with path.open('rb') as fd:
        for chunk in iter(lambda:fd.read(1<<20),b''):
            h.update(chunk)
    return h.hexdigest()


def validate_design(cfg, manifest, v16, selected):
    require(isinstance(cfg,dict) and cfg.get('schema')==SCHEMA,'Wrong v0.21 protocol')
    require(cfg.get('case_id')==manifest.get('case_id')==v16.get('case_id'),
            'Case identifier mismatch')
    require(cfg.get('processed_sha256')==selected.get('dataset_sha256') and
            cfg.get('processed_sha256') and len(cfg['processed_sha256'])==64,
            'Processed data fingerprint mismatch')
    require(cfg.get('v16_protocol_sha256')==canonical_sha(v16) and
            selected.get('v16_protocol_sha256')==canonical_sha(v16),
            'Original joint model search no longer matches configuration')
    require(cfg.get('frozen_pair')=='random_forest__missingness_indicators' and
            selected.get('selected_model')=='random_forest' and
            selected.get('selected_preprocessing')=='missingness_indicators' and
            selected.get('final_development_selection',{}).get('selection',{}).get('pair')==cfg['frozen_pair'],
            'Expected frozen v0.16 research recipe')
    require(isinstance(selected.get('selected_parameters'),dict),
            'Missing frozen winner parameters')
    require(cfg.get('methods')==list(POLICIES),'Unexpected feature-representation portfolio')
    require(cfg.get('primary_metric')=='brier' and v16.get('metric')=='brier' and
            manifest.get('task')=='classification','Binary Brier design required')
    require(cfg.get('holdout_policy')=='development_only_no_evaluation' and
            cfg.get('post_hoc_development_reuse') is True and
            selected.get('holdout_scored') is False, 'Holdout boundary must be acknowledged')
    seeds=cfg.get('seeds')
    require(isinstance(seeds,list) and 2<=len(seeds)<=5 and len(set(seeds))==len(seeds)
            and all(type(s) is int and 1<=s<2**31 for s in seeds), 'Invalid repeated fold seeds')
    require(type(cfg.get('folds')) is int and 2<=cfg['folds']<=5,'Unsupported CV folds')
    require(len(seeds)*cfg['folds']*len(POLICIES)<=100,'Excessive diagnostic model budget')
    require(type(cfg.get('expected_development_n')) is int and cfg['expected_development_n']>=50,
            'Missing expected development count')
    require(cfg.get('raw_pfq_sha256') and len(cfg['raw_pfq_sha256'])==64,
            'Expected raw source fingerprint required')
    require(isinstance(cfg.get('raw_file'),str) and cfg['raw_file'],
            'Declare PFQ_G source path or AUTO_PFQ_G discovery with pinned checksum')
    require(isinstance(cfg.get('v20_audit_relative'),str) and cfg['v20_audit_relative'],
            'Pin the completed PFQ reconciliation report')
    names=manifest['features']['numeric'] + manifest['features']['categorical']
    require(all(f in manifest['features']['numeric'] for f in FEATURE_MAP) and
            manifest['target'] not in names and manifest['id_column'] not in names,
            'Unexpected mobility/target columns')
    return cfg


def code_category(value, source, routing):
    """Convert documented questionnaire codes without ordinalizing code 5."""
    import pandas as pd
    if pd.isna(value):
        require(source in ('PFQ061B','PFQ061C') and routing == 1,
                'Unexplained PFQ blank; do not invent a structural skip')
        return 'SKIP_PFQ054'
    v=float(value)
    require(v.is_integer(), 'Noninteger PFQ source response')
    code=int(v)
    if code in (1,2,3,4):
        require(not (source in ('PFQ061B','PFQ061C') and routing==1),
                'PFQ061B/C reported despite documented skip; review source')
        return f'DIFFICULTY_{code}'
    if code==5:
        require(not (source in ('PFQ061B','PFQ061C') and routing==1),
                'PFQ061B/C code 5 reported despite documented skip')
        return 'DO_NOT_DO_ACTIVITY'
    raise ValueError(f'Unreviewed PFQ code {code}: source={source}; stop before fitting')


def source_encode(development, raw):
    """Verified one-to-one raw join. Preserve originals and derive status/category strings."""
    import numpy as np
    import pandas as pd
    required=set(FEATURE_MAP)|{'SEQN'}
    required_raw={'SEQN','PFQ054',*FEATURE_MAP.values()}
    require(required.issubset(development.columns) and required_raw.issubset(raw.columns),
            'Missing processed or PFQ source columns')
    p=development.copy()
    q=raw[['SEQN','PFQ054',*FEATURE_MAP.values()]].copy()
    for tab,label in ((p,'processed'),(q,'raw')):
        ids=pd.to_numeric(tab['SEQN'],errors='coerce')
        require(ids.notna().all() and np.isfinite(ids.to_numpy(dtype=float)).all()
                and (ids%1==0).all() and ids.is_unique,
                f'Invalid or repeated {label} person identifiers')
        tab['SEQN']=ids.astype('int64')
    joined=p.merge(q,on='SEQN',how='left',validate='one_to_one',indicator=True)
    require(joined['_merge'].eq('both').all(),'PFQ source does not cover every development participant')
    routing=pd.to_numeric(joined['PFQ054'],errors='coerce')
    require(routing.isin([1,2]).all(), 'Unverified PFQ054 routing response')
    summary={}
    for feature,source in FEATURE_MAP.items():
        raw_codes=pd.to_numeric(joined[source],errors='coerce')
        statuses=[code_category(val,source,int(route)) for val,route in zip(raw_codes,routing)]
        observed=pd.to_numeric(joined[feature],errors='coerce')
        valid=raw_codes.isin([1,2,3,4])
        require(bool(((observed[valid]==raw_codes[valid]).all())) and
                bool(observed[~valid].isna().all()),
                'Original processed mobility variable disagrees with source')
        label=feature+'_pfq_category'
        joined[label]=pd.Series(statuses,index=joined.index,dtype=object)
        joined[feature+'_pfq_status']=[('REPORTED' if s.startswith('DIFFICULTY_') else s)
                                      for s in statuses]
        counts={k:int(sum(s==k for s in statuses)) for k in
                [*('DIFFICULTY_'+str(i) for i in (1,2,3,4)),
                 'SKIP_PFQ054','DO_NOT_DO_ACTIVITY']}
        require(sum(counts.values())==len(joined),'Incomplete PFQ categorization')
        summary[feature]=counts
    return joined.drop(columns=['_merge','PFQ054',*FEATURE_MAP.values()]),summary


def predictor_spec(manifest, policy):
    require(policy in POLICIES,'Unapproved preprocessing policy')
    numeric=list(manifest['features']['numeric'])
    categoricals=list(manifest['features']['categorical'])
    if policy=='source_status_augmented':
        categoricals.extend([x+'_pfq_status' for x in FEATURE_MAP])
    if policy=='source_categories':
        numeric=[f for f in numeric if f not in FEATURE_MAP]
        categoricals.extend([x+'_pfq_category' for x in FEATURE_MAP])
    return numeric,categoricals


def make_pipeline(manifest, policy, params):
    """Unfitted fold-safe model; numeric missing indicators held constant across arms."""
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder,StandardScaler
    numeric,categorical=predictor_spec(manifest,policy)
    transformers=[]
    if numeric:
        transformers.append(('numeric',Pipeline([
            ('imputer',SimpleImputer(strategy='median',keep_empty_features=True,add_indicator=True)),
            ('scale',StandardScaler())]),numeric))
    if categorical:
        transformers.append(('categorical',Pipeline([
            ('imputer',SimpleImputer(strategy='most_frequent')),
            ('onehot',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical))
    approved={'n_estimators','max_depth','min_samples_leaf'}
    require(set(params)==approved and all(type(v) is int and v>0 for v in params.values()),
            'Unexpected RF hyperparameters; frozen study only')
    return Pipeline([
        ('features',ColumnTransformer(transformers,remainder='drop',sparse_threshold=0)),
        ('model',RandomForestClassifier(**params,random_state=2026,n_jobs=2))
    ])


def paired_summary(entries):
    require(entries and all(set(x)==set(POLICIES) for x in entries),
            'Unpaired repeated scores')
    values={}
    for name in POLICIES:
        series=[float(x[name]) for x in entries]
        require(all(math.isfinite(z) for z in series),'Nonfinite score')
        values[name]=round(sum(series)/len(series),7)
    base=values[POLICIES[0]]
    return {'repeated_cv_mean_brier':values,
            'brier_gain_vs_legacy':{name:round(base-val,7) for name,val in values.items()},
            'repeats':len(entries),
            'note':'Paired repeated development folds on previously examined participants; descriptive, not external validation'}


def _local_file(project,relative,base):
    require(isinstance(relative,str) and relative,'Missing local file path')
    path=(project/relative).resolve()
    require(path.is_relative_to((project/base).resolve()) and path.is_file(),
            f'Expected file inside {base}/: {relative}')
    return path


def _read_development_only(processed,manifest):
    """Select cohort BEFORE reading any target cell. Streaming CSV skips other cohorts."""
    import pandas as pd
    split=manifest['split']
    require(split['strategy']=='cohort','Development-only cohort contract expected')
    selected=[manifest['id_column'], *manifest['features']['numeric'],
              *manifest['features']['categorical'], manifest['target']]
    cols=set(selected+[split['column']])
    records=[];excluded=0
    with processed.open('r',newline='',encoding='utf-8-sig') as f:
        reader=csv.reader(f)
        columns=next(reader,None)
        require(columns and len(set(columns))==len(columns) and cols.issubset(columns),
                'Missing or duplicate processed source fields')
        location={name:index for index,name in enumerate(columns)}
        split_index=location[split['column']]
        for row in reader:
            require(len(row)==len(columns),'Malformed processed source CSV record')
            if row[split_index]==str(split['development']):
                records.append({col:row[location[col]] for col in selected})
            elif row[split_index]==str(split['evaluation']):
                excluded+=1  # Never index the held-out target field.
            else:
                raise ValueError('Unexpected cohort label')
    require(excluded>0 and records,'Development/holdout partition missing')
    frame=pd.DataFrame.from_records(records)
    for name in manifest['features']['numeric'] + [manifest['target'],manifest['id_column']]:
        frame[name]=pd.to_numeric(frame[name].replace('',float('nan')),errors='coerce')
    for name in manifest['features']['categorical']:
        frame[name]=frame[name].replace('',float('nan')).astype(object)
    require(frame[manifest['id_column']].notna().all() and frame[manifest['id_column']].is_unique,
            'Missing or duplicated development IDs')
    target=frame[manifest['target']]
    require(target.notna().all() and set(target.unique())=={0,1},'Invalid development binary labels')
    return frame,excluded


def load_context(project,config_path):
    from ml.case_joint_selection_v16 import validate_local_release
    from ml.case_engine_v10 import validate_manifest
    import pandas as pd
    project=project.resolve()
    cfg_path=config_path.resolve()
    require(cfg_path.is_relative_to((project/'research').resolve()) and cfg_path.is_file(),
            'Configuration must be inside research/')
    cfg=json.loads(cfg_path.read_text())
    manifest=validate_manifest(json.loads(_local_file(project,cfg['case_manifest'],'research').read_text()))
    v16=json.loads(_local_file(project,cfg['v16_protocol'],'research').read_text())
    selected_path=_local_file(project,cfg['v16_local_report'],'artifacts')
    selected=json.loads(selected_path.read_text())
    require(selected_path.name=='joint_selection.json','Unexpected v0.16 selection file')
    validate_local_release(v16,selected,_local_file(project,cfg['v16_model'],'artifacts').is_file())
    validate_design(cfg,manifest,v16,selected)
    expected_v20=_local_file(project,cfg['v20_audit_relative'],'artifacts')
    report=json.loads(expected_v20.read_text())
    require(report.get('schema')=='FRAILTYSCOPE_LOCAL_PFQ_SKIP_AUDIT_V20' and
            report.get('case_id')==cfg['case_id'] and
            report.get('dataset_sha256')==cfg['processed_sha256'] and
            report.get('raw_pfq_sha256')==cfg['raw_pfq_sha256'] and
            report.get('holdout_labels_read') is False and report.get('model_fits')==0,
            'v0.20 audit provenance does not match')
    require(report.get('linked_n')==cfg['expected_development_n'] and
            report.get('unmatched_development_n')==0 and
            report.get('PFQ054_yes_in_linked_n')==279,
            'Unexpected PFQ reconciliation counts; review before fitting')
    if cfg['raw_file']=='AUTO_PFQ_G':
        base=(project/'data').resolve()
        candidates=[f for f in base.rglob('*') if f.is_file() and
                    f.stem.upper()=='PFQ_G' and f.suffix.lower() in
                    ('.xpt','.sas7bdat','.csv','.parquet')]
        require(len(candidates)==1,
                'Expected exactly one local PFQ_G file under data/; declare raw_file explicitly otherwise')
        raw=candidates[0].resolve()
    else:
        raw=_local_file(project,cfg['raw_file'],'data')
    processed=_local_file(project,manifest['source']['path'],'data')
    require(sha_file(raw)==cfg['raw_pfq_sha256'] and
            sha_file(processed)==cfg['processed_sha256'],'Changed PFQ or processed source bytes')
    frame,holdout_n=_read_development_only(processed,manifest)
    require(len(frame)==cfg['expected_development_n'],'Development cohort size drift')
    suffix=raw.suffix.lower()
    require(raw.stem.upper()=='PFQ_G' and suffix in ('.xpt','.csv','.parquet','.sas7bdat'),
            'Unexpected PFQ source file')
    if suffix=='.xpt': questionnaire=pd.read_sas(raw,format='xport')
    elif suffix=='.sas7bdat': questionnaire=pd.read_sas(raw,format='sas7bdat')
    elif suffix=='.parquet': questionnaire=pd.read_parquet(raw)
    else: questionnaire=pd.read_csv(raw,low_memory=False)
    frame,counts=source_encode(frame,questionnaire)
    require(counts['walking_difficulty']['SKIP_PFQ054']==279 and
            counts['walking_difficulty']['DO_NOT_DO_ACTIVITY']==24 and
            counts['stairs_difficulty']['SKIP_PFQ054']==279 and
            counts['stairs_difficulty']['DO_NOT_DO_ACTIVITY']==13 and
            counts['stooping_difficulty']['DO_NOT_DO_ACTIVITY']==35,
            'PFQ source categorization disagrees with verified reconciliation')
    return cfg,manifest,selected,frame,counts,holdout_n


def run(context):
    import numpy as np
    from sklearn.metrics import brier_score_loss,roc_auc_score,average_precision_score,log_loss
    from ml.case_strategy_v13 import fold_indices
    cfg,manifest,selected,frame,counts,holdout_n=context
    yy=frame[manifest['target']].astype(int).reset_index(drop=True)
    x=frame.drop(columns=[manifest['target'],manifest['id_column']]).reset_index(drop=True)
    params=selected['selected_parameters']
    all_repeats=[];comparison=[]
    for seed in cfg['seeds']:
        folds=list(fold_indices(yy,cfg['folds'],seed,'classification'))
        oof={name:np.full(len(yy),np.nan) for name in POLICIES}
        for i,(tr,va) in enumerate(folds,1):
            for name in POLICIES:
                numeric,categorical=predictor_spec(manifest,name)
                cols=numeric+categorical
                mdl=make_pipeline(manifest,name,params)
                mdl.fit(x.iloc[tr][cols],yy.iloc[tr])
                oof[name][va]=mdl.predict_proba(x.iloc[va][cols])[:,1]
            print(f'PFQ SEMANTICS DEV seed={seed} fold={i}/{len(folds)} complete',flush=True)
        details={}
        for name,scores in oof.items():
            require(np.isfinite(scores).all() and ((scores>=0)&(scores<=1)).all(),
                    'Incomplete out-of-fold probabilities')
            details[name]={'brier':round(float(brier_score_loss(yy,scores)),7),
                           'roc_auc':round(float(roc_auc_score(yy,scores)),6),
                           'average_precision':round(float(average_precision_score(yy,scores)),6),
                           'log_loss':round(float(log_loss(yy,scores,labels=[0,1])),7)}
        comparison.append({name:details[name]['brier'] for name in POLICIES})
        all_repeats.append({'seed':seed,'metrics':details})
        print('PFQ SEMANTICS DEVELOPMENT REPEAT:',seed,
              {name:details[name]['brier'] for name in POLICIES},flush=True)
    result={'schema':REPORT_SCHEMA,'report_type':'LOCAL_DEVELOPMENT_PFQ_ENCODING_DIAGNOSTIC',
            'case_id':cfg['case_id'],'config_sha256':canonical_sha(cfg),
            'processed_sha256':cfg['processed_sha256'], 'raw_pfq_sha256':cfg['raw_pfq_sha256'],
            'frozen_model':'random_forest','frozen_model_parameters':params,
            'n_development':int(len(yy)),'n_holdout_unscored':holdout_n,
            'source_category_counts':counts,'repeated_development_metrics':all_repeats,
            'comparison':paired_summary(comparison),
            'holdout_outcomes_accessed':False,'model_overwritten':False,
            'model_binary_exported':False,'public_export':False,'new_threshold_selected':False,
            'limitations':['Development participants informed earlier encoding and model choices; not independent confirmation.',
              'Frozen Random Forest comparison isolates feature representation, not whole-family nested search.',
              'Repeated CV folds overlap on the same people; descriptive differences are not inferential confidence intervals.',
              'Code 5 is nonperformance of activity, not an ordered disability severity value.',
              'Structural skip is verified for PFQ061B/C only, not PFQ061D.',
              'Other NHANES waves and HUNT instruments require separate source codebook review.',
              'No later-cycle outcome or clinical deployment evidence collected.']}
    return result


def validate_report(cfg,result):
    require(result.get('schema')==REPORT_SCHEMA and
            result.get('report_type')=='LOCAL_DEVELOPMENT_PFQ_ENCODING_DIAGNOSTIC' and
            result.get('case_id')==cfg['case_id'] and
            result.get('config_sha256')==canonical_sha(cfg),
            'Unexpected source encoding report')
    require(result.get('holdout_outcomes_accessed') is False and
            result.get('model_overwritten') is False and
            result.get('model_binary_exported') is False and
            result.get('public_export') is False and
            result.get('new_threshold_selected') is False,
            'Source encoding privacy/holdout contract failed')
    require(len(result.get('repeated_development_metrics',[]))==len(cfg['seeds']),
            'Unexpected diagnostic repeat count')
    require(result.get('n_development')==cfg['expected_development_n'],
            'Unexpected development size')
    return {'case_id':cfg['case_id'],'repeats':len(cfg['seeds']),
            'holdout_scored':False,'model_replaced':False}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    mode=cli.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true')
    mode.add_argument('--run',action='store_true')
    cli.add_argument('--project',default='.')
    cli.add_argument('--config',default='research/cases/nhanes_source_semantics_v21.json')
    args=cli.parse_args()
    project=Path(args.project).resolve()
    cfg=json.loads(_local_file(project,args.config,'research').read_text())
    # Discovery without fitted models. Raw file path can be set by research config.
    if args.plan:
        from ml.case_engine_v10 import validate_manifest
        manifest=validate_manifest(json.loads(_local_file(project,cfg['case_manifest'],'research').read_text()))
        v16=json.loads(_local_file(project,cfg['v16_protocol'],'research').read_text())
        selected=json.loads(_local_file(project,cfg['v16_local_report'],'artifacts').read_text())
        validate_design(cfg,manifest,v16,selected)
        report=json.loads(_local_file(project,cfg['v20_audit_relative'],'artifacts').read_text())
        require(report.get('schema')=='FRAILTYSCOPE_LOCAL_PFQ_SKIP_AUDIT_V20'
                and report.get('raw_pfq_sha256')==cfg['raw_pfq_sha256'],
                'Missing expected PFQ v0.20 provenance')
        print('V21 PLAN:',json.dumps({'case_id':cfg['case_id'],'frozen_recipe':cfg['frozen_pair'],
                'methods':cfg['methods'],'repeats':len(cfg['seeds']),
                'folds_per_repeat':cfg['folds'],
                'estimated_diagnostic_fits':len(cfg['methods'])*len(cfg['seeds'])*cfg['folds'],
                'source_sha_pinned':True,'holdout_scored':False,'model_fitting':False},indent=2))
        return
    context=load_context(project,(project/args.config).resolve())
    cfg,manifest,selected,frame,counts,holdout_n=context
    report=run(context)
    validate_report(cfg,report)
    output=(project/'artifacts'/'cases'/cfg['case_id']/'source_semantics_v21'/
            canonical_sha(cfg)[:12]/'encoding_diagnostic.json').resolve()
    require(output.is_relative_to((project/'artifacts').resolve()),'Output path outside private artifacts')
    require(not output.exists(),'Existing v0.21 audit: refuse overwrite')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as fd:
        json.dump(report,fd,indent=2,allow_nan=False);fd.write('\n')
    print('LOCAL DEVELOPMENT SEMANTIC ENCODING:',output)
    print('PAIRED COMPARISON:',json.dumps(report['comparison'],indent=2))
    print('No participant rows, prediction vectors, holdout scores, or model binary exported.')

if __name__=='__main__':main()
