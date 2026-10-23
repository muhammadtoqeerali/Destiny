"""Fail-closed, public-document-only research readiness receipt; never reads participant data.

This module cannot activate patient scoring. It only checks the immutable public workflow
flags and produces an accurate status receipt for the existing Doctor Portal.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

CASE = 'research/cases/nhanes_workflow_v29.json'
PUBLIC = 'web/app/data/inference-readiness-v39.json'
BLOCKED_FLAGS = (
    'real_data_execution_permitted', 'model_fitting_permitted',
    'holdout_scoring_permitted', 'clinical_use_permitted',
    'public_export_permitted', 'predictions_exported',
    'models_saved', 'independent_validation',
)
OUTCOMES = (
    ('five_year_all_cause_mortality', 'Approximately five-year all-cause mortality',
     'Historical NHANES classification case; not approved or externally validated for new-person inference.'),
    ('incident_diabetes', 'Future new diabetes diagnosis',
     'No verified new-onset diabetes target, training protocol, or approved disease-specific model.'),
    ('incident_stroke', 'Future stroke',
     'No verified future-stroke target, training protocol, or approved disease-specific model.'),
    ('incident_heart_failure', 'Future heart failure',
     'No verified incident-heart-failure target, training protocol, or approved disease-specific model.'),
)

def safe_public_json(root: Path, relative: str) -> dict:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ValueError(f'Missing or unsafe public documentary source: {relative}')
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Public case contract must be a JSON object')
    return data

def build_receipt(root: Path) -> dict:
    contract = safe_public_json(root, CASE)
    if contract.get('schema') != 'FRAILTYSCOPE_INTEGRATED_WORKFLOW_V29' or contract.get('case_id') != 'nhanes_mortality_v10':
        raise ValueError('Unexpected research case identity: independent review required')
    if any(contract.get(flag) is not False for flag in BLOCKED_FLAGS):
        raise ValueError('Public workflow status changed: stop and require a new governed research review')
    if contract.get('prediction_index_status') != 'provisional' or contract.get('holdout_history') != 'previously_inspected':
        raise ValueError('Prediction index / historical evaluation status changed: separate review required')
    if contract.get('candidate_selection') != 'not_performed':
        raise ValueError('Model-selection status changed; do not promote automatically')
    result = {
        'schema': 'FRAILTYSCOPE_INFERENCE_READINESS_V39',
        'case_id': 'nhanes_mortality_v10',
        'source': CASE,
        'basis': 'Public documentary workflow contract only; no private artifacts or participant data read',
        'clinical_inference': False,
        'governance_status': 'BLOCKED_FOR_NEW_ANALYSIS',
        'registered_clinical_models': 0,
        'source_mapping': {
            'mapped_in_prior_documented_review': 3,
            'required_in_prior_documented_review': 14,
            'verification': 'HISTORICAL_DOCUMENTARY_ONLY_NOT_REASSESSED',
        },
        'blockers': [
            {'id':'NO_CLINICAL_APPROVAL','description':'Clinical use and new real-data analysis are not authorized.'},
            {'id':'PROVISIONAL_INDEX','description':'A clinically meaningful prediction index and endpoint timing have not been frozen.'},
            {'id':'PARTIAL_FEATURE_MAPPING','description':'Prior documentary review reports 3 of 14 predictors source-mapped; 11 require review.'},
            {'id':'HOLDOUT_PREVIOUSLY_INSPECTED','description':'The later survey cycle was previously inspected, not untouched independent validation.'},
            {'id':'NO_REGISTERED_CLINICAL_ARTIFACT','description':'No approved fitted model and exact preprocessing bundle are registered for serving.'},
            {'id':'NO_EXTERNAL_CALIBRATION','description':'No suitable fresh independent calibration and subgroup validation for individual clinical use.'},
            {'id':'NO_SECURE_PATIENT_WORKFLOW','description':'No authorized identity, consent, access, auditing and clinician oversight are provisioned.'},
        ],
        'outcomes': [
            {'id':outcome, 'name':name,
             'status':'BLOCKED_HISTORICAL_CASE' if n == 0 else 'NOT_TRAINED_OR_VALIDATED',
             'approved_model': False, 'patient_probability_available': False,
             'explanation': reason} for n,(outcome,name,reason) in enumerate(OUTCOMES)
        ],
        'required_next_evidence': [
            'Written data-controller / ethics approvals and intended clinical-use scope',
            'Prediction timestamp, inclusion criteria, outcomes and source-variable dictionary',
            'Full one-to-one input mapping including structural skips and preprocessing',
            'Approved signed model + preprocessing provenance and immutable version registry',
            'Representative untouched external validation, calibration, uncertainty and subgroup checks',
            'Privacy impact / medical-device assessment, access controls and clinician oversight',
            'Model-specific local attribution checks, monitoring and rollback plan',
        ],
    }
    return result

def serialize(receipt: dict) -> str:
    return json.dumps(receipt, indent=2, ensure_ascii=False) + '\n'

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='Read-only check of bundled public readiness receipt')
    parser.add_argument('--print', action='store_true', dest='display', help='Print public receipt only')
    args = parser.parse_args()
    report = build_receipt(args.root)
    if args.check:
        stored = safe_public_json(args.root, PUBLIC)
        if stored != report:
            raise SystemExit('ERROR: Readiness receipt mismatches public case contract. Do not publish.')
        print('PASS: v0.39 public readiness receipt reproducible; real-person inference remains blocked')
    if args.display:
        print(serialize(report), end='')
    if not (args.check or args.display):
        parser.error('Select --check or --print; never writes research data')

if __name__ == '__main__':
    main()
