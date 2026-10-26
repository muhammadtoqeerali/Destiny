"""v0.39 loopback-only browser QA, public documentary readiness and CI-root support."""
import os
import re
from playwright.sync_api import sync_playwright, expect
BASE=os.getenv('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: Loopback-only browser QA')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.getenv('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for name,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];posted=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda req:posted.append(req.url) if req.method=='POST' else None)
                r=page.request.get(BASE+'/api/inference/readiness')
                assert r.status==200,(name,r.status)
                doc=r.json()
                assert doc['schema']=='FRAILTYSCOPE_INFERENCE_READINESS_V39'
                assert doc['clinical_inference'] is False
                assert doc['registered_clinical_models']==0
                assert len(doc['outcomes'])==4
                assert r.headers.get('cache-control','').startswith('no-store')
                r2=page.request.post(BASE+'/api/inference/readiness',data={'fictional':'only'})
                assert r2.status==405
                assert r2.json()['error']=='READINESS_ENDPOINT_IS_READ_ONLY'
                page.goto(BASE+'/doctor/workspace',wait_until='domcontentloaded')
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Patient assessment',exact=True).click()
                section=page.get_by_label('Verified model readiness evidence')
                expect(section).to_be_visible()
                expect(section.get_by_text('Clinical inference disabled')).to_be_visible()
                section.get_by_role('button',name='Future stroke').click()
                expect(section.get_by_text('No verified future-stroke target',exact=False)).to_be_visible()
                section.get_by_text('Seven documented blockers').click()
                expect(section.get_by_text('no clinical approval',exact=False)).to_be_visible()
                if name=='mobile':
                    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),'Mobile overflow'
                assert not errors,(name,errors)
                assert posted==[],(name,posted)
                print(f'PASS [{name}] v0.39 public readiness, outcome selection, clinical gate and no patient POST')
                ctx.close()
        finally:browser.close()
    print('SUCCESS: v0.39 documentary evidence QA; individual prediction remains unavailable')
if __name__=='__main__':run()
