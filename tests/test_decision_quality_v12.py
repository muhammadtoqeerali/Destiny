"""Only fixed fabricated vectors; NEVER train or load a research model in these tests."""
import copy
import numpy as np
import pytest
from ml.case_decision_quality_v12 import (checked,confusion,metric,threshold_curve,
    bootstrap_intervals,calibration_summary,subgroup_report,group_calibration_bins,
    age_groups,compare_reports)
from scripts.export_decision_quality_v12 import clean


def vector(n=400):
    # Deterministic made-up TEST FIXTURE, not NHANES and not a fitted model.
    y=np.array(([1,0,0,1,0]* (n//5)),int)
    p=np.linspace(.04,.91,len(y))
    return y,p


def test_confusion_boundary():
    y=np.array([0,1,1,0,0,1,1,0,0,1,0,1])
    p=np.array([.2,.8,.4,.7,.1,.6,.2,.9,.15,.8,.1,.9])
    assert confusion(y,p,.5)=={'tn':4,'fp':2,'fn':2,'tp':4}


def test_threshold_curve_invariants():
    y,p=vector()
    c=threshold_curve(y,p)
    assert len(c)==14
    assert all(c[i]['recall']>=c[i+1]['recall'] for i in range(len(c)-1))
    assert all(c[i]['false_positive_rate']>=c[i+1]['false_positive_rate'] for i in range(len(c)-1))
    assert all(0<=row['predicted_positive']<=len(y) for row in c)
    for row in c:
        t=row['threshold'];z=confusion(y,p,t)
        assert row['predicted_positive']==z['tp']+z['fp']
        expected=z['tp']/len(y)-z['fp']/len(y)*t/(1-t)
        assert abs(row['net_benefit']-expected)<1e-6


def test_binary_and_probability_guards():
    with pytest.raises(ValueError): checked([0,1]*7,[1.1,.2]*7)
    with pytest.raises(ValueError): checked([0]*20,[.1]*20)
    with pytest.raises(ValueError): confusion(*vector(),1.0)
    with pytest.raises(ValueError): checked([0,1]*6,[.2]*10)


def test_bootstrap_is_reproducible_without_fitting():
    y,p=vector()
    a=bootstrap_intervals(y,p,.22,draws=100,seed=5)
    assert a==bootstrap_intervals(y,p,.22,draws=100,seed=5)
    assert len(a['intervals'])==5
    assert all(0<=i['lower']<=i['upper']<=1 for i in a['intervals'])
    assert 'ignores NHANES' in a['method']


def test_small_group_suppression():
    y,p=vector()
    gr=np.array(['Very small']*50+['Larger']*350)
    actual=subgroup_report(y,p,gr,.22)
    assert [r['group'] for r in actual]==['Larger']
    assert all(r['n']>=100 for r in actual)


def test_calibration_bands_suppress_small_events():
    y,p=vector()
    group=['G']*len(y)
    bins=group_calibration_bins(y,p,group,bins=3,min_n=50,min_events=10)
    assert bins and all(z['events']>=10 and z['n']-z['events']>=10 for z in bins)


def test_calibration_summary_balanced():
    y,p=vector()
    c=calibration_summary(y,p)
    assert c['n']==len(y) and c['events']==int(sum(y))
    assert abs(c['observed_minus_predicted']-(c['observed_event_rate']-c['mean_predicted_risk']))<0.00001


def test_age_groups_missing_and_topcode():
    a=age_groups([64,65,72,77,80,85,np.nan])
    assert list(a)==[None,'65–69','70–74','75–79','80+', '80+', None]


def test_descriptive_comparison_uses_all_three_real_public_schemas():
    # Fixture reproduces the verified PUBLIC JSON key layout, not real records.
    matrix={'tn':708,'fp':303,'fn':63,'tp':183}
    ev={'n':1257,'roc_auc':.791758,'brier':.129447,'average_precision':.510206,
        'recall':.743902,'precision':.376543,'threshold':.22,'confusion':matrix}
    general={'evaluation':ev,'selected_threshold':.22,'partition_counts':{'test':1257}}
    bmat={'tn':711,'fp':300,'fn':57,'tp':189}
    baseline={'testAtF2':{'roc_auc':.8033,'brier':.1232,'average_precision':.5237,
                          'recall':.7683,'precision':.3865,'confusion':bmat},
              'counts':{'test':1257,'test_events':246},'threshold':.17}
    rmat={'tn':584,'fp':427,'fn':41,'tp':205}
    refined={'test':{'roc_auc':.8006,'brier':.1228,'average_precision':.5313,
                     'recall':.8333,'precision':.3244,'confusion':rmat},
             'counts':{'test':1257,'test_events':246},'selectedThreshold':.12}
    outcome=compare_reports(general,baseline,refined,1257,246)
    assert outcome['comparison_type']=='DESCRIPTIVE_AGGREGATE_ONLY_NOT_PAIRED'
    assert [row['experiment'] for row in outcome['rows']]==[
        'General-purpose CatBoost','Specialist CatBoost','Specialist Histogram Boosting']
    assert [row['threshold'] for row in outcome['rows']]==[.22,.17,.12]
    assert [row['false_positives'] for row in outcome['rows']]==[303,300,427]
    assert [row['roc_auc'] for row in outcome['rows']]==[.791758,.8033,.8006]
    assert 'selected' not in outcome and 'p_value' not in outcome
    with pytest.raises(ValueError,match='different cohort'):
        compare_reports(general,baseline,refined,1257,247)
    broken=copy.deepcopy(baseline)
    broken['testAtF2']['confusion']['fp']+=1
    with pytest.raises(ValueError,match='different cohort'):
        compare_reports(general,broken,refined,1257,246)
    broken=copy.deepcopy(refined)
    del broken['selectedThreshold']
    with pytest.raises(ValueError,match='selected threshold'):
        compare_reports(general,baseline,broken,1257,246)
    broken=copy.deepcopy(baseline)
    del broken['testAtF2']
    with pytest.raises(ValueError,match='expected aggregate metric field'):
        compare_reports(general,broken,refined,1257,246)


def local_fixture():
    y,p=vector()
    # This is a 400-person fabricated fixture, adjusted only at aggregate-validation boundary.
    ev=metric(y,p,.22)
    def fixture_ev():
        return {'roc_auc':ev['roc_auc'],'brier':ev['brier'], 'confusion':ev['confusion']}
    local={'schema':'FRAILTYSCOPE_LOCAL_DECISION_QUALITY_V12',
           'case_id':'nhanes_mortality_v10','dataset_sha256':'test-fingerprint',
           'counts':{'validation':292,'evaluation':1257,'events':246},
           'selected_model':'catboost','selection_threshold_from_validation':.22,
           'validation_reference':ev,'evaluation':ev,
           'threshold_diagnostics_descriptive_only':threshold_curve(y,p),
           'uncertainty':{'method':'Synthetic-fixture-IID-percentile','replicates':100,
                          'intervals':[{'metric':'roc_auc','estimate':ev['roc_auc'],
                                        'lower':max(0,ev['roc_auc']-0.05),'upper':min(1,ev['roc_auc']+0.05)}]},
           'overall_calibration':calibration_summary(y,p),
           'subgroups':[],'subgroup_calibration':[],'experiment_comparison':None,
           'limitations':['Unvalidated, synthetic fixture in test only.']}
    meta={'dataset_sha256':'test-fingerprint','selected_model':'catboost',
          'selected_threshold':.22,'evaluation':fixture_ev()}
    audit={'provenance':'REAL_NHANES_AGGREGATE_ONLY','schema':'FRAILTYSCOPE_PUBLIC_CASE_AUDIT_V11',
           'counts':{'evaluation':1257}}
    return local,meta,audit


def test_public_export_explicit_allowlist():
    local,meta,audit=local_fixture()
    out=clean(local,meta,audit)
    assert out['schema']=='FRAILTYSCOPE_PUBLIC_DECISION_QUALITY_V12'
    assert 'dataset_sha256' not in out
    assert 'individual_scores' not in str(out)
    assert len(out['thresholds'])==14
    assert out['model']=='catboost'


def test_public_export_rejects_mismatched_artifacts():
    local,meta,audit=local_fixture()
    meta['dataset_sha256']='other'
    with pytest.raises(ValueError):clean(local,meta,audit)


def test_public_export_rejects_changed_metrics():
    local,meta,audit=local_fixture()
    local['evaluation']['roc_auc']=.99
    with pytest.raises(ValueError):clean(local,meta,audit)


def test_public_export_rejects_leaky_small_cells():
    local,meta,audit=local_fixture()
    local['subgroups']=[{'group':'tiny','dimension':'Age','n':50,'events':1}]
    with pytest.raises(ValueError):clean(local,meta,audit)
    local,meta,audit=local_fixture()
    local['subgroup_calibration']=[{'group':'tiny','dimension':'Age','n':60,'events':1}]
    with pytest.raises(ValueError):clean(local,meta,audit)


def test_public_export_rejects_nonfinite():
    local,meta,audit=local_fixture()
    local['threshold_diagnostics_descriptive_only'][0]['net_benefit']=float('nan')
    with pytest.raises(ValueError):clean(local,meta,audit)


def test_not_a_paired_significance_test():
    local,meta,audit=local_fixture()
    assert not any('p_value' in k for k in clean(local,meta,audit))
