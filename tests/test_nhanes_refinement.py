from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from ml.nhanes_refinement import diagnostic_bins,cohort_bins,safe_coverage,estimator,suggest
from scripts.export_nhanes_refinement import report_to_public

BASE=Path(__file__).resolve().parents[1]

def test_diagnostic_bins_have_safe_minimums():
    p=np.linspace(.02,.7,200)
    y=np.asarray([0,1]*100)
    res=diagnostic_bins(y,p)
    assert len(res)==5 and all(k['n']==40 for k in res)
    assert sum(x['n'] for x in res)==200

def test_reject_small_calibration_bins():
    with pytest.raises(ValueError):diagnostic_bins(np.arange(10)%2,np.linspace(0,1,10))

def test_age_cohort_categories():
    d=pd.DataFrame({'age':[65]*30+[70]*30+[75]*30+[80]*30})
    assert sum(r['count'] for r in cohort_bins(d))==120

def test_coverage_14_inputs():
    from ml.realdata_nhanes import BASE_FEATURES
    d=pd.DataFrame({c:[1,2,None,2] for c in BASE_FEATURES})
    assert len(safe_coverage(d))==14

@pytest.fixture
def sample_report():
    counts={'train':90,'validation':40,'development':130,'test':140,'test_events':50,'total':270}
    return {'report_type':'AGGREGATE_NHANES_REFINEMENT_V1','data_origin':'NHANES_PUBLIC_2019_LMF',
      'counts':counts,'selected_model':'CatBoost','selected_threshold':.2,
      'model_search':[{'model':m,'cv_brier':.12,'validation':{'roc_auc':.8,'average_precision':.5,'brier':.12},'n_trials':5}
                      for m in ['Logistic regression','Histogram gradient boosting','XGBoost','CatBoost']],
      'test_metrics':{'roc_auc':.8,'average_precision':.5,'brier':.1,'accuracy':.7,'precision':.5,'recall':.6,'f1':.54,
                     'confusion':{'tn':68,'fp':22,'fn':20,'tp':30}},
      'test_weighted_descriptive':None,
      'calibration_bins':[{'group':f'Q{i}','n':28,'predicted':.1,'observed':.1} for i in range(5)],
      'coverage':[], 'age_distribution':[{'label':l,'count':n} for l,n in [('65–69',70),('70–74',60),('75–79',70),('80+ (top-coded)',70)]],
      'importance':[],'shap_features':[]}

def test_export_rejects_small_cells(sample_report):
    with pytest.raises(ValueError,match='Small calibration'):report_to_public(sample_report)

def test_export_rejects_untrusted_keys(sample_report):
    from ml.realdata_nhanes import BASE_FEATURES
    from scripts.export_nhanes_refinement import LABELS
    sample_report['calibration_bins']=[{**x,'n':40} for x in sample_report['calibration_bins']]
    sample_report['counts']['test']=200;sample_report['counts']['total']=330
    sample_report['coverage']=[{'feature':LABELS[x],'observed_pct':90} for x in BASE_FEATURES]
    sample_report['age_distribution'][-1]['count']=130
    sample_report['test_metrics']['confusion']['tn']=128
    sample_report['patient_rows']=[{'name':'secret'}]
    exported=report_to_public(sample_report)
    assert 'patient_rows' not in exported
    assert exported['counts']['total']==330



def _valid_export_fixture(report):
    from ml.realdata_nhanes import BASE_FEATURES
    report['calibration_bins']=[{**x,'n':40} for x in report['calibration_bins']]
    report['counts']['test']=200
    report['counts']['total']=330
    report['test_metrics']['confusion']['tn']=128
    report['age_distribution'][-1]['count']=130
    return report


def test_accept_actual_train_produced_coverage_labels(sample_report):
    from ml.realdata_nhanes import BASE_FEATURES
    report=_valid_export_fixture(sample_report)
    frame=pd.DataFrame({key:[1.0,2.0,None,3.0] for key in BASE_FEATURES})
    report['coverage']=safe_coverage(frame)
    assert any(x['feature']=='PHQ-9 score' for x in report['coverage'])
    export=report_to_public(report)
    assert len(export['featureCoverage'])==14
    assert any(x['name']=='PHQ-9 questionnaire score' for x in export['featureCoverage'])
    assert export['provenance']=='REAL_NHANES_AGGREGATE_ONLY'


def test_reject_duplicate_or_unknown_coverage_names(sample_report):
    from ml.realdata_nhanes import BASE_FEATURES
    from scripts.export_nhanes_refinement import LABELS
    report=_valid_export_fixture(sample_report)
    report['coverage']=[{'feature':LABELS[key],'observed_pct':99.0} for key in BASE_FEATURES]
    report['coverage'][-1]['feature']='Injected unknown field'
    with pytest.raises(ValueError,match='Unapproved feature'):
        report_to_public(report)
    report['coverage'][-1]['feature']=report['coverage'][0]['feature']
    with pytest.raises(ValueError,match='Duplicate feature'):
        report_to_public(report)
