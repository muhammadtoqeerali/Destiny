"""Local, reproducible environment inventory; no secrets or raw records in report."""
from __future__ import annotations
import argparse
import json
import platform
from importlib import metadata
from pathlib import Path

PACKAGES=['numpy','pandas','scikit-learn','scipy','optuna','xgboost','catboost','shap','pytest','joblib']

def build():
    versions={}
    for name in PACKAGES:
        try:versions[name]=metadata.version(name)
        except metadata.PackageNotFoundError:versions[name]=None
    return {'report_type':'LOCAL_ENVIRONMENT_MANIFEST','python':platform.python_version(),
            'platform':platform.system()+' '+platform.machine(),
            'packages':versions,
            'note':'Package and Python versions only. GPU availability and acceleration not implied.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',default='.');a=p.parse_args()
    root=Path(a.project).resolve();dest=root/'artifacts/interview_v10/environment.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    result=build();dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    missing=[x for x,y in result['packages'].items() if y is None]
    if missing:raise SystemExit('Missing case-workflow packages: '+', '.join(missing))
    print('PASS: Case-workflow packages importable; environment report saved locally')
if __name__=='__main__':main()
