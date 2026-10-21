"""Loopback-only NHANES survey record browser. Never binds to a public interface."""
from __future__ import annotations
import argparse
import html
import secrets
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
import pandas as pd
from ml.realdata_nhanes import BASE_FEATURES

LABELS={'age':'Age (80+ grouped)','sex':'Sex','bmi':'Body mass index','walking_difficulty':'Walking difficulty',
 'stairs_difficulty':'Stair difficulty','stooping_difficulty':'Stooping difficulty',
 'heart_failure':'Heart failure','coronary_disease':'Coronary disease','stroke':'Stroke',
 'cancer':'Cancer','diabetes':'Diabetes','hypertension':'Hypertension','ever_smoked':'Ever smoked','phq9_score':'PHQ-9'}

STYLE='''body{font:15px system-ui;background:#f5f8f7;color:#274a4c;margin:0}main{max-width:1050px;margin:40px auto;padding:20px}.bar,.panel{background:white;border:1px solid #e1e8e5;border-radius:15px;padding:25px;margin-bottom:18px}a{color:#157c75;text-decoration:none}.flag{color:#895821;background:#fff5e8;border-radius:8px;padding:12px;margin-bottom:20px}.card{display:inline-block;background:#f6faf8;padding:12px 20px;margin:7px;border-radius:10px;border:1px solid #d9e9e3}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:13px;border-bottom:1px solid #e5ece9}select,button{padding:9px;border-radius:8px;border:1px solid #bdd4ce}button{background:#15766d;color:white}h1{margin:0}small{color:#678}'''

def textval(value):
    if pd.isna(value):return 'Not recorded'
    if isinstance(value,(int,float)) and float(value).is_integer():return str(int(value))
    return str(value)


def serve(csv:Path,port:int=8501):
    frame=pd.read_csv(csv)
    if len(frame)<1000 or 'data_origin' not in frame or set(frame.data_origin)!={'NHANES_PUBLIC_2019_LMF'}:raise ValueError('Expected local NHANES cohort')
    if not set(BASE_FEATURES).issubset(frame.columns):raise ValueError('Missing baseline features')
    # In-memory random opaque tokens; no SEQN rendered or accepted as a query.
    tokens=[secrets.token_urlsafe(8) for _ in range(len(frame))]
    lookup={token:i for i,token in enumerate(tokens)}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=urlsplit(self.path);p=parse_qs(path.query)
            group=p.get('cycle',['All'])[0]
            content='<div class="bar"><h1>NHANES health record explorer</h1><p>Local research review · actual CDC survey records</p></div><div class="flag">Research records are not clinical charts. No repeated patient visits, diagnosis, or individually validated future risk estimates.</div>'
            if path.path=='/record':
                token=p.get('key',[''])[0]
                if token not in lookup:self.send_error(404);return
                row=frame.iloc[lookup[token]]
                content+='<div class="panel"><a href="/">← Cohort directory</a><h2>Respondent measurements</h2><p>Survey cycle: '+html.escape(str(row.cycle))+'</p><table><tbody>'
                for key in BASE_FEATURES:
                    content+='<tr><th>'+html.escape(LABELS.get(key,key))+'</th><td>'+html.escape(textval(row[key]))+'</td></tr>'
                content+='</tbody></table><p><small>Original study sequence identifiers are never displayed. Values may be missing or self-reported.</small></p></div>'
            elif path.path=='/':
                if group not in {'All','2011-2012','2013-2014'}:group='All'
                ids=[i for i in range(len(frame)) if group=='All' or frame.iloc[i].cycle==group]
                try:page=min(99,max(0,int(p.get('page',['0'])[0])))
                except ValueError:page=0
                start=page*20;subset=ids[start:start+20]
                content+='<div class="panel"><h2>Participant records</h2><p>'+str(len(ids))+' local study observations · showing '+str(len(subset))+' records</p>'
                content+='<p>Cycle: '+''.join('<a class="card" href="/?cycle='+c+'">'+c+'</a>' for c in ['All','2011-2012','2013-2014'])+'</p><table><thead><tr><th>Local record</th><th>Age</th><th>Sex</th><th>BMI</th><th>Cycle</th></tr></thead><tbody>'
                for i in subset:
                    row=frame.iloc[i]
                    content+='<tr><td><a href="/record?key='+tokens[i]+'">View measurements</a></td><td>'+html.escape(textval(row.age))+'</td><td>'+html.escape(textval(row.sex))+'</td><td>'+html.escape(textval(row.bmi))+'</td><td>'+html.escape(str(row.cycle))+'</td></tr>'
                content+='</tbody></table><p><a href="/?cycle='+group+'&page='+str(max(0,page-1))+'">Previous</a> · <a href="/?cycle='+group+'&page='+str(page+1)+'">Next</a></p></div>'
            else:self.send_error(404);return
            page_html='<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Local NHANES explorer</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+STYLE+'</style></head><body><main>'+content+'</main></body></html>'
            response=page_html.encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(response)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'")
            self.end_headers();self.wfile.write(response)
        def log_message(self,*args):pass  # No participant-specific HTTP logs
    print(f'LOCAL ONLY: http://127.0.0.1:{port}/ (Ctrl+C to stop)')
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',default='data/processed/nhanes_5yr_local.csv');p.add_argument('--port',type=int,default=8501);a=p.parse_args()
    serve(Path(a.input),a.port)
