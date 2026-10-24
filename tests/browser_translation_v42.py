"""v0.42 desktop/mobile loopback-only public candidate-mapping browser test."""
import os
import re
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('v0.42 browser QA requires local loopback production build')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.getenv('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for name,size in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                context=browser.new_context(viewport=size,reduced_motion='reduce')
                page=context.new_page();errors=[];writes=[]
                page.on('pageerror',lambda x:errors.append(str(x)))
                page.on('request',lambda req:writes.append(req.url) if req.method in ('POST','PUT','PATCH','DELETE') else None)
                receipt=page.request.get(BASE+'/api/inference/translation')
                assert receipt.status==200,(name,receipt.status)
                data=receipt.json()
                assert data['schema']=='FRAILTYSCOPE_SOURCE_TO_FORM_PROMOTION_V42'
                assert data['clinical_inference'] is False
                assert data['registered_clinical_models']==0
                assert data['clinical_promotion_decision']=='DENIED'
                assert len(data['features'])==14 and len(data['outcome_promotion'])==4
                assert receipt.headers.get('cache-control','').startswith('no-store')
                refused=page.request.post(BASE+'/api/inference/translation',data={'fictional':'only'})
                assert refused.status==405
                assert page.request.post(BASE+'/api/inference',data={'fictional':'only'}).status==403
                page.goto(BASE+'/archive/doctor',wait_until='domcontentloaded')
                nav=page.get_by_role('navigation',name='Doctor workspace')
                nav.get_by_role('button',name='Model evidence',exact=True).click()
                cross=page.get_by_role('region',name='Public source-to-form crosswalk')
                expect(cross).to_be_visible()
                expect(cross.get_by_text('Clinical model promotion denied')).to_be_visible()
                assert cross.locator('.v42-field-list button').count()==14
                cross.get_by_role('button',name='11 unresolved').click()
                assert cross.locator('.v42-field-list button').count()==11
                cross.get_by_role('button',name='3 partial').click()
                assert cross.locator('.v42-field-list button').count()==3
                cross.locator('.v42-field-list button').filter(has_text='Walking difficulty').click()
                detail=cross.get_by_role('region',name='Selected source mapping details')
                expect(detail.get_by_text('PFQ054',exact=False)).to_be_visible()
                cross.get_by_role('button',name='All 14').click()
                cross.locator('.v42-field-list button').filter(has_text='Age (years)').click()
                expect(detail.get_by_text('80+',exact=False)).to_be_visible()
                if name=='mobile':
                    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),'Horizontal overflow'
                assert not errors,(name,errors)
                assert writes==[],(name,writes)
                print(f'PASS [{name}] v0.42 public 14-field candidate dictionary, filters, mismatches and no patient POST')
                context.close()
        finally:browser.close()
    print('SUCCESS: v0.42 source-to-form crosswalk browser QA; clinical model promotion denied')
if __name__=='__main__':run()
