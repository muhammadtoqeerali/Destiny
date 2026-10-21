"""Private NHANES exploratory penalized Cox benchmark.

Real survey records stay on the workstation. Uses perturbed public-use mortality
follow-up; no survey-design-valid CIs or clinical prediction claims.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp
from scipy.stats import rankdata
from ml.realdata_nhanes import (BASE_FEATURES, COMPONENTS, CYCLES,
    as_features, read_mortality)

HORIZON = 60.0
FEATURES = tuple(BASE_FEATURES)


def construct_time_to_event(frame: pd.DataFrame, horizon: float = HORIZON) -> pd.DataFrame:
    """Keep early-censored records; avoid binary-horizon selection bias."""
    if not {'ELIGSTAT','MORTSTAT','PERMTH_EXM'}.issubset(frame):
        raise ValueError('Linked mortality columns missing')
    d = frame.copy()
    for key in ['ELIGSTAT','MORTSTAT','PERMTH_EXM']:
        d[key] = pd.to_numeric(d[key], errors='coerce')
    okay = (d.ELIGSTAT.eq(1) & d.MORTSTAT.isin([0,1]) &
            np.isfinite(d.PERMTH_EXM) & d.PERMTH_EXM.ge(0))
    d = d.loc[okay].copy()
    d['duration'] = np.minimum(d.PERMTH_EXM.to_numpy(float), horizon)
    d['event'] = ((d.MORTSTAT.eq(1)) & (d.PERMTH_EXM.le(horizon))).astype(int)
    if d.empty or (d.duration < 0).any() or not d.event.isin([0,1]).all():
        raise ValueError('Invalid time-to-event observations')
    return d


def load_cohort(raw_dir: Path) -> pd.DataFrame:
    """Read all required files locally; include censored before 60 months."""
    frames = []
    for cycle,suffix in CYCLES.items():
        tables = []
        for component in COMPONENTS:
            source=raw_dir/cycle/f'{component}_{suffix}.XPT'
            if not source.is_file():raise FileNotFoundError('Expected cached CDC source: '+str(source))
            d = pd.read_sas(source, format='xport')
            if 'SEQN' not in d or d.SEQN.duplicated().any():
                raise ValueError(f'Invalid sequence identifiers in {component}/{cycle}')
            d['SEQN'] = pd.to_numeric(d.SEQN, errors='coerce').astype('Int64')
            tables.append(d)
        merged = tables[0]
        for d in tables[1:]:
            merged = merged.merge(d, on='SEQN', how='left', validate='one_to_one')
        merged = as_features(merged)
        merged = merged[merged.age.ge(65)].copy()
        mortality_source=raw_dir/cycle/f'NHANES_{cycle.replace("-","_")}_MORT_2019_PUBLIC.dat'
        if not mortality_source.is_file():raise FileNotFoundError('Expected cached linked mortality: '+str(mortality_source))
        mort = read_mortality(mortality_source)
        merged = merged.merge(mort[['SEQN','ELIGSTAT','MORTSTAT','PERMTH_EXM']],
                              on='SEQN', how='inner', validate='one_to_one')
        merged = construct_time_to_event(merged)
        merged['cycle'] = cycle
        frames.append(merged[['SEQN','cycle','duration','event',*FEATURES]])
    cohort = pd.concat(frames, ignore_index=True)
    if cohort.duplicated(['SEQN','cycle']).any():
        raise ValueError('Duplicate respondent')
    if len(cohort) < 2000 or not set(cohort.cycle)==set(CYCLES):
        raise ValueError('Unexpected real NHANES cohort composition')
    return cohort


class Preprocess:
    def __init__(self):
        self.medians = None
        self.scales = None
        self.use_missing_indicator = None
        self.names = None

    @staticmethod
    def numeric(frame:pd.DataFrame)->np.ndarray:
        out = pd.DataFrame(index=frame.index)
        for col in FEATURES:
            if col == 'sex':
                out[col] = frame[col].map({'Male':1, 'Female':0})
            else:
                out[col] = pd.to_numeric(frame[col], errors='coerce')
        return out.to_numpy(dtype=float)

    def fit(self, frame:pd.DataFrame):
        x = self.numeric(frame)
        if not np.isfinite(x[~np.isnan(x)]).all():raise ValueError('Nonfinite covariate')
        with np.errstate(all='ignore'):
            median = np.nanmedian(x, axis=0)
        if not np.isfinite(median).all():raise ValueError('Training feature entirely missing')
        filled = np.where(np.isnan(x), median, x)
        scales = np.std(filled, axis=0)
        self.medians = median
        self.scales = np.where(scales > 1e-6, scales, 1.)
        self.use_missing_indicator = np.isnan(x).mean(axis=0) > 0
        self.names = [f'feature:{z}' for z in FEATURES] + [f'missing:{FEATURES[i]}' for i in range(len(FEATURES)) if self.use_missing_indicator[i]]
        return self

    def transform(self, frame:pd.DataFrame)->np.ndarray:
        if self.medians is None:raise ValueError('Preprocessing not fit')
        x = self.numeric(frame)
        missing = np.isnan(x)
        filled = np.where(missing, self.medians, x)
        if not np.isfinite(filled).all():raise ValueError('Nonfinite covariates')
        return np.column_stack(((filled-self.medians)/self.scales, missing[:,self.use_missing_indicator].astype(float)))


def penalized_cox(x:np.ndarray, time:np.ndarray, event:np.ndarray, alpha:float):
    """Breslow-tie penalized partial likelihood, analytic gradient, training only."""
    x=np.asarray(x,dtype=float); t=np.asarray(time,dtype=float); e=np.asarray(event,dtype=int)
    if x.ndim!=2 or x.shape[0]!=len(t) or len(t)!=len(e) or len(t)<10:
        raise ValueError('Shape error')
    if not np.isfinite(x).all() or not np.isfinite(t).all() or (t<0).any() or not set(e).issubset({0,1}):
        raise ValueError('Invalid survival data')
    if e.sum()<2 or alpha<=0:raise ValueError('Need deaths and positive penalization')
    event_times=np.unique(t[e==1])
    groups=[(x[(t==tt)&(e==1)].sum(axis=0),
             int(((t==tt)&(e==1)).sum()),x[t>=tt]) for tt in event_times]
    n_events=e.sum()
    def objective(beta):
        loss=0.;grad=np.zeros_like(beta)
        for sum_evt,death_count,risk_x in groups:
            z=risk_x@beta
            logden=logsumexp(z)
            weights=np.exp(z-logden)
            loss += death_count*logden - sum_evt@beta
            grad += death_count*(weights@risk_x)-sum_evt
        return float(loss/n_events + .5*alpha*sum(beta*beta)),grad/n_events+alpha*beta
    res=minimize(objective,np.zeros(x.shape[1]),method='L-BFGS-B',jac=True,options={'maxiter':300,'ftol':1e-10})
    if not res.success and np.linalg.norm(res.jac)>0.005:
        raise RuntimeError('Cox fitting failed to converge: '+str(res.message))
    beta=res.x
    scores=x@beta
    event_durations=np.unique(t[e==1])
    increments=np.array([np.sum((t==tt)&(e==1))/np.exp(logsumexp(scores[t>=tt])) for tt in event_durations])
    return beta,event_durations,np.cumsum(increments)


def predict_event_risk(x:np.ndarray,beta:np.ndarray,event_times:np.ndarray,base_cumhaz:np.ndarray,horizon:float=HORIZON)->np.ndarray:
    k=np.searchsorted(event_times,horizon,side='right')-1
    base=float(base_cumhaz[k]) if k>=0 else 0.
    risk=1-np.exp(-base*np.exp(np.clip(np.asarray(x)@beta,-40,40)))
    return np.clip(risk,0.,1.)


def censor_km(t:np.ndarray,e:np.ndarray):
    """Estimate censoring survival in development only; events aren't censorings."""
    t=np.asarray(t,float);e=np.asarray(e,int)
    dates=np.unique(t[e==0]);g=1.;rows=[]
    for date in dates:
        at=int((t>=date).sum());c=int(((t==date)&(e==0)).sum())
        before=g
        if at>0:g*=1-c/at
        rows.append((float(date),before,g))
    return rows


def g_at(rows:list, time:float, before:bool=False)->float:
    g=1.
    for tt,b,a in rows:
        if tt < time or (tt==time and not before):g=a
        else:break
    return float(g)


def ipcw_brier_at(t:np.ndarray,e:np.ndarray,risk:np.ndarray,censor_model:list,horizon:float=HORIZON):
    t=np.asarray(t,float);e=np.asarray(e,int);risk=np.asarray(risk,float)
    if not (len(t)==len(e)==len(risk)):raise ValueError('IPCW dimensions')
    if not (np.isfinite(t).all() and np.isfinite(risk).all() and ((risk>=0)&(risk<=1)).all()):raise ValueError('Invalid IPCW observations')
    output=np.zeros(len(t));survive=t>=horizon;death=(e==1)&(t<=horizon)
    # A death at exactly horizon is an event, never double-count it as survived.
    survive &= ~death
    # Artificial administrative cutoff at 60m is not censoring *before* 60m.
    g_h=g_at(censor_model,horizon,before=True)
    if g_h < 0.05:raise ValueError('Censoring survival too small at horizon')
    output[survive]=(risk[survive]**2)/g_h
    for i in np.where(death)[0]:
        g=g_at(censor_model,t[i],before=True)
        if g<0.05:raise ValueError('Censoring survival too small at event time')
        output[i]=((1-risk[i])**2)/g
    return float(output.mean()),int((~(survive|death)).sum())


def concordance(t:np.ndarray,e:np.ndarray,score:np.ndarray)->float:
    t=np.asarray(t,float);e=np.asarray(e,int);z=np.asarray(score,float)
    correct=0.;pairs=0
    for i in np.flatnonzero(e==1):
        comp=t>t[i]
        pairs+=int(comp.sum())
        correct+=float((z[i]>z[comp]).sum()+.5*(z[i]==z[comp]).sum())
    if not pairs:raise ValueError('No comparable event pairs')
    return correct/pairs


def observed_horizon_auc(t,e,risk,horizon=HORIZON):
    event=(e==1)&(t<=horizon)
    survive=(t>=horizon)&(~event)
    selected=event|survive
    y=event[selected].astype(int);r=risk[selected]
    if y.sum()==0 or y.sum()==len(y):raise ValueError('Only one outcome class')
    ranks=rankdata(r,method='average')
    auc=(ranks[y==1].sum()-(y.sum()*(y.sum()+1)/2))/(y.sum()*(len(y)-y.sum()))
    return float(auc),int(selected.sum()),int((~selected).sum())


def run(cohort:pd.DataFrame)->dict:
    needed={'cycle','duration','event',*FEATURES}
    if not needed.issubset(cohort):raise ValueError('Survival cohort schema incomplete')
    dev=cohort.loc[cohort.cycle.eq('2011-2012')].copy()
    later=cohort.loc[cohort.cycle.eq('2013-2014')].copy()
    if len(dev)<100 or len(later)<100:raise ValueError('Expected distinct real NHANES cycles')
    prep=Preprocess().fit(dev)
    x=prep.transform(dev);xt=prep.transform(later)
    t=dev.duration.to_numpy(float);e=dev.event.to_numpy(int)
    t2=later.duration.to_numpy(float);e2=later.event.to_numpy(int)
    g=censor_km(t,e)
    # Penalty selected on 3-fold training-cycle CV; never look at later-cycle outcomes.
    ids=np.arange(len(dev))
    # Split based on deterministic permuted indices; preprocessing MUST be refit per fold.
    rng=np.random.default_rng(2026);folds=np.array_split(rng.permutation(len(dev)),3)
    result=[]
    for a in (0.01,0.05,0.2):
        vals=[]
        for k in range(3):
            tr=np.setdiff1d(ids,folds[k]);va=folds[k]
            p=Preprocess().fit(dev.iloc[tr]);a_tr=p.transform(dev.iloc[tr]);a_va=p.transform(dev.iloc[va])
            beta,tt,ch=penalized_cox(a_tr,t[tr],e[tr],a)
            r=predict_event_risk(a_va,beta,tt,ch)
            b,_=ipcw_brier_at(t[va],e[va],r,censor_km(t[tr],e[tr]))
            vals.append(b)
        result.append({'penalty':a,'cv_ipcw_brier_60m':round(float(np.mean(vals)),6)})
    chosen=min(result,key=lambda v:v['cv_ipcw_brier_60m'])['penalty']
    beta,et,baseline=penalized_cox(x,t,e,chosen)
    r=predict_event_risk(xt,beta,et,baseline)
    b,cens=ipcw_brier_at(t2,e2,r,g)
    auc,eligible,cens_auc=observed_horizon_auc(t2,e2,r)
    return {
     'source':'CDC NHANES 2011-2014 and 2019 public-use linked mortality',
     'report_type':'LOCAL_SURVIVAL_RESEARCH_ONLY',
     'endpoint':'Exploratory 60-month all-cause mortality; disclosure-perturbed public-use times',
     'study_design':'Development 2011-12 only; later-cycle 2013-14 evaluated after prior inspection',
     'counts':{'development':int(len(dev)),'later_cycle':int(len(later)),
               'development_events_by_60m':int(e.sum()),'later_cycle_events_by_60m':int(e2.sum()),
               'later_cycle_censored_before_60m':int(cens)},
     'method':{'algorithm':'Penalized Cox proportional hazards (Breslow ties)','cv_folds':3,
               'penalty_selected':float(chosen),'penalty_cv_results':result,
               'missingness':'Training-cycle fold-specific median imputation and missing indicators',
               'preprocessing':'Standardized on development only, no identifier or mortality time as predictors'},
     'later_cycle':{'harrell_c':round(float(concordance(t2,e2,xt@beta)),4),
                    'ipcw_brier_60m':round(float(b),4),
                    'ipcw_censor_reference':'Development-cycle censoring KM',
                    'complete_case_roc_auc_60m':round(float(auc),4),
                    'horizon_outcome_known_n':eligible,'horizon_unknown_censored_n':cens_auc},
     'feature_names':prep.names,
     'limitations':['Exploratory model, not an individual prognosis; no clinical use.',
       'The 2019 public-use follow-up durations may be synthetically substituted for confidentiality.',
       'No NHANES complex survey design adjustment, variance estimation, or site-external validation.',
       'Cox proportional-hazards assumption not yet validated and estimates not clinically calibrated.',
       'Later survey cycle previously inspected; this is a reused benchmark, not untouched external validation.']
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-dir',default='data/raw/nhanes')
    p.add_argument('--output',default='artifacts/realdata_nhanes/cox_v09_local.json')
    a=p.parse_args()
    dest=Path(a.output)
    approved=Path('artifacts/realdata_nhanes').resolve()
    if not dest.resolve().is_relative_to(approved):
        raise ValueError('Report must remain under local artifacts/realdata_nhanes/')
    result=run(load_cohort(Path(a.raw_dir)))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('LOCAL RESEARCH ONLY: survival report at',dest)
    print('Later cycle evaluation:',json.dumps(result['later_cycle'],indent=2))
    print('No participant-level records, scores or identifiers were written.')

if __name__=='__main__':main()
