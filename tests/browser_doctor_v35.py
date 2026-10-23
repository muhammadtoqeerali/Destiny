"""Live Chromium Doctor Portal v0.35 checks; local-only, invented form values."""
import os
import re
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: Doctor browser QA is loopback-only')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            for label,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                context=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=context.new_page()
                errors=[]
                page.on('pageerror',lambda err:errors.append(str(err)))
                page.goto(BASE+'/doctor',wait_until='domcontentloaded')
                hero=page.locator('header.v35-hero[aria-label="Doctor Portal introduction"]')
                expect(hero).to_be_visible()
                expect(page.get_by_role('heading',name='Clinical overview')).to_be_visible()
                expect(page.get_by_label('Published NHANES cohort overview')).to_contain_text('2,422')
                expect(page.get_by_role('heading',name='Two survey cycles, one historical benchmark')).to_be_visible()
                scope=page.locator('.v35-scope')
                expect(scope).to_contain_text('not a clinical prediction service')
                scope.locator('summary').click()
                expect(scope).to_contain_text('BLOCKED_FOR_NEW_ANALYSIS')
                page.get_by_role('button',name='Review health profiles').click()
                expect(page.get_by_role('heading',name='Health profiles')).to_be_visible()
                group=page.get_by_label('Participant group')
                assert group.locator('option').count()>=1
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Patient assessment').click()
                expect(page.get_by_role('heading',name='Patient assessment')).to_be_visible()
                progress=page.get_by_role('progressbar',name='Valid assessment fields')
                expect(progress).to_have_attribute('aria-valuenow','0')
                age=page.get_by_label('Age',exact=True)
                age.fill('64')
                expect(age).to_have_attribute('aria-invalid','true')
                age.fill('75')
                expect(age).to_have_attribute('aria-invalid','false')
                expect(progress).to_have_attribute('aria-valuenow','1')
                page.get_by_label('Walking difficulty').select_option('Not asked (structural skip)')
                assert page.locator('.v7-summary-line').filter(has_text='Mobility items reporting difficulty').locator('strong').inner_text().strip()=='0'
                page.get_by_role('button',name='Clear assessment').click()
                expect(progress).to_have_attribute('aria-valuenow','0')
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Visit history').click()
                page.get_by_label('Visit date').fill('2026-01-15')
                page.get_by_label('BMI (kg/m²)').fill('25.2')
                page.get_by_role('button',name='Add visit').click()
                expect(page.get_by_text('dated assessments entered')).to_be_visible()
                page.get_by_role('button',name='Remove visit 2026-01-15').click()
                expect(page.get_by_text('No visits recorded.')).to_be_visible()
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Model evidence').click()
                expect(page.get_by_role('heading',name='Understand the model evidence')).to_be_visible()
                if label=='mobile':
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Horizontal overflow in Doctor Portal'
                assert not errors,(label,errors)
                print(f'PASS [{label}] Doctor v0.35: hero, research limits, health profiles, assessment, visits, model evidence')
                context.close()
            print('SUCCESS: Doctor v0.35 desktop and mobile browser QA passed.')
        finally:
            browser.close()

if __name__=='__main__': run()
