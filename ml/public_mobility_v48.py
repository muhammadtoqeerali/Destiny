"""FrailtyScope Phase 2: new, independent public NHANES mobility benchmark (NOT mortality).

Cross-sectional CURRENT quarter-mile walking difficulty, 65+; 2015-16 development
and 2017-18 held-aside cycle. No prospective or clinical predictions. Raw public
records remain outside the repository; only model-level aggregates are exported.

Run `python -m ml.public_mobility_v48 --download --run --data-root /external/path`.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request

import numpy as np
import pandas as pd
from sklearn.base import clone, BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (roc_auc_score, average_precision_score, brier_score_loss,
                             log_loss, confusion_matrix)
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import sklearn

SCHEMA = 'FRAILTYSCOPE_PUBLIC_NHANES_MOBILITY_V48'
CASE_ID = 'public_nhanes_mobility_2015_2018_v48'  # NEVER nhanes_mortality_v10
CYCLES = { '2015-2016': ('2015','I'), '2017-2018': ('2017','J') }
TABLES = {
    'DEMO':('SEQN','RIDAGEYR','RIAGENDR','SDMVPSU','SDMVSTRA','WTMEC2YR'),
    'PFQ':('SEQN','PFQ054','PFQ061B'),
    'BMX':('SEQN','BMXBMI'),
    'MCQ':('SEQN','MCQ160A','MCQ160B','MCQ160F'),
    'DIQ':('SEQN','DIQ010'),
    'DPQ':('SEQN',*[f'DPQ0{i}0' for i in range(1,10)]),
}
INPUTS = ['age','bmi','phq9_score','arthritis','heart_failure','stroke','diabetes','sex']
NUMERIC = INPUTS[:-1]
CATEGORICAL = ['sex']
SEED = 20261024
# A candidate variable with fewer than 20 observed rows in *either* cycle is
# excluded from the entire experiment, not passed silently to SimpleImputer.
MIN_OBSERVED_PER_CYCLE = 20
# The 2017-18 outcome scores have already been inspected under v0.48.
# Reruns therefore report a repeat sensitivity evaluation, NEVER a fresh holdout.
LATER_CYCLE_PREVIOUSLY_INSPECTED = True
URL_PATTERN = 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{table}_{suffix}.XPT'
# pandas 2.x XPORT decoding of an eight-zero-byte SAS floating-point value.
# This exact tiny nonzero is NOT an NHANES response and must round-trip to 0.
# Never coerce arbitrary small genuine numbers, SAS missing, or refused codes.
SAS_XPORT_ZERO_ARTIFACT = 5.397605346934028e-79


def normalize_xport_zeros(frame: pd.DataFrame) -> pd.DataFrame:
    """Decode SAS IBM-zero artefacts using exact equality, retaining true missingness."""
    numeric = frame.select_dtypes(include=[np.number]).columns
    if len(numeric) == 0:
        return frame
    affected = frame.loc[:,numeric].eq(SAS_XPORT_ZERO_ARTIFACT)
    if not affected.to_numpy().any():
        return frame
    result = frame.copy()
    result.loc[:,numeric] = result.loc[:,numeric].mask(affected,other=0.0)
    return result

class ContractError(ValueError): pass

def check(ok,reason):
    if not ok: raise ContractError('PUBLIC_MOBILITY_REFUSED: '+reason)

def safe_root(data_root:Path, project_root:Path)->Path:
    project=project_root.resolve()
    root=data_root.expanduser().resolve()
    check(not root.is_relative_to(project), 'Data/output directory must be OUTSIDE Git checkout')
    check(root != project.parent, 'Choose a dedicated study subdirectory')
    check(not data_root.is_symlink(), 'Data directory symlink refused')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if os.name=='posix': os.chmod(root,0o700)
    for rel in ('raw','results'):
        folder=root/rel
        check(not folder.is_symlink(),'Symlink folder refused')
        folder.mkdir(exist_ok=True,mode=0o700)
        if os.name=='posix':os.chmod(folder,0o700)
    return root

def download(root:Path):
    """Official CDC XPT only, with no derived/private historical model access."""
    for year,(folder,suffix) in CYCLES.items():
        for table in TABLES:
            filename=f'{table}_{suffix}.XPT'
            target=root/'raw'/filename
            check(not target.is_symlink(),'Symlinked source rejected')
            if target.exists():
                check(target.is_file() and target.stat().st_size>1024,'Invalid existing '+filename)
                print('EXISTS',filename)
                continue
            url=URL_PATTERN.format(year=folder,table=table,suffix=suffix)
            temp=target.with_suffix('.download')
            try:
                req=Request(url,headers={'User-Agent':'Mozilla/5.0 (FrailtyScope public scientific research; no patient export)'})
                with urlopen(req,timeout=90) as response:
                    end=response.geturl()
                    loc=urlparse(end)
                    check(loc.scheme=='https' and loc.hostname in {'wwwn.cdc.gov','www.cdc.gov'},'Untrusted download redirect')
                    with temp.open('wb') as fp:
                        while True:
                            block=response.read(128*1024)
                            if not block: break
                            fp.write(block)
                            check(fp.tell()<30_000_000,'Unexpected source size')
                header=temp.open('rb').read(100)
                check(temp.stat().st_size>1024 and b'HEADER RECORD' in header,
                      'Not a valid SAS XPORT response: '+filename)
                temp.replace(target)
                print('DOWNLOADED',filename, target.stat().st_size,'bytes')
            except Exception as exc:
                temp.unlink(missing_ok=True)
                raise ContractError(f'Cannot download {filename} from CDC. Check the official URL or manually save the XPT to the raw folder. Cause: {type(exc).__name__}') from None

def read_cycle(root:Path, cycle:str):
    suffix=CYCLES[cycle][1]
    merged=None;sha={}
    for table,columns in TABLES.items():
        path=root/'raw'/f'{table}_{suffix}.XPT'
        check(path.is_file() and not path.is_symlink(),'Missing required CDC source '+path.name)
        blob=path.read_bytes()
        check(b'HEADER RECORD' in blob[:100] and len(blob)<30_000_000,'Invalid XPORT source '+path.name)
        sha[path.name]=hashlib.sha256(blob).hexdigest()
        try: df=pd.read_sas(path,format='xport')
        except (ValueError, OSError, TypeError) as exc:
            raise ContractError('Invalid SAS XPORT source '+path.name) from exc
        # Correct the exact pandas IBM-float zero artefact before any value-code
        # mapping, including PHQ-9 (valid 0 means "Not at all").
        df = normalize_xport_zeros(df)
        df.columns=[str(x).upper() for x in df.columns]
        check(set(columns).issubset(df.columns),'Required source columns missing from '+path.name+': '+','.join(sorted(set(columns)-set(df.columns))))
        df=df.loc[:,list(columns)].copy()
        check(df['SEQN'].notna().all() and df['SEQN'].is_unique,'Duplicate/null public sequence identifier '+path.name)
        if merged is None: merged=df
        else: merged=merged.merge(df,on='SEQN',how='left',validate='one_to_one')
    check(merged is not None and len(merged)>0,'No survey records')
    return merged,sha

def map_binary(values:pd.Series, *, borderline=False)->pd.Series:
    x=pd.to_numeric(values,errors='coerce')
    return x.map({1:1.0,2:0.0})  # code 3 'borderline' is NOT definite diabetes

def harmonize(df:pd.DataFrame,cycle:str)->tuple[pd.DataFrame,dict]:
    """No PFQ predictors: avoid using target-like outcomes to predict PFQ061B."""
    for col in set(sum((list(v) for v in TABLES.values()),[])):
        check(col in df.columns,'Missing source variable '+col)
    age=pd.to_numeric(df['RIDAGEYR'],errors='coerce')
    age_ok=age.ge(65) & age.le(80)
    base=df.loc[age_ok].copy()
    pfq=pd.to_numeric(base['PFQ061B'],errors='coerce')
    equip=pd.to_numeric(base['PFQ054'],errors='coerce')
    # When PFQ054==1, B/C were not administered. NEVER impute that as no difficulty.
    valid=pfq.isin([1,2,3,4]) & equip.ne(1)
    usable=base.loc[valid].copy()
    status=pd.to_numeric(usable['PFQ061B'],errors='coerce')
    out=pd.DataFrame(index=usable.index)
    out['age']=pd.to_numeric(usable['RIDAGEYR'],errors='coerce')  # age 80 is top-coded 80+
    bmi=pd.to_numeric(usable['BMXBMI'],errors='coerce')
    out['bmi']=bmi.where(bmi.between(10,80))
    out['sex']=pd.to_numeric(usable['RIAGENDR'],errors='coerce').map({1:'Male',2:'Female'})
    for field,raw in [('arthritis','MCQ160A'),('heart_failure','MCQ160B'),('stroke','MCQ160F'),('diabetes','DIQ010')]:
        out[field]=map_binary(usable[raw])
    phq=pd.DataFrame({name:pd.to_numeric(usable[name],errors='coerce') for name in TABLES['DPQ'][1:]})
    phq=phq.where(phq.isin([0,1,2,3]))
    out['phq9_score']=phq.sum(axis=1,min_count=9)
    # Only AGGREGATE diagnostics; never display or persist person-level DPQ rows.
    phq_complete_respondents=int(out['phq9_score'].notna().sum())
    phq_item_observed={name:int(phq[name].notna().sum()) for name in phq.columns}
    out['target']=status.ge(2).astype('int8')
    out['weight']=pd.to_numeric(usable['WTMEC2YR'],errors='coerce')
    out['psu']=pd.to_numeric(usable['SDMVPSU'],errors='coerce')
    out['stratum']=pd.to_numeric(usable['SDMVSTRA'],errors='coerce')
    out['id']=pd.to_numeric(usable['SEQN'],errors='raise')
    out['cycle']=cycle
    check(out['id'].is_unique and out['id'].notna().all(),'Nonunique ID after harmonization')
    check(out['target'].nunique()==2, 'Both outcome classes required in '+cycle)
    report={
        'cycle':cycle,'eligible_age_65_plus':int(age_ok.sum()),
        'questionnaire_respondents':int(len(out)),
        'excluded_no_valid_PFQ061B':int((~pfq.isin([1,2,3,4])).sum()),
        'excluded_PFQ054_uses_walking_aid':int(equip.eq(1).sum()),
        'target_events':int(out['target'].sum()),
        'observed_event_fraction':round(float(out['target'].mean()),6),
        'feature_missing_percent':{f:round(float(out[f].isna().mean()*100),2) for f in INPUTS},
        'feature_observed_n':{f:int(out[f].notna().sum()) for f in INPUTS},
        'phq9_valid_complete_n':phq_complete_respondents,
        'dpq_item_valid_observed_n':phq_item_observed,
        'sample_age_80_is_topcoded':True,
        'target_codes':'PFQ061B 1=no difficulty; 2/3/4=some/much/unable; 5/7/9/NA and routing excluded',
    }
    return out.reset_index(drop=True),report

def pipeline(estimator, features=None):
    selected=list(INPUTS if features is None else features)
    check(bool(selected) and len(selected)==len(set(selected)) and
          all(f in INPUTS for f in selected), 'Invalid selected predictor inventory')
    numeric=[f for f in selected if f in NUMERIC]
    categorical=[f for f in selected if f in CATEGORICAL]
    transformers=[]
    if numeric:
        transformers.append(('numeric',Pipeline([
            ('impute',SimpleImputer(strategy='median',add_indicator=True)),
            ('scale',StandardScaler())]),numeric))
    if categorical:
        transformers.append(('category',Pipeline([
            ('impute',SimpleImputer(strategy='most_frequent')),
            ('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical))
    return Pipeline([('prep',ColumnTransformer(transformers,remainder='drop',
                                sparse_threshold=0)),('model',estimator)])


def feature_contract(development:pd.DataFrame, heldout:pd.DataFrame):
    # Pre-specified input availability, independent of outcome labels.

    # A previously unmeasurable covariate may not be presented as model input.
    # Do not use validation/test Y or any model performance for this decision.
    n_dev=len(development);n_later=len(heldout)
    check(n_dev>=40 and n_later>=40, 'Too few respondents for feature review')
    observations={f:{'development':int(development[f].notna().sum()),
                     'later_cycle':int(heldout[f].notna().sum())} for f in INPUTS}
    selected=[f for f in INPUTS if min(observations[f].values())>=MIN_OBSERVED_PER_CYCLE]
    removed=[{'feature':f,'reason':'FEWER_THAN_20_OBSERVED_IN_AT_LEAST_ONE_CYCLE',
              'observed_counts':observations[f]} for f in INPUTS if f not in selected]
    check(len(selected)>=2 and 'age' in selected and 'sex' in selected,
          'Too few usable predictors or age/sex unavailable; stop for source audit')
    return selected,{'predeclared_candidate_predictors':INPUTS,
        'included_predictors':selected,'excluded_predictors':removed,
        'available_counts':observations,
        'min_observed_per_cycle':MIN_OBSERVED_PER_CYCLE,
        'used_outcome_labels_for_availability_decision':False}

class CatBoostSklearnAdapter(ClassifierMixin,BaseEstimator):
    """Compatibility adapter for CatBoost releases without sklearn 1.8 classifier tags."""
    def __init__(self,iterations=220,depth=4,learning_rate=0.05,random_state=SEED):
        self.iterations=iterations
        self.depth=depth
        self.learning_rate=learning_rate
        self.random_state=random_state
    def fit(self,X,y):
        from catboost import CatBoostClassifier
        self.inner_=CatBoostClassifier(iterations=self.iterations,depth=self.depth,
                          learning_rate=self.learning_rate,random_seed=self.random_state,
                          verbose=False,thread_count=1,allow_writing_files=False)
        self.inner_.fit(X,y)
        self.classes_=np.unique(y)
        return self
    def predict_proba(self,X):return self.inner_.predict_proba(X)
    def predict(self,X):return self.inner_.predict(X).reshape(-1)

def candidates(features=None):
    registry={
     'Dummy prior': (pipeline(DummyClassifier(strategy='prior'),features),{}),
     'Logistic regression':(pipeline(LogisticRegression(max_iter=1500,random_state=SEED),features),{'model__C':[0.1,1.0,10.0]}),
     'Random forest':(pipeline(RandomForestClassifier(n_estimators=180,n_jobs=1,random_state=SEED),features),{'model__max_depth':[4,9], 'model__min_samples_leaf':[5,15]}),
     'Histogram gradient boosting':(pipeline(HistGradientBoostingClassifier(max_iter=160,early_stopping=False,random_state=SEED),features),{'model__max_leaf_nodes':[7,15], 'model__learning_rate':[0.05,0.1]}),
    }
    # Optional strong tabular challengers. Never pretend they were evaluated if absent.
    if importlib.util.find_spec('xgboost') is not None:
        from xgboost import XGBClassifier
        registry['XGBoost']=(pipeline(XGBClassifier(n_estimators=180,n_jobs=1,tree_method='hist',
                                  eval_metric='logloss',random_state=SEED),features),
                              {'model__max_depth':[2,4],'model__learning_rate':[0.035,0.08]})
    if importlib.util.find_spec('catboost') is not None:
        registry['CatBoost']=(pipeline(CatBoostSklearnAdapter(),features),
                              {'model__depth':[4,6],'model__learning_rate':[0.035,0.08]})
    return registry

def metric(y,p):
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float)
    check(np.isfinite(p).all() and ((p>=0)&(p<=1)).all(),'Non-finite or nonprobabilistic model output')
    check(len(y)>15 and len(np.unique(y))==2,'Insufficient evaluation classes')
    pred=(p>=0.5).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'n':int(len(y)),'events':int(y.sum()),
        'roc_auc':round(float(roc_auc_score(y,p)),5),
        'average_precision':round(float(average_precision_score(y,p)),5),
        'brier':round(float(brier_score_loss(y,p)),5),
        'log_loss':round(float(log_loss(y,p,labels=[0,1])),5),
        'sensitivity_at_0_5':round(float(tp/(tp+fn)) if tp+fn else 0,5),
        'specificity_at_0_5':round(float(tn/(tn+fp)) if tn+fp else 0,5)}

def calibration(y,p):
    out=[]
    for lower,upper in zip(np.linspace(0,1,6)[:-1],np.linspace(0,1,6)[1:]):
        subset=((p>=lower)&(p<upper)) if upper<1 else ((p>=lower)&(p<=upper))
        if subset.sum()>=50:
            out.append({'range':[round(float(lower),2),round(float(upper),2)],
                        'n':int(subset.sum()),'mean_predicted':round(float(p[subset].mean()),4),
                        'observed_fraction':round(float(np.asarray(y)[subset].mean()),4)})
    return out

def bootstrap(y,p,n_boot=250):
    rng=np.random.default_rng(SEED)
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float); idx=np.arange(len(y))
    vals={'roc_auc':[],'brier':[]}
    for i in range(n_boot):
        sample=rng.choice(idx,size=len(idx),replace=True)
        if np.unique(y[sample]).size<2:continue
        vals['roc_auc'].append(roc_auc_score(y[sample],p[sample]))
        vals['brier'].append(brier_score_loss(y[sample],p[sample]))
    return {k:[round(float(x),5) for x in np.quantile(v,[0.025,0.975])] for k,v in vals.items() if len(v)>100}

def subgroup_metrics(y,p,frame):
    data=frame.reset_index(drop=True)
    raw_age=data['age'].astype(float)
    groups={'Female':data['sex'].eq('Female'), 'Male':data['sex'].eq('Male'),
            'Age 65-74':raw_age.between(65,74), 'Age 75+ (80 topcoded)':raw_age.ge(75)}
    out=[]
    for name,mask in groups.items():
        mask=np.asarray(mask,dtype=bool);values=np.asarray(y)[mask]
        if len(values)<50 or values.sum()<10 or (len(values)-values.sum())<10:continue
        subset=metric(values,np.asarray(p)[mask])
        out.append({'group':name,'metrics':subset})
    return out

def weighted_sensitivity(y,p,weights):
    w=np.asarray(weights,dtype=float)
    valid=np.isfinite(w)&(w>0)
    if valid.sum()<50 or len(np.unique(np.asarray(y)[valid]))!=2:return None
    return {'n_positive_weights':int(valid.sum()),
            'brier_exploratory_only':round(float(brier_score_loss(np.asarray(y)[valid],
                 np.asarray(p)[valid],sample_weight=w[valid])),5),
            'survey_design_variance_not_estimated':True}

def train(development:pd.DataFrame,heldout:pd.DataFrame,*,fast=False):
    check(development['id'].is_unique and heldout['id'].is_unique,'Duplicate participants')
    check(set(development['id']).isdisjoint(set(heldout['id'])),'Participant leakage across survey cycles')
    check(set(INPUTS).issubset(development.columns) and set(INPUTS).issubset(heldout.columns),'Missing model feature')
    selected_features, availability = feature_contract(development,heldout)
    dev, val = train_test_split(development,test_size=0.2,stratify=development['target'],random_state=SEED)
    check(set(dev['id']).isdisjoint(set(val['id'])),'Development split leakage')
    # Models selected on 2015-16 only, with the identical CV and validation split.
    cv=StratifiedKFold(n_splits=3,shuffle=True,random_state=SEED)
    y_train=dev['target'].astype(int)
    models={};rows=[]
    for label,(pipe,params) in candidates(selected_features).items():
        if fast and label not in ('Dummy prior','Logistic regression','Random forest'):continue
        # One CV split and deterministic grid per family, never access heldout targets.
        if not fast:
            grid=GridSearchCV(pipe,params or {},scoring='neg_brier_score',cv=cv,n_jobs=1,refit=True,error_score='raise')
            grid.fit(dev[selected_features],y_train)
            fit=grid.best_estimator_
            cv_brier=round(float(-grid.best_score_),5)
            best_params={k.replace('model__',''):v for k,v in grid.best_params_.items()}
        else:
            fit=clone(pipe).fit(dev[selected_features],y_train)
            cv_brier=None;best_params={}
        p=fit.predict_proba(val[selected_features])[:,1]
        scores=metric(val['target'],p)
        models[label]=fit
        rows.append({'model':label,'cv_brier':cv_brier,'validation':scores,'hyperparameters':best_params})
    rows.sort(key=lambda row:(row['validation']['brier'],row['model']))
    selected=rows[0]['model']
    # Only selected development winner is assessed on the later untouched cycle ONCE.
    predictor=models[selected]
    p_test=predictor.predict_proba(heldout[selected_features])[:,1]
    y_test=heldout['target'].to_numpy(dtype=int)
    selected_eval=metric(y_test,p_test)
    check(len(heldout)>=100,'Later-cycle minimum sample size 100')
    # Model-agnostic explainability; computed on validation, NEVER on the test cycle.
    vi=permutation_importance(predictor,val[selected_features],val['target'],n_repeats=5,
                              random_state=SEED,scoring='neg_brier_score')
    ranking=sorted(({'feature':k,'brier_increase':round(float(a),6),
                     'std':round(float(b),6)} for k,a,b in zip(selected_features,vi.importances_mean,vi.importances_std)),
                   key=lambda x:-x['brier_increase'])
    return {'selected_model':selected,
            'selection_rule':'LOWEST_VALIDATION_BRIER; LATER_CYCLE_PREVIOUSLY_INSPECTED',
            'feature_availability_contract':availability,
            'later_cycle_prior_exposure':'V48_PREVIOUSLY_INSPECTED; THIS IS REPEAT_SENSITIVITY_NOT_FRESH_CONFIRMATION',
            'model_comparison_development_only':rows,
            'selected_model_later_cycle_test':selected_eval,
            'test_calibration_bands_min_n_50':calibration(y_test,p_test),
            'test_age_sex_subgroups_suppressed_if_n_lt_50_or_events_lt_10':subgroup_metrics(y_test,p_test,heldout),
            'test_survey_weighted_brier_exploratory':weighted_sensitivity(y_test,p_test,heldout['weight']),
            'test_naive_row_bootstrap_95pct_not_survey_design_CI':bootstrap(y_test,p_test,n_boot=60 if fast else 250),
            'validation_permutation_importance_delta_brier':ranking,
            'split':{'development_fit_n':int(len(dev)),'development_selection_n':int(len(val)),
                     'later_cycle_test_n':int(len(heldout))},
            'do_not_interpret_as_future_frailty_or_clinical_prediction':True,
           }

def write_markdown_summary(out:dict,path:Path):
    e=out['experiment'];m=e['selected_model_later_cycle_test']
    lines=['# FrailtyScope — NHANES public mobility experiment','',
     '**Task:** Current self-reported quarter-mile walking difficulty, NOT future risk or a validated frailty measure.',
     '**Cohort:** NHANES 65+, 2015–16 development; 2017–18 later-cycle repeat evaluation (already inspected in v0.48).',
     '**Source:** CDC official public-use XPT; no HUNT or restricted participant data.','',
     '## Dataset and preprocessing','']
    available=e['feature_availability_contract']
    lines.extend(['**Actually modeled predictors:** '+', '.join(available['included_predictors']),
         '**Excluded for insufficient coverage:** '+(', '.join(x['feature'] for x in available['excluded_predictors']) or 'none'),
         '**Important:** The later-cycle outcome and its metrics were already inspected under v0.48; this is NOT a fresh untouched test.',''])
    for label,cohort in out['cohorts'].items():
        lines.append(f"- {label}: {cohort['questionnaire_respondents']} eligible/questionnaire-valid respondents, "
                     f"{cohort['target_events']} with walking difficulty. ")
    lines.extend(['','## Models: selection on development validation Brier (lower is better)','',
                  '| Candidate | Validation ROC-AUC | Validation Brier | 3-fold CV Brier |',
                  '|---|---:|---:|---:|'])
    for row in e['model_comparison_development_only']:
        lines.append(f"| {row['model']} | {row['validation']['roc_auc']:.3f} | "
                     f"{row['validation']['brier']:.3f} | "
                     f"{row['cv_brier']:.3f} |" if row['cv_brier'] is not None else
                     f"| {row['model']} | {row['validation']['roc_auc']:.3f} | "
                     f"{row['validation']['brier']:.3f} | not computed (fixture mode) |")
    lines.extend(['',f"**Selected:** {e['selected_model']} (never selected on later-cycle test)",'',
                  '## Later-cycle evaluation — selected model only','',
                  f"- ROC-AUC: {m['roc_auc']:.3f}",f"- Average precision: {m['average_precision']:.3f}",
                  f"- Brier score: {m['brier']:.3f}",f"- Sensitivity @0.5: {m['sensitivity_at_0_5']:.3f}",
                  f"- Specificity @0.5: {m['specificity_at_0_5']:.3f}",'',
                  '## What this does NOT establish','',
                  '- No prospective risk, no NHANES-to-HUNT validation, and no patient-specific service.',
                  '- The naive row bootstrap is not complex-survey-design uncertainty.',
                  '- Walking-equipment skip and unanswered activity are excluded; selection bias is possible.',
                  '- Public age 80 is top-coded; PHQ-9 requires nine valid items.',
                  '- Full source code, train-only preprocessing and variable contract are reproducible.',''])
    path.write_text('\n'.join(lines),encoding='utf-8')

def audit_feature_coverage(root:Path):
    """Aggregate-only preflight; no model fitting, no scoring, no record export."""
    frames={};reports={}
    for cycle in CYCLES:
        source,_=read_cycle(root,cycle)
        frames[cycle],reports[cycle]=harmonize(source,cycle)
    _,contract=feature_contract(frames['2015-2016'],frames['2017-2018'])
    print(json.dumps({'case_id':CASE_ID,'audit_only':True,
                      'feature_availability':contract,
                      'phq_item_valid_observed_by_cycle':{
                          k:v['dpq_item_valid_observed_n'] for k,v in reports.items()},
                      'phq_complete_n_by_cycle':{
                          k:v['phq9_valid_complete_n'] for k,v in reports.items()},
                      'individual_rows_exported':False,
                      'clinical_prediction':False},indent=2))

def run(root:Path,*,fast=False):
    inputs={};reports={};digests={}
    for cycle in CYCLES:
        df,source_sha=read_cycle(root,cycle)
        frame,report=harmonize(df,cycle)
        inputs[cycle]=frame;reports[cycle]=report;digests.update(source_sha)
    outcome=train(inputs['2015-2016'],inputs['2017-2018'],fast=fast)
    out={'schema':SCHEMA,'case_id':CASE_ID,'source':'CDC_PUBLIC_USE_NHANES_2015_2018',
         'task':'CROSS_SECTIONAL_CURRENT_MOBILITY_LIMITATION_NOT_FUTURE',
         'source_sha256':digests,'software':{'scikit_learn':sklearn.__version__,'pandas':pd.__version__},
         'outcome_definition':'PFQ061B quarter-mile walking: 1=no difficulty vs 2/3/4=difficulty',
         'candidate_predictors':INPUTS,
         'predictors_actually_used':outcome['feature_availability_contract']['included_predictors'],
         'predictor_exclusions':outcome['feature_availability_contract']['excluded_predictors'],
         'candidate_model_families_available':list(candidates()),
         'source_codebook_notes':'PFQ054 equipment skip, 5/7/9/missing excluded; DPQ full 9-item only; age 80 topcoded; diabetes borderline not yes',
         'cohorts':reports,'experiment':outcome,
         'limits':['One-off public cross-sectional surveys; not prospective risk prediction',
                  'No NHANES complex-survey design-based population inference',
                  'Selection bias from nonresponse, disability equipment routing, MEC/PHQ eligibility',
                  'Later wave already assessed in v0.48; rerun is repeat sensitivity, NOT untouched test',
                  'Later wave evaluation is temporal transfer only, not HUNT external clinical validation',
                  'Single outcome, never a validated clinical frailty diagnosis',
                  'No real participant rows, individual predictions or model binaries exported'],
         'clinical_prediction_permitted':False,
         }
    target=root/'results'/'mobility_aggregate_v48.json'
    check(not target.is_symlink(),'Unsafe output symlink')
    with target.open('w',encoding='utf8') as f:json.dump(out,f,indent=2,allow_nan=False);f.write('\n')
    write_markdown_summary(out,root/'results'/'mobility_report_v48.md')
    print('RESULT WRITTEN:',target,'(aggregate only; no individual predictions)')
    print('FEATURE AVAILABILITY:',json.dumps(outcome['feature_availability_contract'],sort_keys=True))
    print('PREVIOUSLY INSPECTED LATER CYCLE: v0.48 already scored 2017-18; rerun is exploratory.')
    print('WINNER:',outcome['selected_model'],'val Brier:',outcome['model_comparison_development_only'][0]['validation']['brier'],
          'later-wave ROC AUC:',outcome['selected_model_later_cycle_test']['roc_auc'])
    print('WARNING: CURRENT walking difficulty, NOT future frailty, HUNT or patient inference.')
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root',type=Path)
    p.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--download',action='store_true')
    p.add_argument('--run',action='store_true')
    p.add_argument('--audit-coverage',action='store_true',help='Aggregate predictor availability only; no fitting or scoring')
    p.add_argument('--contract',action='store_true')
    a=p.parse_args()
    if a.contract:
        print(json.dumps({'case_id':CASE_ID,'cycles':CYCLES,'files':[f'{k}_{s}.XPT' for _,s in CYCLES.values() for k in TABLES],
         'input_features':INPUTS,'outcome':'PFQ061B_CURRENT_MOBILITY_ONLY',
         'legacy_mortality_reopened':False,'clinical_prediction':False},indent=2))
        return
    check(a.data_root is not None and (a.download or a.run or a.audit_coverage),
          'Supply --data-root and --download, --audit-coverage and/or --run')
    root=safe_root(a.data_root,a.project_root)
    if a.download:download(root)
    if a.audit_coverage:audit_feature_coverage(root)
    if a.run:run(root)
if __name__=='__main__':main()
