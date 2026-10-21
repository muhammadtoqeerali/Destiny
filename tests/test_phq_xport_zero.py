"""Regression tests for a known SAS XPORT zero-decoding issue in NHANES DPQ."""
import numpy as np
import pandas as pd
import pytest

from ml.realdata_nhanes import PHQ, as_features, normalize_xport_zero
from ml.nhanes_quality import phq_diagnostics

ALIAS=5.397605346934028e-79


def test_xport_zero_alias_and_refusal_not_confused():
    original=pd.Series([ALIAS,0.,1.,2.,3.,7.,9.,np.nan])
    decoded=normalize_xport_zero(original)
    assert decoded.iloc[:5].tolist()==[0.,0.,1.,2.,3.]
    assert decoded.iloc[5]==7 and decoded.iloc[6]==9
    assert pd.isna(decoded.iloc[7])


def test_raw_nine_zero_aliases_produce_complete_phq9():
    a=pd.DataFrame({'RIDAGEYR':[70,75,80],'RIAGENDR':[1,2,2]})
    for k in PHQ:
        a[k]=[ALIAS,ALIAS,ALIAS]
    a.loc[1,PHQ[0]]=3.
    a.loc[2,PHQ[-1]]=9.
    decoded=as_features(a)
    assert decoded['phq9_score'].iloc[0]==0.
    assert decoded['phq9_score'].iloc[1]==3.
    assert np.isnan(decoded['phq9_score'].iloc[2])


def test_audit_agrees_with_corrected_data():
    raw=pd.DataFrame({'SEQN':[1,2,3], **{key:[ALIAS,ALIAS,ALIAS] for key in PHQ}})
    raw.loc[1,PHQ[0]]=2.
    raw.loc[2,PHQ[-1]]=7.
    processed=pd.DataFrame({'SEQN':[1,2,3],'phq9_score':[0.,2.,np.nan]})
    result=phq_diagnostics(raw,processed)
    assert result['raw_nine_complete']==2
    assert result['processed_complete']==2
    assert result['mismatch_count']==0
    assert result['xport_zero_alias_values_corrected']>=20


def test_old_processed_phq9_does_not_pass_reaudit():
    raw=pd.DataFrame({'SEQN':[1],**{k:[ALIAS] for k in PHQ}})
    stale=pd.DataFrame({'SEQN':[1],'phq9_score':[np.nan]})
    with pytest.raises(ValueError,match='mismatch'):
        phq_diagnostics(raw,stale)
