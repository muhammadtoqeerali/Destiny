"""Publish ALLOWLISTED NHANES population statistics. Never participant rows/scores."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

PROVENANCE = 'REAL_NHANES_AGGREGATE_ONLY'
ALLOWED_MODELS = {'Regularized logistic regression', 'Histogram gradient boosting', 'XGBoost', 'CatBoost'}
METRICS = ('roc_auc', 'average_precision', 'brier', 'accuracy', 'precision', 'recall', 'f1')


def finite_score(x: object, name: str) -> float:
    if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(float(x)) or not 0 <= float(x) <= 1:
        raise ValueError('Invalid metric: ' + name)
    return round(float(x), 4)


def export(report: dict) -> dict:
    if report.get('report_type') != 'AGGREGATE_RESEARCH_METRICS_ONLY' or report.get('data_origin') != 'NHANES_PUBLIC_2019_LMF':
        raise ValueError('Real NHANES aggregate-report provenance required')
    if report.get('training_cycle') != '2011-2012' or report.get('test_cycle') != '2013-2014':
        raise ValueError('Unexpected development/test cycles')
    counts = report['counts']
    ntrain, nval, ntest, events = (counts[k] for k in ('train','validation','test','test_events'))
    if not all(type(x) is int and x > 0 for x in (ntrain,nval,ntest,events)) or events >= ntest or ntest < 100:
        raise ValueError('Bad aggregate counts')
    if (ntrain+nval) < 100 or len(report.get('validation_comparisons', [])) != 4:
        raise ValueError('Incomplete 4-model benchmark')
    if report['selected_model'] not in ALLOWED_MODELS:
        raise ValueError('Unexpected winning estimator')
    vlist=[]
    for comp in report['validation_comparisons']:
        if comp['model'] not in ALLOWED_MODELS:
            raise ValueError('Unexpected model')
        val=comp['validation']
        vlist.append({'name':comp['model'],'roc_auc':finite_score(val['roc_auc'],'val auc'),
                      'average_precision':finite_score(val['average_precision'],'val ap'),
                      'brier':finite_score(val['brier'],'val brier')})
    if len(set(x['name'] for x in vlist)) != 4:
        raise ValueError('Duplicate model')
    def selected_metrics(name: str) -> dict:
        d=report[name]
        c=d['confusion']
        c2={k:int(c[k]) for k in ('tn','fp','fn','tp')}
        if min(c2.values()) < 0 or sum(c2.values()) != ntest or c2['fn']+c2['tp'] != events:
            raise ValueError('Confusion matrix does not match test counts')
        return {**{k:finite_score(d[k],k) for k in METRICS},'confusion':c2}
    t05=selected_metrics('test_unweighted_threshold_050')
    tuned=selected_metrics('test_unweighted_validation_threshold')
    threshold=finite_score(report['validation_selected_threshold_F2'],'threshold')
    lohi=report['test_auc_95ci_fixed_model_bootstrap']
    ci=[finite_score(lohi[0],'CI low'),finite_score(lohi[1],'CI high')]
    if not ci[0]<=tuned['roc_auc']<=ci[1]:
        raise ValueError('Invalid AUC interval')
    base=finite_score(report['baseline_predict_none_accuracy'],'baseline')
    if abs(base - (1-events/ntest)) > 0.001:
        raise ValueError('Baseline and event count inconsistent')
    return {
       'provenance':PROVENANCE,
       'source':'CDC/NCHS NHANES 2011–2014 public-use files and 2019 public-use linked mortality',
       'target':'Approximately five-year all-cause mortality (perturbed public-use time)',
       'population':'Eligible NHANES participants aged 65+ with classifiable follow-up',
       'cycles':{'development':'2011–2012','test':'2013–2014'},
       'counts':{'development':ntrain+nval,'train':ntrain,'validation':nval,'test':ntest,'test_events':events,'total':ntrain+nval+ntest},
       'features':['Age (top-coded at 80)','Sex','Body mass index','Walking / stair / stooping difficulty','Heart failure','Coronary disease','Stroke','Cancer','Diabetes','Hypertension','Ever smoked','PHQ-9 questionnaire score'],
       'algorithms':vlist,
       'selectedModel':report['selected_model'],'selection':'Lowest validation Brier score',
       'threshold':threshold,'testAt50':t05,'testAtF2':tuned,'auc95ci':ci,
       'majorityAccuracy':base,
       'limitations':[
          'Aggregate public-use NHANES outcomes only: no individual records or predictions on this site.',
          'A US cohort, not HUNT or Norwegian patients. No generalization to NTNU clinical populations is established.',
          'Public linked-mortality follow-up durations are perturbed for disclosure protection; horizon is approximate.',
          'Observational survey, unweighted headline performance; proper survey-design-aware inference is pending.',
          'This is a binary-horizon benchmark, not survival analysis; censoring, recalibration and prospective validation remain.',
          'The selected probability threshold maximizes validation F2 and is not a medically approved triage threshold.',
          'Not a clinical system, not an individual prognosis, not a medical device.'
       ]
    }


def main() -> None:
    a=argparse.ArgumentParser()
    a.add_argument('--report',default='artifacts/realdata_nhanes/report.json')
    a.add_argument('--out',default='web/public/data/nhanes-aggregate.json')
    args=a.parse_args()
    inp=Path(args.report)
    if not inp.is_file(): raise SystemExit('Missing local real-data report: '+str(inp))
    result=export(json.loads(inp.read_text(encoding='utf-8')))
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print('ALLOWLISTED public aggregate file:',out)
    print('Provenance:',result['provenance'],'total:',result['counts']['total'],'test:',result['counts']['test'])
    print('No individual participant records exported.')

if __name__=='__main__':main()
