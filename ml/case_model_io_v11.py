"""Trusted local model-artifact migration and fresh-process reload verification.

Do not run this on model files from external sources. joblib/pickle is executable.
This module NEVER trains a model. It only verifies and reserializes the locally
fitted model using its existing case manifest, data, and evaluation report.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import joblib
import numpy as np
from sklearn.pipeline import Pipeline

# IMPORTANT: Keep CatBoost*Adapter OUT of this module's globals. When called as
# "python -m ml.case_model_io_v11", globals == __main__. Importing the adapter
# names here makes old __main__ pickle references look falsely canonical.
from ml import case_engine_v10 as engine

LEGACY_NAMES = ('CatBoostClassifierAdapter', 'CatBoostRegressorAdapter')

# The probe is run with python -c in an independent __main__ namespace. Neither
# adapter class is installed as a global, so a legacy pickle cannot pass.
CLEAN_RELOAD_PROBE = r'''
import joblib, sys
from sklearn.pipeline import Pipeline
from ml import case_engine_v10 as engine
m = joblib.load(sys.argv[1])
if not isinstance(m, Pipeline) or set(m.named_steps) != {'features', 'model'}:
    raise ValueError('Unexpected model pipeline structure')
cls = type(m.named_steps['model'])
if cls.__name__ in ('CatBoostClassifierAdapter','CatBoostRegressorAdapter'):
    if cls is not getattr(engine, cls.__name__):
        raise ValueError('Model adapter is not the canonical imported class')
print('CLEAN_FRESH_PROCESS_RELOAD_OK')
'''


def fresh_process_reload(path: Path) -> tuple[bool, str]:
    """Return (successful, diagnostic); no trained model or predictions exported."""
    result = subprocess.run(
        [sys.executable, '-c', CLEAN_RELOAD_PROBE, str(path.resolve())],
        capture_output=True, text=True, timeout=90, check=False,
    )
    if result.returncode == 0 and 'CLEAN_FRESH_PROCESS_RELOAD_OK' in result.stdout:
        return True, 'fresh process loaded canonical artifact'
    detail = result.stderr.strip() or result.stdout.strip()
    return False, detail[-1600:]


def is_known_main_adapter_failure(diagnostic: str) -> bool:
    # Python -m displays __main__ using its module spec, e.g.
    # <module 'ml.case_model_io_v11' from '...'> rather than '__main__'.
    main_repr = repr(sys.modules['__main__'])
    return ("Can't get attribute" in diagnostic and
            any(name in diagnostic for name in LEGACY_NAMES) and
            ('__main__' in diagnostic or main_repr in diagnostic))


@contextmanager
def legacy_main_aliases():
    """Temporary, limited compatibility only for known locally created models."""
    main = sys.modules['__main__']
    absent = object()
    old = {name: getattr(main, name, absent) for name in LEGACY_NAMES}
    for name in LEGACY_NAMES:
        setattr(main, name, getattr(engine, name))
    try:
        yield
    finally:
        for name, previous in old.items():
            if previous is absent:
                delattr(main, name)
            else:
                setattr(main, name, previous)


def load_legacy_or_canonical(path: Path):
    """Load without global aliases; retry only the historical __main__ adapter."""
    try:
        model = joblib.load(path)
        return model, False
    except AttributeError as exc:
        # AttributeError may also mean a genuinely broken/corrupt model. The
        # exception must identify precisely the known legacy __main__ adapter.
        diagnostic = str(exc)
        if not is_known_main_adapter_failure(diagnostic):
            raise
    with legacy_main_aliases():
        return joblib.load(path), True


def load_canonical_trusted_model(path: Path):
    """Ordinary strict model load for all diagnostics, with no __main__ aliases."""
    model = joblib.load(path)
    if not isinstance(model, Pipeline) or set(model.named_steps) != {'features', 'model'}:
        raise ValueError('Unexpected local model pipeline')
    cls = type(model.named_steps['model'])
    if cls.__name__ in LEGACY_NAMES and cls is not getattr(engine, cls.__name__):
        raise ValueError('Noncanonical CatBoost adapter; rerun local migration')
    return model


def verify_against_report(model, project: Path, spec: dict):
    """Recompute existing results only on the user's workstation; never fit."""
    engine.validate_manifest(spec)
    case_id = spec['case_id']
    report_path = project / 'artifacts' / 'cases' / case_id / 'metrics.json'
    report = json.loads(report_path.read_text())
    data, target, fingerprint = engine.load_data(project, spec)
    if (report.get('dataset_sha256') != fingerprint or
        report.get('case_id') != case_id or
        report.get('task') != spec['task']):
        raise ValueError('Data fingerprint/case identity disagrees with saved report')
    if not isinstance(model, Pipeline) or set(model.named_steps) != {'features', 'model'}:
        raise ValueError('Expected fitted v0.10 sklearn pipeline')
    if report['selected_model'] == 'catboost':
        expected = (engine.CatBoostClassifierAdapter if spec['task'] == 'classification'
                    else engine.CatBoostRegressorAdapter)
        if type(model.named_steps['model']) is not expected:
            raise ValueError('Wrong or noncanonical fitted CatBoost adapter')
    _, _, evaluation_idx = engine.split_data(data, target, spec)
    predictors = spec['features']['numeric'] + spec['features']['categorical']
    if spec['task'] == 'classification':
        prob = np.asarray(model.predict_proba(data.iloc[evaluation_idx][predictors])[:, 1], float)
        calculated = engine.calculate_metrics('classification', target.iloc[evaluation_idx],
                                              prob, prob, float(report['selected_threshold']))
    else:
        prediction = np.asarray(model.predict(data.iloc[evaluation_idx][predictors]), float)
        calculated = engine.calculate_metrics('regression', target.iloc[evaluation_idx], prediction)
    previous = report['evaluation']
    for key, value in previous.items():
        if key == 'confusion':
            if calculated[key] != value:
                raise ValueError('Saved confusion matrix disagrees with the model')
        elif isinstance(value, (float, int)) and not isinstance(value, bool):
            if key not in calculated or abs(float(calculated[key]) - value) > 0.0001:
                raise ValueError('Saved evaluation metric mismatch: ' + key)
    return {'model': report['selected_model'], 'n': len(evaluation_idx),
            'roc_auc': calculated.get('roc_auc'), 'brier': calculated.get('brier'),
            'confusion': calculated.get('confusion')}


def repair_model(project: Path,
                 config: str = 'research/cases/nhanes_mortality_v10.json') -> dict:
    project = project.resolve()
    spec_path = (project / config).resolve()
    if not spec_path.is_relative_to(project):
        raise ValueError('Case manifest must stay inside the repository')
    spec = json.loads(spec_path.read_text())
    engine.validate_manifest(spec)
    model_dir = (project / 'artifacts' / 'cases' / spec['case_id']).resolve()
    if not model_dir.is_relative_to((project / 'artifacts' / 'cases').resolve()):
        raise ValueError('Case model must remain under local artifacts/cases/')
    source = model_dir / 'best_model.joblib'
    if not source.is_file() or source.is_symlink():
        raise ValueError('Missing trusted local model or unsafe model symlink')

    model, was_legacy = load_legacy_or_canonical(source)
    verified = verify_against_report(model, project, spec)
    if not was_legacy:
        clean, detail = fresh_process_reload(source)
        if not clean:
            raise RuntimeError('In-process load succeeded but independent reload failed: ' + detail)
        return {'status': 'ALREADY_CANONICAL_AND_VERIFIED', 'fresh_process_reload': True, **verified}

    # Re-serialize the verified object with its real module-qualified adapter.
    fd, tmp_name = tempfile.mkstemp(prefix='canonical-v112-', suffix='.joblib', dir=model_dir)
    os.close(fd)
    temp = Path(tmp_name)
    try:
        joblib.dump(model, temp)
        clean, detail = fresh_process_reload(temp)
        if not clean:
            raise RuntimeError('Migrated model failed independent reload: ' + detail)
        independent = joblib.load(temp)
        verify_against_report(independent, project, spec)
        backup = model_dir / 'best_model.v10_legacy_backup.joblib'
        if backup.exists():
            # Reusing an earlier backup is only acceptable if byte-identical.
            if backup.read_bytes() != source.read_bytes():
                raise FileExistsError('An existing backup differs; do not replace it: ' + str(backup))
        else:
            backup.write_bytes(source.read_bytes())
        os.replace(temp, source)
        # The exact bytes tested by the independent process are now at source;
        # do not unnecessarily spawn another interpreter here.
    finally:
        if temp.exists():
            temp.unlink()
    return {'status': 'REPAIRED_AND_VERIFIED', 'fresh_process_reload': True,
            'backup': str(backup), **verified}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='.')
    parser.add_argument('--config', default='research/cases/nhanes_mortality_v10.json')
    args = parser.parse_args()
    result = repair_model(Path(args.project), args.config)
    print('LOCAL MODEL SERIALIZATION:', json.dumps(result, indent=2))
    print('No model fitting, no participant records published.')


if __name__ == '__main__':
    main()
