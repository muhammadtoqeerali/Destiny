from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('path');a=p.parse_args();f=Path(a.path);s=f.read_text();anchor="import './nhanes.css';"
if "import './nhanes-v11.css';" not in s:
    if s.count(anchor)!=1:raise ValueError('Layout CSS structure changed')
    f.write_text(s.replace(anchor,anchor+"\nimport './nhanes-v11.css';"))
print('PASS: Workbench responsive styles registered')
