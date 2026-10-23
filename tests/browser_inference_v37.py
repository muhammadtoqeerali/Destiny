"""Local-only acceptance of synthetic math and fail-closed individual inference."""
import os
import re
from playwright.sync_api import sync_playwright, expect

BASE=os.getenv('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: Browser QA only against loopback production build')


def run():
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        try:
            for label,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                context=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=context.new_page()
                errors=[]
                page.on('pageerror',lambda exc:errors.append(str(exc)))
                # Capture requests and ensure nothing submits patient data.
                requests=[]
                page.on('request',lambda req:requests.append((req.method,req.url)))
                page.goto(BASE+'/doctor',wait_until='domcontentloaded')
                nav=page.get_by_role('navigation',name='Doctor workspace')
                nav.get_by_role('button',name='Patient assessment',exact=True).click()
                gate=page.get_by_role('region',name='Live model availability')
                expect(gate).to_contain_text('Patient prediction not enabled')
                expect(gate).to_contain_text('Clinical inference blocked')
                expect(gate).to_contain_text('0')
                page.get_by_label('Age',exact=True).fill('77')
                page.get_by_label('BMI (kg/m²)').fill('29')
                assert gate.locator('.v37-readiness-metrics>div').nth(0).locator('strong').inner_text()=='2'
                assert gate.locator('.v37-readiness-metrics>div').nth(2).locator('strong').inner_text()=='0'
                gate.get_by_text('Why is the model unavailable?').click()
                expect(gate).to_contain_text('BLOCKED_FOR_NEW_ANALYSIS')
                gate.get_by_role('button',name='Explore a fictional scoring example').click()
                expect(page.get_by_role('heading',name='How an assessment becomes an explanation')).to_be_visible()
                lab=page.get_by_role('region',name='Fictional model calculation laboratory')
                expect(lab.get_by_text('SYNTHETIC / NOT CLINICAL')).to_be_visible()
                meter=lab.get_by_role('meter',name='Simulated fictional class-1 probability')
                initial=float(meter.get_attribute('aria-valuenow'))
                age=lab.get_by_role('slider',name='Fictional age')
                age.focus()
                age.press('End')
                after_age=float(meter.get_attribute('aria-valuenow'))
                assert after_age>initial,(label,initial,after_age)
                lab.get_by_role('combobox',name='Fictional movement category').select_option('2')
                after_mobility=float(meter.get_attribute('aria-valuenow'))
                assert after_mobility>after_age,(label,after_age,after_mobility)
                expect(lab.get_by_text('Exact contributions from this illustrative formula',exact=False)).to_be_visible()
                expect(lab.get_by_text('not death, disease, frailty',exact=False)).to_be_visible()
                lab.get_by_role('button',name='Reset fictional example').click()
                assert abs(float(meter.get_attribute('aria-valuenow'))-initial)<.01
                assert not any(path.endswith('/api/predict') or '/api/inference' in path for _,path in requests)
                assert not any(method=='POST' for method,_ in requests),(label,requests)
                if label=='mobile':
                    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'), 'Horizontal overflow'
                assert not errors,(label,errors)
                print(f'PASS [{label}] blocked real inference; synthetic arithmetic, contribution updates, reset and no data submission')
                context.close()
            print('SUCCESS: v0.37 desktop/mobile synthetic-only inference demonstration QA passed.')
        finally: browser.close()

if __name__=='__main__':run()
