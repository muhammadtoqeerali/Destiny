"""v0.46: deterministic, redacted research handoff action plan (never an approval engine).

Uses only the immutable PUBLIC v0.44 blank request sheet or an explicitly selected,
validated PRIVATE v0.45 response outside the checkout. Never follows evidence
references, opens supporting files, inspects patient records, or grants permissions.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from collections import Counter
from ml.study_evidence_triage_v45 import (
    public_template, triage, safe_read, read_rows, TriageRefused,
)

SCHEMA='FRAILTYSCOPE_RESEARCH_ACTIVATION_PLAN_V46'
PUBLIC='research/cases/study_activation_workplan_v46.json'
# Dependencies describe procedural ordering, never substitute for formal review.
WORKSTREAMS={
 'ethics_and_controller':(0,'Authorization',()),
 'prediction_index':(1,'Definition',('ethics_and_controller',)),
 'incident_outcomes':(1,'Definition',('ethics_and_controller',)),
 'five_year_all_cause_mortality':(1,'Definition',('prediction_index',)),
 'incident_diabetes':(1,'Definition',('incident_outcomes',)),
 'incident_stroke':(1,'Definition',('incident_outcomes',)),
 'incident_heart_failure':(1,'Definition',('incident_outcomes',)),
 'source_mapping':(2,'Harmonization',('prediction_index',)),
 'model_provenance':(3,'Model evidence',('source_mapping','prediction_index')),
 'external_validation':(4,'Independent validation',('model_provenance',)),
 'clinical_security':(5,'Deployment governance',('ethics_and_controller','external_validation')),
}
NEXT_ACTION={
 'NOT_RECEIVED':'REQUEST_MISSING_EVIDENCE',
 'IN_REVIEW':'COMPLETE_REVIEW',
 'EVIDENCE_RECEIVED':'AUTHENTICATE_OFFLINE_EVIDENCE',
 'CHANGES_REQUESTED':'RESOLVE_REVIEW_CHANGES',
 'REJECTED':'RESOLVE_REJECTION_BEFORE_RESUBMISSION',
 'APPROVED':'VERIFY_CLAIMED_SIGNOFF_INDEPENDENTLY',
}


def require(ok:bool, reason:str)->None:
    if not ok:raise TriageRefused('ACTIVATION_REFUSED: '+reason)


def _phase(row:dict)->tuple[int,str,tuple[str,...]]:
    ident=row['request_id']
    if ident in WORKSTREAMS:return WORKSTREAMS[ident]
    if row['category']=='predictor':return (2,'Harmonization',('prediction_index','source_mapping'))
    raise TriageRefused('ACTIVATION_REFUSED: Unknown request category or ID')


def make_plan(root:Path,response_path:Path|None=None)->dict:
    """Status-only outputs: never include opaque tickets or private input paths."""
    root=root.resolve()
    baseline=public_template(root)
    if response_path is None:
        rows=baseline
        source='PUBLIC_BLANK_TEMPLATE_ONLY'
    else:
        # Validates outside-repo location, immutability, exact schema, all statuses.
        triage(root,response_path)
        rows=read_rows(safe_read(response_path.expanduser()))
        source='REDACTED_PRIVATE_RESPONSE_STATUS_ONLY'
    require(len(rows)==25,'Unexpected request count')
    ids=[r['request_id'] for r in baseline]
    require(len(set(ids))==25,'Duplicate public request ID')
    require(set(WORKSTREAMS).issubset(set(ids)),'Missing governance/outcome requests')
    groups=[]
    for index,(base,row) in enumerate(zip(baseline,rows)):
        ident=base['request_id']
        status=row['approval_status']
        require(status in NEXT_ACTION,'Unknown status')
        phase,lane,deps=_phase(base)
        require(all(x in ids and x!=ident for x in deps),'Invalid dependency')
        groups.append({
          'request_id':ident,
          'category':base['category'],
          'reviewer_role':base['reviewer_role'],
          'stage':phase,
          'workstream':lane,
          'depends_on_request_ids':list(deps),
          'reported_status':status,
          'next_action':NEXT_ACTION[status],
          'unverified_signoff_claim':status=='APPROVED',
          'separate_independent_review_required':True,
        })
    groups.sort(key=lambda x:(x['stage'],ids.index(x['request_id'])))
    counts=Counter(r['reported_status'] for r in groups)
    return {
      'schema':SCHEMA,
      'basis':source,
      'requests_total':25,
      'categories':{'predictor':14,'outcome':4,'governance':7},
      'status_counts':{k:counts[k] for k in NEXT_ACTION},
      'workstreams':[{'stage':i,'name':name,'requests':sum(a['stage']==i for a in groups)}
                     for i,name in [(0,'Authorization'),(1,'Definition'),(2,'Harmonization'),
                                    (3,'Model evidence'),(4,'Independent validation'),
                                    (5,'Deployment governance')]],
      'actions':groups,
      'approval_documents_authenticated':0,
      'signatures_verified':False,
      'supporting_evidence_opened':False,
      'patient_records_accessed':False,
      'clinical_inference':False,
      'real_data_execution_permitted':False,
      'clinical_promotion_decision':'DENIED',
      'notice':'Review statuses are claims only; required institutional, scientific and independent evidence must be separately authenticated. Never commit completed response sheets.',
    }


def serialize(obj:dict)->str:
    return json.dumps(obj,ensure_ascii=False,indent=2)+'\n'


def markdown(plan:dict)->str:
    lines=['# FrailtyScope — Redacted study activation action plan',
           '', '**Clinical promotion: DENIED. No approvals authenticated.**', '',
           f"Basis: `{plan['basis']}`. All 25 items require independent assessment.",
           '', 'No private evidence tickets, reviewer names, patient records or file paths are shown.', '']
    for ws in plan['workstreams']:
        lines.extend([f"## Stage {ws['stage']}: {ws['name']}",''])
        for x in plan['actions']:
            if x['stage']==ws['stage']:
                lines.append(f"- **{x['request_id']}** — {x['reviewer_role']}; {x['reported_status']}; next: {x['next_action']}; depends on: {', '.join(x['depends_on_request_ids']) or 'none'}")
        lines.append('')
    lines.extend(['---','**No release or scoring authority is conveyed by this plan.**',''])
    return '\n'.join(lines)


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    choice=p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--check-public-plan',action='store_true')
    choice.add_argument('--template-plan',action='store_true')
    choice.add_argument('--review-response',type=Path)
    p.add_argument('--format',choices=('json','markdown'),default='json')
    a=p.parse_args()
    try:
        result=make_plan(a.root,None if a.review_response is None else a.review_response)
        if a.check_public_plan:
            path=a.root/PUBLIC
            require(path.is_file() and not path.is_symlink(),'Public plan missing/unsafe')
            require(path.read_text(encoding='utf8')==serialize(result),
                    'Public action plan changed; review required')
            print('PASS: 25-item public action plan reproducible; all approvals unverified and clinical promotion DENIED')
        else:
            print(markdown(result) if a.format=='markdown' else serialize(result),end='')
    except (TriageRefused,OSError,ValueError,UnicodeError) as exc:
        # Only fixed error causes can reach this handler; no private field values printed.
        msg=str(exc)
        if not (msg.startswith('TRIAGE_REFUSED: ') or msg.startswith('ACTIVATION_REFUSED: ')):
            msg='ACTIVATION_REFUSED: Cannot inspect provided response'
        raise SystemExit(msg) from None

if __name__=='__main__':main()
