"""Idempotently add actual-data deep analysis to the existing Admin Portal."""
from pathlib import Path
import argparse

def patch(text):
    if "import { EvidenceWorkbenchV11 }" in text:
        return text
    original="import refined from '../../public/data/nhanes-refinement.json';"
    if text.count(original)!=1:raise ValueError('Unexpected Admin import structure; review manually')
    text=text.replace(original,original+"\nimport { EvidenceWorkbenchV11 } from './evidence-workbench-v11';")
    old="'Dataset' | 'Preprocessing' | 'Model training' | 'Performance' | 'Interpretability' | 'Benchmark';"
    if text.count(old)!=1:raise ValueError('Admin stage type changed')
    text=text.replace(old,"'Dataset' | 'Preprocessing' | 'Model training' | 'Performance' | 'Interpretability' | 'Benchmark' | 'Deep analysis';")
    old="['Dataset','Preprocessing','Model training','Performance','Interpretability','Benchmark'];"
    if text.count(old)!=1:raise ValueError('Admin nav list changed')
    text=text.replace(old,"['Dataset','Preprocessing','Model training','Performance','Interpretability','Benchmark','Deep analysis'];")
    mark='<footer className="v7-portal-foot">'
    if text.count(mark)!=1:raise ValueError('Expected Admin footer missing')
    text=text.replace(mark,"{tab==='Deep analysis'&&<EvidenceWorkbenchV11/>}\n   "+mark)
    return text

def main():
    ap=argparse.ArgumentParser();ap.add_argument('file');a=ap.parse_args();p=Path(a.file)
    s=p.read_text();t=patch(s)
    if t!=s:p.write_text(t)
    print('PASS: Added six-stage evidence workbench to Admin Portal')
if __name__=='__main__':main()
