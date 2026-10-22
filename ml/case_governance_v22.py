"""FrailtyScope v0.22 -- source-only research governance / evidence register.

No training, scoring, model loading, or participant-table reading is present.
--plan validates source-controlled assertions. --audit checks only explicitly
registered, LOCAL aggregate-report metadata and saves a PRIVATE checklist.
A completed checklist never certifies study validity, data access, or clinical use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_RESEARCH_EVIDENCE_PROTOCOL_V22'
REPORT_SCHEMA = 'FRAILTYSCOPE_LOCAL_EVIDENCE_LEDGER_V22'
STATES = {'documented', 'limited', 'pending', 'not_applicable'}
STAGES = ('governance', 'data', 'design', 'model', 'evaluation', 'reporting', 'operations')

# id, stage, blocking if pending, question. Broad coverage, not a certification checklist.
CATALOG = (
 ('legal_access','governance',True,'Are approvals, data rights and project scope valid?'),
 ('secure_environment','governance',True,'Are authorized storage, compute, access and retention defined?'),
 ('privacy_disclosure','governance',True,'Are outputs, small cells and participant-level exports controlled?'),
 ('stakeholder_question','governance',True,'Is the actual research/clinical question and intended user defined?'),
 ('population_sampling','data',True,'Are source population, selection, eligibility and nonparticipation characterized?'),
 ('provenance_versions','data',True,'Are raw source, transformations, checksums and dictionary tracked?'),
 ('data_integrity','data',True,'Have types, duplicates, ranges, units, joins and impossible values been checked?'),
 ('missingness_mechanisms','data',False,'Are skips, nonresponse, unavailable values and codebook semantics distinguished?'),
 ('wave_site_harmonization','data',False,'Are instruments/units/definitions compatible across waves and sites?'),
 ('outcome_index_horizon','design',True,'Are prediction time, outcome, horizon and availability precisely defined?'),
 ('followup_censoring','design',True,'Are censoring, competing risks and outcome ascertainment addressed?'),
 ('observation_grain','design',True,'Are repeated visits, family/site groups and event dependence recognized?'),
 ('predictor_availability','design',True,'Are all candidate predictors known at prediction time?'),
 ('leakage_prevention','design',True,'Are IDs, proxies, transformations and tuning isolated from evaluation?'),
 ('splits_and_holdout','design',True,'Are group/time/site splits and holdout reuse history recorded?'),
 ('missingness_processing','model',False,'Are imputations/indicators/categories source-aware and learned inside folds?'),
 ('candidate_models','model',False,'Are simple benchmarks and task-appropriate models compared fairly?'),
 ('tuning_and_reproducibility','model',True,'Are selection, CV, random seeds and computational budgets reproducible?'),
 ('class_imbalance_sample_size','model',False,'Are prevalence, event counts, power and effective sample size considered?'),
 ('survey_and_cluster_design','model',False,'Are weights, PSUs, strata, site clustering and estimands handled if relevant?'),
 ('discrimination_and_error','evaluation',False,'Are task-appropriate discrimination and error scores planned?'),
 ('calibration_and_proper_scores','evaluation',False,'Are calibration and proper scores evaluated without leakage?'),
 ('clinical_decision_utility','evaluation',False,'Are thresholds, harms, net benefit and use-case value justified?'),
 ('uncertainty_and_robustness','evaluation',False,'Are intervals, sensitivity and model selection uncertainty handled?'),
 ('subgroups_fairness','evaluation',False,'Are subgroup sample sizes, heterogeneity and equity assessed safely?'),
 ('external_transportability','evaluation',False,'Is a genuinely independent transport/temporal/site evaluation planned?'),
 ('transparent_reporting','reporting',False,'Are TRIPOD+AI and other study-specific reporting items planned?'),
 ('bias_applicability','reporting',False,'Are PROBAST+AI risk of bias and applicability reviewed separately?'),
 ('figures_reproducibility','reporting',False,'Are cohort flow, calibration, performance and versioned artifacts reproducible?'),
 ('limitations_communication','reporting',True,'Are exploration, perturbed labels and intended-use limits explicit?'),
 ('deployment_scope','operations',True,'Is there a clear no-deployment or approved deployment boundary?'),
 ('drift_monitoring','operations',False,'Is a monitoring, updating and incident plan needed and defined?'),
 ('handoff_and_ownership','operations',False,'Are analyst, PI, custodian and approver roles assigned?'),
)
IDS = tuple(row[0] for row in CATALOG)
CATALOG_MAP = {row[0]: row for row in CATALOG}
LOCAL_TYPES = {
 'v19_readiness': 'FRAILTYSCOPE_LOCAL_READINESS_V19',
 'v20_pfq': 'FRAILTYSCOPE_LOCAL_PFQ_SKIP_AUDIT_V20',
 'v21_semantics': 'FRAILTYSCOPE_LOCAL_SOURCE_SEMANTICS_V21',
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def digest_json(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode()).hexdigest()


def safe_rel(value: str, parent: str) -> bool:
    if not isinstance(value, str) or not value or '\\' in value:
        return False
    p = Path(value)
    return not p.is_absolute() and '..' not in p.parts and p.parts[0] == parent and len(p.parts) >= 2


def check_evidence_reference(value: str) -> None:
    require(isinstance(value, str) and 5 <= len(value) <= 400 and not any(c in value for c in '\r\n\t'),
            'Evidence references must be short, plain-text references')
    require(value.startswith('https://') or safe_rel(value, 'research') or
            safe_rel(value, 'ml') or safe_rel(value, 'tests') or
            safe_rel(value, 'artifacts') or safe_rel(value, 'scripts'),
            'Evidence must be an HTTPS URL or confined relative source/local-artifact path')
    if not value.startswith('https://'):
        require(not re.search(r'(?:^|/)(?:data|web/public)(?:/|$)', value),
                'Do not point evidence references to research tables or public data assets')


def validate_protocol(cfg: dict) -> dict:
    require(isinstance(cfg, dict) and cfg.get('schema') == SCHEMA, 'Unexpected v0.22 schema')
    case = cfg.get('case_id')
    require(isinstance(case, str) and re.fullmatch('[a-z][a-z0-9_]{2,70}', case),
            'Invalid case identifier')
    require(cfg.get('use_class') in ('research_only', 'potential_clinical_future'),
            'Explicit intended-use boundary required')
    require(cfg.get('holdout_history') in ('previously_inspected','locked_new','not_applicable'),
            'Declare holdout history; do not infer pristine evaluation status')
    require(cfg.get('prior_exploration') in (True, False) and
            type(cfg['prior_exploration']) is bool, 'Prior exploration declaration required')
    require(cfg.get('deployment_permitted') is False and
            cfg.get('publish_private_evidence') is False,
            'The evidence-register protocol cannot authorize deployment or private export')
    for fingerprint in ('expected_dataset_sha256','expected_raw_source_sha256'):
        sha=cfg.get(fingerprint)
        require(sha is None or (isinstance(sha,str) and re.fullmatch('[0-9a-f]{64}',sha)),
                'Source fingerprint must be SHA256 or null: '+fingerprint)
    source = cfg.get('related_readiness_v19')
    require(source is None or safe_rel(source, 'research'),
            'Source readiness protocol must remain under research/')
    observations = cfg.get('controls')
    require(isinstance(observations, dict) and set(observations) == set(IDS),
            'All and only approved checklist control IDs must be present')
    for name,entry in observations.items():
        require(isinstance(entry, dict) and entry.get('state') in STATES,
                'Unrecognized status for '+name)
        note = entry.get('note')
        require(isinstance(note,str) and 8 <= len(note) <= 700,
                'Each control needs a meaningful rationale: '+name)
        refs = entry.get('evidence', [])
        require(isinstance(refs,list) and len(refs)<=5 and all(isinstance(r,str) for r in refs)
                and len(refs)==len(set(refs)), 'Invalid reference list: '+name)
        for ref in refs: check_evidence_reference(ref)
        if entry['state'] in ('documented','limited'):
            require(bool(refs), 'Documented/limited claims require source or audit evidence: '+name)
        if entry['state']=='not_applicable':
            require(not refs, 'Not-applicable entries need rationale, not false evidence: '+name)
    if cfg['holdout_history']=='previously_inspected':
        require(observations['splits_and_holdout']['state'] != 'not_applicable',
                'Previously inspected holdout requires explicit limitations')
    local = cfg.get('local_evidence',[])
    require(isinstance(local,list) and len(local)<=12, 'Invalid private evidence pointers')
    ids=[];paths=[]
    for rec in local:
        require(isinstance(rec,dict) and rec.get('type') in LOCAL_TYPES and
                safe_rel(rec.get('path'),'artifacts') and
                isinstance(rec.get('required'),bool), 'Invalid local evidence pointer')
        ids.append(rec['type']); paths.append(rec['path'])
    require(len(ids)==len(set(ids)) and len(paths)==len(set(paths)),
            'Duplicate private audit pointers')
    return cfg


def _safe_report_file(project: Path, relative: str) -> Path:
    base=(project/'artifacts').resolve()
    target=(project/relative).resolve()
    require(target.is_relative_to(base) and target.is_file() and target.suffix=='.json',
            'Missing/unsafe private audit report: '+relative)
    return target


def verify_local_evidence(cfg: dict, project: Path) -> list[dict]:
    """Only saved *aggregate JSON* metadata; do not open CSVs, mortality files or models."""
    checked=[]
    for spec in cfg['local_evidence']:
        target=(project/spec['path']).resolve()
        if not target.is_file():
            require(not spec['required'], 'Required private report missing: '+spec['path'])
            checked.append({'type':spec['type'], 'state':'unavailable_optional'})
            continue
        path=_safe_report_file(project,spec['path'])
        require(path.stat().st_size < 250_000, 'Unexpectedly large aggregate report: '+spec['path'])
        obj=json.loads(path.read_text())
        require(isinstance(obj,dict) and obj.get('schema')==LOCAL_TYPES[spec['type']] and
                obj.get('case_id')==cfg['case_id'] and obj.get('public_export') is False,
                'Private report schema, case or export boundary invalid')
        dataset=cfg.get('expected_dataset_sha256')
        raw_source=cfg.get('expected_raw_source_sha256')
        if dataset is not None:
            observed=(obj.get('processed_sha256') if spec['type']=='v21_semantics'
                      else obj.get('dataset_sha256'))
            require(observed==dataset,'Prior local aggregate report dataset fingerprint mismatch')
        if raw_source is not None and spec['type'] in ('v20_pfq','v21_semantics'):
            require(obj.get('raw_pfq_sha256')==raw_source,
                    'Prior raw questionnaire fingerprint mismatch')
        if spec['type']=='v19_readiness':
            require(obj.get('no_holdout_target_analysis') is True and obj.get('n_model_fits')==0
                    and obj.get('n_model_scores')==0 and obj.get('local_only') is True,
                    'v0.19 no-outcome-access contract broken')
        if spec['type']=='v20_pfq':
            require(obj.get('holdout_labels_read') is False and obj.get('model_fits')==0
                    and obj.get('participant_records_exported') is False,
                    'v0.20 holdout and privacy contract broken')
        if spec['type']=='v21_semantics':
            require(obj.get('holdout_outcomes_accessed') is False and
                    obj.get('model_overwritten') is False and obj.get('model_binary_exported') is False,
                    'v0.21 model/holdout boundary broken')
        checked.append({'type':spec['type'], 'state':'metadata_valid',
                        'path':spec['path'], 'aggregate_only':True})
    return checked


def generate_ledger(cfg:dict, local: list[dict]) -> dict:
    """Conservative documentary inventory; no automatic clinical or modelling clearance."""
    counts=Counter(); stages=defaultdict(lambda:Counter()); actions=[];hard_pending=[]
    for name,stage,blocking,question in CATALOG:
        state=cfg['controls'][name]['state'];counts[state]+=1;stages[stage][state]+=1
        if state in ('pending','limited'):
            actions.append({'control':name,'stage':stage,'priority':'blocking' if blocking else 'review',
                            'state':state,'next_action':question})
        if blocking and state=='pending':hard_pending.append(name)
    if hard_pending:route='PROTOCOL_BLOCKED_PENDING_EVIDENCE'
    elif counts['limited'] or counts['pending']:route='RESEARCH_REVIEW_REQUIRED'
    else:route='DOCUMENTARY_CHECKLIST_COMPLETE_NOT_VALIDATED'
    if cfg['use_class']=='potential_clinical_future':
        route='CLINICAL_USE_NOT_AUTHORIZED'  # deliberately never certifies clinical readiness
    return {
        'schema':REPORT_SCHEMA,'report_type':'LOCAL_SOURCE_AND_AGGREGATE_DOCUMENTARY_REVIEW',
        'case_id':cfg['case_id'],'protocol_sha256':digest_json(cfg),
        'use_class':cfg['use_class'],'holdout_history':cfg['holdout_history'],
        'prior_exploration':cfg['prior_exploration'],
        'route':route,'control_counts':dict(sorted(counts.items())),
        'stage_counts':{stage:dict(sorted(stages[stage].items())) for stage in STAGES},
        'critical_pending':hard_pending,'action_backlog':actions,
        'local_evidence_checks':local,
        'no_models_fitted':True,'no_predictions_generated':True,
        'no_holdout_outcomes_analyzed':True,'private_data_read':False,
        'public_export':False,'clinical_use_permitted':False,
        'limitations':[
          'States are source-controlled assertions with cited evidence, not independent regulatory certification.',
          'Local reports are checked for schema and privacy flags only, not revalidated against raw records.',
          'Study-specific ethical approval and institutional/HUNT data-access decisions remain external.',
          'No checklist can identify a universally best model or replace external evaluation.',
          'Incomplete controls must be resolved using a new assignment protocol before fitting.',
          'Previously inspected evaluation data cannot become fresh independent validation.'
        ]}


def validate_ledger(cfg:dict, report:dict) -> dict:
    require(isinstance(report,dict) and report.get('schema')==REPORT_SCHEMA and
            report.get('report_type')=='LOCAL_SOURCE_AND_AGGREGATE_DOCUMENTARY_REVIEW' and
            report.get('protocol_sha256')==digest_json(cfg) and report.get('case_id')==cfg['case_id'],
            'Unexpected local v0.22 report/protocol')
    require(report.get('no_models_fitted') is True and
            report.get('no_predictions_generated') is True and
            report.get('no_holdout_outcomes_analyzed') is True and
            report.get('private_data_read') is False and report.get('public_export') is False and
            report.get('clinical_use_permitted') is False,
            'Unsafe report claims')
    expected=generate_ledger(cfg,report.get('local_evidence_checks',[]))
    require(report.get('route')==expected['route'] and
            report.get('control_counts')==expected['control_counts'] and
            report.get('critical_pending')==expected['critical_pending'],
            'Source control ledger has been tampered with')
    return {'case_id':cfg['case_id'],'route':report['route'],
            'controls':len(IDS), 'fits':0, 'holdout_scored':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true',help='Source-only checklist validation, no dataset access')
    mode.add_argument('--audit',action='store_true',help='Review aggregate local metadata; save private ledger')
    parser.add_argument('--project',default='.')
    parser.add_argument('--config',default='research/cases/nhanes_governance_v22.json')
    args=parser.parse_args()
    project=Path(args.project).resolve()
    conf=(project/args.config).resolve()
    require(conf.is_relative_to((project/'research').resolve()) and conf.is_file(),
            'Case protocol must be a file under research/')
    cfg=validate_protocol(json.loads(conf.read_text()))
    source=cfg.get('related_readiness_v19')
    if source:
        ref=(project/source).resolve()
        require(ref.is_relative_to((project/'research').resolve()) and ref.is_file(),
                'Related readiness source is absent/unsafe')
        source_cfg=json.loads(ref.read_text())
        require(source_cfg.get('case_id')==cfg['case_id'] and
                source_cfg.get('split',{}).get('holdout_status')==cfg['holdout_history'] and
                (cfg.get('expected_dataset_sha256') is None or
                 source_cfg.get('source',{}).get('expected_sha256')==cfg['expected_dataset_sha256']),
                'Readiness case, holdout history, or source fingerprint differs')
    local=verify_local_evidence(cfg,project) if args.audit else []
    report=generate_ledger(cfg,local)
    validate_ledger(cfg,report)
    print('V22 RESEARCH EVIDENCE PLAN:',json.dumps({
       'case_id':cfg['case_id'], 'route':report['route'],
       'n_controls':len(IDS),'counts':report['control_counts'],
       'critical_pending':report['critical_pending'],
       'local_metadata_checked':len(local), 'n_models_fitted':0,
       'holdout_scored':False,'clinical_use_permitted':False},indent=2))
    print('UNRESOLVED ACTIONS:',json.dumps(report['action_backlog'],indent=2))
    if args.audit:
        output=(project/'artifacts'/'cases'/cfg['case_id']/'governance_v22'/
                digest_json(cfg)[:12]/'evidence_ledger.json').resolve()
        require(output.is_relative_to((project/'artifacts'/'cases').resolve()),
                'Private report path unsafe')
        require(not output.exists(),'Immutable evidence ledger exists: refuse overwrite')
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('x') as stream:
            json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print('PRIVATE SOURCE EVIDENCE LEDGER:',output)
    else:
        print('PLAN ONLY. No local artifact or research dataset opened; nothing saved.')
    print('No models, predictions, holdout outcomes, public export, or deployment.')

if __name__ == '__main__':
    main()
