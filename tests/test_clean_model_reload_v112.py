"""Serialization contract tests ONLY: no estimator training, fitting, or data use."""
import __main__
from pathlib import Path

import joblib
import pytest
from sklearn.pipeline import Pipeline
from ml import case_engine_v10 as engine
from ml import case_model_io_v11 as io


def test_clean_process_detects_main_alias_even_if_parent_can_load(tmp_path):
    """Reproduces the failure missed by v0.11, without fitting any model."""
    old = getattr(__main__, 'CatBoostClassifierAdapter', None)
    Legacy = type('CatBoostClassifierAdapter', (engine.CatBoostClassifierAdapter,), {})
    Legacy.__module__ = '__main__'
    setattr(__main__, 'CatBoostClassifierAdapter', Legacy)
    path = tmp_path / 'legacy.joblib'
    try:
        joblib.dump(Pipeline([('features', 'passthrough'), ('model', Legacy())]), path)
        # Parent __main__ contains a matching symbol, so parent loading succeeds.
        assert isinstance(joblib.load(path), Pipeline)
    finally:
        if old is None:
            delattr(__main__, 'CatBoostClassifierAdapter')
        else:
            setattr(__main__, 'CatBoostClassifierAdapter', old)
    # A direct load would fail without the special alias; no class name is
    # imported into the verifier's __main__ module.
    recovered, was_legacy = io.load_legacy_or_canonical(path)
    assert was_legacy is True
    assert type(recovered.named_steps['model']) is engine.CatBoostClassifierAdapter
    joblib.dump(recovered, path)
    clean, detail = io.fresh_process_reload(path)
    assert clean, detail


def test_canonical_model_is_clean_process_loadable_without_fit(tmp_path):
    path = tmp_path / 'canonical.joblib'
    joblib.dump(Pipeline([('features', 'passthrough'),
                          ('model', engine.CatBoostClassifierAdapter())]), path)
    model, legacy = io.load_legacy_or_canonical(path)
    assert legacy is False
    assert type(model.named_steps['model']) is engine.CatBoostClassifierAdapter
    assert type(io.load_canonical_trusted_model(path).named_steps['model']) is engine.CatBoostClassifierAdapter


def test_corrupted_file_is_not_treated_as_legacy(tmp_path):
    path = tmp_path / 'damaged.joblib'
    path.write_bytes(b'no pickle here')
    with pytest.raises(Exception):
        io.load_legacy_or_canonical(path)
