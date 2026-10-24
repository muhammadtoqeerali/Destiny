"""Desktop and mobile browser QA for the Doctor and Research experience (loopback only, no patient input)."""
import os, re
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('FRAILTYSCOPE_QA_BASE', '')
if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}', BASE):
    raise SystemExit('ERROR: redesign QA must run on an isolated loopback server only')

NO_OVERFLOW = 'document.documentElement.scrollWidth <= window.innerWidth + 1'
RANK0 = "() => [...document.querySelectorAll('.fs-rank li')].find(li => li.style.getPropertyValue('--rank').trim() === '0').innerText"


def check_doctor(page, label):
    page.goto(BASE + '/', wait_until='domcontentloaded')
    expect(page).to_have_url(re.compile(r'/doctor/?$'))
    expect(page.get_by_role('heading', level=1)).to_contain_text('one in four older adults')
    nav = page.get_by_role('navigation', name='Primary')
    assert [t.strip() for t in nav.get_by_role('link').all_inner_texts()] == ['Doctor', 'Research'], label
    expect(nav.get_by_role('link', name='Doctor')).to_have_attribute('aria-current', 'page')
    picto = page.get_by_role('figure')
    expect(picto).to_contain_text('24.9%')
    expect(picto).to_contain_text('26.9%')
    expect(picto).to_contain_text('1,032 respondents')
    expect(page.locator('#glance-title')).to_be_visible()
    expect(page.get_by_text('73', exact=True).first).to_be_visible()

    # Fictional explorer: eight radios, one clear label, keyboard and pointer selection.
    group = page.get_by_role('radiogroup', name='Fictional example profiles')
    radios = group.get_by_role('radio')
    assert radios.count() == 8, label
    expect(page.get_by_text('Fictional example, not a patient.')).to_have_count(1)
    expect(page.get_by_role('heading', name='Example 1')).to_be_visible()
    radios.nth(1).click()
    expect(page.get_by_role('heading', name='Example 2')).to_be_visible()
    expect(radios.nth(1)).to_have_attribute('aria-checked', 'true')
    radios.nth(1).press('ArrowDown')
    expect(radios.nth(2)).to_have_attribute('aria-checked', 'true')
    expect(radios.nth(2)).to_be_focused()
    radios.nth(4).click()  # Example 5 has no recorded grip strength: must degrade gracefully
    expect(page.get_by_text('Not recorded')).to_be_visible()
    expect(page.get_by_text('Synthetic demo model', exact=True)).to_be_visible()
    factors = page.get_by_role('button', name=re.compile('What moved this score'))
    expect(factors).to_have_attribute('aria-expanded', 'false')
    factors.click()
    expect(factors).to_have_attribute('aria-expanded', 'true')
    expect(page.get_by_text('raises score').first).to_be_visible()
    factors.click()
    expect(factors).to_have_attribute('aria-expanded', 'false')
    # The real model's AUC must not appear inside the fictional workspace.
    assert '0.732' not in page.locator('.fs-explorer').inner_text(), label
    assert page.evaluate(NO_OVERFLOW), f'{label}: horizontal overflow on /doctor'
    assert 'interview' not in page.locator('body').inner_text().lower(), label


def sign_in(page):
    page.goto(BASE + '/admin', wait_until='domcontentloaded')
    expect(page).to_have_url(re.compile(r'/admin/login'))
    page.locator('input[name="password"]').fill('not-the-password')
    page.get_by_role('button', name=re.compile('Open research workspace')).click()
    expect(page.locator('#login-error')).to_contain_text('Incorrect password', timeout=15000)
    page.locator('input[name="password"]').fill('admin123')  # public aggregate-demo passcode
    page.get_by_role('button', name=re.compile('Open research workspace')).click()
    expect(page).to_have_url(re.compile(r'/admin/?(?:\?.*)?$'), timeout=15000)


def check_research(page, label):
    expect(page.get_by_role('heading', level=1)).to_contain_text('walking difficulty')
    key = page.get_by_label('Key figures')
    for text in ('2,017', 'CatBoost', '0.1507', '0.732'):
        expect(key).to_contain_text(text)
    expect(page.get_by_text('does not predict future frailty')).to_be_visible()
    tabs = page.get_by_role('tablist', name='Experiment stages')
    expect(tabs.get_by_role('tab')).to_have_count(4)
    expect(tabs.get_by_role('tab', name=re.compile('Data and preprocessing'))).to_have_attribute('aria-selected', 'true')
    expect(page.get_by_text('245 of 985')).to_be_visible()
    expect(page.get_by_text('278 of 1,032')).to_be_visible()
    tabs.get_by_role('tab', name=re.compile('Data and preprocessing')).press('ArrowRight')  # keyboard tab switching
    expect(tabs.get_by_role('tab', name=re.compile('Model selection'))).to_have_attribute('aria-selected', 'true')

    # Model selection: six candidates, honest re-ranking by metric, exact numbers on demand.
    ranking = page.get_by_role('list', name=re.compile('Candidate models'))
    expect(ranking.get_by_role('listitem')).to_have_count(6)
    assert 'CatBoost' in page.evaluate(RANK0)
    page.get_by_role('radio', name='3-fold CV Brier').click()
    page.wait_for_timeout(100)
    assert 'Logistic regression' in page.evaluate(RANK0), 'CV Brier must rank logistic regression first'
    page.get_by_role('radio', name='Validation Brier').click()
    assert 'CatBoost' in page.evaluate(RANK0)
    expect(page.get_by_text('Logistic regression did better in cross-validation')).to_be_visible()
    page.get_by_role('button', name='All numbers and settings').click()
    expect(page.get_by_role('table', name='Candidate models with cross-validation and validation scores')).to_contain_text('0.15070')

    # Evaluation: intervals, calibration with the omitted-bin note, interactive band readout.
    tabs.get_by_role('tab', name=re.compile('Evaluation')).click()
    expect(page.get_by_text('exploratory').first).to_be_visible()
    expect(page.get_by_text('43 further people')).to_be_visible()
    cal = page.get_by_role('group', name=re.compile('Calibration chart'))
    expect(cal).to_be_visible()
    cal.get_by_role('button').first.focus()
    expect(page.locator('.fs-cal-read')).to_contain_text('0%–20%')
    expect(page.locator('.fs-cal-read')).to_contain_text('People')
    page.get_by_role('button', name='Cutoff and weighting details').click()
    expect(page.get_by_text('not tuned or validated')).to_be_visible()

    # Drivers: tooltip is keyboard reachable and dismissible; limits are visible.
    tabs.get_by_role('tab', name=re.compile('What drives it')).click()
    tip = page.get_by_role('button', name='About permutation importance')
    tip.focus()
    expect(page.get_by_role('tooltip')).to_be_visible()
    tip.press('Escape')
    expect(page.get_by_role('tooltip')).to_be_hidden()
    expect(page.get_by_role('list', name=re.compile('Permutation importance'))).to_contain_text('Arthritis')
    expect(page.get_by_text('What it does not')).to_be_visible()
    assert page.evaluate(NO_OVERFLOW), f'{label}: horizontal overflow on research stage'

    # Secondary datasets are clearly separate and compact.
    ds = page.get_by_role('radiogroup', name='Dataset')
    ds.get_by_role('radio', name='Fictional cohort').click()
    expect(page.get_by_text('Not NHANES, not HUNT, not clinical.')).to_be_visible()
    assert page.evaluate(NO_OVERFLOW), f'{label}: overflow on fictional cohort'
    ds.get_by_role('radio', name='Mortality archive').click()
    expect(page.get_by_text('Blocked for new analysis.')).to_be_visible()
    assert page.evaluate(NO_OVERFLOW), f'{label}: overflow on archive'
    assert 'interview' not in page.locator('body').inner_text().lower(), label


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=os.environ.get('FRAILTYSCOPE_QA_CHROMIUM') or None)
        try:
            for label, viewport in [('desktop', {'width': 1440, 'height': 900}), ('mobile', {'width': 390, 'height': 844})]:
                ctx = browser.new_context(viewport=viewport, reduced_motion='reduce')
                page = ctx.new_page()
                errors, bad, external = [], [], []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
                page.on('request', lambda r: bad.append((r.method, r.url)) if ('/api/inference' in r.url or r.method == 'POST' and '/admin' not in r.url) else None)

                page.on('request', lambda r: external.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith('data:') else None)
                check_doctor(page, label)
                page.goto(BASE + '/interview', wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/doctor/?$'))
                page.goto(BASE + '/admin/interview', wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/admin/login'))  # old path keeps the sign-in requirement
                page.goto(BASE + '/archive/admin', wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/admin/login'))
                sign_in(page)
                check_research(page, label)
                page.goto(BASE + '/admin/interview', wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/admin/?$'))  # signed in: forwarded to the canonical page
                page.get_by_role('button', name='Sign out').click()
                expect(page).to_have_url(re.compile(r'/doctor/?$'), timeout=15000)
                page.goto(BASE + '/admin', wait_until='domcontentloaded')
                expect(page).to_have_url(re.compile(r'/admin/login'))
                # The main product loads nothing from third-party hosts and raises no console errors.
                assert not bad, (label, bad)
                assert not external, (label, external)
                assert not errors, (label, errors)
                # Earlier workspaces stay reachable (their legacy stylesheet still requests Google Fonts).
                page.goto(BASE + '/archive', wait_until='domcontentloaded')
                expect(page.get_by_role('link', name=re.compile('Earlier Doctor workspace'))).to_be_visible()
                print(f'PASS [{label}] Doctor/Research routes, fictional isolation, honest model ranking, auth, no inference requests')
                ctx.close()
        finally:
            browser.close()


if __name__ == '__main__':
    run()
