#!/usr/bin/env python3
"""Real Chromium UI smoke-test against built files with mocked data fetches.
No external network or successful live RSS claim is implied by this test.
"""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'public'
HTML=(ASSETS/'index.html').read_text(encoding='utf8')
FILES={f'data/{x.name}':json.loads(x.read_text(encoding='utf8')) for x in (ASSETS/'data').glob('*.json')}

def create_page(browser,**options):
    page=browser.new_page(**options)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.evaluate('(data)=>{window.fetch=async(url)=>({ok:true,json:async()=>data[String(url).split("?")[0]]||{items:[]}})}',FILES)
    page.set_content(HTML,wait_until='load',timeout=15000)
    page.wait_for_function("document.getElementById('healthStatus').textContent.includes('情報')",timeout=15000)
    return page,errors

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
    try:
        page,errs=create_page(browser,viewport={'width':1360,'height':900},locale='zh-TW')
        assert page.locator('#newsList .item').count()>0
        assert page.locator('#newsSource option').all_text_contents()==['全部來源','YouTube','巴哈姆特','其他新聞']
        page.locator('#newsSource').select_option('YouTube')
        assert page.locator('#newsList a').count()>=4, 'YouTube links must be available if live RSS is empty'
        page.locator('#newsSource').select_option('巴哈姆特')
        assert page.locator('#newsList a').count()>=1, 'Bahamut source fallback must remain clickable'
        page.locator('#newsSource').select_option('')
        page.locator('#newsRange').select_option('recent')
        assert '本次篩選' in page.locator('#newsInfo').inner_text()
        page.locator('[data-sub="launches"]').click()
        assert page.locator('#gameGrid .card').count()>0
        assert page.locator('#storeSources a').count()==0
        page.locator('#gamePlatform').select_option('Google Play')
        assert page.locator('#gameGrid .card').count()>0
        page.locator('#gamePlatform').select_option('App Store')
        assert page.locator('#gameGrid .card').count()>0
        page.locator('#gamePlatform').select_option('')
        page.locator('#gameGrid .card').first.locator('button').click()
        assert page.locator('#detail').evaluate('(el)=>el.open')
        page.locator('#detail').evaluate('(el)=>el.close()')
        page.locator('button[data-page="codes"]').click()
        assert page.locator('#codeList button').count()>0
        page.locator('#codeList button').first.click()
        assert page.locator('#codeDialog').evaluate('(el)=>el.open')
        assert page.locator('#codeDialogBody button[data-copycode]').count()>0
        assert '未實測' in page.locator('#codeDialogBody').inner_text()
        page.locator('#closeCodes').click()
        page.locator('button[data-page="guides"]').click()
        assert page.locator('#guideArticles .item').count()>0
        page.locator('button[data-page="calendar"]').click()
        assert page.locator('#calendarView .calendar-chart').count()>0
        assert page.locator('#calendarLegend .legend-item').count()>=4, 'November events must include multiple games'
        assert len(set(page.locator('#calendarLegend .legend-dot').evaluate_all('(els)=>els.map(el=>el.style.background)')))==page.locator('#calendarLegend .legend-dot').count(), 'Colors must be unique per game within a month'
        page.locator('#nextMonth').click()
        page.locator('#prevMonth').click()
        assert not errs,errs
        page.screenshot(path='/mnt/data/game-intel-live-pipeline-browser-check.png',full_page=True)
        print('PASS: Chromium desktop UI: news source/range filters, game filtering/detail, code modal, guides, calendar; no JS exceptions')
        mobile,mobile_errs=create_page(browser,viewport={'width':390,'height':844},is_mobile=True,device_scale_factor=1)
        assert mobile.locator('#tabs button').count()==4
        mobile.locator('button[data-page="codes"]').click()
        assert mobile.locator('#codeList button').count()>0
        assert not mobile_errs,mobile_errs
        print('PASS: Chromium mobile UI: four functional tabs and code list')
    finally:browser.close()
