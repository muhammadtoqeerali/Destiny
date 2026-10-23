"""FrailtyScope v0.29: integrated synthetic-only, fail-closed development workflow.

Source-only --plan and private metadata-only --audit NEVER read participant tables,
research labels, predictions, or fitted models. In-memory execution fits models
ONLY on deliberately invented fixtures. `synthetic_fixture=True` is a caller
contract, NOT an access-control/security sandbox; never pass real research rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_INTEGRATED_WORKFLOW_V29'
REPORT_SCHEMA = 'FRAILTYSCOPE_PRIVATE_INTEGRATED_REVIEW_V29'
EXEC_SCHEMA = 'FRAILTYSCOPE_SYNTHETIC_INTEGRATED_DEVELOPMENT_V29'
BOUNDARY_FIELDS = ('holdout_history', 'prior_exploration', 'prediction_index_status')
SAFETY_FIELDS = ('real_data_execution_permitted', 'model_fitting_permitted',
                 'holdout_scoring_permitted', 'clinical_use_permitted',
                 'public_export_permitted')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def validate_workflow(cfg, v28, v27, v26, v25, v24):
    """Preserve case identity, history, task, folds, candidate and mapping scope."""
    require(isinstance(cfg,dict) and cfg.get('schema')==SCHEMA,
            'Unexpected v0.29 integrated workflow schema')
    predecessors=(v28,v27,v26,v25,v24)
    require(all(isinstance(p,dict) for p in predecessors), 'Missing predecessor contract')
    require(all(p.get('case_id')==cfg.get('case_id') for p in predecessors),
            'Case identity differs across source contracts')
    for field in BOUNDARY_FIELDS:
        require(all(p.get(field)==cfg.get(field) for p in predecessors),
                'Historical study/timing boundary changed: '+field)
    require(cfg.get('scope')=='synthetic_integration_only' and
            all(cfg.get(k) is False for k in SAFETY_FIELDS),
            'Integrated prototype cannot authorize any real-data execution')
    require(all(p.get(k) is False for p in predecessors[:4] for k in SAFETY_FIELDS
                if k in p), 'A predecessor cannot permit real execution or export')
    require(v24.get('real_data_execution_permitted') is False and
            v24.get('scope')=='partial_blueprint' and
            v25.get('scope')=='synthetic_only_blueprint' and
            v26.get('scope')=='synthetic_only_blueprint' and
            v27.get('scope')=='synthetic_only_blueprint' and
            v28.get('scope')=='synthetic_only_blueprint',
            'Unexpected predecessor execution scope')
    from ml.case_task_models_v26 import validate_design as check26
    from ml.case_temporal_v27 import validate_design as check27
    from ml.case_reliability_v28 import validate_design as check28
    check26(v26,v25);check27(v27,v26,v25);check28(v28,v27,v26,v25)
    require(cfg.get('related_v28_protocol') and cfg.get('related_private_v28_review'),
            'Require source and immutable private predecessor references')
    require(cfg.get('task')==v28.get('task')==v26.get('task') and
            cfg['task'] in ('classification','regression'),
            'Only tested classification/regression can use shared v0.28 diagnostics')
    require(cfg.get('split_policy')==v25.get('split_review')==v26.get('split_policy')==v28.get('split_policy')
            and cfg['split_policy'] in ('person_disjoint','forward_time','person_and_forward_time'),
            'Training and assessment split strategies differ')
    require(type(cfg.get('n_splits')) is int and cfg['n_splits']==v26.get('n_splits')==v28.get('n_splits'),
            'Fold count must be unchanged')
    require(type(cfg.get('random_seed')) is int and cfg['random_seed']==v26.get('random_seed'),
            'Do not silently change model-fitting seed')
    require(cfg.get('candidate_names')==v28.get('candidate_names') and
            isinstance(cfg['candidate_names'],list) and len(cfg['candidate_names'])>=2,
            'Candidate list must match approved reliability diagnostic candidates')
    require(set(cfg['candidate_names'])<={item['name'] for item in v26.get('candidates',[])},
            'All integrated model candidates must be registered in v0.26')
    require(cfg.get('reference_candidate')==v28.get('reference_candidate') and
            cfg['reference_candidate'] in cfg['candidate_names'],
            'Reference candidate must match v0.28')
    require(cfg.get('primary_metric')==v26.get('primary_metric')==v28.get('primary_metric'),
            'Development selection metric must be unchanged')
    require(cfg.get('harmonization_wave') in v24.get('waves',{}) and
            v24['waves'][cfg['harmonization_wave']].get('source_verified') is True,
            'Harmonization must use an explicitly source-mapped wave')
    covered={name for wave in v24['waves'].values() for name in wave['features']}
    require(set(v25.get('features',{}))==covered and
            set(v24.get('unmapped_predictors',[])).isdisjoint(covered),
            'Partial harmonized subset cannot silently acquire unmapped predictors')
    require(cfg.get('input_contract')=='source_or_canonical_synthetic_fixture' and
            cfg.get('validation_role')=='development_oof_only' and
            cfg.get('candidate_selection')=='not_performed' and
            cfg.get('predictions_exported') is False and
            cfg.get('models_saved') is False and
            cfg.get('independent_validation') is False,
            'Workflow must not imply saved predictions, model selection or independent evaluation')
    require(v28.get('source_predictions')=='synthetic_out_of_fold_only' and
            v28.get('independent_evaluation') is False and
            v26.get('test_set_role')=='not_accessed',
            'Predecessor evaluation history cannot be reset')
    return cfg


def make_plan(cfg, v24=None):
    return {'schema':REPORT_SCHEMA,'case_id':cfg['case_id'],
            'config_sha256':digest(cfg),'route':'BLOCKED_FOR_NEW_ANALYSIS',
            'task':cfg['task'],'workflow_stages':[
                'v22_v24_documentary_contracts', 'v24_optional_fixed_harmonization',
                'v25_fold_fitted_preprocessing','v26_fold_model_fitting',
                'v28_out_of_fold_reliability_diagnostics'],
            'source_wave':cfg['harmonization_wave'],
            'n_splits':cfg['n_splits'],'candidate_names':cfg['candidate_names'],
            'mapped_features':sorted(v24['waves'][cfg['harmonization_wave']]['features']) if v24 else None,
            'unmapped_predictors':sorted(v24['unmapped_predictors']) if v24 else None,
            'index_status':cfg['prediction_index_status'],
            'holdout_history':cfg['holdout_history'],
            'synthetic_only':True,'no_participant_tables_opened':True,
            'no_models_fitted':True,'no_predictions_generated':True,
            'no_holdout_targets_accessed':True,'public_export':False,
            'limitations':[
                'Source-only readiness remains blocked; synthetic execution is NOT authorized real research execution.',
                'Only the reviewed harmonized predictor subset is represented, not all 14 NHANES features.',
                'The current prediction index remains provisional.',
                'Out-of-fold development reliability is not fresh independent evaluation or a selected-model estimate.',
                'Fixed-prediction cluster intervals omit refitting and selection variability.',
                'Survival/longitudinal specialist demos are not integrated into v0.28 reliability diagnostics.',
                'No survey-design inference, external validation, clinical deployment, models or participant exports.'
            ]}


def run_synthetic_workflow(cfg,v28,v27,v26,v25,v24,frame,y,*,row_ids,
                           groups=None,timestamps=None,source_fixture=False,
                           synthetic_fixture=False):
    """End-to-end fictional development CV; aggregate results returned in memory only.

    `source_fixture=True` means frame holds raw codes for the declared source wave;
    otherwise frame must hold exact canonical feature + __status columns.
    All fold boundaries and input schemas are checked BEFORE the first model fit.
    """
    require(synthetic_fixture is True,'Real research execution is not authorized')
    validate_workflow(cfg,v28,v27,v26,v25,v24)
    from ml.case_harmonization_v24 import harmonize_fixture
    from ml.case_foldsafe_v25 import build_preprocessor, expected_columns, _coerce_frame
    from ml.case_task_models_v26 import _validate_outcome, _fold_indices, _estimator
    from ml.case_reliability_v28 import assess_synthetic_oof
    import pandas as pd
    import numpy as np
    from sklearn.pipeline import Pipeline
    require(isinstance(frame,pd.DataFrame) and frame.columns.is_unique and len(frame)>0,
            'Require a nonempty synthetic DataFrame with unique columns')
    if source_fixture:
        rules=v24['waves'][cfg['harmonization_wave']]['features']
        expected_raw={r['source_column'] for r in rules.values()}
        expected_raw.update(r['skip_if']['column'] for r in rules.values()
                            if r.get('skip_if') is not None)
        require(set(frame.columns)==expected_raw,
                'Source fixture contains extra fields, identifiers, targets or absent raw columns')
        frame, statuses=harmonize_fixture(frame,v24['waves'][cfg['harmonization_wave']],
                                         synthetic_fixture=True)
    else:
        statuses=None
    require(set(frame.columns)==set(expected_columns(v25)),
            'Input must contain exactly the approved canonical feature/status subset')
    _coerce_frame(frame,v25)  # Checks all synthetic input semantics; learns nothing.
    truth=_validate_outcome(y,cfg['task'],len(frame))
    folds=_fold_indices(v26,len(frame),truth,row_ids=row_ids,groups=groups,
                        timestamps=timestamps)
    require(len(folds)==cfg['n_splits'], 'Missing development fold')
    # Require immutable row metadata and participant-level protection for ALL folds.
    require(groups is not None and len(groups)==len(frame) and
            not any(pd.isna(z) for z in groups),
            'All integrated synthetic folds require participant grouping metadata')
    from ml.case_foldsafe_v25 import validate_partition
    for tr,va in folds:
        validate_partition([row_ids[i] for i in tr],[row_ids[i] for i in va],
            policy='person_and_forward_time' if 'time' in cfg['split_policy'] else 'person_disjoint',
            train_groups=[groups[i] for i in tr],valid_groups=[groups[i] for i in va],
            train_time=[timestamps[i] for i in tr] if timestamps is not None else None,
            valid_time=[timestamps[i] for i in va] if timestamps is not None else None)
    candidates={c['name']:c for c in v26['candidates']}
    records=[]
    for tr,va in folds:
        predictions={}
        for name in cfg['candidate_names']:
            model=Pipeline([
                ('preprocessing',build_preprocessor(v25,synthetic_fixture=True)),
                ('estimator',_estimator(cfg['task'],candidates[name],cfg['random_seed']))])
            model.fit(frame.iloc[tr],truth[tr])
            values=(model.predict_proba(frame.iloc[va])[:,1] if cfg['task']=='classification'
                    else model.predict(frame.iloc[va]))
            require(np.asarray(values).shape==(len(va),) and np.isfinite(values).all(),
                    'Model returned invalid synthetic predictions')
            predictions[name]=np.asarray(values,dtype=float).tolist()
        record={'train_ids':[row_ids[i] for i in tr],
                'valid_ids':[row_ids[i] for i in va],
                'train_people':[groups[i] for i in tr],
                'valid_people':[groups[i] for i in va],
                'truth':truth[va].tolist(),'predictions':predictions}
        if 'time' in cfg['split_policy']:
            record['train_time']=[timestamps[i] for i in tr]
            record['valid_time']=[timestamps[i] for i in va]
        records.append(record)
    # Explicitly discard OOF row records after aggregated reliability assessment.
    reliability=assess_synthetic_oof(v28,records,synthetic_fixture=True)
    return {'schema':EXEC_SCHEMA,'case_id':cfg['case_id'],'task':cfg['task'],
            'config_sha256':digest(cfg),'n_synthetic_rows':len(frame),
            'n_folds':len(folds),'synthetic_model_fits':len(folds)*len(cfg['candidate_names']),
            'source_mapping_applied':bool(source_fixture),
            'source_status_counts':statuses, 'aggregate_reliability':reliability,
            'development_only':True,'independent_validation':False,
            'selected_model':None,'models_saved':False,
            'participant_predictions_exported':False,'clinical_use_permitted':False}


def _read_sources(root,config_path):
    from ml.case_foldsafe_v25 import local_file, validate_recipe
    from ml.case_governance_v22 import validate_protocol as check22
    from ml.case_dictionary_timing_v23 import validate_protocol as check23
    from ml.case_harmonization_v24 import validate_protocol as check24
    from ml.case_task_models_v26 import validate_design as check26
    from ml.case_temporal_v27 import validate_design as check27
    from ml.case_reliability_v28 import validate_design as check28
    cfg=json.loads(local_file(root,config_path,'research').read_text())
    v28=json.loads(local_file(root,cfg['related_v28_protocol'],'research').read_text())
    v27=json.loads(local_file(root,v28['related_v27_protocol'],'research').read_text())
    v26=json.loads(local_file(root,v27['related_v26_protocol'],'research').read_text())
    v25=json.loads(local_file(root,v26['related_v25_protocol'],'research').read_text())
    v23=json.loads(local_file(root,v25['related_v23_protocol'],'research').read_text())
    v24=json.loads(local_file(root,v25['related_v24_protocol'],'research').read_text())
    v22=json.loads(local_file(root,v23['related_v22_protocol'],'research').read_text())
    manifest=json.loads(local_file(root,v23['case_manifest'],'research').read_text())
    check22(v22);check23(v23,manifest,v22);check24(v24,v23)
    validate_recipe(v25,v23,v24);check26(v26,v25,manifest);check27(v27,v26,v25)
    check28(v28,v27,v26,v25)
    validate_workflow(cfg,v28,v27,v26,v25,v24)
    return cfg,v28,v27,v26,v25,v24


def main():
    p=argparse.ArgumentParser(description=__doc__)
    actions=p.add_mutually_exclusive_group(required=True)
    actions.add_argument('--plan',action='store_true')
    actions.add_argument('--audit',action='store_true')
    p.add_argument('--project',default='.')
    p.add_argument('--config',default='research/cases/nhanes_workflow_v29.json')
    a=p.parse_args()
    root=Path(a.project).resolve()
    cfg,v28,v27,v26,v25,v24=_read_sources(root,a.config)
    report=make_plan(cfg,v24)
    if a.audit:
        from ml.case_foldsafe_v25 import local_file
        from ml.case_reliability_v28 import digest as digest28, REPORT_SCHEMA as PARENT_SCHEMA
        path=local_file(root,cfg['related_private_v28_review'],'artifacts')
        require(path.suffix=='.json' and path.stat().st_size<250_000,
                'Unsafe prior private documentary review')
        parent=json.loads(path.read_text())
        require(parent.get('schema')==PARENT_SCHEMA and parent.get('case_id')==cfg['case_id']
                and parent.get('config_sha256')==digest28(v28)
                and parent.get('route')=='BLOCKED_FOR_NEW_ANALYSIS'
                and parent.get('v27_private_metadata_verified') is True
                and parent.get('no_participant_tables_opened') is True
                and parent.get('no_models_fitted') is True
                and parent.get('no_predictions_generated') is True
                and parent.get('no_holdout_targets_accessed') is True
                and parent.get('public_export') is False,
                'Prior v0.28 private metadata cannot be used for this audit')
        report['v28_private_metadata_verified']=True
    print('V29 INTEGRATED WORKFLOW PLAN:',json.dumps({k:report[k] for k in (
        'case_id','route','task','source_wave','n_splits','candidate_names',
        'mapped_features','unmapped_predictors','index_status','holdout_history')},indent=2))
    if a.audit:
        target=(root/'artifacts/cases'/cfg['case_id']/'workflow_v29'/
                digest(cfg)[:12]/'workflow_review.json').resolve()
        require(target.is_relative_to((root/'artifacts/cases').resolve()) and
                not target.exists(),'Existing immutable v0.29 private review; refuse overwrite')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream:
            json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print('PRIVATE IMMUTABLE METADATA REVIEW:',target)
    else:
        print('PLAN ONLY. Source contracts checked; no private report or data opened.')
    print('No participant data, research labels, trained models or held-out scores accessed.')


if __name__=='__main__':
    main()
