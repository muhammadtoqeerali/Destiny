"""Local Chromium acceptance: invented values, browser-session-only; never remote or clinical."""
import os
import re
from playwright.sync_api import sync_playwright, expect
BASE=os.environ.get('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: Only loopback browser QA is allowed')

def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for name,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[]
                page.on('pageerror',lambda exc:errors.append(str(exc)))
                page.goto(BASE+'/doctor',wait_until='domcontentloaded')
                nav=page.get_by_role('navigation',name='Doctor workspace')
                nav.get_by_role('button',name='Patient assessment',exact=True).click()
                view=page.get_by_role('region',name='Patient assessment')
                expect(view.get_by_text('Browser session only')).to_be_visible()
                expect(view.get_by_text('No valid observations entered yet')).to_be_visible()
                page.get_by_label('Age',exact=True).fill('75')
                page.get_by_label('BMI (kg/m²)').fill('26.5')
                page.get_by_label('PHQ-9 score').fill('4')
                expect(view.locator('.v36-chip').filter(has_text='Age').first).to_contain_text('75')
                expect(view.get_by_role('progressbar',name='Recorded observation fields')).to_have_attribute('aria-valuenow','3')
                page.get_by_label('Walking difficulty').select_option('Not asked (structural skip)')
                expect(view.get_by_text('Nonparticipation, structural skips',exact=False)).to_be_visible()
                view.get_by_role('button',name='Open follow-up measurements').click()
                expect(page.get_by_role('heading',name='Follow-up measurements')).to_be_visible()
                page.get_by_role('button',name='Use assessment measurements').click()
                assert page.get_by_label('BMI (kg/m²)').input_value()=='26.5'
                assert page.get_by_label('PHQ-9 score').input_value()=='4'
                page.get_by_label('Visit date').fill('2026-01-15')
                page.get_by_role('button',name='Add visit').click()
                page.get_by_label('Visit date').fill('2026-02-15')
                page.get_by_label('BMI (kg/m²)').fill('27')
                page.get_by_label('PHQ-9 score').fill('5')
                page.get_by_role('button',name='Add visit').click()
                follow=page.get_by_role('region',name='Visit history')
                expect(follow.get_by_text('+0.5 kg/m²')).to_be_visible()
                expect(follow.get_by_text('+1.0 points')).to_be_visible()
                nav.get_by_role('button',name='Model evidence',exact=True).click()
                expect(page.get_by_role('heading',name='How an assessment becomes an explanation')).to_be_visible()
                theater=page.get_by_role('region',name='Model evidence')
                expect(theater.get_by_text('Age:',exact=False).first).to_be_visible()
                theater.get_by_role('button',name='Pause motion').click()
                expect(theater.get_by_role('button',name='Resume motion')).to_be_visible()
                theater.get_by_role('button',name='Next step').click()
                expect(theater.get_by_role('heading',name='Meaning is preserved')).to_be_visible()
                expect(theater.get_by_text('not an actual explanation of a patient-specific prediction',exact=False)).to_be_visible()
                page.reload(wait_until='domcontentloaded')
                nav=page.get_by_role('navigation',name='Doctor workspace')
                nav.get_by_role('button',name='Patient assessment',exact=True).click()
                expect(page.get_by_text('No valid observations entered yet')).to_be_visible()
                nav.get_by_role('button',name='Visit history',exact=True).click()
                expect(page.get_by_text('No visits recorded.')).to_be_visible()
                if name=='mobile':assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'), 'Mobile horizontal overflow'
                assert not errors,(name,errors)
                print(f'PASS [{name}] v0.36 live assessment, visit prefill, descriptive change, animated explanation and reload privacy')
                ctx.close()
            print('SUCCESS: v0.36 Doctor journey desktop/mobile QA passed; no patient inference or persistence.')
        finally:browser.close()
if __name__=='__main__':run()
