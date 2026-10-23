#!/usr/bin/env python3
"""Reproducible teaching-only models on invented pseudo-records; no NHANES/HUNT access.

Runs entirely on generated examples. Produces a client-bundled JSON registry, never
model artifacts trained on actual people. The fictional labels have no clinical meaning.
"""
import argparse
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'web/app/data/fictional-model-registry-v38.json'
SEED=38062026
FEATURES=['age_signal','bmi_signal','phq_signal','movement_signal','history_signal','smoking_signal']
DEFINITIONS=[
 ('fictional_pathway_a','Invented outcome A','Fictional output A, unrelated to real illness',[-0.45,0.52,0.22,0.08,0.38,0.16,0.19]),
 ('fictional_pathway_b','Invented outcome B','Fictional output B, unrelated to real illness',[-0.85,0.20,-0.18,0.30,0.62,0.27,0.10]),
 ('fictional_pathway_c','Invented outcome C','Fictional output C, unrelated to real illness',[-0.25,0.10,0.12,0.55,0.24,-0.08,0.34]),
]

def sigmoid(value):
    return 1.0/(1.0+math.exp(-max(-30,min(30,value))))

def generated():
    rng=random.Random(SEED)
    records=[]
    for _ in range(1200):
        age=rng.randint(65,95); bmi=round(rng.uniform(18,40),1); phq=rng.randint(0,27)
        movement=rng.randrange(3); history=rng.randrange(2); smoking=rng.randrange(2)
        signals=[(age-75)/10,(bmi-26)/8,(phq-8)/8,movement/2,history,smoking]
        targets=[]
        for _,_,_,truth in DEFINITIONS:
            probability=sigmoid(truth[0]+sum(s*w for s,w in zip(signals,truth[1:])))
            targets.append(1 if rng.random()<probability else 0)
        records.append((signals,targets))
    return records

def fit(records,target_index):
    # Plain deterministic batch gradient descent, intentionally no imports of real ML artifacts.
    theta=[0.0]*7
    for _ in range(380):
        gradients=[0.0]*7
        for x,ys in records:
            p=sigmoid(theta[0]+sum(a*b for a,b in zip(theta[1:],x)))
            error=p-ys[target_index]
            gradients[0]+=error
            for j,value in enumerate(x,1): gradients[j]+=error*value
        scale=len(records)
        for j in range(7):
            penalty=0 if j==0 else 0.015*theta[j]
            theta[j]-=0.48*(gradients[j]/scale+penalty)
    return [round(n,6) for n in theta]

def registry():
    rows=generated()
    models=[]
    for index,(ident,title,description,_) in enumerate(DEFINITIONS):
        fitted=fit(rows[:960],index)
        models.append(dict(id=ident,title=title,description=description,
          intercept=fitted[0],weights=dict(zip(FEATURES,fitted[1:])),
          model_type='synthetic_logistic_regression',trained_on='generated_fictional_examples',
          clinical_use_permitted=False, outcome_is_real=False))
    return {'schema':'FRAILTYSCOPE_FICTIONAL_MULTI_OUTCOME_V38',
      'provenance':'SYNTHETIC_GENERATED_ONLY','version':'synthetic-v38.0',
      'independent_clinical_validation':False,'clinical_use_permitted':False,
      'training':{'generated_records':1200,'fit_records':960,'synthetic_check_records':240,
       'seed':SEED,'algorithm':'deterministic_batch_gradient_descent',
       'any_real_participants':False},
      'features':FEATURES,'models':models}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--check',action='store_true')
    p.add_argument('--output',default=str(OUTPUT))
    args=p.parse_args()
    serialized=json.dumps(registry(),indent=2,ensure_ascii=False)+'\n'
    dest=Path(args.output)
    if args.check:
        assert dest.read_text(encoding='utf-8')==serialized,'Synthetic registry out of date; do not publish'
        print('PASS: synthetic model registry reproducible; only invented rows used')
    else:
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(serialized,encoding='utf-8')
        print('WROTE teaching-only synthetic registry:',dest)

if __name__=='__main__':main()
