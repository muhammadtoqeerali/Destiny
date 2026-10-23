"""Real loopback-only Chromium QA for GET-only predefined synthetic fixture serving."""
import os
import re
from playwright.sync_api import sync_playwright, expect

BASE=os.getenv('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: v0.40 QA must use local 127.0.0.1 production server')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.getenv('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for name,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];posts=[];synthetic_gets=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda request: posts.append(request.url) if request.method=='POST' else (synthetic_gets.append(request.url) if '/api/inference/synthetic' in request.url else None))
                route=BASE+'/api/inference/synthetic'
                r=page.request.get(route+'?fixture=fictional_reference')
                assert r.status==200,(name,r.status)
                doc=r.json();assert doc['schema']=='FRAILTYSCOPE_SYNTHETIC_SERVING_V40'
                assert doc['patient_data_accepted'] is False and doc['clinical_inference'] is False
                assert len(doc['results'])==3
                for item in doc['results']:
                    total=item['intercept']+sum(c['log_odds_contribution'] for c in item['contributions'])
                    assert abs(total-item['logit'])<1e-10
                    assert len(item['contributions'])==6
                    assert 0<item['synthetic_class_1_probability']<1
                for suffix in ['?fixture=fictional_reference&age=75','?fixture=fictional_reference&fixture=fictional_variant_b','?fixture=not_real','']:
                    bad=page.request.get(route+suffix)
                    assert bad.status==400,(name,suffix,bad.status)
                assert page.request.post(route,data={'age':75,'patient_id':'fictional'}).status==405
                assert page.request.post(BASE+'/api/inference',data={'x':1}).status==403
                page.goto(BASE+'/doctor',wait_until='domcontentloaded')
                nav=page.get_by_role('navigation',name='Doctor workspace')
                nav.get_by_role('button',name='Patient assessment',exact=True).click()
                page.get_by_label('Age',exact=True).fill('79')
                nav.get_by_role('button',name='Model evidence',exact=True).click()
                section=page.get_by_role('region',name='Synthetic server-side inference')
                expect(section).to_be_visible()
                expect(section.get_by_role('heading',name='A working server-side model and explanation')).to_be_visible()
                expect(section.get_by_text('GET-only fixture contract',exact=False)).to_be_visible()
                result=section.locator('.v40-results button').first
                expect(result).to_contain_text('Invented outcome A')
                old=result.locator('strong').inner_text()
                section.get_by_label('Choose a fictional fixture').select_option('fictional_variant_b')
                expect(section.get_by_text('GET-only fixture contract',exact=False)).to_be_visible()
                new=result.locator('strong').inner_text()
                assert old!=new, (name,old,new)
                expect(section.locator('.v40-line')).to_have_count(7)
                assert posts==[],(name,posts)
                assert all('age=79' not in u and 'patient' not in u for u in synthetic_gets),synthetic_gets
                assert not errors,(name,errors)
                if name=='mobile':assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),'Mobile horizontal overflow'
                print(f'PASS [{name}] v0.40 GET-only synthetic server, multioutput coefficients, strict rejection and patient isolation')
                ctx.close()
        finally:browser.close()
    print('SUCCESS: v0.40 synthetic serving browser QA passed. No patient inference.')
if __name__=='__main__':run()
