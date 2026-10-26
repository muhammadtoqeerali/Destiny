"""Desktop/mobile Doctor and Research smoke: no patient data and no inference calls."""
import os,re
from playwright.sync_api import sync_playwright, expect
BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: redesign QA restricted to isolated loopback')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.environ.get('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for label,size in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=size,reduced_motion='reduce')
                page=ctx.new_page();errors=[];requests=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:requests.append(r.url) if '/api/inference' in r.url else None)
                page.goto(BASE+'/',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/doctor/?$'))
                expect(page.get_by_role('heading',name=re.compile('Understand the person'))).to_be_visible()
                nav=page.get_by_role('navigation',name='Portal navigation')
                assert nav.get_by_role('link').count()==2
                assert not page.get_by_role('link',name='Interview focus').count()
                expect(page.get_by_role('group',name='Fictional profile overview')).to_be_visible()
                people=page.get_by_role('complementary',name='Fictional profile selection')
                assert people.get_by_role('button').count()==8
                people.get_by_role('button').filter(has_text='Example 2').click()
                expect(page.get_by_role('heading',name=re.compile('Example 2'))).to_be_visible()
                expect(page.get_by_text('Earlier dated visit records:',exact=False)).to_be_visible()
                explain=page.get_by_role('button',name=re.compile('What shaped this illustrative score'))
                explain.click()
                expect(explain).to_have_attribute('aria-expanded','true')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'),label
                page.goto(BASE+'/interview',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/doctor/?$'))
                page.goto(BASE+'/admin',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile('/admin/login'))
                page.locator('input[name="password"]').fill('admin123')
                page.get_by_role('button',name=re.compile('Open research workspace')).click()
                expect(page).to_have_url(re.compile(r'/admin/?(?:\?.*)?$'),timeout=15000)
                expect(page.get_by_role('heading',name=re.compile('Evidence, without'))).to_be_visible()
                model_summary=page.get_by_label('Key model results')
                expect(model_summary).to_be_visible()
                expect(model_summary).to_contain_text('CatBoost')
                expect(model_summary).to_contain_text('0.1507')
                expect(model_summary).to_contain_text('0.732')
                stage=page.get_by_role('navigation',name='Research stages')
                stage.get_by_role('button',name=re.compile('Model comparison')).click()
                expect(page.get_by_role('heading',name=re.compile('Compare like with like'))).to_be_visible()
                page.get_by_role('button',name='3-fold CV Brier ↓').click()
                expect(page.get_by_label('Candidate model rankings')).to_contain_text('Logistic regression')
                stage.get_by_role('button',name=re.compile('Evaluation')).click()
                expect(page.get_by_role('heading',name=re.compile('The numbers'))).to_be_visible()
                stage.get_by_role('button',name=re.compile('Model insights')).click()
                expect(page.get_by_role('heading',name=re.compile('What the model relied on'))).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'),label
                page.goto(BASE+'/admin/interview',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/admin/?$'))
                page.goto(BASE+'/archive/doctor',wait_until='domcontentloaded')
                expect(page.get_by_role('navigation',name='Doctor workspace')).to_be_visible()
                assert not errors,(label,errors)
                assert not requests,(label,requests)
                print(f'PASS [{label}] focused Doctor/Research, fictional separation, legacy access, protected admin, no inference')
                ctx.close()
        finally:browser.close()
if __name__=='__main__':run()
