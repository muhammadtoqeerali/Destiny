"""NHANES real-data model refinement: Optuna nested-in-development search.

All participant-level data, predictions and fitted models remain local. Training
and hyperparameter tuning use 2011-12 only; 2013-14 is the fixed later-cycle
benchmark (previously inspected in project v0.6, not a new untouched holdout).
Do not treat the result as a clinical prediction or survey-design-valid inference.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score, brier_score_loss
from ml.realdata_nhanes import BASE_FEATURES
from ml.realdata_train import pipeline, scores, tune_threshold

PROVENANCE='NHANES_PUBLIC_2019_LMF'
REPORT_TYPE='AGGREGATE_NHANES_REFINEMENT_V1'

class TunableCatBoost(ClassifierMixin,BaseEstimator):
    def __init__(self, iterations=220, depth=4, learning_rate=0.05, l2_leaf_reg=5.0, seed=42):
        self.iterations=iterations;self.depth=depth;self.learning_rate=learning_rate
        self.l2_leaf_reg=l2_leaf_reg;self.seed=seed

    def fit(self,X,y):
        from catboost import CatBoostClassifier
        self.estimator_=CatBoostClassifier(iterations=self.iterations,depth=self.depth,
            learning_rate=self.learning_rate,l2_leaf_reg=self.l2_leaf_reg,
            random_seed=self.seed,thread_count=4,loss_function='Logloss',verbose=False,
            allow_writing_files=False)
        self.estimator_.fit(X,y)
        self.classes_=self.estimator_.classes_
        return self

    def predict_proba(self,X):return self.estimator_.predict_proba(X)
    def predict(self,X):return self.estimator_.predict(X).reshape(-1)


def estimator(name,params,seed):
    if name=='Logistic regression':
        return LogisticRegression(C=params['C'],max_iter=2000,random_state=seed)
    if name=='Histogram gradient boosting':
        return HistGradientBoostingClassifier(max_iter=params['n_estimators'],
            max_leaf_nodes=params['max_leaf_nodes'],learning_rate=params['learning_rate'],
            l2_regularization=params['l2'],random_state=seed)
    if name=='XGBoost':
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=params['n_estimators'],max_depth=params['max_depth'],
           learning_rate=params['learning_rate'],min_child_weight=params['min_child_weight'],
           reg_lambda=params['reg_lambda'],subsample=.90,colsample_bytree=.90,
           random_state=seed,n_jobs=4,tree_method='hist',eval_metric='logloss')
    if name=='CatBoost':
        return TunableCatBoost(iterations=params['n_estimators'],depth=params['depth'],
            learning_rate=params['learning_rate'],l2_leaf_reg=params['l2'],seed=seed)
    raise ValueError('Unknown model family')


def suggest(trial,name):
    if name=='Logistic regression':
        return {'C':trial.suggest_float('C',.01,15,log=True)}
    if name=='Histogram gradient boosting':
        return {'n_estimators':trial.suggest_int('n_estimators',80,260,step=30),
                'max_leaf_nodes':trial.suggest_int('max_leaf_nodes',6,24,step=3),
                'learning_rate':trial.suggest_float('learning_rate',.015,.14,log=True),
                'l2':trial.suggest_float('l2',.1,20,log=True)}
    if name=='XGBoost':
        return {'n_estimators':trial.suggest_int('n_estimators',100,400,step=50),
                'max_depth':trial.suggest_int('max_depth',2,5),
                'learning_rate':trial.suggest_float('learning_rate',.015,.13,log=True),
                'min_child_weight':trial.suggest_int('min_child_weight',3,15),
                'reg_lambda':trial.suggest_float('reg_lambda',1,30,log=True)}
    if name=='CatBoost':
        return {'n_estimators':trial.suggest_int('n_estimators',120,360,step=40),
                'depth':trial.suggest_int('depth',3,6),
                'learning_rate':trial.suggest_float('learning_rate',.02,.12,log=True),
                'l2':trial.suggest_float('l2',2,15,log=True)}
    raise ValueError('Unknown model family')


def diagnostic_bins(y,p,weights=None,n_bins=5):
    """Five approximately equally sized test bins; aggregate only, no raw scores."""
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float)
    w=np.ones(len(p),dtype=float) if weights is None else np.asarray(weights,dtype=float)
    if len(y)!=len(p) or len(w)!=len(p):raise ValueError('Input length mismatch')
    if not np.isfinite(p).all() or (p<0).any() or (p>1).any():raise ValueError('Invalid probabilities')
    parts=np.array_split(np.argsort(p,kind='stable'),n_bins)
    out=[]
    for ix,part in enumerate(parts):
        if len(part)<30:raise ValueError('Too few records for public calibration bin')
        use=w[part]
        if not np.isfinite(use).all() or (use<0).any() or use.sum()==0:raise ValueError('Invalid weights')
        out.append({'group':f'Q{ix+1}','n':int(len(part)),
           'predicted':round(float(np.average(p[part],weights=use)),4),
           'observed':round(float(np.average(y[part],weights=use)),4)})
    return out


def safe_coverage(df):
    out=[]
    labels={
      'age':'Age (80+ top-coded)','sex':'Sex','bmi':'Body mass index','walking_difficulty':'Walking difficulty',
      'stairs_difficulty':'Stair difficulty','stooping_difficulty':'Stooping difficulty',
      'heart_failure':'Heart failure','coronary_disease':'Coronary disease','stroke':'Stroke',
      'cancer':'Cancer','diabetes':'Diabetes','hypertension':'Hypertension',
      'ever_smoked':'Ever smoked','phq9_score':'PHQ-9 score'}
    for c in BASE_FEATURES:
        obs=int(df[c].notna().sum())
        out.append({'feature':labels[c],'observed_pct':round(100*obs/len(df),1),'n_missing':len(df)-obs})
    return out


def cohort_bins(df):
    agebins=[(65,69,'65–69'),(70,74,'70–74'),(75,79,'75–79'),(80,125,'80+ (top-coded)')]
    result=[]
    for lo,hi,label in agebins:
        n=int(df.age.between(lo,hi).sum())
        if n<20:raise ValueError('Small age cell')
        result.append({'label':label,'count':n})
    return result


def explanation_summary(model,tr,va,seed=42):
    """Model-agnostic permutation importance on validation, not SHAP."""
    sample=va.sample(n=min(250,len(va)),random_state=seed)
    imp=permutation_importance(model,sample[BASE_FEATURES],sample['outcome_5yr'],
        n_repeats=5,random_state=seed,scoring='roc_auc',n_jobs=1)
    return sorted([{'feature':name,'auc_drop':round(float(value),4)}
                   for name,value in zip(BASE_FEATURES,imp.importances_mean)],
                  key=lambda v:v['auc_drop'],reverse=True)


def shap_summary(model,tr,va,seed=42):
    """Real-model SHAP on numeric transformed features, grouped by original column.

    The pipeline's training-fitted transform is applied to validation examples;
    case-level outputs are NOT retained or exported. Only mean absolute values.
    """
    import shap
    pre=model.named_steps['preprocess']
    classifier=model.named_steps['model']
    background=tr[BASE_FEATURES].sample(n=min(32,len(tr)),random_state=seed)
    focus=va[BASE_FEATURES].sample(n=min(24,len(va)),random_state=seed+1)
    xb=np.asarray(pre.transform(background),dtype=float)
    xv=np.asarray(pre.transform(focus),dtype=float)
    def pred(arr):return classifier.predict_proba(arr)[:,1]
    mask=shap.maskers.Independent(xb,max_samples=32)
    explain=shap.Explainer(pred,mask,algorithm='permutation',seed=seed)
    values=explain(xv,max_evals=2*xv.shape[1]+1,silent=True).values
    means=np.abs(np.asarray(values)).mean(axis=0)
    features=pre.get_feature_names_out()
    grouped={k:0.0 for k in BASE_FEATURES}
    for name,v in zip(features,means):
        short=name.split('__',1)[-1]
        short=short.removeprefix('missingindicator_')
        if short in grouped: key=short
        elif short.startswith('sex_'):key='sex'
        else:raise ValueError('Unknown transformed input: '+name)
        grouped[key]+=float(v)
    return sorted([{'feature':k,'mean_abs_shap':round(value,5)}
         for k,value in grouped.items()],key=lambda x:x['mean_abs_shap'],reverse=True)


def run(source:Path,out:Path,trials=10,seed=42,with_shap=True):
    import optuna
    df=pd.read_csv(source)
    if len(df)<2000 or set(df.data_origin)!={PROVENANCE}:raise ValueError('Expected local real NHANES records')
    if df.duplicated(['cycle','SEQN']).any():raise ValueError('Duplicate participant')
    if not set(BASE_FEATURES+['outcome_5yr','survey_weight']).issubset(df.columns):raise ValueError('Missing columns')
    dev=df[df.cycle.eq('2011-2012')].copy();test=df[df.cycle.eq('2013-2014')].copy()
    if len(dev)<700 or len(test)<700:raise ValueError('Invalid cycle sizes')
    tr,va=train_test_split(dev,test_size=.25,stratify=dev.outcome_5yr,random_state=seed)
    search=[];best_models={}
    for name in ['Logistic regression','Histogram gradient boosting','XGBoost','CatBoost']:
        def obj(trial):
            hp=suggest(trial,name)
            cv=StratifiedKFold(n_splits=3,shuffle=True,random_state=seed)
            probs=[]
            for ixtrain,ixvalid in cv.split(tr[BASE_FEATURES],tr.outcome_5yr):
                tt=tr.iloc[ixtrain];vv=tr.iloc[ixvalid]
                pipe=pipeline(estimator(name,hp,seed))
                pipe.fit(tt[BASE_FEATURES],tt.outcome_5yr)
                pred=pipe.predict_proba(vv[BASE_FEATURES])[:,1]
                probs.append(brier_score_loss(vv.outcome_5yr,pred))
            return float(np.mean(probs))
        study=optuna.create_study(direction='minimize',sampler=optuna.samplers.TPESampler(seed=seed))
        study.optimize(obj,n_trials=trials,show_progress_bar=False)
        fitted=pipeline(estimator(name,study.best_params,seed))
        fitted.fit(tr[BASE_FEATURES],tr.outcome_5yr)
        p=fitted.predict_proba(va[BASE_FEATURES])[:,1]
        validation=scores(va.outcome_5yr,p)
        search.append({'model':name,'cv_brier':round(float(study.best_value),4),
                       'validation':{k:validation[k] for k in ['roc_auc','average_precision','brier']},
                       'n_trials':trials,'parameters':study.best_params})
        best_models[name]=(fitted,p)
        print(f'{name:28} CV Brier={study.best_value:.4f} validation AUC={validation["roc_auc"]:.4f}',flush=True)
    best=min(search,key=lambda d:(d['validation']['brier'],-d['validation']['roc_auc']))
    selected=best['model'];model,p_val=best_models[selected]
    threshold=tune_threshold(va.outcome_5yr,p_val)
    p=model.predict_proba(test[BASE_FEATURES])[:,1]
    unweighted=scores(test.outcome_5yr,p,cutoff=threshold)
    w=pd.to_numeric(test.survey_weight,errors='coerce').to_numpy()
    w=np.where(np.isfinite(w)&(w>0),w,0)
    weighted=scores(test.outcome_5yr,p,cutoff=threshold,weights=w) if w.sum()>0 else None
    shap_features=None;shap_error=None
    if with_shap:
        try:shap_features=shap_summary(model,tr,va,seed)
        except Exception as exc:shap_error=f'{type(exc).__name__}: SHAP aggregation unavailable'
    report={
       'report_type':REPORT_TYPE,'data_origin':PROVENANCE,
       'source':'CDC NHANES 2011–2014 and 2019 public-use linked mortality',
       'target':'Approximately five-year all-cause mortality',
       'counts':{'development':int(len(dev)),'train':int(len(tr)),'validation':int(len(va)),
                 'test':int(len(test)),'test_events':int(test.outcome_5yr.sum()),'total':int(len(df))},
       'model_search':search,'selected_model':selected,'selected_threshold':threshold,
       'test_metrics':unweighted,'test_weighted_descriptive':weighted,
       'calibration_bins':diagnostic_bins(test.outcome_5yr,p),
       'coverage':safe_coverage(df),'age_distribution':cohort_bins(df),
       'feature_importance_method':'Validation ROC-AUC drop after single-column permutation',
       'importance':explanation_summary(model,tr,va,seed),
       'shap_features':shap_features,'shap_status':'computed' if shap_features is not None else (shap_error or 'not requested'),
       'methodology':{'optimization':'3-fold cross-validation inside training partition using Optuna',
                      'model_selection':'2011–12 validation Brier','later_cycle':'2013–14 holdout',
                      'later_cycle_exposure':'Previously inspected in v0.6; not a new untouched test cohort',
                      'survey_inference':'Descriptive sample-weighted estimates; PSU/strata design-based variance not computed',
                      'follow_up':'Public-use follow-up time perturbed for some participants'},
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('Saved aggregate-only local report:',out,flush=True)
    print('Selected:',selected,'ROC-AUC',unweighted['roc_auc'],'Recall',unweighted['recall'],flush=True)
    return report


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--input',default='data/processed/nhanes_5yr_local.csv')
    a.add_argument('--out',default='artifacts/realdata_nhanes/refinement.json')
    a.add_argument('--trials',type=int,default=10)
    a.add_argument('--no-shap',action='store_true')
    args=a.parse_args()
    if not 2<=args.trials<=80:raise SystemExit('Trials must be between 2 and 80')
    run(Path(args.input),Path(args.out),trials=args.trials,with_shap=not args.no_shap)
if __name__=='__main__':main()
