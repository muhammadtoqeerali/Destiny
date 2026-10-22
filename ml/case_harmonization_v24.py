"""FrailtyScope v0.24: declarative data harmonization contracts (source-only CLI).

CLI never opens participant tables, fitted models, predictions, or labels.
In-memory transform is for *invented synthetic test fixtures only* in v0.24.
Real-data execution is reserved for a separately authorized future workflow.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re

SCHEMA = 'FRAILTYSCOPE_HARMONIZATION_PROTOCOL_V24'
REPORT_SCHEMA = 'FRAILTYSCOPE_PRIVATE_HARMONIZATION_REVIEW_V24'
STATUSES = {'refused', 'unknown', 'not_applicable', 'does_not_do_activity',
            'not_recorded', 'structural_skip', 'not_measured', 'below_detection'}
KINDS = {'numeric', 'ordinal', 'categorical', 'binary'}
FORBIDDEN = {'outcome', 'outcome_5yr', 'mortstat', 'permth_exm', 'permth_int',
             'eligstat', 'duration', 'event', 'death_date', 'seqn', 'person_id',
             'patient_id', 'id', 'label', 'target'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def local_file(root, relative, folder):
    require(isinstance(relative, str) and relative and '\\' not in relative,
            'Expected safe relative source path')
    p = Path(relative)
    require(not p.is_absolute() and '..' not in p.parts and p.parts[0] == folder,
            'Source path must remain inside '+folder+'/')
    result = (root / p).resolve()
    require(result.is_relative_to((root / folder).resolve()) and result.is_file(),
            'Required source file not found')
    return result


def canonical_code(value):
    """Exact source code equality, preserving strings; never infer response meaning."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        raise ValueError('Boolean input is not an approved code')
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('Unrecognized source code: '+str(type(value))) from None
    require(d.is_finite(), 'Nonfinite source code')
    return format(d.normalize(), 'f')


def is_missing(value):
    import pandas as pd
    result = pd.isna(value)
    require(isinstance(result, (bool, type(pd.NA))) or str(type(result)).endswith("numpy.bool'>"),
            'Nested input values are unsupported')
    return bool(result)


def _validate_feature(name, spec, dictionary_sources):
    require(re.fullmatch(r'[a-z][a-z0-9_]{1,64}', name) is not None,
            'Invalid canonical field')
    require(name not in FORBIDDEN and not name.endswith('__status'),
            'Targets, person IDs and reserved names cannot be harmonized predictors')
    require(isinstance(spec, dict) and spec.get('kind') in KINDS,
            'Unknown feature type: '+name)
    source = spec.get('source_column')
    require(isinstance(source, str) and re.fullmatch('[A-Za-z][A-Za-z0-9_]{1,50}', source),
            'Invalid source field for '+name)
    require(source.casefold() not in FORBIDDEN and source in dictionary_sources,
            'Undocumented or prohibited source column for '+name)
    require(isinstance(spec.get('canonical_unit'), str) and spec['canonical_unit'].strip(),
            'Canonical units required')
    require(isinstance(spec.get('source_unit'), str) and spec['source_unit'].strip(),
            'Source units required')
    require(isinstance(spec.get('mapping_evidence'), str) and len(spec['mapping_evidence'])>=10,
            'Document a codebook/source evidence reference')
    ref=spec['mapping_evidence']
    safe_local = (ref.startswith('research/') and '..' not in Path(ref).parts and\
                  '\\' not in ref)
    require((ref.startswith('https://') or safe_local) and\
            not any(c in ref for c in '\r\n\t'),
            'Evidence must refer to codebook URL or safe source documentation')
    missing = spec.get('missing_codes', {})
    require(isinstance(missing, dict) and all(isinstance(k, str) and
            isinstance(v, str) and v in STATUSES for k, v in missing.items()),
            'Invalid special missing-code mapping')
    codes = spec.get('value_codes', {})
    require(isinstance(codes, dict) and all(isinstance(k, str) for k in codes) and
            not (set(missing) & set(codes)), 'Overlapping observed and special codes')
    require(all(k == canonical_code(k) for k in list(missing)+list(codes)),
            'Ambiguous numeric code spellings in mappings')
    if spec['kind'] != 'numeric':
        require(len(codes)>0 and all(isinstance(v, (str, int, float)) and
                not isinstance(v, bool) for v in codes.values()),
                'Categorical, binary and ordinal values require explicit code mappings')
        require(spec.get('numeric_scale') is None and spec.get('numeric_offset') is None,
                'Unit conversion is only for numeric continuous predictors')
        if spec['kind'] in ('binary','ordinal'):
            require(all(type(v) in (int, float) and math.isfinite(v) for v in codes.values()),
                    'Binary/ordinal output must be numeric')
        if spec['kind'] == 'binary':
            require(set(codes.values()) <= {0,1} and set(codes.values()) == {0,1},
                    'Binary mappings must contain exactly zero/one categories')
    else:
        require(not codes, 'Numeric continuous fields do not accept ordinal code mappings')
        factor,offset = spec.get('numeric_scale'), spec.get('numeric_offset')
        require(type(factor) in (int,float) and math.isfinite(factor) and factor>0 and
                type(offset) in (int,float) and math.isfinite(offset),
                'Explicit finite positive numeric conversion required')
        if spec['canonical_unit']!=spec['source_unit'] or factor!=1 or offset!=0:
            require(spec.get('unit_conversion_verified') is True,
                    'Unit conversion requires explicit source verification')
        bounds=spec.get('valid_range')
        require(isinstance(bounds, list) and len(bounds)==2 and all(
            type(z) in (int,float) and math.isfinite(z) for z in bounds) and
            bounds[0]<bounds[1], 'Numeric bounds required')
    blank=spec.get('blank_status')
    require(blank is None or blank in STATUSES, 'Unknown null/missing status')
    rule=spec.get('skip_if')
    if rule is not None:
        require(isinstance(rule, dict) and set(rule)=={'column','equals'} and
                isinstance(rule['column'],str) and
                re.fullmatch('[A-Za-z][A-Za-z0-9_]{1,50}',rule['column']) and
                isinstance(rule['equals'],str), 'Invalid routing rule')
        require(rule['column'].casefold() not in FORBIDDEN and
                spec.get('blank_status')=='structural_skip',
                'Skip routing requires structural skip semantics')
    else:
        require(blank!='structural_skip',
                'Structural skip requires a source-backed routing rule')


def validate_protocol(cfg, dictionary):
    require(isinstance(cfg, dict) and cfg.get('schema')==SCHEMA,
            'Incorrect v0.24 schema')
    require(cfg.get('case_id')==dictionary.get('case_id'),
            'Harmonization/dictionary case mismatch')
    require(cfg.get('related_v23_protocol') and
            cfg.get('holdout_history')==dictionary.get('holdout_history') and
            cfg.get('prior_exploration')==dictionary.get('prior_exploration'),
            'Validation history must match the v0.23 dictionary')
    require(cfg.get('scope')=='partial_blueprint' and
            cfg.get('real_data_execution_permitted') is False and
            cfg.get('model_fitting_permitted') is False and
            cfg.get('holdout_scoring_permitted') is False and
            cfg.get('public_export_permitted') is False,
            'v0.24 is a partial source-only blueprint, not an execution clearance')
    predictors=dictionary.get('predictors')
    require(isinstance(predictors, dict) and predictors,
            'Missing source predictor dictionary')
    waves=cfg.get('waves')
    require(isinstance(waves,dict) and 1<=len(waves)<=12,
            'Define one or more documented collection waves')
    covered=set()
    by_feature={}
    for wave,info in waves.items():
        require(isinstance(wave,str) and 2<=len(wave)<=45 and isinstance(info,dict),
                'Invalid wave or wave specification')
        require(info.get('source_verified') is True and isinstance(info.get('features'),dict),
                'Wave mappings need source verification')
        for name,spec in info['features'].items():
            require(name in predictors,'Unknown predictor in harmonization '+name)
            _validate_feature(name,spec,predictors[name]['source_variables'])
            covered.add(name)
            if name in by_feature:
                other=by_feature[name]
                require((spec['kind'],spec['canonical_unit'])==
                        (other['kind'],other['canonical_unit']),
                        'Inconsistent output type/unit across waves for '+name)
                if spec['kind']!='numeric':
                    require(set(spec['value_codes'].values()) ==
                            set(other['value_codes'].values()),
                            'Inconsistent canonical categories across waves for '+name)
            else:by_feature[name]=spec
    declared=cfg.get('unmapped_predictors')
    require(isinstance(declared,list) and len(declared)==len(set(declared)) and
            set(declared)==set(predictors)-covered,
            'Unmapped predictor inventory must exactly cover remaining dictionary features')
    require(cfg.get('prediction_index_status')==dictionary['prediction_index']['definition_status'],
            'Prediction-index review cannot be reset by harmonization')
    return cfg


def harmonize_fixture(frame, spec, *, synthetic_fixture=False):
    """Apply ONE wave's mapping to invented in-memory rows only (no I/O).

    Emits canonical features + explicit status columns; unexpected codes, missing
    values, routing conflicts and out-of-range observations raise ValueError.
    """
    require(synthetic_fixture is True,'v0.24 forbids real-data application')
    import pandas as pd
    require(isinstance(frame,pd.DataFrame) and isinstance(spec,dict),
            'Expected synthetic DataFrame and wave spec')
    features=spec.get('features',{})
    require(features, 'No features selected')
    need={info['source_column'] for info in features.values()}
    need |= {info['skip_if']['column'] for info in features.values()
             if info.get('skip_if') is not None}
    require(need.issubset(frame.columns) and frame.columns.is_unique,
            'Missing input columns or duplicate source column names')
    results={};counts={}
    for name,rule in features.items():
        values=[];statuses=[]
        for _,row in frame.iterrows():
            original=row[rule['source_column']]
            skip=rule.get('skip_if')
            routed=(skip is not None and not is_missing(row[skip['column']]) and
                    canonical_code(row[skip['column']])==skip['equals'])
            if routed:
                require(is_missing(original),
                        'Source routing conflicts with observed answer: '+name)
            if is_missing(original):
                require(rule.get('blank_status') is not None and
                        (rule['blank_status']!='structural_skip' or routed),
                        'Unexplained blank in '+name)
                values.append(None);statuses.append(rule['blank_status']);continue
            key=canonical_code(original)
            if key in rule['missing_codes']:
                require(not routed, 'Nonblank special code violates skip: '+name)
                values.append(None);statuses.append(rule['missing_codes'][key]);continue
            require(not routed, 'Reported value violates documented skip: '+name)
            if rule['kind']=='numeric':
                try:value=float(key)
                except ValueError:raise ValueError('Unrecognized numeric value in '+name) from None
                require(math.isfinite(value), 'Nonfinite numeric value')
                value=value*rule['numeric_scale']+rule['numeric_offset']
                require(math.isfinite(value) and
                        rule['valid_range'][0]<=value<=rule['valid_range'][1],
                        'Observed value outside approved range: '+name)
            else:
                require(key in rule['value_codes'], 'Unreviewed source code '+name+': '+key)
                value=rule['value_codes'][key]
            values.append(value);statuses.append('observed')
        results[name]=values;results[name+'__status']=statuses
        counts[name]=dict(sorted(Counter(statuses).items()))
    return pd.DataFrame(results,index=frame.index),counts


def make_plan(cfg):
    mapped=sorted({name for wave in cfg['waves'].values() for name in wave['features']})
    return {'schema':REPORT_SCHEMA,'case_id':cfg['case_id'],
            'config_sha256':digest(cfg),'route':'BLOCKED_FOR_NEW_ANALYSIS',
            'index_status':cfg['prediction_index_status'],
            'holdout_history':cfg['holdout_history'],
            'mapped_predictors':mapped,'unmapped_predictors':cfg['unmapped_predictors'],
            'mapped_waves':sorted(cfg['waves']),
            'source_only_blueprint':True,'no_participant_tables_opened':True,
            'no_models_fitted':True,'no_predictions_generated':True,
            'no_holdout_targets_accessed':True,'public_export':False,
            'limitations':['Partial predictor coverage is not complete feature-readiness.',
                'v0.23 prediction index is provisional; no use at prediction time certified.',
                'Synthetic-only in-memory harmonization is not authorized real-data execution.',
                'No automatic imputation, row exclusion, or training outside development folds.',
                'Cross-wave comparability requires domain-expert and source review.',
                'Previously inspected later NHANES cycle cannot be reused as fresh validation.']}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    mode=cli.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true')
    mode.add_argument('--audit',action='store_true')
    cli.add_argument('--project',default='.')
    cli.add_argument('--config',default='research/cases/nhanes_harmonization_v24.json')
    a=cli.parse_args()
    root=Path(a.project).resolve()
    cfg=json.loads(local_file(root,a.config,'research').read_text())
    v23=json.loads(local_file(root,cfg['related_v23_protocol'],'research').read_text())
    from ml.case_dictionary_timing_v23 import validate_protocol as check_dictionary
    from ml.case_governance_v22 import validate_protocol as check_governance
    manifest=json.loads(local_file(root,v23['case_manifest'],'research').read_text())
    prior=json.loads(local_file(root,v23['related_v22_protocol'],'research').read_text())
    check_governance(prior);check_dictionary(v23,manifest,prior)
    validate_protocol(cfg,v23)
    report=make_plan(cfg)
    if a.audit:
        prev=local_file(root,cfg['related_private_v23_ledger'],'artifacts')
        require(prev.suffix=='.json' and prev.stat().st_size<250_000,
                'Unsafe prior private metadata report')
        doc=json.loads(prev.read_text())
        from ml.case_dictionary_timing_v23 import digest as prior_digest, REPORT_SCHEMA as PRIOR_SCHEMA
        require(doc.get('schema')==PRIOR_SCHEMA and
                doc.get('protocol_sha256')==prior_digest(v23) and
                doc.get('case_id')==cfg['case_id'] and
                doc.get('no_models_fitted') is True and
                doc.get('no_data_rows_opened') is True and
                doc.get('no_holdout_targets_accessed') is True and
                doc.get('public_export') is False,
                'Prior private metadata cannot support v0.24 review')
        report['v23_private_metadata_verified']=True
    print('V24 SOURCE HARMONIZATION PLAN:',json.dumps({key:report[key] for key in (
        'case_id','route','index_status','holdout_history','mapped_predictors',
        'unmapped_predictors','mapped_waves')},indent=2))
    if a.audit:
        target=(root/'artifacts/cases'/cfg['case_id']/'harmonization_v24'/
                digest(cfg)[:12]/'harmonization_review.json').resolve()
        require(target.is_relative_to((root/'artifacts/cases').resolve()),'Unsafe output path')
        require(not target.exists(),'Existing immutable v0.24 review: refuse overwrite')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream:
            json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print('PRIVATE SOURCE METADATA REVIEW:',target)
    else:
        print('PLAN ONLY. No private artifacts or participant data opened.')
    print('No models, predictions, held-out target labels or source datasets accessed.')

if __name__=='__main__':main()
