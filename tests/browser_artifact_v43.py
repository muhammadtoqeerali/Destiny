"""Real browser QA of v0.43 public synthetic-only artifact acceptance; loopback only."""
import os
import re
from playwright.sync_api import sync_playwright,expect
BASE=os.getenv('FRAILTYSCOPE_QA_BASE','')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}',BASE):
    raise SystemExit('ERROR: v0.43 QA must target isolated loopback build')

def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.getenv('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for name,viewport in [('desktop',{'width':1440,'height':900}),('mobile',{'width':390,'height':844})]:
                ctx=browser.new_context(viewport=viewport,reduced_motion='reduce')
                page=ctx.new_page();errors=[];writes=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda req:writes.append(req.url) if req.method in ('POST','PUT','PATCH','DELETE') else None)
                response=page.request.get(BASE+'/api/inference/artifacts')
                assert response.status==200,(name,response.status)
                data=response.json()
                assert data['schema']=='FRAILTYSCOPE_ARTIFACT_ACCEPTANCE_V43'
                assert data['clinical_promotion_decision']=='DENIED'
                assert data['clinical_inference'] is False
                assert data['registered_clinical_models']==0
                assert data['artifact_binary_loaded'] is False and data['patient_data_used'] is False
                assert len(data['checks'])==10 and len(data['clinical_outcomes'])==4
                assert response.headers['cache-control'].startswith('no-store')
                assert page.request.post(BASE+'/api/inference/artifacts',data={'fictional':True}).status==405
                assert page.request.post(BASE+'/api/inference',data={'fictional':True}).status==403
                page.goto(BASE+'/doctor/workspace',wait_until='domcontentloaded')
                page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Model evidence',exact=True).click()
                section=page.get_by_role('region',name='Synthetic artifact acceptance dossier')
                expect(section).to_be_visible()
                expect(section.get_by_text('Clinical promotion denied')).to_be_visible()
                assert section.get_by_label('Artifact acceptance check list').locator('article').count()==10
                section.get_by_role('button',name='Source fingerprints').click()
                area=section.get_by_label('Public synthetic source fingerprints')
                expect(area).to_be_visible()
                expect(area.get_by_text(data['model_registry_sha256'])).to_be_visible()
                section.get_by_role('button',name='Four clinical gates').click()
                assert section.get_by_label('Clinical outcome promotion decisions').locator('article').count()==4
                if name=='mobile':
                    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),'Horizontal overflow'
                assert not errors,(name,errors)
                assert writes==[],(name,writes)
                print(f'PASS [{name}] v0.43 fictional manifest fingerprints, four denied promotions, no patient POST')
                ctx.close()
        finally:browser.close()
    print('SUCCESS: v0.43 artifact acceptance desktop/mobile browser QA; clinical scoring prohibited')
if __name__=='__main__':run()
