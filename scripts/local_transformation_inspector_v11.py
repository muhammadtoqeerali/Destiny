"""Loopback-only rendering of actual de-identified training examples and transforms.

Not an interview presentation generator. The page is a workstation research
inspector; never deploy on public Vercel/GitHub. No original IDs shown.
"""
from __future__ import annotations
import argparse, html, json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STYLE='''body{font:14px/1.55 system-ui,sans-serif;margin:0;background:#f4f8f7;color:#264a4c}main{max-width:1180px;margin:36px auto;padding:20px}header,.card{background:white;border:1px solid #dfeae7;border-radius:14px;padding:23px;margin-bottom:17px}h1{margin:0 0 8px;font-size:25px}h2{font-size:18px;margin-top:0}p,small{color:#60807f}.good{background:#e8f5ee;color:#227255;border-radius:6px;padding:6px 10px;font-size:12px}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #eaf0ee;padding:10px}th{background:#f5faf8;color:#456e6e}details{margin:15px 0;border-radius:10px;border:1px solid #e2efec;padding:12px 18px}summary{font-weight:700;cursor:pointer}.cols{display:grid;grid-template-columns:1fr 1fr;gap:22px}.scroll{overflow:auto}td.code{font-family:monospace;color:#287f76}@media(max-width:800px){.cols{grid-template-columns:1fr}}'''

def escape(x):return html.escape(str(x),quote=True)

def page(report:dict)->str:
    if report.get('schema')!='FRAILTYSCOPE_CASE_AUDIT_V11' or report.get('report_type')!='LOCAL_DEIDENTIFIED_AUDIT':
        raise ValueError('Unexpected local audit format')
    examples=report.get('local_examples',[])
    if len(examples)>5 or any('raw' not in r or 'transformed_vector' not in r for r in examples):
        raise ValueError('Invalid controlled local example count')
    output='''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>FrailtyScope · Local data transformation</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>'''+STYLE+'''</style></head><body><main><header><span class="good">LOCAL RESEARCH WORKSPACE</span><h1>Fitted preprocessing inspection</h1><p>De-identified training observations · real local dataset · raw measurements and transformed model inputs</p></header>'''
    output+='<section class="card"><h2>Fitted transformations</h2><div class="scroll"><table><thead><tr><th>Variable</th><th>Method</th><th>Training fill value</th><th>Missing before</th><th>Missing after</th></tr></thead><tbody>'
    for m in report['preprocessing']['methods']:
        output+='<tr>'+''.join('<td>'+escape(m[k])+'</td>' for k in ('label','method','impute_value','training_missing','after_missing'))+'</tr>'
    output+='</tbody></table></div></section><section class="card"><h2>Actual training examples</h2><p>Examples are limited to five, selected from the training partition. Identifiers, outcomes and individual predictions are omitted. Values must remain on this workstation.</p>'
    for row in examples:
        output+='<details><summary>'+escape(row['record'])+' · Expand measurement transformation</summary><div class="cols"><div class="scroll"><h3>Recorded input</h3><table><tbody>'
        for key,value in row['raw'].items():
            output+='<tr><th>'+escape(key)+'</th><td>'+escape('Missing' if value is None else value)+'</td></tr>'
        output+='</tbody></table></div><div class="scroll"><h3>Numerical model vector</h3><table><tbody>'
        for i,val in enumerate(row['transformed_vector']):
            output+='<tr><th>Encoded dimension '+str(i+1)+'</th><td class="code">'+escape(val)+'</td></tr>'
        output+='</tbody></table></div></div></details>'
    output+='</section><p>Study records are not hospital patient charts. No clinically approved patient prediction is generated.</p></main></body></html>'
    return output

def serve(path:Path,port:int=8502):
    data=json.loads(path.read_text());view=page(data).encode('utf-8')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path!='/':self.send_error(404);return
            self.send_response(200)
            for name,val in [('Content-Type','text/html; charset=utf-8'),('Content-Length',str(len(view))),
                ('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),
                ('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'")]:
                self.send_header(name,val)
            self.end_headers();self.wfile.write(view)
        def log_message(self,*args):pass
    print(f'LOCAL ONLY: http://127.0.0.1:{port}/ (Ctrl+C to stop)',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',default='artifacts/cases/nhanes_mortality_v10/forensic_audit_v11_local.json');p.add_argument('--port',type=int,default=8502)
    a=p.parse_args();target=Path(a.file).resolve();root=Path('artifacts/cases').resolve()
    if not target.is_relative_to(root):raise ValueError('Local inspector files must stay under ignored artifacts/cases/')
    if a.port<1024 or a.port>65535:raise ValueError('Unsupported TCP port')
    serve(target,a.port)
