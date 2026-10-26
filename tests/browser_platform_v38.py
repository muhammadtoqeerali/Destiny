"""Loopback-only end-to-end QA of real fitted fictional multi-outcome scoring and locked API."""
import os
import re
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('Browser QA requires 127.0.0.1 on an isolated production build')

def run():
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True,executable_path=os.environ.get('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for size,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];posts=[]
                page.on('pageerror',lambda err:errors.append(str(err)))
                page.on('request',lambda req:posts.append(req.url) if req.method in ('POST','PUT') else None)
                # A deliberately fictional request must be refused, without parsing the body.
                reply=page.request.post(BASE+'/api/inference',data={'invented_example':True})
                assert reply.status==403,(size,reply.status)
                contract=reply.json()
                assert contract['status']=='BLOCKED_FOR_NEW_ANALYSIS'
                assert contract['clinical_inference'] is False
                assert contract['registered_clinical_models']==0
                assert reply.headers.get('cache-control','').startswith('no-store')
                page.goto(BASE+'/archive/doctor',wait_until='domcontentloaded')
                nav=page.get_by_role('navigation',name='Doctor workspace')
                nav.get_by_role('button',name='Patient assessment',exact=True).click()
                readiness=page.get_by_label('Clinical outcome availability')
                expect(readiness).to_be_visible()
                expect(readiness.get_by_text('Five-year all-cause mortality')).to_be_visible()
                expect(readiness.get_by_text('Future stroke')).to_be_visible()
                nav.get_by_role('button',name='Model evidence',exact=True).click()
                lab=page.get_by_role('region',name='Trained fictional multi-outcome modeling studio')
                expect(lab).to_be_visible()
                expect(lab.get_by_text('NOT PATIENT PREDICTIONS')).to_be_visible()
                cards=lab.locator('.v38-result')
                assert cards.count()==3
                before=cards.nth(0).locator('strong').inner_text()
                lab.get_by_label('Synthetic movement category').select_option('2')
                after=cards.nth(0).locator('strong').inner_text()
                assert before!=after,(size,before,after)
                cards.nth(1).click()
                expect(lab.get_by_text('Exact coefficients: Invented outcome B')).to_be_visible()
                assert lab.locator('.v38-effect').count()==6
                lab.get_by_role('button',name='Reset fictional example').click()
                assert cards.nth(0).locator('strong').inner_text()==before
                assert posts==[],(size,posts)
                if size=='mobile':
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+2'),'Mobile horizontal overflow'
                assert not errors,(size,errors)
                print('PASS',size,'v0.38: three fitted fictional outputs, exact explanations, reset, locked API and no profile POST')
                ctx.close()
        finally:browser.close()
    print('SUCCESS: v0.38 multi-outcome synthetic-only desktop/mobile QA')
if __name__=='__main__':run()
