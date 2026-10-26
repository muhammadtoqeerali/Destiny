"""Loopback-only browser acceptance of public v0.44 study-team handoff."""
import os
import re
from playwright.sync_api import sync_playwright,expect
BASE=os.getenv('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('v0.44 browser QA requires isolated loopback production build')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.getenv('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for size,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];writes=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda req:writes.append(req.url) if req.method in ('POST','PUT','PATCH','DELETE') else None)
                url=BASE+'/api/inference/handoff'
                response=page.request.get(url)
                assert response.status==200,(size,response.status)
                receipt=response.json()
                assert receipt['schema']=='FRAILTYSCOPE_STUDY_HANDOFF_V44'
                assert receipt['clinical_inference'] is False
                assert receipt['registered_clinical_models']==0
                assert receipt['clinical_promotion_decision']=='DENIED'
                assert len(receipt['feature_evidence_requests'])==14
                assert len(receipt['outcome_evidence_requests'])==4
                assert len(receipt['governance_requests'])==7
                assert response.headers.get('cache-control','').startswith('no-store')
                assert page.request.get(url+'?patient_id=fictional').status==400
                assert page.request.post(url,data={'fictional':'only'}).status==405
                assert page.request.post(BASE+'/api/inference',data={'fictional':True}).status==403
                page.goto(BASE+'/archive/doctor',wait_until='domcontentloaded')
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Model evidence',exact=True).click()
                section=page.get_by_role('region',name='Study team evidence handoff')
                expect(section).to_be_visible()
                expect(section.get_by_text('Clinical promotion denied')).to_be_visible()
                assert section.get_by_label('Predictor review requests').locator('article').count()==14
                section.get_by_label('Source status').select_option('UNRESOLVED')
                assert section.get_by_label('Predictor review requests').locator('article').count()==11
                section.get_by_label('Source status').select_option('PARTIAL_2011_2012_ONLY')
                assert section.get_by_label('Predictor review requests').locator('article').count()==3
                section.get_by_role('button',name='Four outcome definitions').click()
                assert section.get_by_label('Outcome protocol requests').locator('article').count()==4
                section.get_by_role('button',name='Governance & validation').click()
                assert section.get_by_label('Governance evidence requests').locator('article').count()==7
                if size=='mobile':
                    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),'Mobile overflow'
                assert not errors,(size,errors)
                assert writes==[],(size,writes)
                print(f'PASS [{size}] v0.44 14 mapping reviews, 4 outcome requests, 7 governance gates, no patient POST')
                ctx.close()
        finally:browser.close()
    print('SUCCESS: v0.44 public evidence handoff desktop/mobile QA; clinical prediction remains blocked')
if __name__=='__main__':run()
