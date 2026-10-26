"""Independent v0.51 responsive visual contract, source provenance and interaction smoke test."""
import os,re
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: doctor overview QA is loopback only')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.environ.get('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for label,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];requests=[]
                page.on('pageerror',lambda err:errors.append(str(err)))
                page.on('request',lambda r:requests.append(r.url) if '/api/inference' in r.url and r.method=='POST' else None)
                page.goto(BASE+'/doctor',wait_until='domcontentloaded')
                expect(page.get_by_role('heading',name='Health at a glance.')).to_be_visible()
                expect(page.get_by_role('region',name='Fictional cohort summary')).to_contain_text('03')
                detail=page.get_by_label('Selected fictional example details')
                assert page.locator('button.d51-patient').count()==8
                page.locator('button.d51-patient').nth(4).click()
                expect(detail).to_contain_text('Example 05')
                expect(detail).to_contain_text('40.1%')
                expect(detail).to_contain_text('No earlier visits')
                page.get_by_text('Research interpretation and limitations').click()
                expect(page.get_by_text('previously inspected',exact=False).first).to_be_visible()
                chart=page.get_by_role('region',name='Real NHANES population research')
                expect(chart).to_contain_text('985')
                expect(chart).to_contain_text('1,032')
                expect(chart).to_contain_text('24.9%')
                expect(chart).to_contain_text('26.9%')
                expect(chart).to_contain_text('17.3%')
                page.get_by_role('link',name='Open detailed workspace').click()
                expect(page).to_have_url(re.compile(r'/doctor/workspace/?$'))
                expect(page.get_by_role('heading',name='Clinical overview')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'),label+' overflow'
                assert not errors,(label,errors)
                assert not requests,(label,requests)
                print(f'PASS [{label}] original Doctor research preserved; new presentation numeric, separate and responsive')
                ctx.close()
        finally:browser.close()
if __name__=='__main__':run()
