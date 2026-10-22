"""FrailtyScope v0.25: synthetic-only, contract-controlled, fold-safe preprocessing.

Source-level v0.24 mapping is a separate operation. This release never loads
participant datasets or fits genuine research models. The in-memory builder
accepts only explicitly designated synthetic fixtures; sklearn cloning works
within pipelines and CV. Future authorized adapters need their own review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from sklearn.base import BaseEstimator, TransformerMixin

SCHEMA = 'FRAILTYSCOPE_FOLDSAFE_PROTOCOL_V25'
REPORT_SCHEMA = 'FRAILTYSCOPE_PRIVATE_FOLDSAFE_PLAN_V25'
FORBIDDEN = {'seqn', 'person_id', 'patient_id', 'id', 'target', 'label',
             'outcome', 'outcome_5yr', 'mortstat', 'permth_exm', 'permth_int',
             'eligstat', 'duration', 'event', 'death_date', 'cycle', 'survey_weight'}
ALLOWED_KINDS = {'numeric', 'ordinal', 'binary', 'categorical'}
ALLOWED_STATUS = {'observed','refused','unknown','not_applicable',
                  'does_not_do_activity','not_recorded','structural_skip',
                  'not_measured','below_detection'}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def local_file(project, relative, folder):
    require(isinstance(relative,str) and relative and '\\' not in relative,
            'Missing/unsafe relative path')
    path=Path(relative)
    require(not path.is_absolute() and '..' not in path.parts and
            len(path.parts)>=2 and path.parts[0]==folder,
            'File must be under '+folder+'/')
    resolved=(project/path).resolve()
    require(resolved.is_relative_to((project/folder).resolve()) and resolved.is_file(),
            'Required source or aggregate metadata file unavailable')
    return resolved


def validate_recipe(recipe, dictionary, harmonization):
    require(isinstance(recipe,dict) and recipe.get('schema')==SCHEMA,
            'Unrecognized preprocessing protocol')
    require(recipe.get('case_id')==dictionary.get('case_id')==harmonization.get('case_id'),
            'Case identifiers differ')
    require(recipe.get('holdout_history')==dictionary.get('holdout_history')==harmonization.get('holdout_history')
            and recipe.get('prior_exploration')==dictionary.get('prior_exploration')==harmonization.get('prior_exploration'),
            'Holdout or exploration history cannot be reset')
    require(recipe.get('prediction_index_status')==dictionary['prediction_index']['definition_status']
            ==harmonization['prediction_index_status'], 'Prediction index history changed')
    require(recipe.get('scope')=='synthetic_only_blueprint' and
            recipe.get('real_data_execution_permitted') is False and
            recipe.get('model_fitting_permitted') is False and
            recipe.get('holdout_scoring_permitted') is False and
            recipe.get('clinical_use_permitted') is False and
            recipe.get('public_export_permitted') is False,
            'Blueprint cannot grant real-data or clinical permission')
    require(recipe.get('related_v24_protocol') and recipe.get('related_v23_protocol'),
            'Prior contracts required')
    require(recipe.get('numeric_missing')=='median' and recipe.get('numeric_all_missing')=='error'
            and recipe.get('numeric_scale') in ('standard','robust','none')
            and recipe.get('numeric_indicators') is True,
            'Unsupported numeric policy')
    require(recipe.get('categorical_missing') in ('constant','most_frequent') and
            recipe.get('categorical_unknown') in ('error','ignore'),
            'Unsupported categorical policy')
    require(recipe.get('status_unknown')=='error', 'Missing-status semantics must fail closed')
    require(recipe.get('split_review') in ('person_disjoint','forward_time','person_and_forward_time'),
            'Explicit split strategy required')
    specs=recipe.get('features')
    require(isinstance(specs,dict) and specs,'Declare at least one feature')
    covered={name for wave in harmonization['waves'].values() for name in wave['features']}
    require(set(specs)==covered and not set(specs).intersection(FORBIDDEN),
            'Features must match exactly the covered v0.24 harmonization subset')
    for name,item in specs.items():
        require(isinstance(name,str) and re.fullmatch(r'[a-z][a-z0-9_]{1,64}',name)
                and name.casefold() not in FORBIDDEN and '__' not in name,
                'Unsafe feature name')
        require(isinstance(item,dict) and item.get('kind') in ALLOWED_KINDS
                and item.get('representation') in ('numeric','one_hot'),
                'Unrecognized feature type or representation: '+name)
        require((item['kind']=='numeric' and item['representation']=='numeric') or
                (item['kind']=='categorical' and item['representation']=='one_hot') or
                item['kind'] in ('ordinal','binary'),
                'Invalid representation for '+name)
        mapped=[w['features'][name] for w in harmonization['waves'].values()
                if name in w['features']]
        require(all(rule['kind']==item['kind'] for rule in mapped),
                'Feature kind differs from source contract')
        status=item.get('allowed_statuses')
        require(isinstance(status,list) and 'observed' in status and
                len(status)==len(set(status)) and set(status)<=ALLOWED_STATUS,
                'Explicit source-status vocabulary required')
        fixed=item.get('allowed_values')
        if fixed is not None:
            require(isinstance(fixed,list) and fixed and len(fixed)==len(set(map(str,fixed)))
                    and all(type(x) in (int,float,str) and str(x)!='__MISSING__' for x in fixed),
                    'Invalid fixed codebook categories')
        if item['representation']=='one_hot':
            require(fixed is not None or recipe['categorical_unknown']=='error',
                    'Unknown-category policy needs an explicit strategy')
        require(item.get('source_status_required') is True,
                'Never silently discard source missingness status')
        for rule in mapped:
            observed_status={'observed',rule.get('blank_status')}
            observed_status.update(rule.get('missing_codes',{}).values())
            require((observed_status-{None}) <= set(status),
                    'Unrepresented v0.24 response status: '+name)
            if fixed is not None and rule['kind']!='numeric':
                require(set(map(str,rule.get('value_codes',{}).values()))<=set(map(str,fixed)),
                        'Codebook output categories are not covered: '+name)
    return recipe


def expected_columns(recipe):
    return [col for name in recipe['features'] for col in (name,name+'__status')]


def _coerce_frame(frame,recipe):
    """Pure input contract; returns a fresh normalized DataFrame, no statistics learned."""
    import numpy as np
    import pandas as pd
    require(isinstance(frame,pd.DataFrame) and frame.columns.is_unique,
            'Require unique DataFrame columns')
    columns=expected_columns(recipe)
    require(len(frame)>0 and set(frame.columns)==set(columns),
            'Expected only canonical predictor and source-status columns (no ID/label)')
    clean=pd.DataFrame(index=frame.index)
    for name,spec in recipe['features'].items():
        statuses=frame[name+'__status']
        require(statuses.notna().all() and
                all(type(x) is str and x in spec['allowed_statuses'] for x in statuses),
                'Missing or undeclared source status: '+name)
        raw=frame[name]
        observed=statuses.eq('observed')
        require(bool(raw.notna().eq(observed).all()),
                'Observed/missing values disagree with source statuses: '+name)
        if spec['representation']=='numeric':
            require(all(type(x) in (int,float,np.int64,np.int32,np.float64,np.float32)
                        and not isinstance(x,bool) for x in raw[observed]),
                    'Numeric representation requires numeric values: '+name)
            num=pd.to_numeric(raw,errors='coerce')
            require(bool(np.isfinite(num[observed].to_numpy(dtype=float)).all()),
                    'Non-finite numeric predictor: '+name)
            clean[name]=num.astype(float)
        else:
            for val in raw[observed]:
                require(type(val) in (str,int,float,np.int32,np.int64,np.float32,np.float64)
                        and not isinstance(val,bool),
                        'Non-scalar or unsupported category: '+name)
            from ml.case_harmonization_v24 import canonical_code
            codes=raw.astype(object).map(lambda x: canonical_code(x) if pd.notna(x) else None)
            fixed=spec.get('allowed_values')
            if fixed is not None:
                allowed={canonical_code(x) for x in fixed}
                require(set(codes[observed])<=allowed,
                        'Unreviewed codebook category: '+name)
            clean[name]=codes.where(codes.notna(),float('nan'))
        clean[name+'__status']=statuses.astype(str)
    return clean.loc[:,columns]


class ContractFrameValidator(BaseEstimator, TransformerMixin):
    """sklearn-compatible transformer. Fitting does not inspect labels."""
    def __init__(self, recipe):
        self.recipe=recipe

    def fit(self, X, y=None):
        data=self.transform(X)
        for name,spec in self.recipe['features'].items():
            if spec['representation']=='numeric':
                require(data[name].notna().any(),'All-missing training feature: '+name)
            else:
                require(data[name].notna().any(),'All-missing training category: '+name)
        return self

    def transform(self, X):
        return _coerce_frame(X,self.recipe)


def build_preprocessor(recipe, *, synthetic_fixture=False):
    """UNFITTED sklearn Pipeline. Its caller must split first, then fit train only."""
    require(synthetic_fixture is True,'Real-data preprocessing not authorized by v0.25')
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer, MissingIndicator
    from sklearn.preprocessing import OneHotEncoder, StandardScaler, RobustScaler
    from sklearn.pipeline import Pipeline
    trans=[]
    for name,item in recipe['features'].items():
        if item['representation']=='numeric':
            stages=[('impute',SimpleImputer(strategy='median',keep_empty_features=True))]
            scaler={'standard':StandardScaler(),'robust':RobustScaler(),
                    'none':'passthrough'}[recipe['numeric_scale']]
            if scaler!='passthrough':stages.append(('scale',scaler))
            trans.append(('n_'+name,Pipeline(stages),[name]))
            trans.append(('missing_'+name,MissingIndicator(features='all'),[name]))
        else:
            strategy=recipe['categorical_missing']
            imputer=SimpleImputer(strategy=strategy,fill_value='__MISSING__'
                                  if strategy=='constant' else None)
            fixed=item.get('allowed_values')
            categories=[[str(x) for x in fixed]+(['__MISSING__'] if strategy=='constant' else [])] if fixed else 'auto'
            enc=OneHotEncoder(categories=categories,handle_unknown=recipe['categorical_unknown'],
                              sparse_output=False)
            trans.append(('c_'+name,Pipeline([('impute',imputer),('encode',enc)]),[name]))
        trans.append(('s_'+name,OneHotEncoder(categories=[item['allowed_statuses']],
                        handle_unknown='error',sparse_output=False),[name+'__status']))
    return Pipeline([('contract',ContractFrameValidator(recipe)),
                     ('encode',ColumnTransformer(trans, remainder='drop',sparse_threshold=0))])


def make_model_pipeline(recipe, estimator, *, synthetic_fixture=False):
    """Unfitted end-to-end pipeline, usable with classification/regression estimators.

    For survival/longitudinal studies use build_preprocessor inside a separately
    validated specialist estimator; this module does not implement censoring.
    """
    require(synthetic_fixture is True,'Real-data model pipelines not authorized')
    from sklearn.pipeline import Pipeline
    return Pipeline([('preprocessing',build_preprocessor(recipe,synthetic_fixture=True)),
                     ('estimator',estimator)])


def validate_partition(train_ids, valid_ids, *, policy, train_groups=None,
                       valid_groups=None, train_time=None, valid_time=None):
    """Protect split boundaries using metadata OUTSIDE the predictor matrix."""
    import pandas as pd
    a=list(train_ids);b=list(valid_ids)
    require(a and b and len(a)==len(set(a)) and len(b)==len(set(b)) and
            not set(a).intersection(b),'Overlapping or duplicate participant-row identifiers')
    require(policy in ('person_disjoint','forward_time','person_and_forward_time'),
            'Missing split-policy declaration')
    if policy in ('person_disjoint','person_and_forward_time'):
        require(train_groups is not None and valid_groups is not None,
                'Grouped split requires person/group identifiers')
        g1=list(train_groups);g2=list(valid_groups)
        require(len(g1)==len(a) and len(g2)==len(b) and
                all(pd.notna(x) for x in g1+g2) and not set(g1).intersection(g2),
                'Participant/site group appears in both training and validation')
    if policy in ('forward_time','person_and_forward_time'):
        require(train_time is not None and valid_time is not None,
                'Prospective split needs timestamps')
        t1=pd.to_datetime(list(train_time),errors='coerce',utc=True)
        t2=pd.to_datetime(list(valid_time),errors='coerce',utc=True)
        require(len(t1)==len(a) and len(t2)==len(b) and
                not t1.isna().any() and not t2.isna().any() and t1.max()<t2.min(),
                'Training records must precede all validation records')
    return {'boundary_checked':True,'policy':policy,'n_train':len(a),'n_valid':len(b)}


def prepare_synthetic_fold(recipe, train, valid, *, train_ids, valid_ids,
                           train_groups=None, valid_groups=None,
                           train_time=None, valid_time=None, synthetic_fixture=False):
    """Check split first, learn transformations on training partition ONLY."""
    require(synthetic_fixture is True,'Real-data folds not authorized')
    boundary=validate_partition(train_ids,valid_ids,policy=recipe['split_review'],
                     train_groups=train_groups,valid_groups=valid_groups,
                     train_time=train_time,valid_time=valid_time)
    require(len(train)==boundary['n_train'] and len(valid)==boundary['n_valid'],
            'Predictor and split lengths differ')
    pipeline=build_preprocessor(recipe,synthetic_fixture=True)
    training=pipeline.fit_transform(train)
    evaluation=pipeline.transform(valid)
    return pipeline,training,evaluation,boundary


def make_plan(recipe):
    numeric=[n for n,v in recipe['features'].items() if v['representation']=='numeric']
    categorical=[n for n,v in recipe['features'].items() if v['representation']=='one_hot']
    return {'schema':REPORT_SCHEMA,'case_id':recipe['case_id'],
            'config_sha256':digest(recipe),'route':'BLOCKED_FOR_NEW_ANALYSIS',
            'index_status':recipe['prediction_index_status'],
            'holdout_history':recipe['holdout_history'],
            'n_features':len(recipe['features']),'numeric':numeric,'one_hot':categorical,
            'source_status_columns':len(recipe['features']),
            'split_policy':recipe['split_review'],'synthetic_only':True,
            'no_participant_tables_opened':True,'no_models_fitted':True,
            'no_holdout_targets_accessed':True,'public_export':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    actions=parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--plan',action='store_true')
    actions.add_argument('--audit',action='store_true')
    parser.add_argument('--project',default='.')
    parser.add_argument('--config',default='research/cases/nhanes_foldsafe_v25.json')
    args=parser.parse_args()
    root=Path(args.project).resolve()
    cfg=json.loads(local_file(root,args.config,'research').read_text())
    v24=json.loads(local_file(root,cfg['related_v24_protocol'],'research').read_text())
    v23=json.loads(local_file(root,cfg['related_v23_protocol'],'research').read_text())
    from ml.case_harmonization_v24 import validate_protocol as check_v24,digest as digest_v24
    from ml.case_dictionary_timing_v23 import validate_protocol as check_v23
    from ml.case_governance_v22 import validate_protocol as check_v22
    manifest=json.loads(local_file(root,v23['case_manifest'],'research').read_text())
    v22=json.loads(local_file(root,v23['related_v22_protocol'],'research').read_text())
    check_v22(v22);check_v23(v23,manifest,v22);check_v24(v24,v23)
    validate_recipe(cfg,v23,v24)
    review=make_plan(cfg)
    if args.audit:
        prev=local_file(root,cfg['related_private_v24_review'],'artifacts')
        require(prev.suffix=='.json' and prev.stat().st_size<250_000,
                'Private parent metadata exceeds allowed size')
        parent=json.loads(prev.read_text())
        require(parent.get('schema')=='FRAILTYSCOPE_PRIVATE_HARMONIZATION_REVIEW_V24'
                and parent.get('case_id')==cfg['case_id'] and
                parent.get('config_sha256')==digest_v24(v24) and
                parent.get('v23_private_metadata_verified') is True and
                parent.get('no_participant_tables_opened') is True and
                parent.get('no_models_fitted') is True and
                parent.get('no_holdout_targets_accessed') is True and
                parent.get('public_export') is False,
                'Prior private audit metadata invalid')
        review['v24_private_metadata_verified']=True
    print('V25 FOLD SAFE PREPROCESSING PLAN:',json.dumps(review,indent=2))
    if args.audit:
        out=(root/'artifacts/cases'/cfg['case_id']/'foldsafe_v25'/
             digest(cfg)[:12]/'foldsafe_review.json').resolve()
        require(out.is_relative_to((root/'artifacts/cases').resolve())
                and not out.exists(),'Cannot overwrite private immutable audit')
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x') as f:json.dump(review,f,indent=2,allow_nan=False);f.write('\n')
        print('PRIVATE IMMUTABLE METADATA REVIEW:',out)
    print('No participant records, models, labels, holdout scores, or predictions accessed.')

if __name__=='__main__':main()
