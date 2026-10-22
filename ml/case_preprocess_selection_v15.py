"""FrailtyScope v0.15: workstation-only *nested* preprocessing selection.

This is a development-only, exploratory reassessment of feature/missingness choices
suggested by v0.14. Because the same cohort informed those choices, these nested
folds are NOT fresh independent validation. Evaluation/holdout rows are not used
for fitting, preprocessing selection or scoring. Nothing runs at import time.

Only models with a single regularization parameter are supported: logistic, ridge.
Ablation variants are drawn strictly from the validated v0.14 manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_NESTED_PREPROCESS_SELECTION_V15'
SUPPORTED_FAMILIES = {'logistic': ('classification', 'C'), 'ridge': ('regression', 'alpha')}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical_sha(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                      ensure_ascii=False).encode()).hexdigest()


def validate_design(config: dict, manifest: dict, strategy: dict,
                    selection: dict, ablation: dict, prior_report: dict) -> dict:
    """Pure contract checks: no model loading, dataset reads, or fitting."""
    require(isinstance(config, dict) and config.get('schema') == SCHEMA, 'Invalid v0.15 schema')
    require(config.get('case_id') == manifest.get('case_id') == strategy.get('case_id')
            == ablation.get('case_id'), 'Mismatched case IDs')
    require(selection.get('schema') == 'FRAILTYSCOPE_CASE_STRATEGY_V13' and
            selection.get('holdout_used_in_selection') is False, 'Prior model selection not sealed')
    require(selection.get('manifest_sha256') == canonical_sha(manifest) and
            selection.get('protocol_sha256') == canonical_sha(strategy),
            'Manifest or strategy changed since v0.13')
    require(selection.get('selected_model') in SUPPORTED_FAMILIES,
            'v0.15 only supports regularized logistic and ridge; do not substitute a family')
    task, param = SUPPORTED_FAMILIES[selection['selected_model']]
    require(manifest.get('task') == task, 'Selected family incompatible with prediction task')
    require(strategy.get('primary_metric') == config.get('primary_metric'),
            'v0.15 metric must match v0.13 declaration')
    require(prior_report.get('schema') == 'FRAILTYSCOPE_DEVELOPMENT_ABLATION_V14' and
            prior_report.get('case_id') == manifest['case_id'] and
            prior_report.get('n_evaluation_predictions_generated') == 0 and
            prior_report.get('selection_or_model_replacement_performed') is False,
            'v0.14 report must be development-only')
    require(prior_report.get('manifest_sha256') == canonical_sha(manifest) and
            prior_report.get('strategy_sha256') == canonical_sha(strategy) and
            prior_report.get('ablation_config_sha256') == canonical_sha(ablation),
            'Stale or mismatched v0.14 ablation report')
    require(prior_report.get('selected_model_fixed') == selection.get('selected_model') and
            prior_report.get('selected_hyperparameters_fixed') == selection.get('selected_params'),
            'Prior ablation did not use the v0.13 winner')
    require(prior_report.get('primary_metric') == config['primary_metric'],
            'Prior ablation metric changed')
    require('reference' in [v.get('name') for v in ablation['variants']],
            'Reference preprocessing missing')
    selected_variants = config.get('variants')
    available = [v['name'] for v in ablation['variants']]
    require(isinstance(selected_variants, list) and 2 <= len(selected_variants) <= 5
            and len(set(selected_variants)) == len(selected_variants)
            and selected_variants[0] == 'reference'
            and all(v in available for v in selected_variants), 'Invalid subset of ablation variants')
    require('missingness_indicators' in selected_variants,
            'Explicit missingness-indicator comparator required')
    for key in ('outer_folds', 'inner_folds'):
        require(type(config.get(key)) is int and 2 <= config[key] <= 5,
                'Invalid '+key)
    seeds = config.get('outer_seeds')
    require(isinstance(seeds, list) and 1 <= len(seeds) <= 4
            and all(type(s) is int and 0 <= s < 2**31 for s in seeds)
            and len(set(seeds)) == len(seeds), 'Invalid outer seeds')
    grid = config.get('regularization_grid')
    require(isinstance(grid, list) and 3 <= len(grid) <= 15
            and all(type(x) in (int, float) and math.isfinite(x) and 0.001 <= x <= 100
                    for x in grid) and len(set(grid)) == len(grid),
            'Invalid positive regularization grid')
    require(all(grid[i] < grid[i+1] for i in range(len(grid)-1)),
            'Regularization grid must be sorted ascending')
    margin = config.get('practical_tie_margin')
    require(type(margin) in (float, int) and math.isfinite(margin)
            and 0 <= margin <= 0.02, 'Invalid practical margin')
    require(config.get('holdout_policy') == 'development_only_no_evaluation',
            'v0.15 cannot run against holdout')
    estimated_fits = len(seeds) * config['outer_folds'] * (
        len(selected_variants) * len(grid) * config['inner_folds'] + 2)
    require(estimated_fits <= 2000,
            'Projected training budget too high: narrow the config before running')
    require(param in ('C', 'alpha'), 'Invalid model parameter')
    return config


def choose_preprocessing(records: list[dict], variant_order: list[str],
                         practical_margin: float) -> dict:
    """Among each variant's best hyperparameters, select lowest inner CV loss.

    Prefer reference if it is within the predeclared practical tie margin.
    This is a preference policy, NOT statistical equivalence or new validation.
    """
    require(bool(records) and bool(variant_order) and variant_order[0] == 'reference',
            'Missing inner CV comparison')
    require(all(r.get('variant') in variant_order and
                isinstance(r.get('loss'), (int, float)) and math.isfinite(r['loss'])
                for r in records), 'Invalid inner CV losses')
    require(all(any(r['variant'] == n for r in records) for n in variant_order),
            'Candidate variant absent')
    require(math.isfinite(practical_margin) and practical_margin >= 0,
            'Invalid margin')
    best_per_variant = {
        name: min((r for r in records if r['variant'] == name),
                  key=lambda z: (z['loss'], z['regularization']))
        for name in variant_order
    }
    lowest = min(r['loss'] for r in best_per_variant.values())
    eligible = [v for v in variant_order
                if best_per_variant[v]['loss'] <= lowest + practical_margin + 1e-12]
    selected = eligible[0]  # reference wins a practical tie
    winner = best_per_variant[selected]
    ref = best_per_variant['reference']
    return {
        'variant': selected, 'regularization': float(winner['regularization']),
        'inner_loss': float(winner['loss']), 'reference_inner_loss': float(ref['loss']),
        'reference_regularization': float(ref['regularization']),
        'best_possible_inner_loss': float(lowest),
        'tie_margin': float(practical_margin),
        'eligible_variants': eligible,
    }


def paired_summary(rows: list[dict]) -> dict:
    """Summarize pooled OOF losses per repeat; repeats are NOT independent samples."""
    import numpy as np
    require(bool(rows) and all(isinstance(r.get('reference_loss'), (float, int)) and
             isinstance(r.get('selected_loss'), (float, int)) and
             math.isfinite(r['reference_loss']) and math.isfinite(r['selected_loss'])
             for r in rows), 'Nonfinite paired loss record')
    gains = np.asarray([r['reference_loss'] - r['selected_loss'] for r in rows], float)
    return {
        'reference_mean_loss': round(float(np.mean([r['reference_loss'] for r in rows])), 6),
        'selection_mean_loss': round(float(np.mean([r['selected_loss'] for r in rows])), 6),
        'mean_loss_gain_vs_reference': round(float(np.mean(gains)), 6),
        'gain_by_repeat': [round(float(v), 6) for v in gains],
        'repeats_with_lower_selection_loss': int((gains > 0).sum()),
        'repeats': len(rows),
        'inference': 'Exploratory development-only paired nested CV; repeated splits reuse the same people.'
    }


def locate_context(project: Path, config_path: Path):
    """Read verified v0.13/v0.14 local contracts. Never inspect holdout labels."""
    from ml.case_ablation_v14 import load_context, sha_json
    project = project.resolve()
    target = config_path.resolve()
    require(target.is_relative_to((project/'research').resolve()) and target.is_file(),
            'v0.15 config must exist under research/')
    config = json.loads(target.read_text())
    ablation_path = (project/config.get('ablation_config', '')).resolve()
    require(ablation_path.is_relative_to((project/'research').resolve()) and ablation_path.is_file(),
            'v0.14 config must exist under research/')
    context = load_context(project, ablation_path)
    ablation, manifest, strategy, selection, digest, x, y, groups = context
    run_path = (project/'artifacts'/'cases'/manifest['case_id']/'ablation_v14'/
                sha_json(ablation)[:12]/'development_ablation.json')
    require(run_path.is_file(), 'Run the v0.14 development ablation first')
    prior = json.loads(run_path.read_text())
    validate_design(config, manifest, strategy, selection, ablation, prior)
    require(prior.get('dataset_sha256') == digest and
            prior.get('n_development') == len(y), 'Dataset does not match prior ablation')
    return config, context, prior


def inner_search(x, y, groups, manifest, selection, ablation, config, seed):
    """Workstation fitting ONLY; inner folds refit the full pipeline each time."""
    import numpy as np
    from ml.case_strategy_v13 import fold_indices, primary_loss
    from ml.case_engine_v10 import _pred
    from ml.case_ablation_v14 import model_pipeline, columns_for
    by_name = {v['name']: v for v in ablation['variants']}
    variants = config['variants']
    family = selection['selected_model']
    param = SUPPORTED_FAMILIES[family][1]
    folds = list(fold_indices(y, config['inner_folds'], seed, manifest['task'], groups))
    records = []
    for name in variants:
        variant = by_name[name]
        num, cat = columns_for(manifest, variant)
        for value in config['regularization_grid']:
            override = {'selected_model': family, 'selected_params': {param: value}}
            scores = []
            for tr, va in folds:
                model = model_pipeline(manifest, override, variant)
                model.fit(x.iloc[tr][num+cat], y.iloc[tr])
                predictions = np.asarray(_pred(model, x.iloc[va][num+cat], manifest['task']), float)
                require(len(predictions) == len(va) and np.isfinite(predictions).all(),
                        'Invalid inner-fold predictions')
                scores.append(primary_loss(y.iloc[va], predictions, manifest['task'],
                                           config['primary_metric']))
            records.append({'variant': name, 'regularization': float(value),
                            'loss': float(np.mean(scores))})
    return choose_preprocessing(records, variants, config['practical_tie_margin'])


def run(context):
    """No evaluation-row predictions; all OOF scoring is on DEVELOPMENT only."""
    import numpy as np
    from ml.case_strategy_v13 import fold_indices, primary_loss
    from ml.case_engine_v10 import _pred
    from ml.case_ablation_v14 import model_pipeline, columns_for
    config, ablation_context = context
    ablation, manifest, strategy, selection, digest, x, y, groups = ablation_context
    family = selection['selected_model']
    param = SUPPORTED_FAMILIES[family][1]
    variants = {v['name']: v for v in ablation['variants']}
    repeat_rows, fold_rows = [], []
    for seed in config['outer_seeds']:
        outer = list(fold_indices(y, config['outer_folds'], seed, manifest['task'], groups))
        reference_oof = np.full(len(y), np.nan)
        selected_oof = np.full(len(y), np.nan)
        for fold_number, (tr, va) in enumerate(outer, start=1):
            group_inner = groups[tr] if groups is not None else None
            decision = inner_search(x.iloc[tr].reset_index(drop=True),
                                    y.iloc[tr].reset_index(drop=True), group_inner,
                                    manifest, selection, ablation, config,
                                    seed+1000*fold_number)
            for choice, name, reg in [('reference', 'reference', decision['reference_regularization']),
                                      ('selection', decision['variant'], decision['regularization'])]:
                variant = variants[name]
                num, cat = columns_for(manifest, variant)
                override = {'selected_model': family, 'selected_params': {param: reg}}
                model = model_pipeline(manifest, override, variant)
                model.fit(x.iloc[tr][num+cat], y.iloc[tr])
                preds = np.asarray(_pred(model, x.iloc[va][num+cat], manifest['task']), float)
                require(len(preds) == len(va) and np.isfinite(preds).all(),
                        'Invalid outer-fold predictions')
                (reference_oof if choice == 'reference' else selected_oof)[va] = preds
            fold_rows.append({'seed': seed, 'fold': fold_number,
                              'assessment_n': len(va), 'selected_variant': decision['variant'],
                              'selected_regularization': round(decision['regularization'], 8),
                              'reference_regularization': round(decision['reference_regularization'], 8),
                              'inner_selected_loss': round(decision['inner_loss'], 7),
                              'inner_reference_loss': round(decision['reference_inner_loss'], 7)})
            print(f'DEV NESTED seed={seed} fold={fold_number}/{len(outer)}: '
                  f"preprocess={decision['variant']}", flush=True)
        require(np.isfinite(reference_oof).all() and np.isfinite(selected_oof).all(),
                'Incomplete outer-fold OOF estimates')
        ref_loss = primary_loss(y, reference_oof, manifest['task'], config['primary_metric'])
        sel_loss = primary_loss(y, selected_oof, manifest['task'], config['primary_metric'])
        repeat_rows.append({'seed': seed, 'n': len(y),
                            'reference_loss': round(float(ref_loss), 8),
                            'selected_loss': round(float(sel_loss), 8)})
        print(f'DEV NESTED REPEAT {seed}: reference={ref_loss:.6f} '
              f'selection={sel_loss:.6f}', flush=True)
    freq = Counter(row['selected_variant'] for row in fold_rows)
    return {'schema': SCHEMA,
            'report_type': 'LOCAL_EXPLORATORY_NESTED_DEVELOPMENT_ONLY',
            'case_id': manifest['case_id'], 'dataset_sha256': digest,
            'manifest_sha256': canonical_sha(manifest),
            'strategy_sha256': canonical_sha(strategy),
            'ablation_sha256': canonical_sha(ablation),
            'v15_protocol_sha256': canonical_sha(config),
            'selected_family': family,
            'outer_folds': config['outer_folds'], 'inner_folds': config['inner_folds'],
            'outer_seeds': config['outer_seeds'],
            'preprocessing_candidates': config['variants'],
            'regularization_parameter': param,
            'regularization_grid': config['regularization_grid'],
            'n_development': int(len(y)), 'n_evaluation_predictions_generated': 0,
            'model_replaced': False, 'public_export': False,
            'fold_selection_counts': dict(freq),
            'fold_selection_details': fold_rows,
            'repeated_nested': repeat_rows,
            'comparison': paired_summary(repeat_rows),
            'interpretation': 'Compared inner-fold-selected preprocessing and regularization '
                              'against an inner-fold-tuned reference on paired outer folds.',
            'limitations': [
                'The same NHANES development data previously informed candidate feature choices.',
                'These nested CV folds are post-hoc exploratory reuse, not independent confirmation.',
                'Repeated CV uses overlapping people; repeat SD is not an inferential confidence interval.',
                'No later-cycle holdout scores generated or used to select preprocessing.',
                'No model promotion, clinical threshold or externally validated outcome.'
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true', help='Check contracts only; no model fitting')
    mode.add_argument('--run', action='store_true', help='Workstation development nested-CV fitting')
    parser.add_argument('--project', default='.')
    parser.add_argument('--config', default='research/cases/nhanes_preprocess_selection_v15.json')
    args = parser.parse_args()
    project = Path(args.project).resolve()
    context = locate_context(project, project/args.config)
    config, ablation_context, prior = context
    ablation, manifest, strategy, selection, digest, x, y, groups = ablation_context
    if args.plan:
        print('V15 PLAN:', json.dumps({
            'dataset_sha256': digest, 'case_id': manifest['case_id'],
            'development_n': len(y), 'evaluation_used': False,
            'prior_ablation_verified': True,
            'family': selection['selected_model'], 'candidate_variants': config['variants'],
            'outer_folds': config['outer_folds'], 'inner_folds': config['inner_folds'],
            'outer_repeats': len(config['outer_seeds']),
            'regularization_grid': config['regularization_grid'],
            'estimated_fold_fits': len(config['outer_seeds'])*config['outer_folds']*(
                len(config['variants'])*len(config['regularization_grid'])*config['inner_folds']+2),
            'training': False
        }, indent=2))
        print('No fitting, holdout inference, model replacement, or public export.')
        return
    output = (project/'artifacts'/'cases'/manifest['case_id']/'preprocess_selection_v15'/
              canonical_sha(config)[:12]/'nested_development.json').resolve()
    require(output.is_relative_to((project/'artifacts'/'cases').resolve()),
            'Output outside ignored artifact directory')
    require(not output.exists(), 'Existing v0.15 evidence: refuse overwrite')
    report = run((config, ablation_context))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as f:
        f.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print('LOCAL NESTED PREPROCESS REPORT:', output)
    print('NESTED COMPARISON:', json.dumps(report['comparison'], indent=2))
    print('No model binaries, individual scores, holdout inferences or public JSON exported.')

if __name__ == '__main__':
    main()
