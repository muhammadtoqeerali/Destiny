"""Case-independent tabular experiment runner. Local research only, never public prediction.

No datasets bundled; manifests point exclusively into this project's ignored data/.
Evaluation cohort is not used for preprocessing, tuning, calibration or model choice.
The output is aggregate metadata and metrics; fitted model binaries stay local.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
    confusion_matrix, f1_score, mean_absolute_error, mean_squared_error,
    precision_score, r2_score, recall_score, roc_auc_score)
from sklearn.model_selection import KFold, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

VERSION = '1.0'
CLASSIFICATION = {'dummy', 'logistic', 'random_forest', 'hist_boost', 'xgboost', 'catboost'}
REGRESSION = {'dummy', 'ridge', 'random_forest', 'hist_boost', 'xgboost', 'catboost'}
FORBIDDEN_FEATURES = {'seqn','patient_id','person_id','id','outcome','outcome_5yr',
     'mortstat','permth_exm','eligstat','duration','event','death_date',
     'followup_days','followup_months','data_origin','survey_weight'}
ALLOWED_NAME = re.compile(r'^[a-z][a-z0-9_]{2,70}$')


def _require(cond:bool, message:str):
    if not cond: raise ValueError(message)


def validate_manifest(spec:dict)->dict:
    """Fail closed on unexpected features, invalid folds, ambiguous endpoints."""
    _require(isinstance(spec,dict),'Manifest must be JSON object')
    name=spec.get('case_id')
    _require(isinstance(name,str) and ALLOWED_NAME.fullmatch(name) is not None,'Invalid case_id')
    _require(spec.get('task') in ('classification','regression'),'Only tabular binary classification or regression supported')
    task=spec['task']; src=spec.get('source',{}); f=spec.get('features',{}); split=spec.get('split',{})
    _require(isinstance(src,dict) and isinstance(src.get('path'),str),'Source path required')
    _require(isinstance(f,dict) and isinstance(f.get('numeric'),list) and isinstance(f.get('categorical'),list),'Feature lists required')
    cols=f['numeric']+f['categorical']
    _require(bool(cols) and all(isinstance(x,str) and x.strip() for x in cols),'Nonempty feature names required')
    _require(len(cols)==len(set(cols)),'Duplicate feature name')
    target=spec.get('target'); id_col=spec.get('id_column')
    _require(isinstance(target,str) and isinstance(id_col,str) and target!=id_col,'Target and identifier required')
    _require(target not in cols and id_col not in cols,'Target/ID leakage in predictors')
    _require(not (set(x.lower() for x in cols) & FORBIDDEN_FEATURES),'Known outcome/ID/follow-up leakage')
    _require(all(x != spec.get('split',{}).get('column') for x in cols),'Cohort split variable cannot be a predictor')
    _require(not any(re.search(r'(?:^|_)(?:death|mortality|target|label|outcome|followup|date_of_death)(?:_|$)',x.lower()) for x in cols),'Suspicious leakage column')
    _require(isinstance(split,dict) and split.get('strategy') in ('cohort','random'),'Split strategy must be cohort or random')
    fraction=split.get('validation_fraction',0.25)
    _require(isinstance(fraction,(int,float)) and not isinstance(fraction,bool) and 0.1 <= fraction <= 0.4,'Invalid validation_fraction')
    if split['strategy']=='random':
        ev=split.get('evaluation_fraction',0.25)
        _require(isinstance(ev,(int,float)) and not isinstance(ev,bool) and 0.1<=ev<=0.5,'Invalid evaluation_fraction')
    if split['strategy']=='cohort':
        _require(isinstance(split.get('column'),str) and split['column'] not in cols,'Cohort split column required and cannot be a model feature')
        a=split.get('development');b=split.get('evaluation')
        _require(isinstance(a,(str,int)) and isinstance(b,(str,int)) and a!=b,'Different development/evaluation cohorts required')
    methods=spec.get('models')
    valid=CLASSIFICATION if task=='classification' else REGRESSION
    _require(isinstance(methods,list) and bool(methods) and all(x in valid for x in methods),'Unsupported model family')
    _require(len(set(methods))==len(methods),'Repeated model family')
    _require('dummy' in methods,'Dummy baseline is required')
    _require(any(x!='dummy' for x in methods),'At least one trained model is required')
    trials=spec.get('trials_per_model',6)
    _require(isinstance(trials,int) and not isinstance(trials,bool) and 1 <= trials <= 40,'Optuna trial budget must be 1–40')
    _require(spec.get('cv_folds',3) in (3,4,5),'CV folds must be 3–5')
    if task=='classification':
        _require(spec.get('selection_metric','brier') in ('brier','roc_auc'),'Unsupported classification selection metric')
    else:
        _require(spec.get('selection_metric','rmse') in ('rmse','mae'),'Unsupported regression selection metric')
    if 'provenance' in src:
        p=src['provenance'];_require(isinstance(p,dict) and all(isinstance(p.get(z),str) for z in ('column','value')),'Invalid provenance declaration')
    return spec


def safe_local_input(project:Path,relative:str)->Path:
    base=(project/'data').resolve()
    path=(project/relative).resolve()
    _require(path.is_relative_to(base),'Input CSV must remain under ignored data/')
    _require(path.is_file() and path.suffix.lower() in ('.csv','.xlsx','.parquet','.dta','.sas7bdat','.xpt'),
             'Existing local CSV, XLSX, Parquet, Stata or SAS file required')
    return path


def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def read_local_table(path:Path,spec:dict)->pd.DataFrame:
    suffix=path.suffix.lower()
    if suffix=='.csv':return pd.read_csv(path,low_memory=False)
    if suffix=='.xlsx':
        sheet=spec.get('source',{}).get('sheet',0)
        _require(isinstance(sheet,(str,int)) and not isinstance(sheet,bool),'Excel sheet must be name or index')
        return pd.read_excel(path,sheet_name=sheet)
    if suffix=='.parquet':return pd.read_parquet(path)
    if suffix=='.dta':return pd.read_stata(path,convert_categoricals=False)
    if suffix in ('.sas7bdat','.xpt'):
        return pd.read_sas(path,format='sas7bdat' if suffix=='.sas7bdat' else 'xport')
    raise ValueError('Unsupported research table format')

def load_data(project:Path,spec:dict):
    path=safe_local_input(project,spec['source']['path'])
    frame=read_local_table(path,spec)
    cols=spec['features']['numeric']+spec['features']['categorical']
    required=set(cols+[spec['target'],spec['id_column']])
    if spec['split']['strategy']=='cohort':required.add(spec['split']['column'])
    if 'provenance' in spec['source']:required.add(spec['source']['provenance']['column'])
    _require(required.issubset(frame.columns),'Missing columns: '+str(sorted(required-set(frame.columns))))
    _require(frame[spec['id_column']].notna().all() and not frame[spec['id_column']].duplicated().any(),'Missing/duplicate IDs')
    if 'provenance' in spec['source']:
        p=spec['source']['provenance']
        _require(set(frame[p['column']].dropna().unique())=={p['value']} and frame[p['column']].notna().all(),'Incorrect or mixed data origin')
    _require(frame[spec['target']].notna().all(),'Missing target labels; define explicit eligible cohort first')
    if spec['task']=='classification':
        _require(set(pd.to_numeric(frame[spec['target']],errors='coerce').dropna().unique())=={0,1},'Binary target must include classes 0 and 1 only')
        y=pd.to_numeric(frame[spec['target']]).astype(int)
    else:
        y=pd.to_numeric(frame[spec['target']],errors='coerce')
        _require(np.isfinite(y.to_numpy()).all(),'Regression target must be finite numeric')
    for col in spec['features']['numeric']:
        raw=frame[col]
        values=pd.to_numeric(raw,errors='coerce')
        _require((raw.isna() | values.notna()).all(),'Unexpected text in numeric feature: '+col)
        frame[col]=values
        _require(np.isfinite(values.dropna().to_numpy(dtype=float)).all(),'Invalid numerical value: '+col)
    for col in spec['features']['categorical']:
        frame[col]=frame[col].astype('string').astype(object).where(frame[col].notna(),np.nan)
        _require(frame[col].notna().any(),'Categorical feature entirely missing: '+col)
    return frame, y, digest(path)


def split_data(frame:pd.DataFrame,y:pd.Series,spec:dict):
    s=spec['split'];idx=np.arange(len(frame));strat=y if spec['task']=='classification' else None
    if s['strategy']=='cohort':
        col=frame[s['column']].astype(str)
        dev=idx[col.eq(str(s['development'])).to_numpy()]
        test=idx[col.eq(str(s['evaluation'])).to_numpy()]
        _require(len(dev)+len(test)==len(frame),'Other cohort values present: define a clean source first')
    else:
        dev,test=train_test_split(idx,test_size=float(s.get('evaluation_fraction',0.25)),
                       stratify=strat,random_state=2026)
    _require(len(dev)>=35 and len(test)>=15,'Insufficient development/evaluation records')
    strat_dev=y.iloc[dev] if spec['task']=='classification' else None
    train,val=train_test_split(dev,test_size=float(s.get('validation_fraction',0.25)),
                              stratify=strat_dev,random_state=2026)
    _require(not (set(train)&set(val) or set(train)&set(test) or set(val)&set(test)),'Partition overlap')
    if spec['task']=='classification':
        for part in (train,val,test):
            c=y.iloc[part].value_counts();_require(len(c)==2 and c.min()>=2,'Both classes required in each split')
        _require(y.iloc[train].value_counts().min() >= spec.get('cv_folds',3),'Too few minority cases for CV')
    return np.sort(train),np.sort(val),np.sort(test)


def make_preprocess(numeric,categorical):
    tr=[]
    if numeric:tr.append(('numeric',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),
                                            ('scale',StandardScaler())]),numeric))
    if categorical:tr.append(('category',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),
                        ('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical))
    return ColumnTransformer(tr,remainder='drop',sparse_threshold=0)


class CatBoostClassifierAdapter(ClassifierMixin, BaseEstimator):
    """Current CatBoost + sklearn 1.8 tags-compatible classifier wrapper."""
    def __init__(self, iterations=200, depth=4, learning_rate=0.05, l2_leaf_reg=5.0):
        self.iterations=iterations;self.depth=depth
        self.learning_rate=learning_rate;self.l2_leaf_reg=l2_leaf_reg
    def fit(self,X,y):
        from catboost import CatBoostClassifier
        self.estimator_=CatBoostClassifier(iterations=self.iterations,depth=self.depth,
            learning_rate=self.learning_rate,l2_leaf_reg=self.l2_leaf_reg,
            random_seed=2026,thread_count=2,verbose=False,allow_writing_files=False)
        self.estimator_.fit(X,y)
        self.classes_=np.asarray(self.estimator_.classes_)
        return self
    def predict(self,X):return np.asarray(self.estimator_.predict(X)).reshape(-1).astype(int)
    def predict_proba(self,X):return np.asarray(self.estimator_.predict_proba(X))

class CatBoostRegressorAdapter(RegressorMixin, BaseEstimator):
    """Current CatBoost + sklearn 1.8 tags-compatible regressor wrapper."""
    def __init__(self, iterations=200, depth=4, learning_rate=0.05, l2_leaf_reg=5.0):
        self.iterations=iterations;self.depth=depth
        self.learning_rate=learning_rate;self.l2_leaf_reg=l2_leaf_reg
    def fit(self,X,y):
        from catboost import CatBoostRegressor
        self.estimator_=CatBoostRegressor(iterations=self.iterations,depth=self.depth,
            learning_rate=self.learning_rate,l2_leaf_reg=self.l2_leaf_reg,
            random_seed=2026,thread_count=2,verbose=False,allow_writing_files=False)
        self.estimator_.fit(X,y);return self
    def predict(self,X):return np.asarray(self.estimator_.predict(X)).reshape(-1)


def model_for(name,task,params=None):
    p=dict(params or {})
    if task=='classification':
        if name=='dummy':return DummyClassifier(strategy='prior')
        if name=='logistic':return LogisticRegression(max_iter=1300,random_state=2026,**p)
        if name=='random_forest':return RandomForestClassifier(n_jobs=2,random_state=2026,**p)
        if name=='hist_boost':return HistGradientBoostingClassifier(random_state=2026,**p)
        if name=='xgboost':
            from xgboost import XGBClassifier
            return XGBClassifier(tree_method='hist',n_jobs=2,random_state=2026,eval_metric='logloss',**p)
        if name=='catboost':return CatBoostClassifierAdapter(**p)
    else:
        if name=='dummy':return DummyRegressor(strategy='mean')
        if name=='ridge':return Ridge(**p)
        if name=='random_forest':return RandomForestRegressor(n_jobs=2,random_state=2026,**p)
        if name=='hist_boost':return HistGradientBoostingRegressor(random_state=2026,**p)
        if name=='xgboost':
            from xgboost import XGBRegressor
            return XGBRegressor(tree_method='hist',n_jobs=2,random_state=2026,**p)
        if name=='catboost':return CatBoostRegressorAdapter(**p)
    raise ValueError('Unknown model '+str(name))


def propose(trial,name,task):
    if name in ('logistic','ridge'):return {'C':trial.suggest_float('C',0.02,20.,log=True)} if name=='logistic' else {'alpha':trial.suggest_float('alpha',0.02,30.,log=True)}
    if name=='random_forest':return {'n_estimators':trial.suggest_int('n_estimators',80,240,step=40),
                                    'max_depth':trial.suggest_int('max_depth',3,12),
                                    'min_samples_leaf':trial.suggest_int('min_samples_leaf',2,12)}
    if name=='hist_boost':return {'max_iter':trial.suggest_int('max_iter',70,220,step=30),
                      'max_leaf_nodes':trial.suggest_int('max_leaf_nodes',5,23,step=3),
                      'learning_rate':trial.suggest_float('learning_rate',0.015,0.15,log=True),
                      'l2_regularization':trial.suggest_float('l2_regularization',0.02,15.,log=True)}
    if name=='xgboost':return {'n_estimators':trial.suggest_int('n_estimators',100,260,step=40),
          'max_depth':trial.suggest_int('max_depth',2,5),
          'learning_rate':trial.suggest_float('learning_rate',0.02,0.14,log=True),
          'reg_lambda':trial.suggest_float('reg_lambda',0.5,20.,log=True)}
    if name=='catboost':return {'iterations':trial.suggest_int('iterations',120,280,step=40),
          'depth':trial.suggest_int('depth',3,6),
          'learning_rate':trial.suggest_float('learning_rate',0.02,0.12,log=True),
          'l2_leaf_reg':trial.suggest_float('l2_leaf_reg',1.,15.,log=True)}
    raise ValueError('No parameter space for '+name)


def calculate_metrics(task,y,pred,proba=None,threshold=0.5)->dict:
    y=np.asarray(y);pred=np.asarray(pred)
    if task=='regression':
        return {'n':int(len(y)),'rmse':round(float(np.sqrt(mean_squared_error(y,pred))),6),
          'mae':round(float(mean_absolute_error(y,pred)),6),'r2':round(float(r2_score(y,pred)),6)}
    prob=np.asarray(proba,dtype=float)
    _require(np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all(),'Invalid probabilities')
    lbl=(prob >=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,lbl,labels=[0,1]).ravel()
    return {'n':int(len(y)), 'roc_auc':round(float(roc_auc_score(y,prob)),6),
            'average_precision':round(float(average_precision_score(y,prob)),6),
            'brier':round(float(brier_score_loss(y,prob)),6),
            'accuracy':round(float(accuracy_score(y,lbl)),6),
            'precision':round(float(precision_score(y,lbl,zero_division=0)),6),
            'recall':round(float(recall_score(y,lbl,zero_division=0)),6),
            'f1':round(float(f1_score(y,lbl,zero_division=0)),6),
            'threshold':round(float(threshold),6),
            'confusion':{'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)}}


def selected_threshold(y,prob):
    from sklearn.metrics import fbeta_score
    # Development-only threshold selection, no evaluation label access.
    candidates=np.linspace(0.05,0.95,91)
    vals=[fbeta_score(y,prob>=t,beta=2,zero_division=0) for t in candidates]
    return float(candidates[int(np.argmax(vals))])


def fit_pipeline(numeric,categorical,name,task,params,frame,y):
    pipeline=Pipeline([('features',make_preprocess(numeric,categorical)),
                       ('model',model_for(name,task,params))])
    return pipeline.fit(frame,y)


def _pred(model,x,task):
    return model.predict_proba(x)[:,1] if task=='classification' else model.predict(x)


def cv_score(x,y,numeric,categorical,name,task,params,folds,metric=None):
    fold=StratifiedKFold(n_splits=folds,shuffle=True,random_state=2026) if task=='classification' else KFold(n_splits=folds,shuffle=True,random_state=2026)
    scores=[]
    for tr,va in fold.split(x,y if task=='classification' else None):
        mod=fit_pipeline(numeric,categorical,name,task,params,x.iloc[tr],y.iloc[tr])
        yp=_pred(mod,x.iloc[va],task)
        if task=='classification':
            metric = metric or 'brier'
            scores.append(float(1-roc_auc_score(y.iloc[va],yp)) if metric=='roc_auc'
                          else float(brier_score_loss(y.iloc[va],yp)))
        else:
            metric = metric or 'rmse'
            scores.append(float(mean_absolute_error(y.iloc[va],yp)) if metric=='mae'
                          else float(np.sqrt(mean_squared_error(y.iloc[va],yp))))
    return float(np.mean(scores))


def _better(metric,task):return metric=='roc_auc' if task=='classification' else False


def run_case(project:Path,spec:dict,trial_override:int|None=None)->dict:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    validate_manifest(spec)
    frame,y,sha=load_data(project,spec)
    tr,va,te=split_data(frame,y,spec)
    cols=spec['features']['numeric']+spec['features']['categorical'];num=spec['features']['numeric'];cat=spec['features']['categorical']
    train_x=frame.iloc[tr][cols];val_x=frame.iloc[va][cols];test_x=frame.iloc[te][cols]
    train_y=y.iloc[tr];val_y=y.iloc[va];test_y=y.iloc[te]
    task=spec['task'];metric=spec.get('selection_metric','brier' if task=='classification' else 'rmse')
    candidates=[]; trained={}
    ntrials=trial_override if trial_override is not None else spec.get('trials_per_model',6)
    _require(isinstance(ntrials,int) and 1<=ntrials<=40,'Trial override outside 1–40')
    for name in spec['models']:
        now=time.monotonic();params={};cv=None
        if name!='dummy':
            study=optuna.create_study(direction='minimize',sampler=optuna.samplers.TPESampler(seed=2026))
            study.optimize(lambda t:cv_score(train_x,train_y,num,cat,name,task,propose(t,name,task),spec.get('cv_folds',3),metric),
                           n_trials=ntrials,show_progress_bar=False)
            params=study.best_params;cv=round(float(study.best_value),6)
        model=fit_pipeline(num,cat,name,task,params,train_x,train_y)
        pv=_pred(model,val_x,task)
        metrics=calculate_metrics(task,val_y,pv,pv)
        record={'model':name,'parameters':params,'cv_score':cv,'validation':metrics,
                'fit_search_seconds':round(time.monotonic()-now,2)}
        candidates.append(record);trained[name]=model
        print(f"{name:15s} | validation {metric}: {metrics[metric]:.4f} | CV: {cv}",flush=True)
    contenders=[z for z in candidates if z['model']!='dummy']
    top=(max if _better(metric,task) else min)(contenders,key=lambda z:z['validation'][metric])
    winning=top['model'];model=trained[winning]
    val_prob=_pred(model,val_x,task)
    threshold=selected_threshold(val_y,val_prob) if task=='classification' else None
    test_pred=_pred(model,test_x,task)
    test=calculate_metrics(task,test_y,test_pred,test_pred,threshold if threshold is not None else 0.5)
    dummy=trained['dummy'];dp=_pred(dummy,test_x,task)
    baseline=calculate_metrics(task,test_y,dp,dp)
    # Importance on validation only; no outcome information from evaluation used for training or selection.
    score='roc_auc' if task=='classification' else 'neg_mean_squared_error'
    pi=permutation_importance(model,val_x,val_y,scoring=score,n_repeats=3,random_state=2026,n_jobs=1)
    importance=[{'feature':f,'mean_metric_drop':round(float(z),6)}
         for f,z in sorted(zip(cols,pi.importances_mean),key=lambda pair:-pair[1])]
    missing={c:round(float(frame[c].isna().mean()),5) for c in cols}
    return {'schema':'FRAILTYSCOPE_CASE_V10','report_type':'LOCAL_AGGREGATE_RESEARCH_ONLY',
        'case_id':spec['case_id'],'display_name':spec.get('display_name',spec['case_id']),
        'dataset_sha256':sha,'task':task,'target':spec['target'],
        'split':{'strategy':spec['split']['strategy'],'counts':{'train':int(len(tr)),'validation':int(len(va)),'evaluation':int(len(te))},
                'development_cohort':spec['split'].get('development'),'evaluation_cohort':spec['split'].get('evaluation'),
                'note':'One later-cycle evaluation after validation selection; previously inspected cohorts are not new external validation'},
        'preprocessing':'Training-only fold-specific median/mode imputation, standardization and one-hot encoding',
        'features':{'numeric':num,'categorical':cat,'missing_fraction':missing},
        'selection_metric':metric,'cv_objective':'minimize '+('1 - ROC-AUC' if metric=='roc_auc' else metric),'candidate_models':candidates,'selected_model':winning,
        'selected_threshold':threshold,'evaluation':test,'dummy_baseline_evaluation':baseline,
        'permutation_importance_validation':importance,
        'limitations':['Observational, exploratory and not clinical predictions.',
                       'No design-based inference or protected-group performance guarantees.',
                       'Evaluation records used for reporting only, not selection.']}


def render_markdown(r:dict)->str:
    def f(v):return '—' if v is None else f'{v:.4f}'
    m=r['selection_metric']; rows=['| Model | Training CV loss ↓ | Validation '+m+' | Selected |', '|---|---:|---:|:---:|']
    for c in r['candidate_models']:
        rows.append(f"| {c['model']} | {f(c['cv_score'])} | {f(c['validation'][m])} | {'Yes' if c['model']==r['selected_model'] else ''} |")
    eval_rows='\n'.join(f"| {key} | {value} |" for key,value in r['evaluation'].items() if isinstance(value,(int,float)))
    imp='\n'.join(f"| {v['feature']} | {v['mean_metric_drop']:.4f} |" for v in r['permutation_importance_validation'][:10])
    return (f"# {r['display_name']} — experiment results\n\n"
         f"**Data:** local CSV fingerprint `{r['dataset_sha256'][:16]}` · **Outcome:** `{r['target']}` · **Task:** {r['task']}\n\n"
         f"**Split:** {r['split']['counts']} · **Selection metric:** {m}\n\n"
         "## Development comparison\n\n"+'\n'.join(rows)+'\n\n'
         f"## Chosen model: {r['selected_model']}\n\nModel selected on validation metrics; evaluation set reserved until selection.\n\n"
         "## Evaluation metrics\n\n| Metric | Value |\n|---|---:|\n"+eval_rows+'\n\n'
         "## Permutation relevance (validation only)\n\n| Feature | Metric drop |\n|---|---:|\n"+imp+'\n\n'
         "## Interpretation boundaries\n\n"+'\n'.join('- '+x for x in r['limitations'])+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',default='.')
    p.add_argument('--config',required=True)
    p.add_argument('--trials',type=int)
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args();project=Path(args.project).resolve()
    cfg=(project/args.config).resolve()
    _require(cfg.is_relative_to(project),'Manifest must live in project')
    spec=validate_manifest(json.loads(cfg.read_text()))
    frame,y,sha=load_data(project,spec)
    tr,va,te=split_data(frame,y,spec)
    print('READY:',spec['case_id'],'real/local rows',len(frame),'sha256',sha[:12],'partitions',len(tr),len(va),len(te))
    if args.dry_run:return
    report=run_case(project,spec,args.trials)
    out=(project/'artifacts'/'cases'/spec['case_id']).resolve()
    _require(out.is_relative_to((project/'artifacts').resolve()),'Reports must remain in ignored local artifacts/')
    out.mkdir(parents=True,exist_ok=True)
    (out/'metrics.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    (out/'experiment_summary.md').write_text(render_markdown(report))
    # Persist the selected fitted development-training pipeline locally. Do NOT refit on evaluation.
    import joblib
    tr, _, _ = split_data(frame,y,spec)
    num=spec['features']['numeric']; cat=spec['features']['categorical']
    cols=num+cat
    params=next(z['parameters'] for z in report['candidate_models'] if z['model']==report['selected_model'])
    winner=fit_pipeline(num,cat,report['selected_model'],spec['task'],params,frame.iloc[tr][cols],y.iloc[tr])
    joblib.dump(winner,out/'best_model.joblib')
    print('LOCAL TRAINED MODEL (trusted files only):',out/'best_model.joblib')
    print('LOCAL RESULTS:',out/'metrics.json')
    print('EXPERIMENT SUMMARY:',out/'experiment_summary.md')
    print('MODEL:',report['selected_model'],'EVALUATION:',report['evaluation'])
    print('No individual rows or predictions published.')
if __name__=='__main__':main()
