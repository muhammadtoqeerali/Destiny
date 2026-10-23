#!/usr/bin/env python3
"""Source-only patch against exact v0.42 anchors; refuses unexpected changes or second apply."""
import argparse
from pathlib import Path
PATCHES={
 '.github/workflows/ci.yml': [
    ('      - name: Verify v0.42 public source-to-form crosswalk\n', '      - name: Verify v0.43 synthetic-only model-artifact manifest\n        run: PYTHONPATH=. python -m ml.artifact_acceptance_v43 --check\n      - name: Validate v0.43 artifact acceptance regression contracts\n        run: python -m pytest -q tests/test_artifact_v43.py\n      - name: Verify v0.42 public source-to-form crosswalk\n'),
 ],
 'scripts/run_browser_qa_v34.sh': [
    ('FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_translation_v42.py\n', 'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_translation_v42.py\nFRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_artifact_v43.py\n'),
 ],
 'web/app/components/clinical-workspace.tsx': [
    ("import {ModelTranslationV42} from './model-translation-v42';\n", "import {ModelTranslationV42} from './model-translation-v42';\nimport {ArtifactAcceptanceV43} from './artifact-acceptance-v43';\n"),
    ('     <ModelTranslationV42/>\n', '     <ModelTranslationV42/>\n     <ArtifactAcceptanceV43/>\n'),
 ],
 'web/app/layout.tsx': [
    ("import './translation-v42.css';\n", "import './translation-v42.css';\nimport './artifact-v43.css';\n"),
 ],
}

def transform(name,source):
    if name not in PATCHES:raise ValueError('Unexpected source target: '+name)
    for old,new in PATCHES[name]:
        if source.count(old)!=1:raise ValueError('Missing/ambiguous v0.42 patch anchor: '+name)
        if new!=old and new in source:raise ValueError('Already patched source: '+name)
        source=source.replace(old,new,1)
    return source

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    a=p.parse_args()
    root=a.root.resolve();changed={}
    for name in PATCHES:
        f=root/name
        if not f.is_file() or f.is_symlink():raise ValueError('Unsafe/missing tracked source: '+name)
        changed[f]=transform(name,f.read_text(encoding='utf8'))
    for file,content in changed.items():
        file.write_text(content,encoding='utf8')
        print('PATCHED:',file.relative_to(root))
    print('PASS: Source-only synthetic artifact metadata linked; clinical model gate unchanged')
if __name__=='__main__':main()
