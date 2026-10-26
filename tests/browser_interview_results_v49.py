"""Desktop/mobile QA of public real NHANES aggregate + separate fictional profile examples."""
import os,re
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: v0.49 browser QA accepts loopback only')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.environ.get('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for label,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];requests=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:requests.append((r.method,r.url)) if '/api/inference' in r.url else None)
                page.goto(BASE+'/interview',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/doctor/?$'))
                real=page.get_by_role('region',name='Real NHANES population research')
                expect(real).to_be_visible()
                expect(real).to_contain_text(re.compile(r'current self-reported difficulty walking a quarter mile', re.I))
                expect(real).to_contain_text('1,032')
                expect(real).to_contain_text('0.732')
                assert page.locator('.d51-patient').count()==8
                expect(page.get_by_label('Selected fictional example details')).to_contain_text('Synthetic record')
                assert not requests,requests
                # The protected public-aggregate demo uses its existing, public-only passcode.
                page.goto(BASE+'/admin/interview',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile('/admin/login'))
                page.locator('input[name="password"]').fill('admin123')
                page.get_by_role('button',name=re.compile('Open research workspace')).click()
                # This is a Next.js server action, not a plain synchronous form POST.
                # Wait for its /admin redirect (which confirms the auth cookie was
                # written) before a new goto, or that goto may cancel login.
                expect(page).to_have_url(re.compile(r'/admin/?(?:\?.*)?$'),timeout=15000)
                page.goto(BASE+'/admin/interview',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/admin/interview/?$'))
                admin=page.get_by_role('region',name='Real NHANES mobility experiment results')
                expect(admin).to_be_visible()
                expect(admin).to_contain_text('0.732')
                expect(admin).to_contain_text('0.15070')
                expect(admin).to_contain_text('not an untouched independent test')
                assert page.get_by_role('table').count()>=1
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Mobile horizontal overflow'
                assert not errors,(label,errors)
                assert not requests,(label,requests)
                print(f'PASS [{label}] real NHANES aggregate / synthetic separation, original protected model evidence and auth')
                ctx.close()
        finally:browser.close()
if __name__=='__main__':run()
