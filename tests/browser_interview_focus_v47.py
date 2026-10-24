"""Playwright smoke test for clean interview entrypoints; no patient submission."""
import os,re
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: Interview QA must run on isolated loopback only')

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
                expect(page).to_have_url(re.compile('/interview$'))
                expect(page.get_by_role('heading',name='Older adult health, made understandable.')).to_be_visible()
                assert page.get_by_role('navigation',name='Portal navigation').get_by_role('link',name='Interview focus').count()==1
                people=page.get_by_role('region',name='Fictional profile selection')
                assert people.locator('button.if-person').count()==8
                people.locator('button.if-person').nth(1).click()
                expect(page.get_by_role('heading',name='Health snapshot · Example 2')).to_be_visible()
                assert 'Generated' in page.locator('.if-card').all_inner_texts()[1]
                page.get_by_role('button',name=re.compile('Show the model pipeline')).click()
                expect(page.get_by_text('Train-only imputation and encoding')).to_be_visible()
                page.goto(BASE+'/admin/interview',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile('/admin/login'))
                assert not requests,(name,requests)
                assert not errors,(name,errors)
                print(f'PASS [{name}] v0.47 clean interview presentation, artificial profiles, protected admin and no inference submission')
                ctx.close()
        finally:browser.close()
if __name__=='__main__':run()
