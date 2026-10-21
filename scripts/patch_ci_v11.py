"""Patch exact CI allowlist and add v11 regression tests, fail closed on drift."""
from pathlib import Path
import argparse

def patch(s):
    if 'test_case_forensics_v11.py' in s and 'nhanes-case-audit-v11.json' in s:return s
    test='tests/test_case_engine_v10.py'
    if s.count(test)!=1:raise ValueError('Unexpected CI tests list')
    s=s.replace(test,test+' tests/test_case_forensics_v11.py')
    old="expected={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json'}"
    new="expected={'nhanes-aggregate.json','nhanes-refinement.json','nhanes-cohort-profile.json','nhanes-case-audit-v11.json'}"
    if s.count(old)!=1:raise ValueError('CI public asset allowlist changed')
    s=s.replace(old,new)
    old="              else:\n                  assert obj['counts']['total']>=2000"
    new="""              elif fname=='nhanes-case-audit-v11.json':
                  assert obj['schema']=='FRAILTYSCOPE_PUBLIC_CASE_AUDIT_V11'
                  assert obj['counts']['all']==2422
                  assert obj['counts']['evaluation']==1257
                  assert 'local_examples' not in obj
                  assert all(x['n']>=50 for x in obj['evaluation']['calibration'])
                  assert all(x['n']>=100 for x in obj['evaluation']['subgroups'])
              else:
                  assert obj['counts']['total']>=2000"""
    if s.count(old)!=1:raise ValueError('CI payload schema conditional changed')
    s=s.replace(old,new)
    return s
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('file');a=p.parse_args();f=Path(a.file);s=f.read_text();t=patch(s)
    if t!=s:f.write_text(t)
    print('PASS: CI tests and four allowed aggregate payloads updated')
