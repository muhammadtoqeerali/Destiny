"""Chromium browser QA of local built demo. Only fictional form entries and public aggregates.

Run through scripts/run_browser_qa_v34.sh. It refuses a remote origin by design.
"""
import json
import os
import re
import sys
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('FRAILTYSCOPE_QA_BASE', '')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}', BASE):
    raise SystemExit('ERROR: Browser QA accepts local HTTP 127.0.0.1 only')


def run():
    with sync_playwright() as pw:
        opts={'headless':True}
        if os.environ.get('FRAILTYSCOPE_QA_CHROMIUM'):
            opts['executable_path']=os.environ['FRAILTYSCOPE_QA_CHROMIUM']
        browser=pw.chromium.launch(**opts)
        try:
            for name,viewport in [
                ('desktop',{'width':1440,'height':900}),
                ('mobile',{'width':390,'height':844}),
            ]:
                errors=[]
                context=browser.new_context(viewport=viewport, reduced_motion='reduce')
                page=context.new_page()
                page.on('pageerror',lambda ex:errors.append(str(ex)))
                status=page.request.get(f'{BASE}/api/status')
                assert status.status==200,(name,'/api/status',status.status)
                result=status.json()
                assert result['schema']=='FRAILTYSCOPE_PUBLIC_RELEASE_STATUS_V34'
                assert result['release']=='v0.34'
                assert result['evidence']['new_real_data_execution']=='BLOCKED_FOR_NEW_ANALYSIS'
                assert result['evidence']['clinical_prediction'] is False
                assert status.headers.get('cache-control','').startswith('no-store')
                assert not any(word in json.dumps(result).lower() for word in ('admin123','password','session_secret'))
                git=result['deployment']['git_commit']
                assert git is None or re.fullmatch('[a-f0-9]{40}',git)
                print(f'PASS [{name}] release receipt; git identity {git[:10] if git else "unavailable"}')

                page.goto(BASE+'/archive/doctor',wait_until='domcontentloaded')
                expect(page.get_by_role('heading',name='Clinical overview')).to_be_visible()
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Health profiles',exact=True).click()
                expect(page.get_by_role('heading',name='Health profiles')).to_be_visible()
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Patient assessment',exact=True).click()
                expect(page.get_by_role('heading',name='Patient assessment')).to_be_visible()
                age=page.get_by_label('Age',exact=True)
                age.fill('64')
                expect(page.locator('p.v7-fine[role="alert"]')).to_contain_text('outside the permitted range')
                age.fill('75')
                expect(page.locator('p.v7-fine[role="alert"]')).to_have_count(0)
                page.get_by_label('Walking difficulty').select_option('Does not do activity')
                expect(page.get_by_text('Mobility items reporting difficulty')).to_be_visible()
                # Structural/nonperformance responses must not count as difficulty.
                assert page.locator('.v7-summary-line').filter(has_text='Mobility items reporting difficulty').locator('strong').inner_text().strip()=='0'
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Visit history',exact=True).click()
                expect(page.get_by_role('heading',name='Follow-up measurements')).to_be_visible()
                page.get_by_label('Visit date').fill('2026-01-15')
                # A BMI measurement is required for a visit entry.
                page.get_by_label('BMI (kg/m²)').fill('26.5')
                page.get_by_role('button',name='Add visit').click()
                expect(page.get_by_text('dated assessments entered')).to_be_visible()
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Model evidence',exact=True).click()
                expect(page.get_by_role('heading',name='How an assessment becomes an explanation')).to_be_visible()
                print(f'PASS [{name}] Doctor Portal navigation, validity, and temporary visit behavior')

                page.goto(BASE+'/admin',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/admin/login'))
                page.locator('input[name="password"]').fill('definitely-not-the-passcode')
                page.get_by_role('button',name=re.compile('Open research workspace')).click()
                expect(page.get_by_text('Incorrect password.')).to_be_visible()
                page.locator('input[name="password"]').fill('admin123')
                page.get_by_role('button',name=re.compile('Open research workspace')).click()
                expect(page).to_have_url(re.compile(r'/admin$'))
                # Sign-in lands on the redesigned Research page; the earlier studio now lives under /archive.
                page.goto(BASE+'/archive/admin',wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/archive/admin$'))
                expect(page.get_by_role('heading',name=re.compile('Every experiment has'))).to_be_visible()
                expect(page.get_by_label('Published software release identity')).to_contain_text('v0.34')
                assert 'Public demo passcode' not in page.content()
                page.get_by_role('button',name=re.compile('Pipeline explorer')).click()
                expect(page.get_by_label('Pipeline explorer')).to_be_visible()
                page.get_by_role('button',name='Next gate').click()
                page.get_by_role('button',name=re.compile('Model evidence',re.I)).first.click()
                expect(page.get_by_label('Historical model evidence')).to_be_visible()
                page.get_by_role('button',name=re.compile('Brier')).click()
                expect(page.get_by_role('group',name=re.compile('Brier score interactive bars'))).to_be_visible()
                page.get_by_role('button',name=re.compile('Quality & lineage')).click()
                expect(page.get_by_label('Quality and lineage')).to_be_visible()
                print(f'PASS [{name}] Engine Studio interactions & release evidence')

                tabs=page.get_by_role('navigation',name='Model development stages')
                for tab in ('Dataset','Preprocessing','Model training','Performance','Interpretability','Benchmark','Deep analysis','Decision quality'):
                    tabs.get_by_role('button',name=re.compile(r'^\d+ '+re.escape(tab)+r'$')).click()
                    expect(page.locator('main, .v7-admin').first).to_be_visible()
                expect(page.get_by_role('heading',name='Threshold sensitivity and false-positive burden')).to_be_visible()
                chart=page.locator('svg[role="img"][aria-label*="threshold"]').first
                expect(chart).to_be_visible()
                assert chart.locator('path').count() >= 2
                select=page.locator('label').filter(has_text='Inspect threshold').locator('select')
                assert select.input_value()=='0.22'
                select.select_option('0.35')
                expect(page.get_by_text('Selected 0.35')).to_be_visible()
                view=page.locator('label').filter(has_text='View').locator('select')
                view.select_option('benefit')
                expect(page.locator('svg[role="img"][aria-label*="Net benefit"]')).to_be_visible()
                assert page.locator('svg[role="img"][aria-label*="Net benefit"] path').count() >= 3
                expect(page.get_by_text('Model net benefit')).to_be_visible()
                print(f'PASS [{name}] Admin sections and SVG threshold/benefit switch')
                assert not errors,(name,errors)
                context.close()
            print('SUCCESS: Chromium desktop and mobile browser QA passed. Historical data unchanged.')
        finally:
            browser.close()

if __name__=='__main__':
    run()
