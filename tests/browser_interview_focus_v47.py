"""Desktop/mobile QA of clean entry and fictional case explorer; retains legacy route contract."""
import os,re
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: Doctor browser QA is loopback only')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.environ.get('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for name,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];requests=[]
                page.on('pageerror',lambda x:errors.append(str(x)))
                page.on('request',lambda req:requests.append((req.method,req.url)) if '/api/inference' in req.url else None)
                page.goto(BASE+'/',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/doctor/?$'))
                expect(page.get_by_role('heading',name='Health at a glance.')).to_be_visible()
                nav=page.get_by_role('navigation',name='Portal navigation')
                assert nav.get_by_role('link',name='Interview focus').count()==0
                assert nav.get_by_role('link',name='Doctor').count()==1
                explorer=page.get_by_role('region',name='Fictional profile explorer')
                assert explorer.locator('button.d51-patient').count()==8
                explorer.locator('button.d51-patient').nth(1).click()
                expect(page.get_by_role('heading',name='Example 02')).to_be_visible()
                expect(page.get_by_label('Selected fictional example details')).to_contain_text('26.0%')
                page.goto(BASE+'/interview',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/doctor/?$'))
                page.goto(BASE+'/admin/interview',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile('/admin/login'))
                assert not requests,(name,requests)
                assert not errors,(name,errors)
                print(f'PASS [{name}] clean Doctor landing, fictional profiles, hidden interview navigation and protected Admin')
                ctx.close()
        finally:browser.close()
if __name__=='__main__':run()
