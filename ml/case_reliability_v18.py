"""FrailtyScope v0.18 — development-only missingness and calibration diagnostics.

No import-time fitting. --plan never fits. --run is for the researcher's workstation.
Assesses a FROZEN, previously selected v0.16 recipe. This is post-hoc exploratory
reuse of development data, NOT new nested model selection or holdout validation.
No person-level scores, raw rows, calibrator binaries, or existing models exported.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_RELIABILITY_AUDIT_V18'

def require(condition, message):
    if not condition: raise ValueError(message)

def bounded_scores(probabilities):
    import numpy as np
    a = np.asarray(probabilities,dtype=float).reshape(-1)
    require(len(a)>0 and np.isfinite(a).all() and ((a>=0)&(a<=1)).all(),
            'Probabilities must be finite and in [0,1]')
    return a

def logit_scores(probabilities):
    import numpy as np
    p = np.clip(bounded_scores(probabilities),1e-6,1-1e-6)
    return np.log(p/(1-p))

def validate_design(cfg, joint, manifest, report):
    from ml.case_joint_selection_v16 import digest_json,pair_name,candidate_pairs
    require(isinstance(cfg,dict) and cfg.get('schema')==SCHEMA,'Invalid reliability schema')
    require(manifest.get('task')=='classification','v0.18 supports binary classification only')
    require(cfg.get('case_id')==joint.get('case_id')==manifest.get('case_id')==report.get('case_id'),
            'Mismatched case IDs')
    require(cfg.get('v16_protocol_sha256')==digest_json(joint) and
            report.get('v16_protocol_sha256')==digest_json(joint),
            'Selected-model protocol hash mismatch')
    require(report.get('dataset_sha256') and report.get('selected_model') in joint['families'],
            'Incomplete saved selection')
    pairs = {pair_name(*p) for p in candidate_pairs(joint)}
    expected=pair_name(report['selected_model'],report.get('selected_preprocessing'))
    require(report.get('final_development_selection',{}).get('selection',{}).get('pair')==expected
            and expected in pairs, 'Selected recipe does not match declared candidates')
    require(cfg.get('frozen_selected_pair')==expected,'Recipe changed after v0.16 selection')
    require(cfg.get('holdout_policy')=='development_only_no_evaluation' and
            cfg.get('post_hoc_development_reuse') is True and
            report.get('holdout_scored') is False,
            'Explicit post-hoc/holdout contract required')
    for key in ('outer_folds','inner_folds'):
        require(type(cfg.get(key)) is int and 2<=cfg[key]<=5,'Invalid '+key)
    seeds=cfg.get('outer_seeds')
    require(isinstance(seeds,list) and 1<=len(seeds)<=4 and len(set(seeds))==len(seeds)
            and all(type(s) is int and 1<=s<2**31 for s in seeds), 'Invalid outer seeds')
    require(not set(seeds).intersection(joint.get('outer_seeds',[])),'Use distinct diagnostic seeds')
    require(cfg.get('methods')==['identity','sigmoid','isotonic'],
            'Only declared identity, sigmoid, isotonic methods supported')
    for key,lo,hi in [('isotonic_min_calibration_n',1000,10000),
                      ('calibration_bins',3,10),('min_calibration_bin_n',30,200),
                      ('min_missing_group_n',20,200)]:
        require(type(cfg.get(key)) is int and lo<=cfg[key]<=hi,'Invalid '+key)
    require(cfg['calibration_bins']*cfg['min_calibration_bin_n'] <= 1000,
            'Unrealistic calibration-bin minimum')
    require(len(seeds)*cfg['outer_folds']*(cfg['inner_folds']+1) <= 150,
            'Calibration study training budget exceeds allowed limit')
    return {'frozen_recipe':expected,
            'outer_assessments':len(seeds)*cfg['outer_folds'],
            'max_base_model_fits':len(seeds)*cfg['outer_folds']*(cfg['inner_folds']+1)}

def summarize_missingness(x, labels, minimum):
    """Development only. Missingness association != causal skip/MNAR mechanism."""
    import numpy as np
    require(len(x)==len(labels) and len(x)>0,'Unpaired development features/labels')
    yy=np.asarray(labels,dtype=int)
    require(set(yy).issubset({0,1}) and len(set(yy))==2,'Expected binary outcome')
    rows=[]
    for name in x.columns:
        missing=x[name].isna().to_numpy()
        count=int(missing.sum());observed=len(yy)-count
        if count==0:continue
        eligible=count>=minimum and observed>=minimum
        rows.append({'feature':str(name),'n_development':int(len(yy)),
            'missing_n':count,'missing_pct':round(float(100*count/len(yy)),4),
            'observed_n':observed,'event_rate_missing':round(float(yy[missing].mean()),6) if eligible else None,
            'event_rate_observed':round(float(yy[~missing].mean()),6) if eligible else None,
            'event_rate_difference_missing_minus_observed':
                round(float(yy[missing].mean()-yy[~missing].mean()),6) if eligible else None,
            'event_rate_suppressed':not eligible,
            'missingness_reason':'UNVERIFIED_CODEBOOK_REVIEW_REQUIRED'})
    return sorted(rows,key=lambda r:(-r['missing_n'],r['feature']))

def diagnostic_metrics(y,p,bins,min_bin):
    import numpy as np
    from sklearn.metrics import brier_score_loss,log_loss,roc_auc_score,average_precision_score
    from ml.case_stability_v17 import equal_frequency_calibration
    a=np.asarray(y,dtype=int);pred=bounded_scores(p)
    require(len(a)==len(pred) and set(a)=={0,1},'Invalid labels/probabilities')
    cal=equal_frequency_calibration(a,pred,bins,min_bin)
    return {'n':int(len(a)),'brier':round(float(brier_score_loss(a,pred)),7),
            'log_loss':round(float(log_loss(a,pred,labels=[0,1])),7),
            'roc_auc':round(float(roc_auc_score(a,pred)),6),
            'average_precision':round(float(average_precision_score(a,pred)),6),
            'descriptive_ece':cal['ece_descriptive'],
            'mean_risk_minus_event_rate':cal['mean_probability_minus_prevalence'],
            'calibration_bins':cal['bins']}

def choose_nothing(comparisons):
    """No auto-promotion: only factual relative Brier/LogLoss deltas."""
    require('identity' in comparisons and 'sigmoid' in comparisons,
            'Reference and sigmoid comparisons required')
    base=comparisons['identity']
    require(all(math.isfinite(base[key]) for key in ('brier','log_loss')),
            'Invalid reference metrics')
    return [{'method':name,'delta_brier_vs_identity':round(float(z['brier']-base['brier']),7),
             'delta_log_loss_vs_identity':round(float(z['log_loss']-base['log_loss']),7),
             'delta_descriptive_ece_vs_identity':round(float(z['descriptive_ece']-base['descriptive_ece']),6)}
            for name,z in comparisons.items()]

def get_context(project:Path,cfg_path:Path):
    from ml.case_joint_selection_v16 import locate_context,digest_json,validate_local_release
    project=project.resolve();cfg_path=cfg_path.resolve();research=(project/'research').resolve()
    require(cfg_path.is_relative_to(research) and cfg_path.is_file(),
            'Configuration must exist inside research/')
    cfg=json.loads(cfg_path.read_text());rel=cfg.get('v16_config')
    require(isinstance(rel,str) and rel,'Missing v0.16 protocol file')
    source=(project/rel).resolve()
    require(source.is_relative_to(research) and source.is_file(),'Unsafe or missing joint protocol')
    original=locate_context(project,source)
    joint,manifest,strategy,ablation,data_sha,x,y,groups=original
    output=(project/'artifacts'/'cases'/manifest['case_id']/'joint_selection_v16'/
            digest_json(joint)[:12])
    rp=output/'joint_selection.json';mp=output/'winner_development_only.joblib'
    require(rp.is_file() and mp.is_file(),'v0.16 selection/artifact unavailable')
    saved=json.loads(rp.read_text())
    validate_local_release(joint,saved,mp.is_file())
    require(saved.get('dataset_sha256')==data_sha and
            saved.get('manifest_sha256')==digest_json(manifest) and
            saved.get('strategy_sha256')==digest_json(strategy),
            'Existing selection does not match dataset and manifest')
    plan=validate_design(cfg,joint,manifest,saved)
    return cfg,original,saved,plan

def _apply_calibrators(train_probs,train_y,test_probs,cfg):
    """Calibrators fit on outer-TRAIN cross-fitted scores, not assessment labels."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.isotonic import IsotonicRegression
    xx=logit_scores(train_probs).reshape(-1,1)
    test=bounded_scores(test_probs)
    y=np.asarray(train_y,dtype=int)
    require(len(y)==len(xx) and len(set(y))==2,'Invalid calibration-training sample')
    sigmoid=LogisticRegression(C=1.0,max_iter=1000,solver='lbfgs')
    sigmoid.fit(xx,y)
    values={'identity':test,
            'sigmoid':sigmoid.predict_proba(logit_scores(test).reshape(-1,1))[:,1]}
    if len(y)>=cfg['isotonic_min_calibration_n']:
        iso=IsotonicRegression(y_min=0,y_max=1,out_of_bounds='clip')
        iso.fit(bounded_scores(train_probs),y)
        values['isotonic']=np.asarray(iso.predict(test),float)
    return values

def run(context):
    """EXPLICIT workstation-only calibration study; frozen model recipe."""
    import numpy as np
    from ml.case_strategy_v13 import fold_indices
    from ml.case_joint_selection_v16 import _build
    from ml.case_engine_v10 import _pred
    cfg,original,saved,plan=context
    joint,manifest,strategy,ablation,data_sha,x,y,groups=original
    pair=saved['selected_model'],saved['selected_preprocessing'],saved['selected_parameters']
    missingness=summarize_missingness(x,y,cfg['min_missing_group_n'])
    records=[]
    for seed in cfg['outer_seeds']:
        n=len(y)
        oof={'identity':np.full(n,np.nan),'sigmoid':np.full(n,np.nan)}
        isotonic_eligible=True
        outer=list(fold_indices(y,cfg['outer_folds'],seed,'classification',groups))
        for fold,(tr,va) in enumerate(outer,1):
            xtr=x.iloc[tr].reset_index(drop=True);ytr=y.iloc[tr].reset_index(drop=True)
            grp=groups[tr] if groups is not None else None
            inner_probs=np.full(len(ytr),np.nan)
            for itr,iva in fold_indices(ytr,cfg['inner_folds'],seed+fold*1001,'classification',grp):
                mdl,cols=_build(manifest,ablation,*pair)
                mdl.fit(xtr.iloc[itr][cols],ytr.iloc[itr])
                inner_probs[iva]=_pred(mdl,xtr.iloc[iva][cols],'classification')
            require(np.isfinite(inner_probs).all(),'Incomplete calibration OOF scores')
            mdl,cols=_build(manifest,ablation,*pair)
            mdl.fit(x.iloc[tr][cols],y.iloc[tr])
            outer_pred=bounded_scores(_pred(mdl,x.iloc[va][cols],'classification'))
            calibrated=_apply_calibrators(inner_probs,ytr,outer_pred,cfg)
            if 'isotonic' not in calibrated:isotonic_eligible=False
            if 'isotonic' in calibrated and 'isotonic' not in oof:
                oof['isotonic']=np.full(n,np.nan)
            for name,p in calibrated.items():
                require(np.isfinite(p).all() and ((p>=0)&(p<=1)).all(),
                        'Invalid calibrated probabilities')
                oof[name][va]=p
            print(f'CALIBRATION DEV seed={seed} fold={fold}/{len(outer)} '
                  f'isotonic={"fitted" if "isotonic" in calibrated else "skipped_low_n"}',flush=True)
        if not isotonic_eligible:oof.pop('isotonic',None)
        metrics={}
        for name,p in oof.items():
            require(np.isfinite(p).all(),'Incomplete outer assessment predictions')
            metrics[name]=diagnostic_metrics(y,p,cfg['calibration_bins'],
                                             cfg['min_calibration_bin_n'])
        records.append({'seed':seed,'n_development':n,'calibrators_assessed':list(metrics),
                'calibrators_skipped':(['isotonic'] if not isotonic_eligible else []),
                'metrics':metrics,'comparisons':choose_nothing(metrics)})
        print('CALIBRATION DEVELOPMENT REPEAT:',seed,
              {k:v['brier'] for k,v in metrics.items()},flush=True)
    from ml.case_joint_selection_v16 import digest_json
    return {'schema':SCHEMA,'report_type':'LOCAL_POST_HOC_DEVELOPMENT_RELIABILITY_ONLY',
       'case_id':manifest['case_id'],'dataset_sha256':data_sha,
       'manifest_sha256':digest_json(manifest),'v16_protocol_sha256':digest_json(joint),
       'reliability_protocol_sha256':digest_json(cfg),'frozen_selected_pair':cfg['frozen_selected_pair'],
       'cohort':{'development_n':len(y),'evaluation_predictions_generated':0},
       'missingness_audit':missingness,'repeated_development_calibration':records,
       'holdout_scored':False,'model_replaced':False,'new_model_binary_saved':False,
       'calibrator_promoted':False,'public_export':False,
       'limitations':[
         'Post-hoc recipe: development participants previously informed model/preprocessing/hyperparameter choice.',
         'Calibration is cross-fitted inside outer training only; assessment folds are untouched during calibration fit.',
         'This does not remove bias from earlier model selection on the same participants.',
         'Cross-fitted calibration predicts models trained on smaller inner folds than outer fitted models.',
         'Repeated outer folds reuse people and are not independent confirmation or survey-design uncertainty.',
         'ECE is bin-sensitive; lower binned ECE is not sufficient for adoption.',
         'Missingness associations cannot identify missing-at-random, MNAR, questionnaire skips or causal mechanisms.',
         'Isotonic skipped if calibration sample smaller than the declared minimum.',
         'No new fitted model, threshold, calibrator, patient predictions or holdout scores published.']}

def validate_local_report(cfg,joint,manifest,result):
    from ml.case_joint_selection_v16 import digest_json
    require(result.get('schema')==SCHEMA and
            result.get('report_type')=='LOCAL_POST_HOC_DEVELOPMENT_RELIABILITY_ONLY',
            'Not the expected local research audit')
    require(result.get('case_id')==manifest.get('case_id')==cfg.get('case_id') and
            result.get('manifest_sha256')==digest_json(manifest) and
            result.get('v16_protocol_sha256')==digest_json(joint) and
            result.get('reliability_protocol_sha256')==digest_json(cfg),
            'Inconsistent case/protocol fingerprint')
    require(result.get('frozen_selected_pair')==cfg.get('frozen_selected_pair'),
            'Recipe changed during diagnostics')
    require(result.get('holdout_scored') is False and
            result.get('cohort',{}).get('evaluation_predictions_generated')==0 and
            result.get('model_replaced') is False and
            result.get('calibrator_promoted') is False and
            result.get('new_model_binary_saved') is False and
            result.get('public_export') is False, 'Privacy/holdout/model boundary broken')
    rows=result.get('repeated_development_calibration')
    require(isinstance(rows,list) and len(rows)==len(cfg['outer_seeds']),
            'Incomplete outer repeats')
    require({r.get('seed') for r in rows}==set(cfg['outer_seeds']),
            'Incorrect or duplicate repeat seeds')
    for row in rows:
        methods=row.get('metrics',{})
        require('identity' in methods and 'sigmoid' in methods and
                set(methods).issubset(cfg['methods']), 'Missing required calibration comparisons')
        for metric in methods.values():
            require(metric.get('n')==result['cohort']['development_n'] and
                    all(type(metric.get(k)) in (int,float) and math.isfinite(metric[k])
                        for k in ('brier','log_loss','roc_auc','average_precision','descriptive_ece')),
                    'Invalid calibration summary metrics')
    require(isinstance(result.get('missingness_audit'),list),'Missing missingness audit')
    return {'case_id':result['case_id'],'repeats':len(rows),
            'methods':sorted({k for r in rows for k in r['metrics']}),
            'holdout_scored':False,'calibrator_promoted':False}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    modes=ap.add_mutually_exclusive_group(required=True)
    modes.add_argument('--plan',action='store_true',help='Verify design and data only; no fitting')
    modes.add_argument('--run',action='store_true',help='Run calibration experiments on workstation')
    ap.add_argument('--project',default='.')
    ap.add_argument('--config',default='research/cases/nhanes_reliability_v18.json')
    args=ap.parse_args();project=Path(args.project).resolve()
    context=get_context(project,(project/args.config))
    cfg,original,saved,plan=context
    joint,manifest,strategy,ablation,data_sha,x,y,groups=original
    if args.plan:
        print('V18 RELIABILITY PLAN:',json.dumps({
          'case_id':manifest['case_id'],'dataset_sha256':data_sha,
          'n_development':len(y),'frozen_recipe':plan['frozen_recipe'],
          'n_outer_assessments':plan['outer_assessments'],
          'estimated_base_fits':plan['max_base_model_fits'],
          'methods':cfg['methods'],
          'isotonic_min_calibration_n':cfg['isotonic_min_calibration_n'],
          'holdout_scored':False,'training':False},indent=2))
        print('No fitting, holdout scoring or public export.')
        return
    from ml.case_joint_selection_v16 import digest_json
    output=(project/'artifacts'/'cases'/manifest['case_id']/'reliability_v18'/
            digest_json(cfg)[:12]/'reliability_audit.json').resolve()
    require(output.is_relative_to((project/'artifacts'/'cases').resolve()),
            'Output must remain inside ignored artifacts/cases')
    require(not output.exists(),'Immutable v0.18 report already exists; refuse overwrite')
    result=run(context)
    validate_local_report(cfg,joint,manifest,result)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as file:
        json.dump(result,file,indent=2,allow_nan=False);file.write('\n')
    print('LOCAL DEVELOPMENT RELIABILITY REPORT:',output)
    for rec in result['repeated_development_calibration']:
        print('REPEAT',rec['seed'],'METRICS:',json.dumps({k:{a:v[a] for a in
                  ('brier','log_loss','roc_auc','average_precision','descriptive_ece')}
                  for k,v in rec['metrics'].items()}))
    print('No fitted calibrators or models saved, no participant data published, no holdout scored.')

if __name__=='__main__':main()
