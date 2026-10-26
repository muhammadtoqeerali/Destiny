"""Loopback-only Doctor public scientific and invented-data validation acceptance."""
import os
import re
from playwright.sync_api import sync_playwright,expect
BASE=os.getenv('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: v0.41 browser QA must use loopback HTTP only')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.getenv('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for name,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];posts=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda req:posts.append(req.url) if req.method in ('POST','PUT') else None)
                endpoint=BASE+'/api/inference/validation'
                r=page.request.get(endpoint)
                assert r.status==200,(name,r.status)
                payload=r.json()
                assert payload['schema']=='FRAILTYSCOPE_VALIDATION_REHEARSAL_V41'
                assert payload['clinical_inference'] is False
                assert payload['scientific_readiness']['registered_clinical_models']==0
                assert len(payload['scientific_readiness']['features'])==14
                assert len(payload['scientific_readiness']['outcome_plans'])==4
                assert len(payload['fictional_validation']['metrics'])==3
                assert r.headers.get('cache-control','').startswith('no-store')
                assert page.request.get(endpoint+'?age=75').status==400
                assert page.request.post(endpoint,data={'invented_only':True}).status==405
                assert page.request.post(BASE+'/api/inference',data={'fictional':'only'}).status==403
                page.goto(BASE+'/archive/doctor',wait_until='domcontentloaded')
                nav=page.get_by_role('navigation',name='Doctor workspace')
                nav.get_by_role('button',name='Patient assessment',exact=True).click()
                page.get_by_label('Age',exact=True).fill('74')
                nav.get_by_role('button',name='Model evidence',exact=True).click()
                section=page.get_by_role('region',name='Validation rehearsal and clinical approval gate')
                expect(section).to_be_visible()
                expect(section.get_by_text('Clinical serving blocked')).to_be_visible()
                expect(section.get_by_text('0 / 4')).to_be_visible()
                expect(section.get_by_text('240',exact=True)).to_be_visible()
                section.get_by_role('button',name='Future stroke').click()
                expect(section.get_by_text('Future stroke').first).to_be_visible()
                expect(section.get_by_text('new onset target not defined',exact=False)).to_be_visible()
                section.get_by_text('Review all 14 historical predictor mappings').click()
                assert section.locator('.v41-feature-list>div').count()==14
                assert section.locator('.v41-synthetic article').count()==3
                assert not errors,(name,errors)
                assert posts==[],(name,posts)
                if name=='mobile':
                    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),'Mobile overflow'
                print(f'PASS [{name}] v0.41 14-feature review, four clinical gates, invented holdback validation and no patient POST')
                ctx.close()
        finally:browser.close()
    print('SUCCESS: v0.41 public science + synthetic-only validation QA; clinical inference blocked')
if __name__=='__main__':run()
