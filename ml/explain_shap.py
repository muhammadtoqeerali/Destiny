"""Optional SHAP for the *synthetic* selected multi-outcome model.

Outputs local explanation report only; never writes to the public frontend.
SHAP explains model response, NOT a feature's causal medical effect.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from ml.multioutcome import make_synthetic_cohort


def run(outcome:str,artifacts:Path,seed:int=42,n:int=6000,n_background:int=25,n_cases:int=5)->dict:
    import shap
    path=artifacts/f'{outcome}.joblib'
    state=joblib.load(path)
    if state.get('synthetic_only') is not True or state.get('target')!=outcome:
        raise ValueError('Only locally trained synthetic-model artifacts supported by this demonstration')
    df=make_synthetic_cohort(n=n,seed=seed)
    from ml.advanced_multitarget import split_synthetic
    train,_,test=split_synthetic(df,seed)
    pipe=state['pipeline']
    cols=state['features']
    pre=pipe.named_steps['preprocess']
    feature_names=pre.get_feature_names_out()
    background=pre.transform(df.iloc[train[:n_background]][cols])
    examples=pre.transform(df.iloc[test[:n_cases]][cols])
    def predict(matrix):
        return pipe.named_steps['classifier'].predict_proba(matrix)[:,1]
    explainer=shap.Explainer(predict,shap.maskers.Independent(background),algorithm='permutation')
    vals=explainer(examples,max_evals=2*len(feature_names)+1)
    global_rank=np.mean(np.abs(vals.values),axis=0)
    ranking=sorted(zip(feature_names,global_rank),key=lambda x:float(x[1]),reverse=True)
    return {'origin':'SYNTHETIC','outcome':outcome,'method':'SHAP permutation on preprocessed inputs',
            'units':'predicted probability','nCases':n_cases,
            'features':[{'name':str(name),'mean_abs_shap':round(float(value),6)} for name,value in ranking[:12]],
            'caveat':'SHAP measures model-attribution relative to the given background. Not causal, not clinical validation.'}


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--outcome',default='fall_within_12m')
    a.add_argument('--n',type=int,default=6000)
    a.add_argument('--seed',type=int,default=42)
    a.add_argument('--artifacts',default='artifacts')
    a.add_argument('--output',default='artifacts/shap_synthetic.json')
    args=a.parse_args()
    path=Path(args.output)
    if 'web/public' in path.as_posix():a.error('Local SHAP report must never be saved in public website assets')
    report=run(args.outcome,Path(args.artifacts),args.seed,args.n)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('Saved local synthetic explanation:',path)

if __name__=='__main__':main()
