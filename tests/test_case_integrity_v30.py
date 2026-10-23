"""v0.30 source/fixture-only integrity tests. Never open private artifacts."""
import copy
import json
from pathlib import Path

import pytest

from ml.case_integrity_v30 import (
    SCHEMA, REPORT_SCHEMA, SMOKE_SCHEMA, SOURCE_PATHS, _check_finite,
    _strict_json, canonical_digest, invented_fixture, inventory, plan,
    source_file, synthetic_smoke, validate_integrity, write_immutable_review,
)

ROOT = Path(__file__).resolve().parents[1]


def config():
    return json.loads((ROOT / 'research/cases/nhanes_integrity_v30.json').read_text())


def test_v30_protocol_and_cross_version_hash_ledger():
    cfg = config()
    assert validate_integrity(cfg) is cfg
    data = inventory(ROOT, cfg)
    assert len(data['source_contracts']) == 8
    assert [item['path'] for item in data['source_contracts']] == list(SOURCE_PATHS)
    assert all(len(row['bytes_sha256']) == 64 and
               len(row['canonical_sha256']) == 64 for row in data['source_contracts'])
    assert len(data['source_chain_sha256']) == 64
    assert plan(ROOT, cfg)['schema'] == REPORT_SCHEMA
    assert plan(ROOT, cfg)['v29_private_metadata_verified'] is False


def test_reproducibility_on_internal_invented_fixture_only():
    a = synthetic_smoke(ROOT, config())
    b = synthetic_smoke(ROOT, config())
    assert a == b
    assert a['schema'] == SMOKE_SCHEMA
    assert a['deterministic_repetition_verified'] is True
    assert a['n_invented_rows'] == 72 and a['n_folds'] == 3
    assert not a['row_predictions_recorded'] and not a['model_files_written']
    assert not a['public_export'] and not a['independent_validation']


def test_fixture_is_invented_and_has_stable_person_grouping():
    x, y, rows, people = invented_fixture()
    assert len(x) == 72 and len(y) == 72
    assert len(set(rows)) == 72 and len(set(people)) == 36
    assert all(people[2*i] == people[2*i+1] for i in range(36))
    assert set(x.columns) == {'PFQ054', 'PFQ061B', 'PFQ061C', 'PFQ061D'}


@pytest.mark.parametrize('mutation', [
    lambda c: c.update(scope='real_data_ready'),
    lambda c: c.update(route='READY_FOR_NEW_ANALYSIS'),
    lambda c: c.update(study_protocol_clearance=True),
    lambda c: c.update(real_data_execution_permitted=True),
    lambda c: c.update(public_export_permitted=True),
    lambda c: c.update(models_saved=True),
    lambda c: c.update(independent_validation=True),
    lambda c: c.update(holdout_history='new_independent_holdout'),
    lambda c: c.update(prediction_index_status='signed_off'),
    lambda c: c.update(candidate_selection='winner'),
    lambda c: c.update(source_contract_paths=c['source_contract_paths'][1:]),
    lambda c: c.update(source_contract_paths=c['source_contract_paths'] + ['data/processed.csv']),
    lambda c: c.update(related_v29_protocol='data/participant_data.csv'),
    lambda c: c.update(case_id='new_real_study'),
    lambda c: c.update(validation_role='external_validation'),
])
def test_study_boundary_fail_closed(mutation):
    cfg = copy.deepcopy(config())
    mutation(cfg)
    with pytest.raises(ValueError):
        validate_integrity(cfg)


@pytest.mark.parametrize('text', ['{"x":1,"x":2}', '{"x":NaN}',
                                   '{"x":Infinity}', '{"x":-Infinity}'])
def test_ambiguous_or_nonfinite_json_rejected(text):
    with pytest.raises(ValueError):
        _strict_json(text)


def test_nonfinite_runtime_aggregate_rejected():
    with pytest.raises(ValueError, match='Nonfinite'):
        _check_finite({'foo': [1.0, {'bar': float('nan')}]})
    with pytest.raises(ValueError, match='Nonfinite'):
        _check_finite({'foo': float('inf')})


def test_changed_source_bytes_change_inventory(tmp_path):
    folder = tmp_path / 'research/cases'
    folder.mkdir(parents=True)
    p = folder / 'demo.json'
    p.write_text('{"a":1}\n')
    original = p.read_bytes()
    p.write_text('{ "a":1 }\n')
    assert canonical_digest(_strict_json(original.decode())) == canonical_digest(_strict_json(p.read_text()))
    assert original != p.read_bytes()
    from hashlib import sha256
    assert sha256(original).hexdigest() != sha256(p.read_bytes()).hexdigest()


def test_source_path_cannot_escape_research(tmp_path):
    (tmp_path / 'research').mkdir()
    (tmp_path / 'research' / 'good.json').write_text('{}')
    assert source_file(tmp_path, 'research/good.json').is_file()
    for path in ('../secret.json', '/etc/passwd', 'artifacts/secret.json',
                 'research/../../secret.json', 'research/good.csv'):
        with pytest.raises((ValueError, FileNotFoundError)):
            source_file(tmp_path, path)


def test_private_documentary_review_is_exclusive_write(tmp_path):
    p = tmp_path / 'artifacts/cases/integrity/review.json'
    write_immutable_review(p, {'schema': REPORT_SCHEMA, 'public_export': False})
    first = p.read_bytes()
    with pytest.raises(ValueError, match='immutable'):
        write_immutable_review(p, {'schema': 'OVERWRITE'})
    assert p.read_bytes() == first


def test_no_private_files_are_loaded_by_public_plan():
    output = plan(ROOT, config())
    assert output['source_only'] and output['synthetic_only']
    assert output['route'] == 'BLOCKED_FOR_NEW_ANALYSIS'
    assert not output['public_export'] and not output['models_saved']
    assert output['holdout_history'] == 'previously_inspected'
    assert output['prediction_index_status'] == 'provisional'
    assert all(entry['path'].startswith('research/cases/') for entry in output['source_contracts'])


def test_immutable_review_detects_source_change_without_opening_private_data(tmp_path, monkeypatch):
    from ml import case_integrity_v30 as m
    fake = {'schema': REPORT_SCHEMA, 'case_id': 'nhanes_mortality_v10',
            'source_chain_sha256': 'original', 'v29_private_metadata_verified': True}
    p = tmp_path / 'artifacts/integrity_review.json'
    write_immutable_review(p, fake)
    monkeypatch.setattr(m, 'plan', lambda root, cfg: dict(fake, v29_private_metadata_verified=False))
    monkeypatch.setattr(m, 'inventory', lambda root, cfg: {'source_chain_sha256': 'original'})
    monkeypatch.setattr(m, 'prior_v29_review', lambda root, cfg, info: True)
    monkeypatch.setattr(m, 'private_review_file', lambda root, cfg: p)
    assert m.verified_review(tmp_path, {}) == p
    monkeypatch.setattr(m, 'plan', lambda root, cfg: dict(fake,
                            source_chain_sha256='tampered', v29_private_metadata_verified=False))
    with pytest.raises(ValueError, match='disagrees'):
        m.verified_review(tmp_path, {})


def test_preexisting_public_threshold_data_numeric_contract_only():
    # Existing historical AGGREGATE JSON. Do not regenerate, export or score any outcomes.
    p = ROOT / 'web/public/data/nhanes-decision-quality-v12.json'
    report = _strict_json(p.read_text())
    points = report['thresholds']
    assert len(points) == 14 and len({p['threshold'] for p in points}) == 14
    assert all(0 < p['threshold'] < 1 for p in points)
    for p in points:
        for field in ('threshold', 'recall', 'false_positive_rate',
                      'net_benefit', 'treat_all_net_benefit', 'treat_none_net_benefit'):
            assert type(p[field]) in (int, float)
            _check_finite(p[field])
