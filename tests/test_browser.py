"""Opt-in browser acceptance tests; run with RUN_BROWSER_TESTS=1."""
import importlib.util
import os
from pathlib import Path
import random
import sqlite3
import struct
import threading
import zlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from werkzeug.serving import make_server

from conftest import TEST_SEPAY_KEY, bank_webhook

pytestmark=pytest.mark.skipif(os.getenv('RUN_BROWSER_TESTS')!='1',reason='Opt in with RUN_BROWSER_TESTS=1 and install requirements-dev.txt')
ROOT=Path(__file__).resolve().parents[1]
QR_PIXEL=bytes.fromhex('89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c020000000b4944415478da6364f80f00010501012718e3660000000049454e44ae426082')


@pytest.fixture
def browser_page(service_cluster):
    playwright=pytest.importorskip('playwright.sync_api')
    spec=importlib.util.spec_from_file_location('test_gateway',ROOT/'gateway/app.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    server=make_server('127.0.0.1',0,module.create_app(),threaded=True)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True);thread.start()
    executable=os.getenv('BROWSER_EXECUTABLE')
    if not executable:
        for candidate in ('C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'):
            if Path(candidate).exists(): executable=candidate;break
    try:
        with playwright.sync_playwright() as p:
            browser=p.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
            # wait_for_function polls with eval, which the real policy forbids. The policy
            # itself is exercised by test_content_security_policy_does_not_block_the_interface.
            page=browser.new_page(viewport={'width':1440,'height':1000},locale='vi-VN',reduced_motion='reduce',bypass_csp=True)
            page.set_default_timeout(30000)
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            yield page,service_cluster,errors
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def login(page,cluster,role,username=None):
    if username is None:
        user_id={'admin':1,'resident':3,'technician':11}[role]
        with sqlite3.connect(cluster.db_path) as db:
            username=db.execute('SELECT username FROM users WHERE user_id=?',(user_id,)).fetchone()[0]
    page.locator('#auth-form [name=username]').fill(username)
    page.locator('#auth-form [name=password]').fill(cluster.password)
    page.locator('#auth-form [type=submit]').click()
    page.locator('#page .page-heading h1').wait_for()
    page.wait_for_function("document.querySelector('#page')?.getAttribute('aria-busy') !== 'true'")


def visit(page,route):
    page.locator(f'.nav a[href="#{route}"]').click()
    page.wait_for_function("route => document.querySelector('#page')?.dataset.route === route && document.querySelector('#page')?.getAttribute('aria-busy') !== 'true' && !!document.querySelector('#page .page-heading h1')",arg=route)
    page.locator('#page .page-heading h1').wait_for()
    assert page.locator('#page .error-box').count()==0
    assert page.locator('#page').inner_text().find('Không thể tải')==-1


def mock_firebase_browser(page):
    """Exercise the real push controller, with no Google traffic or OS popups."""
    page.add_init_script("""(() => {
      Object.defineProperty(window, 'Notification', {value: {permission:'granted', requestPermission:async()=>Notification.permission}});
      const registration={getNotifications:async()=>[],pushManager:{getSubscription:async()=>({unsubscribe:async()=>true})}};
      Object.defineProperty(navigator,'serviceWorker',{value:{register:async()=>registration,getRegistration:async()=>registration,ready:Promise.resolve(registration)}});
    })()""")
    page.route('**/api/notifications/push-config',lambda route:route.fulfill(json={
        'configured':True,'config':{'projectId':'browser-test','apiKey':'fake','messagingSenderId':'123','appId':'fake','vapidKey':'fake'}}))
    def sdk(route):
        source=("export const getApps=()=>[];export const initializeApp=(options)=>({options});"
            if route.request.url.endswith('/firebase-app.js') else
            "export const isSupported=async()=>true;export const getMessaging=()=>({});export const getToken=async()=>'browser-token';export const deleteToken=async()=>true;export const onMessage=(m,fn)=>{window.firebaseEmit=fn;return()=>{window.firebaseEmit=null}};")
        route.fulfill(body=source,headers={'Content-Type':'text/javascript','Access-Control-Allow-Origin':'*'})
    page.route('https://www.gstatic.com/firebasejs/10.14.1/*',sdk)
    page.reload()


def test_firebase_opt_in_reload_foreground_disable_logout(browser_page):
    page,cluster,errors=browser_page
    mock_firebase_browser(page)
    login(page,cluster,'resident')
    visit(page,'notifications')
    page.locator('[data-action=push-enable]').click()
    page.locator('[data-action=push-disable]').wait_for()
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute("SELECT user_id FROM notification_push_tokens WHERE token='browser-token'").fetchone()==(3,)
    page.evaluate("firebaseEmit({data:{user_id:'4',title:'WRONG RECIPIENT'}})")
    assert 'WRONG RECIPIENT' not in page.locator('#toasts').inner_text()
    page.evaluate("firebaseEmit({data:{user_id:'3',title:'Correct push'}})")
    assert 'Correct push' in page.locator('#toasts').inner_text()
    page.reload()
    page.wait_for_function("typeof window.firebaseEmit === 'function'")
    assert page.evaluate("AnCuPush.active()")
    page.locator('[data-action=push-disable]').click()
    page.locator('[data-action=push-enable]').wait_for()
    assert page.evaluate("localStorage.getItem('ancu_push_owner')") is None
    assert page.evaluate("caches.open('ancu-push').then(c=>c.match('/__ancu_push_owner__')).then(Boolean)") is False
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM notification_push_tokens WHERE token='browser-token'").fetchone()==(0,)
    page.locator('[data-action=push-enable]').click()
    page.locator('[data-action=push-disable]').wait_for()
    with page.expect_response(lambda response: '/push-tokens' in response.url and response.request.method=='DELETE'):
        page.locator('[data-action=logout]').click()
    assert page.evaluate("localStorage.getItem('ancu_push_owner')") is None
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM notification_push_tokens WHERE token='browser-token'").fetchone()==(0,)
    assert not errors,errors


def test_firebase_permission_denied_does_not_register(browser_page):
    page,cluster,errors=browser_page
    mock_firebase_browser(page)
    login(page,cluster,'resident')
    visit(page,'notifications')
    page.evaluate("Notification.permission='denied'")
    page.locator('[data-action=push-enable]').click()
    page.locator('#toasts .error').wait_for()
    assert not page.evaluate("AnCuPush.active()")
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute('SELECT COUNT(*) FROM notification_push_tokens').fetchone()==(0,)
    assert not errors,errors


def assert_brand_and_image_copy(page):
    assert page.locator('.brand-name').inner_text().strip().rstrip('.')=='AN CƯ'
    visible_text=page.locator('body').inner_text().casefold()
    assert 'minh hoạ' not in visible_text and 'minh họa' not in visible_text


def test_registration_login_and_personal_profile(browser_page):
    page,cluster,errors=browser_page
    assert_brand_and_image_copy(page)
    with sqlite3.connect(cluster.db_path) as db:
        apartment_code=db.execute('SELECT code FROM apartments WHERE apartment_id=1').fetchone()[0]
    page.locator('[data-action=auth-switch]').click()
    for name,value in {'apartment_code':apartment_code,'full_name':'Cư dân đăng ký mới','username':'new.user-1','email':'new@gmail.com','password':'MatKhau123'}.items():
        page.locator(f'#auth-form [name={name}]').fill(value)
    phone=page.locator('#auth-form [name=phone]')
    assert phone.get_attribute('required') is not None
    page.locator('#auth-form [type=submit]').click()
    assert phone.evaluate('(input)=>input.validity.valueMissing')
    assert page.locator('#auth-form').get_attribute('data-register')=='true'
    phone.fill('0901234567')
    assert page.locator('#auth-form [name=username]').evaluate('(input)=>input.checkValidity()')
    password=page.locator('#auth-form [name=password]')
    password.fill('12')
    page.locator('#auth-form [type=submit]').click()
    assert password.evaluate('(input)=>input.validationMessage')=='Mật khẩu cần ít nhất 6 ký tự.'
    password.fill('MatKhau123')
    page.locator('#auth-form [type=submit]').click()
    page.wait_for_function("document.querySelector('#auth-form')?.dataset.register === 'false'")
    assert page.evaluate("sessionStorage.getItem('ancu_token')") is None
    assert page.locator('#auth-form [name=username]').input_value()=='new.user-1'
    page.locator('#auth-form [name=password]').fill('MatKhau123')
    page.locator('#auth-form [type=submit]').click()
    page.locator('#page .page-heading h1').wait_for()
    assert page.locator('.nav a.active').get_attribute('data-route')=='overview'
    visit(page,'profile')
    assert page.locator('#account-label').inner_text()=='Cư dân đăng ký mới'
    assert apartment_code in page.locator('#resident-apt-tag').inner_text()
    assert apartment_code in page.locator('#page').inner_text()
    page.locator('[data-action=profile-edit]').click()
    assert page.locator('#modal-form [aria-label="Số căn hộ"]').input_value()==apartment_code
    page.locator('#modal-form [name=full_name]').fill('Tên đã cập nhật')
    page.locator('#modal-form [name=email]').fill('updated@gmail.com')
    phone=page.locator('#modal-form [name=phone]')
    assert phone.get_attribute('required') is not None
    assert phone.input_value()=='0901234567'
    phone.fill('')
    page.locator('#modal-form [type=submit]').click()
    assert phone.evaluate('(input)=>input.validity.valueMissing')
    phone.fill('0987654321')
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    page.locator('#page').get_by_text('Tên đã cập nhật',exact=True).wait_for()
    assert 'updated@gmail.com' in page.locator('#page').inner_text()
    page.reload()
    page.locator('#page').get_by_text('Tên đã cập nhật',exact=True).wait_for()
    assert '0987654321' in page.locator('#page').inner_text()
    page.locator('[data-action=profile-edit]').click()
    page.locator('#modal-form [name=username]').fill('renamed.user')
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    page.locator('#page').get_by_text('renamed.user',exact=True).wait_for()
    page.locator('[data-action=password-edit]').click()
    for name,value in {'current_password':'wrong','new_password':'new12345','confirm_password':'other123'}.items():
        page.locator(f'#modal-form [name={name}]').fill(value)
    page.locator('#modal-form [type=submit]').click()
    page.locator('#modal-form .form-error').get_by_text('Mật khẩu hiện tại không đúng.').wait_for()
    page.locator('#modal-form [name=current_password]').fill('MatKhau123')
    page.locator('#modal-form [type=submit]').click()
    page.locator('#modal-form .form-error').get_by_text('Mật khẩu mới và mật khẩu nhập lại không trùng khớp.').wait_for()
    page.locator('#modal-form [name=confirm_password]').fill('new12345')
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    # The token was replaced: this tab must still be signed in after the old one is revoked.
    page.locator('#page').get_by_text('renamed.user',exact=True).wait_for()
    page.locator('[data-action=logout]').click()
    page.locator('#auth-form [name=username]').fill('renamed.user')
    page.locator('#auth-form [name=password]').fill('MatKhau123')
    page.locator('#auth-form [type=submit]').click()
    page.locator('#auth-form .form-error').get_by_text('Sai tên đăng nhập hoặc mật khẩu, vui lòng kiểm tra lại').wait_for()
    with sqlite3.connect(cluster.db_path) as db:
        db.execute("UPDATE users SET status='locked',lock_reason=? WHERE username='renamed.user'",('Cần xác minh thông tin',))
    page.locator('#auth-form [name=password]').fill('new12345')
    page.locator('#auth-form [type=submit]').click()
    page.locator('#modal-title').get_by_text('Tài khoản đã bị khóa',exact=True).wait_for()
    assert 'Cần xác minh thông tin' in page.locator('#modal').inner_text()
    assert not errors,errors


@pytest.mark.parametrize('role',['admin','resident','technician'])
def test_role_navigation_and_responsive_layout(browser_page,role):
    page,cluster,errors=browser_page
    login(page,cluster,role)
    assert_brand_and_image_copy(page)
    routes=page.locator('.nav a').evaluate_all('(nodes)=>nodes.map(n=>n.hash.slice(1))')
    if role!='admin': assert 'users' not in routes and 'reports' not in routes
    for route in routes:
        visit(page,route)
    assert 'chatbot' not in routes  # the assistant is opened from the sidebar card only
    page.locator('.support-card [data-route=chatbot]').click()
    page.wait_for_function("document.querySelector('#page')?.dataset.route === 'chatbot' && document.querySelector('#page')?.getAttribute('aria-busy') !== 'true'")
    assert 'Giờ yên tĩnh' not in page.locator('.chat-suggestions').inner_text()
    page.locator('#chat-form [name=question]').fill('Hieu thuoc o dau?')
    page.locator('#chat-form [type=submit]').click()
    page.wait_for_function("document.querySelector('#chat-form').dataset.busy === 'false'")
    assert 'hiệu thuốc' in page.locator('.chat-message.bot').last.inner_text().lower()
    visit(page,'overview')
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
    page.locator('[data-action=menu]').click()
    page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().left >= 0")
    page.locator('.nav a[href="#notifications"]').click()
    page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")
    page.locator('#page .page-heading h1').wait_for()
    assert not errors,errors


@pytest.mark.parametrize('role',['admin','resident'])
def test_rail_dock_and_today_column_follow_the_agreed_layout(browser_page,role):
    page,cluster,errors=browser_page
    login(page,cluster,role)
    visit(page,'overview')
    page.set_viewport_size({'width':1440,'height':900})
    assert page.locator('.nav a[href="#complaints"]').is_visible()
    assert page.evaluate("document.querySelector('.nav').scrollHeight <= document.querySelector('.nav').clientHeight")
    assert page.locator('.notification-bell').is_visible() and page.locator('[data-action=logout]').is_visible()
    assert page.evaluate("document.querySelector('.today-panel').getBoundingClientRect().left >= document.querySelector('.overview-main').getBoundingClientRect().right")
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")
    assert page.locator('.notification-bell').is_visible() and page.locator('[data-action=logout]').is_visible()
    assert page.evaluate("document.querySelector('.today-panel').getBoundingClientRect().top >= document.querySelector('.overview-main').getBoundingClientRect().bottom")
    if role=='resident':
        headings=page.locator('#page h2').all_inner_texts()
        assert headings.index('Hóa đơn cần thanh toán')<headings.index('Hôm nay')
    page.locator('.dock a[href="#complaints"]').click()
    page.locator('#page[data-route="complaints"] .page-heading h1').wait_for()
    assert page.locator('.dock a.active').get_attribute('data-route')=='complaints'
    assert not errors,errors


# Visible text under 11px, and form controls under 16px (iOS zooms into those). Chart labels are SVG text.
PHONE_TEXT_SIZES="""(root) => {
  const small=[],controls=[];
  for (const el of document.querySelectorAll(root+' *')) {
    if (el.closest('svg') || (root==='#app' && el.closest('.sidebar'))) continue;
    const box=el.getBoundingClientRect(), size=parseFloat(getComputedStyle(el).fontSize);
    if (!box.width || !box.height) continue;
    if (el.matches('input:not([type=checkbox]):not([type=radio]):not([type=file]), select, textarea') && size<16) controls.push(`${el.id} ${size}px`);
    const own=[...el.childNodes].filter(n => n.nodeType===3).map(n => n.textContent.trim()).join('');
    if (own && size<11) small.push(`${el.className} ${size}px "${own.slice(0,30)}"`);
  }
  return {small,controls};
}"""


def test_phone_text_is_readable_and_the_dock_clears_the_iphone_home_bar(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'resident')
    for route in ('overview','billing','notifications'):
        visit(page,route)
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")
        assert page.evaluate(PHONE_TEXT_SIZES,'#app')=={'small':[],'controls':[]},route
        page.set_viewport_size({'width':1440,'height':1000})
    page.set_viewport_size({'width':390,'height':844})
    page.locator('[data-action=menu]').click()
    page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().left >= 0")
    assert page.evaluate(PHONE_TEXT_SIZES,'.sidebar')=={'small':[],'controls':[]},'menu'
    assert 'viewport-fit=cover' in page.locator('meta[name=viewport]').get_attribute('content')
    try:
        page.context.new_cdp_session(page).send('Emulation.setSafeAreaInsetsOverride',{'insets':{'top':0,'bottom':34,'left':0,'right':0}})
    except Exception:
        pytest.skip('This browser cannot emulate the iPhone safe area')
    page.wait_for_function("getComputedStyle(document.querySelector('.dock')).paddingBottom === '34px'")
    assert page.evaluate("innerHeight - document.querySelector('.dock a').getBoundingClientRect().bottom")>=34
    assert not errors,errors


def test_admin_has_the_wide_sidebar_separate_today_cards_and_can_remove_a_policy(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'admin')
    visit(page,'overview')
    page.set_viewport_size({'width':1440,'height':900})
    assert page.evaluate("document.querySelector('.sidebar').getBoundingClientRect().width")>=200
    assert page.locator('.nav a[href="#residents"]').inner_text().strip()=='Cư dân & hợp đồng'
    assert page.locator('.floor-display').count()==0
    assert page.evaluate("getComputedStyle(document.querySelector('.today-step'),'::after').content")=='none'
    question='Sân pickleball trên sân thượng mở cửa lúc mấy giờ?'
    page.locator('.support-card [data-route=chatbot]').click()
    page.locator('[data-action=tab][data-tab=faqs]').click()
    page.locator('[data-action=faq-create]').click()
    page.locator('#modal-form [name=question]').fill(question)
    page.locator('#modal-form [name=answer]').fill('Mở từ 6 giờ đến 21 giờ.')
    page.locator('#modal-form [type=submit]').click()
    card=page.locator('.notice-card',has_text=question)
    card.wait_for()
    card.locator('[data-action=faq-delete]').click()
    page.locator('#modal-form [type=submit]').click()
    card.wait_for(state='detached')
    assert not errors,errors


def noisy_png(size=1400):
    raw=b''.join(b'\x00'+random.randbytes(size*3) for _ in range(size))
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,1))+chunk(b'IEND',b'')


def test_complaint_accepts_a_large_photo_by_shrinking_it(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'resident')
    visit(page,'complaints')
    page.locator('[data-action=complaint-create]').click()
    page.locator('#modal-form [name=category]').fill('Vệ sinh')
    page.locator('#modal-form [name=content]').fill('Ảnh chụp hành lang')
    photo=noisy_png()
    assert len(photo)>450*1024
    page.locator('#field-attachments').set_input_files([{'name':'hanh-lang.png','mimeType':'image/png','buffer':photo}])
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal')?.open")
    saved=cluster.call('complaint','/api/complaints',role='resident',user_id=3).json()['items'][0]
    assert saved['category']=='Vệ sinh' and saved['attachments'][0]['name']=='hanh-lang.jpg'
    assert saved['attachments'][0]['type']=='image/jpeg' and len(saved['attachments'][0]['data'])<=600*1024
    assert not errors,errors


def test_resident_opens_policies_from_the_overview_and_the_report_counts_complaints(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'resident')
    visit(page,'overview')
    page.locator('.overview-shortcut[data-tab=faqs]').click()
    page.locator('#page[data-route=chatbot] .tab.active[data-tab=faqs]').wait_for()
    page.locator('#page .notice-card').first.wait_for()
    assert page.locator('[data-action=faq-create]').count()==0
    page.locator('.support-card [data-route=chatbot]').click(force=True)
    page.locator('#page .tab.active[data-tab=chat]').wait_for()
    page.locator('[data-action=logout]').click()
    login(page,cluster,'admin')
    visit(page,'reports')
    stats=page.locator('#page .stat-card').all_inner_texts()
    assert any('Khiếu nại' in text for text in stats) and any('Thu điện nước' in text for text in stats)
    assert any('Thu dịch vụ 6 tháng' in text for text in stats)
    visit(page,'apartments')
    assert 'Chủ sở hữu' in page.locator('#page thead').inner_text()
    assert not errors,errors


def test_parking_registration_rules_preserve_draft_and_submit(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'resident')
    visit(page,'parking')
    page.locator('[data-action=parking-request]').click()
    vehicle_type=page.locator('#modal-form [name=vehicle_type]')
    vehicle_type.wait_for()
    assert vehicle_type.locator('option').evaluate_all('(options)=>options.map(option=>option.value)')==['motorbike','electric_bike','bicycle']
    fee=page.locator('#modal-form [name=monthly_fee]')
    assert fee.get_attribute('readonly') is not None
    assert fee.input_value()=='100000'
    plate=page.locator('#modal-form [name=plate_number]')
    assert plate.get_attribute('required') is not None
    vehicle_type.select_option('bicycle')
    assert fee.input_value()=='50000'
    assert plate.get_attribute('required') is None
    vehicle_type.select_option('electric_bike')
    assert fee.input_value()=='100000'
    assert plate.get_attribute('required') is not None
    assert not plate.evaluate('(input)=>input.checkValidity()')
    plate.fill('59E1-987.65')
    months=page.locator('#modal-form [name=registration_months]')
    registered_date=page.locator('#modal-form [name=registered_date]')
    assert registered_date.get_attribute('type')=='date'
    assert registered_date.get_attribute('required') is not None
    # The allowed months follow the start date: November leaves exactly November and December.
    registered_date.fill('2026-11-01')
    assert (months.get_attribute('min'),months.get_attribute('max'))==('2','2')
    # January allows up to six months, the last beginning in June.
    registered_date.fill('2027-01-01')
    assert (months.get_attribute('min'),months.get_attribute('max'))==('2','6')
    assert 'kỳ thu phí kết thúc tháng 6/2027' in page.locator('#parking-months-help').inner_text()
    months.fill('1')
    assert months.evaluate('(input)=>input.validity.rangeUnderflow')
    months.fill('7')
    assert months.evaluate('(input)=>input.validity.rangeOverflow')
    months.fill('6')
    # Calendar months from the start date: 1 January for six months runs to the end of 30 June.
    months.dispatch_event('change')
    assert 'Gửi đến hết ngày 30/06/2027' in page.locator('#parking-months-help').inner_text()
    with sqlite3.connect(cluster.db_path) as db:
        apartment_code=db.execute('SELECT code FROM apartments WHERE apartment_id=1').fetchone()[0]
    assert page.locator('#modal-form [name=apartment_code]').input_value()==apartment_code
    page.locator('#modal-form [name=notes]').fill('Xe màu xanh, giữ nguyên nội dung đã nhập.')
    draft=page.locator('#modal-form').evaluate('(form)=>Object.fromEntries(new FormData(form))')
    page.evaluate("window.parkingDraftForm=document.querySelector('#modal-form')")
    for close_action in ('button','escape','backdrop'):
        page.locator('[data-action=parking-rules-modal]').click()
        page.locator('#modal-title').get_by_text('Quy định đăng ký gửi xe tại chung cư',exact=True).wait_for()
        if close_action=='button':
            page.locator('#modal .modal-footer').get_by_role('button',name='Đóng',exact=True).click()
        elif close_action=='escape':
            page.keyboard.press('Escape')
        else:
            page.mouse.click(2,2)
        page.locator('#modal-form [name=vehicle_type]').wait_for()
        assert page.evaluate("document.querySelector('#modal').open")
        assert page.evaluate("document.querySelector('#modal-form')===window.parkingDraftForm")
        assert page.locator('#modal-form').evaluate('(form)=>Object.fromEntries(new FormData(form))')==draft
    with page.expect_response(lambda response:response.url.endswith('/api/complaints') and response.request.method=='POST') as submitted:
        page.locator('#modal-form [type=submit]').click()
    assert submitted.value.status==201,submitted.value.text()
    saved=submitted.value.json()
    assert saved['type']=='registration' and saved['category']=='Đăng ký gửi xe'
    assert draft['plate_number'] in saved['content'] and draft['notes'] in saved['content']
    page.wait_for_function("!document.querySelector('#modal').open")
    page.locator('#toasts .toast').filter(has_text='Đã gửi').last.wait_for()
    assert not errors,errors


def test_complaint_type_opens_procedure_registration_form(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'resident')
    visit(page,'complaints')
    page.locator('[data-action=complaint-create]').click()
    page.locator('#modal-form [name=category]').fill('Tiếng ồn')
    page.locator('#modal-form [name=type]').select_option('registration')
    page.locator('#modal-form [name=attachment_links]').wait_for()
    # Procedure registration is its own form, not the parking application.
    assert page.locator('#modal-form [name=vehicle_type]').count()==0
    assert 'Danh mục / Tên thủ tục' in page.locator('#modal-form').inner_text()
    page.locator('#modal-form [name=type]').select_option('complaint')
    page.locator('#modal-form [name=attachment_links]').wait_for(state='detached')
    assert page.locator('#modal-form [name=category]').input_value()=='Tiếng ồn'
    # Complaints take photos too; only web links are specific to procedures.
    assert page.locator('#modal-form [name=attachment_files]').count()==1
    page.locator('#modal-form [name=type]').select_option('registration')
    page.locator('#modal-form [name=attachment_links]').wait_for()
    page.locator('#modal-form [name=category]').fill('Đăng ký thi công nội thất')
    page.locator('#modal-form [name=attachment_files]').set_input_files(files=[{'name':'ban-ve.png','mimeType':'image/png','buffer':b'\x89PNG\r\n\x1a\n'}])
    page.locator('#modal-form [name=attachment_links]').fill('https://example.com/ho-so')
    page.locator('#modal-form [name=content]').fill('Thi công từ 08:00 đến 17:00 trong 3 ngày.')
    with page.expect_response(lambda response:response.url.endswith('/api/complaints') and response.request.method=='POST') as submitted:
        page.locator('#modal-form [type=submit]').click()
    assert submitted.value.status==201,submitted.value.text()
    saved=submitted.value.json()
    assert saved['type']=='registration' and saved['category']=='Đăng ký thi công nội thất'
    assert [a['name'] for a in saved['attachments']]==['ban-ve.png','https://example.com/ho-so']
    page.wait_for_function("!document.querySelector('#modal').open && document.querySelector('#page').getAttribute('aria-busy') !== 'true'")
    page.locator('#table-search').fill(f"  YC{saved['complaint_id']}  ")
    row=page.locator('tbody tr').filter(has_text=f"#YC{saved['complaint_id']}")
    row.wait_for()
    assert page.locator('tbody tr:not([hidden])').count()==1
    row.locator('[data-action=complaint-edit]').last.click()
    assert 'ban-ve.png' in page.locator('#modal').inner_text()
    assert not errors,errors


def test_management_reply_notifies_only_the_complaint_sender(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'resident')
    visit(page,'complaints')
    page.locator('[data-action=complaint-create]').click()
    page.locator('#modal-form [name=category]').fill('Tiếng ồn hành lang')
    page.locator('#modal-form [name=content]').fill('Nhờ Ban quản lý nhắc mọi người giữ yên tĩnh sau giờ nghỉ.')
    with page.expect_response(lambda response:response.url.endswith('/api/complaints') and response.request.method=='POST') as submitted:
        page.locator('#modal-form [type=submit]').click()
    assert submitted.value.status==201,submitted.value.text()
    complaint=submitted.value.json()
    complaint_id=complaint['complaint_id']
    page.wait_for_function("!document.querySelector('#modal').open && document.querySelector('#page').getAttribute('aria-busy') !== 'true'")
    page.locator('[data-action=logout]').click()
    login(page,cluster,'admin')
    visit(page,'complaints')
    row=page.locator('tbody tr').filter(has_text=f'#YC{complaint_id}')
    row.get_by_role('button',name='Phản hồi',exact=True).click()
    reply=page.locator('#modal-form [name=response]')
    assert reply.get_attribute('required') is not None
    reply.fill('   ')
    page.locator('#modal-form [type=submit]').click()
    page.locator('#modal-form .form-error').get_by_text('Vui lòng nhập nội dung phản hồi cho cư dân.',exact=True).wait_for()
    first_reply='Ban quản lý đã nhắc nhở các căn hộ giữ yên tĩnh. Cảm ơn bạn đã báo.'
    reply.fill(first_reply)
    page.locator('#modal-form [name=status]').select_option('resolved')
    with page.expect_response(lambda response:response.url.endswith(f'/api/complaints/{complaint_id}') and response.request.method=='PATCH') as answered:
        page.locator('#modal-form [type=submit]').click()
    assert answered.value.status==200,answered.value.text()
    page.wait_for_function("!document.querySelector('#modal').open && document.querySelector('#page').getAttribute('aria-busy') !== 'true'")
    row.get_by_role('button',name='Sửa phản hồi',exact=True).click()
    status=page.locator('#modal-form [name=status]')
    assert status.locator('option').evaluate_all('(options)=>options.map(option=>option.value)')==['resolved']
    assert page.locator('#modal-form [name=response]').input_value()==first_reply
    revised_reply='Ban quản lý đã nhắc nhở các căn hộ. Nếu còn tiếng ồn, bạn vui lòng báo lại thời gian xảy ra.'
    page.locator('#modal-form [name=response]').fill(revised_reply)
    with page.expect_response(lambda response:response.url.endswith(f'/api/complaints/{complaint_id}') and response.request.method=='PATCH') as amended:
        page.locator('#modal-form [type=submit]').click()
    assert amended.value.status==200,amended.value.text()
    assert amended.value.json()['status']=='resolved'
    page.wait_for_function("!document.querySelector('#modal').open && document.querySelector('#page').getAttribute('aria-busy') !== 'true'")
    page.locator('[data-action=logout]').click()
    login(page,cluster,'resident')
    visit(page,'notifications')
    page.locator('[data-action=notice-filter][data-filter=private]').click()
    page.wait_for_function("document.querySelector('#page').getAttribute('aria-busy') !== 'true'")
    notices=page.locator('.notice-card').filter(has_text=f'Ban quản lý đã phản hồi yêu cầu #YC{complaint_id}')
    assert notices.count()==2
    notices.first.click()
    page.locator('#modal-title').get_by_text(f'Ban quản lý đã phản hồi yêu cầu #YC{complaint_id}',exact=True).wait_for()
    assert revised_reply in page.locator('#modal').inner_text()
    assert 'Thông báo riêng' in page.locator('#modal').inner_text()
    page.locator('#modal .modal-header [data-action=close-modal]').click()
    visit(page,'complaints')
    row=page.locator('tbody tr').filter(has_text=f'#YC{complaint_id}')
    assert row.get_by_role('button',name='Phản hồi',exact=True).count()==0
    row.get_by_role('button',name='Chi tiết',exact=True).click()
    assert revised_reply in page.locator('#modal').inner_text()
    assert 'Phản hồi của Ban quản lý' in page.locator('#modal').inner_text()
    own_notices=cluster.call('notification','/api/notifications',role='resident').json()['items']
    assert len([n for n in own_notices if n['title']==f'Ban quản lý đã phản hồi yêu cầu #YC{complaint_id}'])==2
    other_notices=cluster.call('notification','/api/notifications',role='resident',user_id=4).json()['items']
    assert not any(n['title']==f'Ban quản lý đã phản hồi yêu cầu #YC{complaint_id}' for n in other_notices)
    assert not errors,errors


def test_tab_switch_preserves_visible_content_until_response(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'admin')
    visit(page,'parking')
    vehicles=cluster.call('parking','/api/parking/guest-daily').json()
    before=page.locator('#page').inner_text()
    page.evaluate("""() => {
        window.previousParkingPanel=document.querySelector('#page .panel');
        window.loadingInserted=false;
        window.loadingObserver=new MutationObserver(records=>{
            for(const record of records)for(const node of record.addedNodes){
                if(node.nodeType===1 && (node.matches('.loading')||node.querySelector('.loading')))window.loadingInserted=true;
            }
        });
        window.loadingObserver.observe(document.querySelector('#page'),{childList:true,subtree:true});
    }""")
    pending=[]
    page.route('**/api/parking/guest-daily',lambda route:pending.append(route))
    with page.expect_request('**/api/parking/guest-daily'):
        page.locator('[data-action=tab][data-tab=guest]').click()
    page.wait_for_function("document.querySelector('#page').getAttribute('aria-busy') === 'true'")
    assert page.locator('#page').inner_text()==before
    assert page.evaluate("document.querySelector('#page .panel')===window.previousParkingPanel")
    assert page.locator('#page .loading').count()==0
    assert not page.evaluate('window.loadingInserted')
    assert len(pending)==1
    pending[0].fulfill(json=vehicles)
    page.wait_for_function("document.querySelector('#page').getAttribute('aria-busy') !== 'true' && document.querySelector('#page .tab.active')?.dataset.tab === 'guest'")
    assert not page.evaluate('window.loadingInserted')
    assert page.locator('#page .error-box').count()==0
    assert not errors,errors


def test_report_export_uses_latest_completed_selection(browser_page):
    page,cluster,errors=browser_page
    login(page,cluster,'admin')
    held_years=set()
    pending={}

    def report_for(year):
        totals={'billed_amount':year*1000,'collected_amount':year*1000,'outstanding_amount':0,
                'invoice_count':1,'paid_count':1}
        return {'year':year,'items':[{'period':f'{year}-01',**totals}],'totals':totals}

    def reports(route):
        year=int(parse_qs(urlsplit(route.request.url).query)['year'][0])
        if year in held_years:
            pending[year]=route
        else:
            route.fulfill(json=report_for(year))

    page.route('**/api/billing/reports?*',reports)
    visit(page,'reports')
    years=page.locator('#report-year option').evaluate_all('(options)=>options.map(option=>Number(option.value))')
    earlier_request,latest_request=years[1:3]
    held_years.add(earlier_request)
    downloads=[]
    page.on('download',lambda download:downloads.append(download))
    with page.expect_request(f'**/api/billing/reports?year={earlier_request}&*'):
        page.locator('#report-year').select_option(str(earlier_request))
    page.wait_for_function("document.querySelector('#page').getAttribute('aria-busy') === 'true'")
    page.locator('[data-action=report-export]').click()
    page.locator('#toasts .toast').get_by_text('Vui lòng đợi báo cáo cập nhật xong.',exact=True).wait_for()
    assert not downloads
    with page.expect_request(f'**/api/billing/reports?year={latest_request}&*'):
        page.locator('#report-year').select_option(str(latest_request))
    page.wait_for_function("year => document.querySelector('#page').getAttribute('aria-busy') !== 'true' && document.querySelector('#report-year').value === String(year)",arg=latest_request)
    with page.expect_response(f'**/api/billing/reports?year={earlier_request}&*') as old_response:
        pending[earlier_request].fulfill(json=report_for(earlier_request))
    old_response.value.finished()
    page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    assert page.locator('#report-year').input_value()==str(latest_request)
    assert f'{latest_request}-01' in page.locator('tbody').inner_text()
    assert f'{earlier_request}-01' not in page.locator('tbody').inner_text()
    with page.expect_download() as download:
        page.locator('[data-action=report-export]').click()
    assert download.value.suggested_filename==f'bao-cao-doanh-thu-{latest_request}.csv'
    csv=Path(download.value.path()).read_text(encoding='utf-8-sig')
    assert f'{latest_request}-01' in csv and f'{earlier_request}-01' not in csv
    assert len(downloads)==1
    assert not errors,errors


def test_admin_creation_and_resident_payment_in_browser(browser_page):
    page,cluster,errors=browser_page
    page.route('**/api/billing/orders/*/qr',lambda route:route.fulfill(body=QR_PIXEL,content_type='image/png'))
    login(page,cluster,'admin')
    visit(page,'apartments')
    page.locator('[data-action=apartment-create]').click()
    for name,value in {'code':'BROWSER-101','block':'BROWSER','floor':'1','area':'72'}.items():
        page.locator(f'#modal-form [name={name}]').fill(value)
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    page.locator('text=BROWSER-101').first.wait_for()
    visit(page,'billing')
    assert page.locator('#page .page-heading h1').inner_text()=='Quản lý hóa đơn'
    assert page.locator('.nav a[href="#billing"]').inner_text().strip()=='Quản lý hóa đơn'
    page.locator('[data-action=invoice-create]').click()
    page.locator('#modal-form [name=apartment_id]').select_option('1')
    page.locator('#modal-form [name=period]').fill('2098-11')
    page.locator('#modal-form [name=due_date]').fill('2098-12-15')
    page.locator('#modal-form [name=electricity_usage]').fill('140')
    page.locator('#modal-form [name=electricity_unit_price]').fill('3000')
    page.locator('#modal-form [name=water_usage]').fill('11')
    page.locator('#modal-form [name=water_unit_price]').fill('10000')
    assert '530.000' in page.locator('#utility-preview').inner_text()
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    admin_row=page.locator('tbody tr').filter(has_text='2098-11')
    assert admin_row.locator('button').first.inner_text().strip()=='Chi tiết'
    admin_row.locator('button').first.click()
    page.locator('#modal[open] [data-action=invoice-cash]').wait_for(state='visible')
    assert page.locator('#modal [data-action=invoice-pay]').count()==0
    assert page.locator('#modal [data-action=invoice-cash]').count()==1
    assert 'chỉ ghi nhận thu khi đã nhận đủ tiền' in page.locator('#page').inner_text()
    page.locator('#modal [data-action=close-modal]').first.click()
    page.locator('[data-action=logout]').click()
    login(page,cluster,'resident')
    visit(page,'billing')
    assert page.locator('#page .page-heading h1').inner_text()=='Hóa đơn & thanh toán'
    row=page.locator('tbody tr').filter(has_text='2098-11')
    row.locator('button').first.click()
    page.locator('#modal [data-action=invoice-pay]').wait_for(state='visible')
    assert page.locator('#modal [data-action=invoice-cash]').count()==0
    page.locator('#modal [data-action=invoice-pay]').click()
    page.locator('#payment-status').get_by_text('Đang chờ chuyển khoản',exact=True).wait_for()
    order_id=page.evaluate("sessionStorage.getItem('ancu_vietqr_order_3')")
    order=cluster.call('billing',f'/api/billing/orders/{order_id}',role='resident').json()
    assert page.locator('#payment-actions [data-action=receipt]').count()==0
    response=cluster.call('billing','/api/billing/sepay/webhook',method='POST',json=bank_webhook(order),headers={'Authorization':'Apikey '+TEST_SEPAY_KEY})
    assert response.status_code==201,response.text
    # Nothing to press: the open dialog notices the verified payment on its own.
    page.locator('#payment-status').get_by_text('Đã xác nhận thanh toán',exact=True).wait_for()
    page.locator('#modal [data-action=close-modal]').first.click()
    page.wait_for_function("[...document.querySelectorAll('tbody tr')].some(r => r.textContent.includes('2098-11') && r.textContent.includes('Đã thanh toán'))")
    row=page.locator('tbody tr').filter(has_text='2098-11')
    assert 'Đã thanh toán' in row.inner_text()
    page.locator('[data-action=tab][data-tab=payments]').click()
    page.locator('[data-action=receipt]').first.wait_for()
    with page.expect_download() as download:
        page.locator('[data-action=receipt]').first.click()
    assert download.value.suggested_filename.endswith('.png')
    assert not errors,errors


@pytest.mark.parametrize('role', ['admin', 'resident'])
def test_invoice_live_times_and_notification_apartment(browser_page, role):
    page,cluster,errors=browser_page
    # Vietnam times must be identical even on a browser in another timezone.
    page.context.new_cdp_session(page).send('Emulation.setTimezoneOverride',{'timezoneId':'America/Los_Angeles'})
    login(page,cluster,role)
    visit(page,'billing')
    response=cluster.call('billing','/api/billing/invoices/monthly',method='POST',json={
        'apartment_id':1,'period':'2098-08','due_date':'2098-09-10','electricity_fee':10000,'water_fee':5000})
    assert response.status_code==201,response.text
    identifier=response.json()['invoice_id']
    search=f'HD{identifier:04d}'  # search is by invoice code
    page.locator('#table-search').fill(search)
    with sqlite3.connect(cluster.db_path) as db:
        db.execute('UPDATE monthly_invoices SET created_at=? WHERE invoice_id=?',('2026-11-06 18:30:45',identifier))
    row=page.locator('tbody tr').filter(has_text='2098-08')
    row.wait_for(state='visible',timeout=15000)  # Polling, without navigation/reload.
    assert page.locator('#table-search').input_value()==search
    assert '01:30:45' in row.inner_text() and '07/11/2026' in row.inner_text()
    row.locator('button').first.click()
    created=page.locator('#modal .detail-list > div').filter(has=page.get_by_text('Thời gian lập hóa đơn',exact=True)).locator('dd')
    assert '01:30:45' in created.inner_text()
    response=cluster.call('billing',f'/api/billing/invoices/monthly/{identifier}/pay',method='POST',json={'payment_method':'cash'})
    assert response.status_code==201,response.text
    paid_at=response.json()['paid_at']
    expected=datetime.fromisoformat(paid_at).strftime('%H:%M:%S')
    paid=page.locator('#modal .detail-list > div').filter(has=page.get_by_text('Thời gian thanh toán',exact=True)).locator('dd')
    page.wait_for_function("value => document.querySelector('#modal').textContent.includes(value)",arg=expected,timeout=15000)
    assert expected in paid.inner_text()
    assert page.locator('#modal [data-action=invoice-pay]').count()==0
    assert page.locator('#modal [data-action=invoice-cash]').count()==0
    page.locator('#modal [data-action=close-modal]').first.click()
    page.wait_for_function("[...document.querySelectorAll('tbody tr')].some(r => r.textContent.includes('2098-08') && r.textContent.includes('Đã thanh toán'))",timeout=15000)
    assert page.locator('#table-search').input_value()==search
    # Ordinary edits must not be replaced by the background refresh.
    if role=='admin':
        page.locator('[data-action=invoice-create]').click()
        page.locator('#modal-form [name=electricity_usage]').fill('123.45')
        page.wait_for_timeout(5500)
        assert page.locator('#modal-form [name=electricity_usage]').input_value()=='123.45'
        page.locator('#modal [data-action=close-modal]').first.click()
    with cluster.apps['billing'].app_context():
        cluster.modules['billing'].dispatch_outbox()
    with sqlite3.connect(cluster.db_path) as db:
        event=f"billing:{'paid-admin' if role=='admin' else 'paid'}:monthly:{identifier}"
        notification_id=db.execute('SELECT notification_id FROM notification_events WHERE event_id=?',(event,)).fetchone()[0]
        apartment_code=db.execute('SELECT code FROM apartments WHERE apartment_id=1').fetchone()[0]
    visit(page,'notifications')
    page.locator(f'[data-action=notice-detail][data-id="{notification_id}"]').click()
    apartment=page.locator('#modal .detail-list > div').filter(has=page.get_by_text('Căn hộ',exact=True)).locator('dd')
    assert apartment.inner_text()==apartment_code
    assert expected in page.locator('#modal').inner_text()
    # UTC and offset timestamps represent the same instant, including rollover.
    assert page.evaluate("dateTime('2026-11-06 18:30:45')") == page.evaluate("dateTime('2026-11-07T01:30:45+07:00')")
    assert not errors,errors


def test_registered_apartment_without_contract_shows_awaiting_confirmation(browser_page):
    page,cluster,errors=browser_page
    with sqlite3.connect(cluster.db_path) as db:
        resident_id=db.execute('SELECT resident_id FROM residents WHERE user_id=3').fetchone()[0]
        apartment_code=db.execute('SELECT code FROM apartments WHERE apartment_id=1').fetchone()[0]
        db.execute("UPDATE apartment_contracts SET status='terminated' WHERE resident_id=?",(resident_id,))
        db.execute('UPDATE residents SET registered_apartment_code=? WHERE resident_id=?',(apartment_code,resident_id))
    login(page,cluster,'resident')
    visit(page,'billing')
    page.locator('#billing-apartment-notice').wait_for()
    assert apartment_code in page.locator('#resident-apt-tag').inner_text()
    assert '(chưa xác nhận)' in page.locator('#resident-apt-tag').inner_text()
    assert 'chưa được Ban quản lý xác nhận' in page.locator('#billing-apartment-notice').inner_text()
    assert page.locator('#page .stat-card').count()==0
    assert 'Chưa thể xem hóa đơn' in page.locator('#page').inner_text()
    assert page.locator('#page tbody tr').count()==0
    assert page.locator('[data-action=invoice-pay]').count()==0
    assert not errors,errors


def test_admin_confirms_and_revokes_co_resident_invoice_access(browser_page):
    page,cluster,errors=browser_page
    username='co.resident-qa'
    full_name='Cư dân thử xác nhận'
    with sqlite3.connect(cluster.db_path) as db:
        apartment_code=db.execute('SELECT code FROM apartments WHERE apartment_id=1').fetchone()[0]
        original_contracts=db.execute('SELECT * FROM apartment_contracts ORDER BY contract_id').fetchall()
    registered=cluster.call('auth','/api/auth/register',method='POST',json={
        'username':username,'password':cluster.password,'full_name':full_name,
        'email':'coresident@gmail.com','phone':'0901234567','apartment_code':apartment_code})
    assert registered.status_code==201,registered.text
    for apartment_id,fee in ((1,123000),(2,987000)):
        created=cluster.call('billing','/api/billing/invoices/monthly',method='POST',json={
            'apartment_id':apartment_id,'period':'2097-09','electricity_fee':fee,'water_fee':20000,'due_date':'2097-10-15'})
        assert created.status_code==201,created.text

    login(page,cluster,'resident',username=username)
    visit(page,'billing')
    assert page.locator('#billing-apartment-notice').count()==1
    assert page.locator('#page tbody tr').count()==0
    page.locator('[data-action=logout]').click()

    login(page,cluster,'admin')
    visit(page,'residents')
    resident_row=page.locator('tbody tr').filter(has_text=full_name)
    resident_row.locator('[data-action=resident-apartments]').click()
    assert page.locator('#modal-form [name=apartment_id]').input_value()=='1'
    assert 'không tạo hoặc thay đổi hợp đồng' in page.locator('#modal').inner_text()
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    page.wait_for_function("name => [...document.querySelectorAll('#page tbody tr')].some(r=>r.textContent.includes(name)&&!r.textContent.includes('(đăng ký)'))",arg=full_name)
    page.locator('[data-action=logout]').click()

    login(page,cluster,'resident',username=username)
    visit(page,'billing')
    assert page.locator('#billing-apartment-notice').count()==0
    assert '(chưa xác nhận)' not in page.locator('#resident-apt-tag').inner_text()
    own_invoice=page.locator('tbody tr').filter(has_text='2097-09')
    assert own_invoice.count()==1
    assert apartment_code in own_invoice.inner_text()
    assert '987.000' not in page.locator('#page').inner_text()
    own_invoice.locator('[data-action=invoice-detail]').click()
    # Invoice details load asynchronously before the payment button is rendered.
    page.locator('#modal [data-action=invoice-pay]').wait_for(state='visible')
    assert page.locator('#modal [data-action=invoice-pay]').count()==1
    assert page.locator('#modal [data-action=invoice-cash]').count()==0
    page.locator('#modal [data-action=close-modal]').first.click()
    page.locator('[data-action=logout]').click()

    login(page,cluster,'admin')
    visit(page,'residents')
    page.locator('tbody tr').filter(has_text=full_name).locator('[data-action=resident-apartments]').click()
    page.locator('#modal [data-action=resident-apartment-remove]').click()
    page.get_by_role('heading',name='Gỡ xác nhận căn hộ',exact=True).wait_for()
    assert 'Hợp đồng không bị thay đổi' in page.locator('#modal').inner_text()
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    page.locator('[data-action=logout]').click()
    login(page,cluster,'resident',username=username)
    visit(page,'billing')
    assert page.locator('#billing-apartment-notice').count()==1
    assert page.locator('#page tbody tr').count()==0
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute('SELECT * FROM apartment_contracts ORDER BY contract_id').fetchall()==original_contracts
    assert not errors,errors


def browser_order(invoice_id=1, **overrides):
    order={'order_id':'VQR-ui-checkout','invoice_type':'monthly','invoice_id':invoice_id,
           'amount':150000,'mode':'sepay','environment':'test','status':'pending',
           'qr_image_url':None,'payment_id':None,'is_owner':True,'can_pay':True,
           'payer_user_id':3,'transfer_content':'QLCCUI12345',
           'bank':{'code':'VCB','name':'Vietcombank','account_number':'0123456789','account_name':'BQL TEST'},
           'expires_at':(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat()}
    order.update(overrides)
    return order


def browser_invoice(cluster, period='2098-10'):
    response=cluster.call('billing','/api/billing/invoices/monthly',method='POST',json={
        'apartment_id':1,'period':period,'electricity_fee':120000,'water_fee':30000,
        'due_date':'2098-11-15'})
    assert response.status_code==201,response.text
    return response.json()


def route_browser_order(page, order):
    page.route(f"**/api/billing/invoices/monthly/{order['invoice_id']}/checkout",lambda route:route.fulfill(json=order))
    page.route('**/api/billing/orders/'+order['order_id'],lambda route:route.fulfill(json=order))
    page.route('**/api/billing/orders/'+order['order_id']+'/reconcile',lambda route:route.fulfill(json=order))


def open_browser_payment(page, cluster, period='2098-10'):
    login(page,cluster,'resident')
    visit(page,'billing')
    page.locator('tbody tr').filter(has_text=period).locator('[data-action=invoice-detail]').click()
    page.locator('#modal [data-action=invoice-pay]').click()


def test_sepay_order_resumes_without_trusting_return_parameters(browser_page):
    page,cluster,errors=browser_page
    order=browser_order()
    route_browser_order(page,order)
    login(page,cluster,'resident')
    page.evaluate("sessionStorage.setItem('ancu_vietqr_order_3','VQR-ui-checkout')")
    origin=page.url.split('#')[0].split('?')[0].rstrip('/')
    page.goto(origin+'/?payment_status=success&payment_id=999#billing')
    page.locator('#payment-status').get_by_text('Đang chờ chuyển khoản',exact=True).wait_for()
    assert page.locator('#payment-actions [data-action=receipt]').count()==0
    assert page.evaluate("sessionStorage.getItem('ancu_vietqr_order_3')")=='VQR-ui-checkout'
    page.locator('#modal [data-action=close-modal]').first.click()
    order.update(status='awaiting_confirmation',can_pay=False)
    page.reload()
    page.locator('#payment-status h3').get_by_text('Chờ ngân hàng xác nhận',exact=True).wait_for()
    assert page.locator('#payment-options').is_hidden()
    assert page.locator('#payment-actions [data-action=payment-cancel]').count()==0
    assert page.locator('#payment-actions [data-action=invoice-pay]').count()==0
    order.update(status='success',payment_id=812)
    page.locator('#payment-status').get_by_text('Đã xác nhận thanh toán',exact=True).wait_for()
    assert page.evaluate("sessionStorage.getItem('ancu_vietqr_order_3')") is None
    assert not errors,errors


@pytest.mark.parametrize('environment',['test','live'])
def test_sepay_checkout_confirms_itself_and_only_reports_errors_in_browser(browser_page,environment):
    """There is nothing to report or check: verified server state alone marks the invoice paid."""
    page,cluster,errors=browser_page
    invoice=browser_invoice(cluster)
    order=browser_order(invoice['invoice_id'],environment=environment)
    route_browser_order(page,order)
    outage={'on':False}
    def order_state(route):
        if outage['on']:
            route.fulfill(status=502,json={'error':'Billing tạm thời không phản hồi.'})
        else:
            route.fulfill(json=order)
    page.route('**/api/billing/orders/VQR-ui-checkout',order_state)
    page.route('**/api/billing/payments/monthly/812/receipt',lambda route:route.fulfill(json={
        'title':'Biên nhận','issuer':'Chung cư','notice':'SEPAY TEST','rows':[['Mã biên nhận','MONTHLY-812']],'footer':'Nội bộ'}))
    open_browser_payment(page,cluster)
    page.locator('#payment-status').get_by_text('Đang chờ chuyển khoản',exact=True).wait_for()
    if environment=='test':
        assert 'SePay Test' in page.locator('#modal-title').inner_text()
    else:
        assert page.locator('#modal-title').inner_text()=='Thanh toán VietQR'
    assert 'tiền thật' not in page.locator('#modal').inner_text()
    assert page.locator('#modal [data-action=payment-confirm], #modal [data-action=payment-check]').count()==0
    assert 'QLCCUI12345' in page.locator('#payment-options').inner_text()
    assert 'không phải hạn thanh toán hóa đơn' in page.locator('#payment-expiry').inner_text()
    assert page.locator('#payment-feedback').is_hidden()
    outage['on']=True
    page.locator('#payment-feedback').get_by_text('Chưa cập nhật được trạng thái thanh toán. Billing tạm thời không phản hồi.',exact=True).wait_for()
    assert page.locator('#payment-actions [data-action=receipt]').count()==0
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute('SELECT status FROM monthly_invoices WHERE invoice_id=?',(invoice['invoice_id'],)).fetchone()[0]!='paid'
    order.update(status='success',payment_id=812)
    outage['on']=False
    page.locator('#payment-status').get_by_text('Đã xác nhận thanh toán',exact=True).wait_for()
    assert page.locator('#payment-feedback').is_hidden()
    assert page.evaluate("sessionStorage.getItem('ancu_vietqr_order_3')") is None
    with page.expect_download() as download:
        page.locator('#payment-actions [data-action=receipt]').click()
    assert download.value.suggested_filename=='bien-nhan-monthly-812.png'
    assert not errors,errors


def test_sepay_other_household_member_cannot_see_qr_or_transfer_details(browser_page):
    page,cluster,errors=browser_page
    invoice=browser_invoice(cluster)
    order=browser_order(invoice['invoice_id'],is_owner=False,can_pay=False,payer_user_id=17,
                        qr_image_url='/api/billing/orders/VQR-ui-checkout/qr')
    route_browser_order(page,order)
    qr_requests=[]
    page.route('**/api/billing/orders/VQR-ui-checkout/qr',lambda route:qr_requests.append(route.request.url) or route.abort())
    open_browser_payment(page,cluster)
    page.locator('#payment-status').get_by_text('Một thành viên khác đang thanh toán',exact=True).wait_for()
    assert page.locator('#payment-options').is_hidden()
    assert page.locator('#payment-qr').count()==0
    assert '0123456789' not in page.locator('#modal').inner_text()
    assert 'QLCCUI12345' not in page.locator('#modal').inner_text()
    assert page.locator('#payment-actions [data-action=payment-confirm]').count()==0
    assert page.locator('#payment-actions [data-action=payment-cancel]').count()==0
    assert page.locator('#payment-actions [data-action=invoice-pay]').count()==0
    assert not qr_requests
    order.update(status='success',payment_id=812)
    page.locator('#payment-status').get_by_text('Đã xác nhận thanh toán',exact=True).wait_for()
    assert not errors,errors


def test_sepay_expired_session_hides_bank_details_and_cancel_requires_warning(browser_page):
    page,cluster,errors=browser_page
    invoice=browser_invoice(cluster)
    order=browser_order(invoice['invoice_id'],expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
    route_browser_order(page,order)
    open_browser_payment(page,cluster)
    page.locator('#payment-status').get_by_text('Phiên thanh toán đã hết thời gian',exact=True).wait_for()
    assert page.locator('#payment-options').is_hidden()
    assert page.locator('#payment-actions [data-action=payment-confirm]').count()==0
    assert page.locator('#payment-actions [data-action=payment-cancel]').count()==0
    order.update(expires_at=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat())
    page.locator('#payment-actions [data-action=payment-cancel]').wait_for()
    cancel_requests=[]
    def cancel(route):
        cancel_requests.append(route.request.method)
        order.update(status='cancelled',can_pay=False)
        route.fulfill(json=order)
    page.route('**/api/billing/orders/VQR-ui-checkout/cancel',cancel)
    messages=[]
    def dismiss(dialog):
        messages.append(dialog.message)
        dialog.dismiss()
    page.once('dialog',dismiss)
    page.locator('#payment-actions [data-action=payment-cancel]').click()
    assert 'CHƯA chuyển khoản' in messages[0]
    assert not cancel_requests
    page.once('dialog',lambda dialog:dialog.accept())
    page.locator('#payment-actions [data-action=payment-cancel]').click()
    page.locator('#payment-status').get_by_text('Phiên thanh toán đã hủy',exact=True).wait_for()
    assert cancel_requests==['POST']
    assert page.locator('#payment-actions [data-action=invoice-pay]').inner_text().strip()=='Mở phiên mới'
    assert not errors,errors


@pytest.mark.parametrize('role',['admin','technician'])
def test_staff_edit_their_personal_information(browser_page,role):
    page,cluster,errors=browser_page
    login(page,cluster,role)
    visit(page,'profile')
    assert page.locator('#modal').evaluate('(modal)=>modal.open') is False
    page.locator('[data-action=profile-edit]').click()
    page.locator('#modal-form [name=full_name]').fill('Nhân Sự Cập Nhật')
    page.locator('#modal-form [name=id_card]').fill('079000000002')
    assert page.locator('#modal-form [data-action=close-modal]').count()==0
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    page.locator('#page').get_by_text('Nhân Sự Cập Nhật',exact=True).wait_for()
    assert '079000000002' in page.locator('#page').inner_text()
    assert 'Nhân Sự Cập Nhật' in page.locator('#header-greeting-title').inner_text()
    page.locator('[data-action=password-edit]').click()
    page.locator('#modal-form [name=new_password]').wait_for()
    assert not errors,errors


def test_admin_releases_a_payment_the_bank_never_confirmed(browser_page):
    page,cluster,errors=browser_page
    created=cluster.call('billing','/api/billing/invoices/monthly',method='POST',json={
        'apartment_id':1,'period':'2096-03','electricity_fee':50000,'water_fee':20000,'due_date':'2096-04-15'})
    assert created.status_code==201,created.text
    invoice_id=created.json()['invoice_id']
    order=cluster.call('billing',f'/api/billing/invoices/monthly/{invoice_id}/checkout',method='POST',role='resident',json={}).json()
    assert cluster.call('billing',f"/api/billing/orders/{order['order_id']}/confirm-transfer",method='POST',role='resident',json={}).status_code==200
    login(page,cluster,'admin')
    visit(page,'billing')
    page.locator('tbody tr').filter(has_text='2096-03').locator('[data-action=invoice-detail]').click()
    page.locator('[data-action=invoice-release]').click()
    page.locator('#modal-form [name=note]').fill('Sao kê không có khoản chuyển')
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    assert cluster.call('billing',f'/api/billing/invoices/monthly/{invoice_id}').json()['active_payment_status'] is None
    assert not errors,errors


def test_contract_form_tells_residents_with_the_same_name_apart(browser_page):
    page,cluster,errors=browser_page
    ids=[]
    apartment=cluster.call('resident','/api/apartments',method='POST',json={'code':'UI-SAME','block':'TEST','floor':1,'area':70}).json()['apartment_id']
    # Residents join only by registering; two people happen to share a name.
    for number,phone in ((1,'0900000011'),(2,'0900000012')):
        created=cluster.call('auth','/api/auth/register',method='POST',json={
            'username':f'trung.ten{number}','password':'TrungTen!2026','full_name':'Phạm Trùng Tên',
            'email':f'trungten{number}@gmail.com','phone':phone,'apartment_code':'UI-SAME'})
        assert created.status_code==201,created.text
        user_id=created.json()['user']['user_id']
        ids.append(cluster.call('resident','/api/residents/me',role='resident',user_id=user_id).json()['resident_id'])
    login(page,cluster,'admin')
    visit(page,'residents')
    assert page.locator('[data-action=resident-create]').count()==0
    page.locator('[data-action=tab][data-tab=contracts]').click()
    page.locator('[data-action=contract-create]').click()
    page.locator('#modal-form [name=apartment_id]').select_option(str(apartment))
    page.locator('#modal-form [name=contract_type]').select_option('ownership')
    # Plain text: no suggestion list, so no dropdown arrow.
    assert page.locator('#modal-form [name=resident_name]').get_attribute('list') is None
    page.locator('#modal-form [name=resident_name]').fill('Phạm Trùng Tên')
    page.locator('#modal-form [type=submit]').click()
    page.locator('#modal-form .form-error').get_by_text('Có nhiều cư dân trùng tên',exact=False).wait_for()
    page.locator('#modal-form [name=resident_name]').fill(f'Phạm Trùng Tên (#{ids[1]})')
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    contracts=cluster.call('resident','/api/contracts').json()['items']
    assert next(row for row in contracts if row['apartment_id']==apartment)['resident_id']==ids[1]
    assert not errors,errors


def test_content_security_policy_does_not_block_the_interface(browser_page):
    page,cluster,_=browser_page
    context=page.context.browser.new_context(viewport={'width':1440,'height':1000},locale='vi-VN')
    strict=context.new_page()
    problems=[]
    strict.on('console',lambda message:problems.append(message.text) if 'Content Security Policy' in message.text else None)
    strict.on('pageerror',lambda error:problems.append(str(error)))
    strict.goto(page.url)
    strict.locator('#auth-form').wait_for()
    strict.wait_for_load_state('networkidle')
    assert strict.evaluate("[...document.images].every(image=>image.complete&&image.naturalWidth>0)")
    assert strict.evaluate("document.fonts.ready.then(()=>document.fonts.status)")=='loaded'
    with sqlite3.connect(cluster.db_path) as db:
        username=db.execute('SELECT username FROM users WHERE user_id=1').fetchone()[0]
    strict.locator('#auth-form [name=username]').fill(username)
    strict.locator('#auth-form [name=password]').fill(cluster.password)
    strict.locator('#auth-form [type=submit]').click()
    strict.locator('#page .page-heading h1').wait_for()
    for route in ('residents','billing','notifications'):
        strict.locator(f'.nav a[href="#{route}"]').click()
        strict.locator(f'#page[data-route="{route}"] .page-heading h1').wait_for()
    context.close()
    assert not problems,problems


def test_sepay_missing_configuration_disables_resident_checkout(browser_page):
    page,cluster,errors=browser_page
    browser_invoice(cluster)
    page.route('**/api/billing/payment-config',lambda route:route.fulfill(json={
        'mode':'sepay','environment':'test','ready':False,'missing':['SEPAY_WEBHOOK_API_KEY'],
        'message':'Ban quản lý cần kết nối tài khoản SePay và ngân hàng nhận tiền.'}))
    login(page,cluster,'resident')
    visit(page,'billing')
    assert 'cần kết nối tài khoản SePay' in page.locator('#payment-mode-notice').inner_text()
    page.locator('tbody tr').filter(has_text='2098-10').locator('[data-action=invoice-detail]').click()
    assert page.locator('#modal [data-action=invoice-pay]').is_disabled()
    assert not errors,errors


def test_sepay_partial_receipt_refreshes_qr_for_remaining_amount(browser_page):
    page,cluster,errors=browser_page
    invoice=browser_invoice(cluster)
    order=browser_order(invoice['invoice_id'],paid_amount=0,remaining_amount=150000,
                        qr_image_url='/api/billing/orders/VQR-ui-checkout/qr')
    route_browser_order(page,order)
    qr_amounts=[]
    def qr(route):
        assert route.request.headers.get('authorization','').startswith('Bearer ')
        qr_amounts.append(order['remaining_amount'])
        route.fulfill(body=QR_PIXEL,content_type='image/png')
    page.route('**/api/billing/orders/VQR-ui-checkout/qr',qr)
    open_browser_payment(page,cluster)
    page.locator('#payment-qr').wait_for(state='visible')
    assert qr_amounts==[150000]
    first_image=page.locator('#payment-qr').get_attribute('src')
    order.update(paid_amount=100000,remaining_amount=50000)
    # "150.000" also contains "50.000", so wait for the shortfall line the next status check renders.
    page.locator('#payment-status').get_by_text('Chỉ chuyển phần còn thiếu',exact=False).wait_for()
    page.locator('#payment-qr').wait_for(state='visible')
    assert qr_amounts==[150000,50000]
    assert page.locator('#payment-qr').get_attribute('src')!=first_image
    assert not page.locator('#payment-amount').inner_text().startswith('150')
    assert '50.000' in page.locator('#payment-options').inner_text()
    assert page.locator('#payment-actions [data-action=payment-cancel]').count()==0
    assert not errors,errors


def test_sepay_admin_tracks_surplus_and_only_records_manual_resolution(browser_page):
    page,cluster,errors=browser_page
    transaction={'transaction_id':91,'amount':200000,'allocated_amount':150000,'unallocated_amount':50000,
                 'status':'overpaid','issue':'Cư dân chuyển dư','invoice_type':'monthly','invoice_id':17,
                 'bank_reference':'BANK-QA-91','received_at':'2026-11-06T10:00:00+07:00',
                 'resolution':None,'resolution_note':None}
    page.route('**/api/billing/sepay/transactions',lambda route:route.fulfill(json={'items':[transaction]}))
    resolutions=[]
    def resolve(route):
        data=route.request.post_data_json
        resolutions.append(data)
        transaction.update(resolution=data['resolution'],resolution_note=data['note'])
        route.fulfill(json=transaction)
    page.route('**/api/billing/sepay/transactions/91/resolve',resolve)
    login(page,cluster,'admin')
    visit(page,'billing')
    page.locator('[data-action=tab][data-tab=bank-transactions]').click()
    page.locator('#bank-issues-summary').get_by_text('1 khoản cần xử lý',exact=False).wait_for()
    assert '50.000' in page.locator('#bank-issues-summary').inner_text()
    page.locator('[data-action=bank-transaction-resolve]').click()
    assert 'không chuyển tiền hoặc hoàn tiền' in page.locator('#modal').inner_text()
    note=page.locator('#modal-form [name=note]')
    page.locator('#modal-form [type=submit]').click()
    assert note.evaluate('(input)=>input.validity.valueMissing')
    assert not resolutions
    page.locator('#modal-form [name=resolution]').select_option('refunded')
    note.fill('BQL đã chuyển hoàn 50.000đ, chứng từ BANK-REFUND-91.')
    page.locator('#modal-form [type=submit]').click()
    page.wait_for_function("!document.querySelector('#modal').open")
    assert resolutions==[{'resolution':'refunded','note':'BQL đã chuyển hoàn 50.000đ, chứng từ BANK-REFUND-91.'}]
    page.locator('#page tbody').get_by_text('Đã hoàn trả',exact=True).wait_for()
    assert not errors,errors


def test_password_toggle_stays_available_and_auth_copy(browser_page):
    page,cluster,errors=browser_page
    assert 'Đăng nhập để quản lý không gian sống của bạn.' in page.locator('#auth-form').inner_text()
    password=page.locator('#auth-form [name=password]')
    toggle=page.locator('#auth-form [data-action=toggle-password]')
    password.fill('secret1')
    page.locator('#auth-form [name=username]').click()  # blur, then come back
    password.click()
    assert toggle.is_visible()
    toggle.click()
    assert password.get_attribute('type')=='text' and toggle.get_attribute('aria-pressed')=='true'
    toggle.click()
    assert password.get_attribute('type')=='password'
    page.locator('[data-action=auth-switch]').click()
    assert page.locator('#auth-form [name=apartment_code]').get_attribute('placeholder')=='Ví dụ: A101'
    assert page.locator('#auth-form [data-action=toggle-password]').is_visible()
    assert not errors,errors
