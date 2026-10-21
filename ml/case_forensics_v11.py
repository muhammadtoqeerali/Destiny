"""Case-independent, split-aware forensic EDA and model review, local-first.

Public export must go through export_case_audit_v11.py; report here can contain
locally visible examples. Never check local report, IDs, predictions into Git.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from ml.case_engine_v10 import validate_manifest, load_data, split_data, digest, fit_pipeline
from ml.case_model_io_v11 import load_canonical_trusted_model

LABELS = {'age':'Age (years; 80+ top-coded)','bmi':'Body mass index (kg/m²)',
    'walking_difficulty':'Walking limitation (1–4)','stairs_difficulty':'Stair limitation (1–4)',
    'stooping_difficulty':'Stooping limitation (1–4)', 'heart_failure':'Heart failure',
    'coronary_disease':'Coronary disease','stroke':'Stroke','cancer':'Cancer history',
    'diabetes':'Diabetes','hypertension':'Hypertension','ever_smoked':'Smoking history',
    'phq9_score':'PHQ-9 (0–27)','sex':'Sex'}
# These are data dictionary descriptions, not inferred diagnoses.
DESCRIPTIONS = {'age':'Interview age; age 80+ is top-coded in this public-use cohort.',
    'bmi':'Exam-measured body mass index; not a clinical diagnosis.',
    'phq9_score':'Sum of nine valid responses coded 0–3; requires all nine valid items.',
    'walking_difficulty':'Reported difficulty walking; 1=no, 2=some, 3=much, 4=unable.',
    'stairs_difficulty':'Reported difficulty on stairs; 1=no, 2=some, 3=much, 4=unable.',
    'stooping_difficulty':'Reported difficulty stooping; 1=no, 2=some, 3=much, 4=unable.',
    'sex':'Sex code from the NHANES public-use questionnaire.'}
MIN_BIN = 20

def finite(v):
    return None if v is None or not np.isfinite(float(v)) else round(float(v),4)

def pct(n,d):return round(100*n/d,2) if d else 0.

def quantiles(s:pd.Series)->dict:
    x=pd.to_numeric(s,errors='coerce').dropna().to_numpy(float)
    if not len(x):return {}
    p=np.percentile(x,[0,1,25,50,75,99,100]);return dict(zip(('min','p01','q25','median','q75','p99','max'),[finite(v) for v in p]))

def feature_profile(frame:pd.DataFrame,col:str,kind:str)->dict:
    s=frame[col];n=len(s);ok=s.notna();observed=int(ok.sum());missing=n-observed
    base={'feature':col,'label':LABELS.get(col,col.replace('_',' ').title()),
      'description':DESCRIPTIONS.get(col,'Recorded study variable; interpret using source codebook.'),
      'type':kind,'observed':observed,'missing':missing,'missing_pct':pct(missing,n),
      'unique':int(s.nunique(dropna=True))}
    if kind=='numeric':
        v=pd.to_numeric(s,errors='coerce').dropna()
        q=quantiles(v);base['summary']=q
        if len(v)>3:
            iqr=q['q75']-q['q25'];outliers=int(((v<q['q25']-1.5*iqr)|(v>q['q75']+1.5*iqr)).sum())
            base['iqr_outlier_pct']=pct(outliers,n) if iqr>0 else 0.
        else:base['iqr_outlier_pct']=None
        # Discrete coded health conditions and functioning scales: real frequencies.
        if v.nunique()<=8:
            counts=v.value_counts().sort_index()
            codes={0:'No',1:'Yes'} if col in {'heart_failure','coronary_disease','stroke','cancer','diabetes','hypertension','ever_smoked'} else {}
            if col in {'walking_difficulty','stairs_difficulty','stooping_difficulty'}:
                codes={1:'No difficulty',2:'Some difficulty',3:'Much difficulty',4:'Unable'}
            base['distribution']=[{'bin':codes.get(int(z),str(finite(z))),'n':int(count)}
                for z,count in counts.items() if count>=MIN_BIN]
            base['distribution_suppressed_n']=int(sum(count for count in counts.values if count<MIN_BIN))
        # Continuous quantities: quantile bins. Never export raw individual values.
        elif len(v)>=4*MIN_BIN and v.nunique()>4:
            edges=np.unique(np.quantile(v,[0,.2,.4,.6,.8,1]))
            if len(edges)>2:
                freq=pd.cut(v,bins=edges,include_lowest=True,duplicates='drop').value_counts(sort=False)
                base['distribution']=[{'bin':f'{finite(z.left)}–{finite(z.right)}','n':int(count)} for z,count in freq.items() if count>=MIN_BIN]
                base['distribution_suppressed_n']=int(sum(count for count in freq.values if count<MIN_BIN))
    else:
        counts=s.fillna('Missing').astype(str).value_counts()
        base['distribution']=[{'bin':str(code)[:45],'n':int(count)} for code,count in counts.items() if count>=MIN_BIN and code!='Missing'][:20]
        base['distribution_suppressed_n']=int(sum(count for code,count in counts.items() if count<MIN_BIN and code!='Missing'))
    return base

def cross_cycle_shift(frame,indices_a,indices_b,cols):
    shifts=[]
    for c in cols:
        a=pd.to_numeric(frame.iloc[indices_a][c],errors='coerce').dropna()
        b=pd.to_numeric(frame.iloc[indices_b][c],errors='coerce').dropna()
        if len(a)<50 or len(b)<50:continue
        denom=math.sqrt((a.var(ddof=1)+b.var(ddof=1))/2)
        smd=abs(float(a.mean()-b.mean()))/denom if denom>1e-10 else 0.
        shifts.append({'feature':c,'standardized_mean_difference':finite(smd),
            'development_missing_pct':pct(len(indices_a)-len(a),len(indices_a)),
            'evaluation_missing_pct':pct(len(indices_b)-len(b),len(indices_b))})
    return sorted(shifts,key=lambda z: -(z['standardized_mean_difference'] or 0))

def correlations(frame,numeric):
    numeric=list(numeric)
    if len(numeric)<2:return []
    df=frame[numeric].apply(pd.to_numeric,errors='coerce')
    corr=df.corr(method='spearman',min_periods=80)
    pairs=[]
    for j,left in enumerate(numeric):
        for right in numeric[j+1:]:
            v=corr.loc[left,right]
            if np.isfinite(v):pairs.append({'a':left,'b':right,'spearman_rho':finite(v)})
    return sorted(pairs,key=lambda p:-abs(p['spearman_rho']))[:18]

def preprocessing_audit(model,frame,train_idx,val_idx,num,cat):
    """Read exact fitted transformers, not an approximate preprocessing recipe."""
    tr=model.named_steps['features'];p=tr.named_transformers_
    output=[];example=[]
    for ix,c in enumerate(num):
        imp=p['numeric'].named_steps['impute'];scale=p['numeric'].named_steps['scale']
        med=float(imp.statistics_[ix]);mean=float(scale.mean_[ix]);std=float(scale.scale_[ix]);
        before=pd.to_numeric(frame.iloc[train_idx][c],errors='coerce');v=pd.to_numeric(frame.iloc[val_idx][c],errors='coerce')
        output.append({'feature':c,'label':LABELS.get(c,c),'method':'Median imputation + z-score',
             'fit_partition':'Training only','training_missing':int(before.isna().sum()),
             'validation_missing':int(v.isna().sum()),'after_missing':0,
             'impute_value':finite(med),'center':finite(mean),'scale':finite(std),
             'observed_training_median':finite(before.median()),'transformed_training_median':finite((med-mean)/std),
             'before_range':quantiles(before),'after_range':quantiles((before.fillna(med)-mean)/std)})
        example.append({'feature':c,'label':LABELS.get(c,c), 'source':'Training quartile values; not individual records',
            'before':[finite(before.quantile(k)) for k in (.25,.5,.75)],
            'after':[finite((before.quantile(k)-mean)/std) for k in (.25,.5,.75)]})
    for ix,c in enumerate(cat):
        pipe=p['category'];imputer=pipe.named_steps['impute'];encoder=pipe.named_steps['encode']
        cats=[str(k) for k in encoder.categories_[ix]]
        output.append({'feature':c,'label':LABELS.get(c,c),'method':'Most frequent imputation + one-hot encoding',
            'fit_partition':'Training only','training_missing':int(frame.iloc[train_idx][c].isna().sum()),
            'validation_missing':int(frame.iloc[val_idx][c].isna().sum()),'after_missing':0,
            'impute_value':str(imputer.statistics_[ix]),'output_columns':[f'{c} = {v}' for v in cats]})
    n_output=int(tr.transform(frame.iloc[train_idx[:1]][num+cat]).shape[1])
    return {'methods':output,'quantile_examples':example,'input_feature_count':len(num)+len(cat),
       'output_feature_count':n_output,'note':'Training-only fitted values; quartile examples are summaries, not respondent records.'}

def calibration(y,prob,k=8):
    """Quantile reliability bins; only publish groups with >=50 observations."""
    s=pd.DataFrame({'actual':np.asarray(y,int),'prob':np.asarray(prob,float)})
    if len(s)<400:return []
    s['group']=pd.qcut(s['prob'].rank(method='first'),q=min(k,len(s)//50),labels=False,duplicates='drop')
    out=[]
    for i,g in s.groupby('group'):
        if len(g)>=50:
            out.append({'bin':int(i)+1,'n':len(g),'predicted':finite(g.prob.mean()),
                'observed':finite(g.actual.mean())})
    return out

def performance_groups(frame,y,prob,threshold,idx):
    if not {'age','sex'}.issubset(frame):return []
    sub=frame.iloc[idx];labels=np.asarray(y,int);probs=np.asarray(prob,float)
    groups={'65–69':(sub.age>=65)&(sub.age<=69),'70–74':(sub.age>=70)&(sub.age<=74),
            '75–79':(sub.age>=75)&(sub.age<=79),'80+':sub.age>=80,
            'Female':sub.sex.eq('Female'),'Male':sub.sex.eq('Male')}
    out=[]
    for name,mask in groups.items():
        ids=np.flatnonzero(np.asarray(mask));yy=labels[ids];pp=probs[ids]
        n=len(yy);ev=int(yy.sum())
        if n<100 or ev<20 or n-ev<20:continue
        pred=pp>=threshold
        out.append({'group':name,'n':n,'events':ev,'event_rate':finite(yy.mean()),
            'roc_auc':finite(roc_auc_score(yy,pp)),
            'recall':finite((pred & (yy==1)).sum()/ev),
            'false_positive_rate':finite((pred & (yy==0)).sum()/(n-ev)),
            'brier':finite(brier_score_loss(yy,pp))})
    return out

def learning_curve(frame,y,train_idx,val_idx,spec,candidates):
    """Training-size diagnostic of the already selected model; never use evaluation rows."""
    selected=next(z for z in candidates if z['model']==spec['_winner'])
    if spec['task']!='classification':return []
    params=selected['parameters'];num=spec['features']['numeric'];cat=spec['features']['categorical'];cols=num+cat
    iy=np.asarray(train_idx);result=[]
    for fraction in (0.25,0.5,0.75,1.):
        if fraction==1.: ids=iy
        else:
            ids,_=train_test_split(iy,train_size=fraction,stratify=y.iloc[iy],random_state=2026)
        candidate=fit_pipeline(num,cat,selected['model'],spec['task'],params,frame.iloc[ids][cols],y.iloc[ids])
        tprob=candidate.predict_proba(frame.iloc[ids][cols])[:,1]
        vprob=candidate.predict_proba(frame.iloc[val_idx][cols])[:,1]
        result.append({'train_n':len(ids),'training_brier':finite(brier_score_loss(y.iloc[ids],tprob)),
          'validation_brier':finite(brier_score_loss(y.iloc[val_idx],vprob))})
    return result

def raw_local_preview(frame,train_idx,model,num,cat,limit=5):
    """Workstation-only illustration: real de-identified training rows, no IDs."""
    ids=np.asarray(train_idx[:limit]);d=frame.iloc[ids][num+cat]
    tr=model.named_steps['features'].transform(d)
    if hasattr(tr,'toarray'):tr=tr.toarray()
    return [{'record':f'Local row {i+1}',
      'raw':{c:(None if pd.isna(v) else str(v)[:60]) for c,v in zip(num+cat,row)},
      'transformed_vector':[finite(v) for v in np.asarray(tr[i]).ravel().tolist()]}
      for i,row in enumerate(d.itertuples(index=False,name=None))]

def generate(project:Path,spec:dict):
    validate_manifest(spec)
    frame,y,sha=load_data(project,spec)
    train,val,test=split_data(frame,y,spec)
    out=project/'artifacts'/'cases'/spec['case_id']
    metrics=json.loads((out/'metrics.json').read_text())
    if metrics['dataset_sha256']!=sha or metrics['case_id']!=spec['case_id']:
        raise ValueError('Experiment fingerprint mismatch: retrain case first')
    if metrics['task']!=spec['task']:raise ValueError('Task mismatch')
    # Never load arbitrary model files. Local artifacts from one's own pipeline only.
    model=load_canonical_trusted_model(out/'best_model.joblib')
    num=spec['features']['numeric'];cat=spec['features']['categorical'];features=num+cat
    source=frame.iloc[test][features];values=np.asarray(model.predict_proba(source)[:,1] if spec['task']=='classification' else model.predict(source))
    if spec['task']=='classification':
        from ml.case_engine_v10 import calculate_metrics
        now=calculate_metrics('classification',y.iloc[test],values,values,float(metrics['selected_threshold']))
        for metric in ('roc_auc','brier','recall','precision'):
            if abs(now[metric]-metrics['evaluation'][metric])>0.002:
                raise ValueError('Saved fitted model and case metrics disagree on '+metric)
        if now['confusion']!=metrics['evaluation']['confusion']:
            raise ValueError('Saved model predictions do not reproduce reported evaluation counts')
    base={'schema':'FRAILTYSCOPE_CASE_AUDIT_V11','report_type':'LOCAL_DEIDENTIFIED_AUDIT',
        'case_id':spec['case_id'],'source_sha256':sha,'task':spec['task'],
        'counts':{'all':len(frame),'train':len(train),'validation':len(val),'evaluation':len(test)},
        'feature_profiles':[feature_profile(frame,c,'numeric' if c in num else 'categorical') for c in features],
        'cohort_shift':cross_cycle_shift(frame, np.r_[train,val],test,num),
        'correlations':correlations(frame.iloc[train],num),
        'preprocessing':preprocessing_audit(model,frame,train,val,num,cat),
        'selection':{'metric':metrics['selection_metric'],'model':metrics['selected_model'],
          'candidates':[{'name':r['model'],'cv_score':r['cv_score'],
          'validation':r['validation'],'parameters':r['parameters'],
          'fit_search_seconds':r['fit_search_seconds']} for r in metrics['candidate_models']],
          'permutation_importance_validation':metrics['permutation_importance_validation'],
          'learning_curve':learning_curve(frame,y,train,val,{**spec,'_winner':metrics['selected_model']},metrics['candidate_models'])},
        'evaluation':{'metrics':metrics['evaluation'],'baseline':metrics['dummy_baseline_evaluation']},
        'local_examples':raw_local_preview(frame,train,model,num,cat),
        'methodology':{'selection':'Lowest validation Brier score among trained candidates, following training-only Optuna CV.',
          'data_split':'Training and validation: 2011–2012; evaluation: 2013–2014.',
          'is_external_validation':False,'preprocessing':'Fitted on training subset only; no evaluation-derived parameters.',
          'limitations':['Later survey cycle had already been inspected in earlier project iterations.',
             'Population survey with unweighted model-performance metrics; no design-based confidence intervals.',
             'Public mortality times may be disclosure-perturbed. Not a clinical prediction system.']}}
    quality_file=project/'artifacts'/'realdata_nhanes'/'quality_v08.json'
    if spec['case_id']=='nhanes_mortality_v10' and quality_file.is_file():
        quality=json.loads(quality_file.read_text())
        if quality['sample_size']!=len(frame) or quality['phq9_flag']!='COVERAGE_OK':
            raise ValueError('PHQ-9 source correction not validated against active cohort')
        cycles=quality['phq9_by_cycle']
        base['data_integrity']={'phq9_observed_percent':float(quality['phq9_complete_percent']),
           'source_check_mismatches':int(sum(z['mismatch_count'] for z in cycles.values())),
           'xport_zero_values_normalized':int(sum(z.get('xport_zero_alias_values_corrected',0) for z in cycles.values())),
           'reporting':'Verified against raw CDC DPQ files after correcting SAS XPORT zero aliases'}
    if spec['task']=='classification':
        threshold=float(metrics['selected_threshold']);probs=np.asarray(values,float)
        base['evaluation']['calibration']=calibration(y.iloc[test].to_numpy(),probs)
        base['evaluation']['subgroups']=performance_groups(frame,y.iloc[test].to_numpy(),probs,threshold,test)
        base['evaluation']['observed_prevalence']=finite(np.asarray(y.iloc[test]).mean())
    else:
        base['evaluation']['calibration']=[];base['evaluation']['subgroups']=[]
    return base

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',default='research/cases/nhanes_mortality_v10.json');p.add_argument('--project',default='.')
    args=p.parse_args();project=Path(args.project).resolve();cfg=(project/args.config).resolve()
    if not cfg.is_relative_to(project):raise ValueError('Config must be inside project')
    spec=json.loads(cfg.read_text());r=generate(project,spec)
    out=(project/'artifacts'/'cases'/spec['case_id']/'forensic_audit_v11_local.json')
    out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print('LOCAL FORENSIC AUDIT:',out,'features',len(r['feature_profiles']),'split counts',r['counts'])
    print('Real local examples confined to local ignored artifacts. No public export from this command.')
if __name__=='__main__':main()
