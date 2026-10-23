"""FrailtyScope v0.30: synthetic-only reproducibility and source integrity.

--plan reads versioned research JSON only; --audit/--verify inspect only
immutable private documentary metadata; --smoke executes freshly invented
in-memory synthetic fixtures only. No participant tables, labels, fitted model
artifacts, private predictions, or public research exports are ever loaded.
The synthetic_fixture flag in predecessor APIs is NOT a security sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_WORKFLOW_INTEGRITY_V30'
REPORT_SCHEMA = 'FRAILTYSCOPE_PRIVATE_INTEGRITY_REVIEW_V30'
SMOKE_SCHEMA = 'FRAILTYSCOPE_SYNTHETIC_REPRODUCIBILITY_V30'
SOURCE_PATHS = (
    'research/cases/nhanes_governance_v22.json',
    'research/cases/nhanes_dictionary_timing_v23.json',
    'research/cases/nhanes_harmonization_v24.json',
    'research/cases/nhanes_foldsafe_v25.json',
    'research/cases/nhanes_task_models_v26.json',
    'research/cases/nhanes_temporal_v27.json',
    'research/cases/nhanes_reliability_v28.json',
    'research/cases/nhanes_workflow_v29.json',
)
ALLOWED_ACTIONS = ('--plan', '--audit', '--verify', '--smoke')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical_digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _strict_json(data):
    def unique_pairs(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, 'Duplicate JSON source key')
            result[k] = v
        return result
    def no_constant(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(data, object_pairs_hook=unique_pairs, parse_constant=no_constant)


def source_file(root, value, folder='research'):
    require(isinstance(value, str) and value and '\\' not in value,
            'Source reference must be a relative POSIX path')
    p = Path(value)
    require(not p.is_absolute() and '..' not in p.parts and p.parts[0] == folder,
            'Only source-controlled research metadata is admissible')
    full = (root / p).resolve(strict=True)
    allowed = (root / folder).resolve(strict=True)
    require(full.is_relative_to(allowed) and full.is_file() and full.suffix == '.json',
            'Unsafe source path or unsupported type')
    require(full.stat().st_size < 250_000, 'Oversized metadata source')
    return full


def validate_integrity(cfg):
    require(isinstance(cfg, dict) and cfg.get('schema') == SCHEMA,
            'Incorrect integrity schema')
    require(cfg.get('scope') == 'synthetic_only_integrity' and
            cfg.get('route') == 'BLOCKED_FOR_NEW_ANALYSIS' and
            cfg.get('study_protocol_clearance') is False and
            cfg.get('real_data_execution_permitted') is False and
            cfg.get('public_export_permitted') is False and
            cfg.get('models_saved') is False and
            cfg.get('independent_validation') is False,
            'Integrity contract cannot grant research execution or deployment')
    require(cfg.get('case_id') == 'nhanes_mortality_v10' and
            cfg.get('related_v29_protocol') == SOURCE_PATHS[-1] and
            cfg.get('source_contract_paths') == list(SOURCE_PATHS) and
            cfg.get('validation_role') == 'synthetic_development_oof_only',
            'Unrecognized source chain or study history')
    require(cfg.get('holdout_history') == 'previously_inspected' and
            cfg.get('prediction_index_status') == 'provisional' and
            cfg.get('candidate_selection') == 'not_performed',
            'Study constraints cannot silently change')
    return cfg


def inventory(root, cfg):
    """Revalidate entire v22-v29 protocol and hash source bytes and contracts."""
    validate_integrity(cfg)
    from ml.case_workflow_v29 import _read_sources, digest as v29_digest
    v29, v28, v27, v26, v25, v24 = _read_sources(root, cfg['related_v29_protocol'])
    require(v29['case_id'] == cfg['case_id'] and
            v29['holdout_history'] == cfg['holdout_history'] and
            v29['prediction_index_status'] == cfg['prediction_index_status'],
            'v0.29 source conflicts with immutable study boundary')
    rows = []
    for name in SOURCE_PATHS:
        p = source_file(root, name)
        data = p.read_bytes()
        parsed = _strict_json(data.decode('utf-8'))
        require(isinstance(parsed, dict) and parsed.get('case_id') == cfg['case_id'],
                'Source case mismatch')
        rows.append({'path': name, 'bytes_sha256': hashlib.sha256(data).hexdigest(),
                     'canonical_sha256': canonical_digest(parsed)})
    require(rows[-1]['canonical_sha256'] == v29_digest(v29),
            'v0.29 provenance does not match canonical config')
    return {'source_contracts': rows, 'source_chain_sha256': canonical_digest(rows),
            'v29_config_sha256': v29_digest(v29), 'v29_config': v29,
            'run_configs': (v29, v28, v27, v26, v25, v24)}


def plan(root, cfg):
    info = inventory(root, cfg)
    return {'schema': REPORT_SCHEMA, 'case_id': cfg['case_id'],
            'route': 'BLOCKED_FOR_NEW_ANALYSIS',
            'config_sha256': canonical_digest(cfg),
            'v29_config_sha256': info['v29_config_sha256'],
            'source_chain_sha256': info['source_chain_sha256'],
            'source_contracts': info['source_contracts'],
            'source_only': True, 'synthetic_only': True,
            'v29_private_metadata_verified': False,
            'no_participant_tables_opened': True, 'no_models_fitted': True,
            'no_predictions_generated': True, 'no_holdout_targets_accessed': True,
            'public_export': False, 'models_saved': False,
            'holdout_history': cfg['holdout_history'],
            'prediction_index_status': cfg['prediction_index_status'],
            'validation_role': cfg['validation_role']}


def private_review_file(root, cfg):
    base = (root / 'artifacts/cases').resolve()
    path = (root / 'artifacts/cases' / cfg['case_id'] / 'integrity_v30' /
            canonical_digest(cfg)[:12] / 'integrity_review.json').resolve()
    require(path.is_relative_to(base), 'Review must remain in local artifacts')
    return path


def prior_v29_review(root, cfg, info):
    from ml.case_workflow_v29 import REPORT_SCHEMA as PARENT_SCHEMA
    p = (root / 'artifacts/cases' / cfg['case_id'] / 'workflow_v29' /
         info['v29_config_sha256'][:12] / 'workflow_review.json').resolve()
    require(p.is_relative_to((root / 'artifacts/cases').resolve()) and
            p.is_file() and p.stat().st_size < 250_000,
            'Expected immutable v0.29 private documentary review missing')
    obj = _strict_json(p.read_text())
    checks = {'schema': PARENT_SCHEMA, 'case_id': cfg['case_id'],
              'config_sha256': info['v29_config_sha256'],
              'route': 'BLOCKED_FOR_NEW_ANALYSIS',
              'v28_private_metadata_verified': True,
              'no_participant_tables_opened': True, 'no_models_fitted': True,
              'no_predictions_generated': True, 'no_holdout_targets_accessed': True,
              'public_export': False}
    require(all(obj.get(key) == value for key, value in checks.items()),
            'Private predecessor review is inconsistent')
    return True


def write_immutable_review(path, obj):
    require(not path.exists(), 'Existing immutable integrity review; refuse overwrite')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create; no overwrite, no update to old fitted research artifacts.
    with path.open('x', encoding='utf-8') as output:
        json.dump(obj, output, sort_keys=True, indent=2, allow_nan=False)
        output.write('\n')


def verified_review(root, cfg):
    expected = plan(root, cfg)
    info = inventory(root, cfg)
    prior_v29_review(root, cfg, info)
    p = private_review_file(root, cfg)
    require(p.is_file() and p.stat().st_size < 250_000,
            'Immutable v0.30 review is absent or oversized')
    obj = _strict_json(p.read_text())
    expected['v29_private_metadata_verified'] = True
    require(obj == expected, 'Immutable review disagrees with current source chain')
    return p


def _check_finite(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            _check_finite(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _check_finite(v)
    elif isinstance(obj, float):
        require(math.isfinite(obj), 'Nonfinite synthetic output')


def invented_fixture(n=72):
    """Generate ONLY fabricated questionnaire rows; no file/data read."""
    import pandas as pd
    import numpy as np
    require(type(n) is int and n >= 24 and n % 2 == 0,
            'Invented fixture must have a suitable even number of rows')
    raw = []
    for i in range(n):
        routed = i % 11 == 0
        raw.append({'PFQ054': 1 if routed else 2,
                    'PFQ061B': None if routed else (5 if i % 13 == 0 else i % 4 + 1),
                    'PFQ061C': None if routed else (5 if i % 17 == 0 else (i + 1) % 4 + 1),
                    'PFQ061D': 5 if i % 19 == 0 else (i + 2) % 4 + 1})
    return (pd.DataFrame(raw), np.array([i % 2 for i in range(n)]),
            [f'fixture_row_{i}' for i in range(n)],
            [f'fixture_person_{i // 2}' for i in range(n)])


def synthetic_smoke(root, cfg):
    """Repeat generated synthetic integration, attest aggregates; persist nothing."""
    info = inventory(root, cfg)
    from ml.case_workflow_v29 import run_synthetic_workflow
    model_cfg = info['run_configs']
    def one():
        frame, y, row_ids, groups = invented_fixture()
        result = run_synthetic_workflow(*model_cfg, frame, y,
                row_ids=row_ids, groups=groups, source_fixture=True,
                synthetic_fixture=True)
        _check_finite(result)
        require(result.get('n_synthetic_rows') == 72 and
                result.get('n_folds') == 3 and
                result.get('synthetic_model_fits') == 6 and
                result.get('participant_predictions_exported') is False and
                result.get('selected_model') is None and
                result.get('models_saved') is False and
                result.get('independent_validation') is False,
                'Inconsistent development-only synthetic execution')
        return canonical_digest(result)
    first = one()
    require(first == one(), 'Repeated synthetic workflow was not deterministic')
    return {'schema': SMOKE_SCHEMA, 'case_id': cfg['case_id'],
            'source_chain_sha256': info['source_chain_sha256'],
            'config_sha256': canonical_digest(cfg),
            'random_seed': info['v29_config']['random_seed'],
            'synthetic_aggregate_sha256': first,
            'deterministic_repetition_verified': True,
            'n_invented_rows': 72, 'n_folds': 3,
            'row_predictions_recorded': False, 'public_export': False,
            'model_files_written': False, 'independent_validation': False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    actions = ap.add_mutually_exclusive_group(required=True)
    for name in ALLOWED_ACTIONS:
        actions.add_argument(name, action='store_true')
    ap.add_argument('--project', default='.')
    ap.add_argument('--config', default='research/cases/nhanes_integrity_v30.json')
    a = ap.parse_args()
    root = Path(a.project).resolve()
    cfg = _strict_json(source_file(root, a.config).read_text())
    validate_integrity(cfg)
    if a.plan:
        out = plan(root, cfg)
        print('V30 SOURCE-ONLY WORKFLOW INTEGRITY PLAN:',
              json.dumps({k: out[k] for k in ('case_id', 'route',
                  'source_chain_sha256', 'holdout_history',
                  'prediction_index_status')}, indent=2))
        print('PLAN ONLY. No private metadata, participants, or models accessed.')
    elif a.smoke:
        print('V30 GENERATED-SYNTHETIC REPRODUCIBILITY:',
              json.dumps(synthetic_smoke(root, cfg), indent=2))
        print('Synthetic-only model fits in memory; no research records accessed.')
    elif a.audit:
        out = plan(root, cfg)
        info = inventory(root, cfg)
        prior_v29_review(root, cfg, info)
        out['v29_private_metadata_verified'] = True
        target = private_review_file(root, cfg)
        write_immutable_review(target, out)
        print('PRIVATE IMMUTABLE WORKFLOW INTEGRITY REVIEW:', target)
    else:
        p = verified_review(root, cfg)
        print('PASS: v0.30 source digests agree with immutable private review:', p)
    print('Real-data analysis remains BLOCKED_FOR_NEW_ANALYSIS. No participant tables, holdout targets or saved models opened.')


if __name__ == '__main__':
    main()
