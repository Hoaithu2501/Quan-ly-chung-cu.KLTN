"""Browser checks for the QLCC bug sheet of 2026-11-09; run with RUN_BROWSER_TESTS=1."""
import os
import sqlite3

import pytest

from test_browser import browser_page, login, visit  # noqa: F401
from test_bug_sheet_fixes import confirm, overdue_invoice, register_vehicle
from test_resident_memberships import make_apartment, register_resident

pytestmark = pytest.mark.skipif(os.getenv("RUN_BROWSER_TESTS") != "1", reason="Opt in with RUN_BROWSER_TESTS=1")
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
    "0000000b4944415478da6364f80f00010501012718e3660000000049454e44ae426082"
)


def enter(page, username, password):
    page.locator("#auth-form [name=username]").fill(username)
    page.locator("#auth-form [name=password]").fill(password)
    page.locator("#auth-form [type=submit]").click()
    page.locator("#page .page-heading h1").wait_for()
    page.wait_for_function("document.querySelector('#page')?.getAttribute('aria-busy') !== 'true'")


def new_resident(cluster, code, username, confirmed=True):
    apartment_id = make_apartment(cluster, code)
    user_id, profile = register_resident(cluster, code, username)
    if confirmed:
        confirm(cluster, profile, apartment_id)
    return apartment_id, user_id, profile


def test_resident_overview_and_requests(browser_page):
    page, cluster, errors = browser_page
    new_resident(cluster, "UI-101", "ui.resident", confirmed=False)
    with sqlite3.connect(cluster.db_path) as db:
        db.execute("UPDATE notifications SET created_at='2000-01-01 00:00:00'")
    enter(page, "ui.resident", "Membership!2026")
    assert page.locator("#floor-display").count() == 0
    assert "Căn hộ đã được xác nhận" not in page.locator("#page").inner_text()
    assert page.locator(".today-empty").inner_text() == "Hôm nay chưa có thông báo nào"

    visit(page, "parking")
    page.locator("[data-action=parking-request]").click()
    apartment = page.locator("#modal-form [name=apartment_code]")
    assert apartment.input_value() == "UI-101" and apartment.get_attribute("readonly") is not None
    page.locator("[data-action=parking-rules-modal]").click()
    sizes = page.evaluate("[...document.querySelectorAll('#modal .modal-body li, #modal .modal-body p')].map(e => getComputedStyle(e).fontSize)")
    assert len(set(sizes)) == 1, sizes
    page.locator("#modal .modal-footer [data-action=close-modal]").click()
    page.locator("#modal .modal-header [data-action=close-modal]").click()

    visit(page, "complaints")
    page.locator("[data-action=complaint-create]").click()
    assert page.locator("label.file-choose").inner_text().strip() == "Chọn tệp"
    assert page.locator("#field-attachments").is_hidden() or page.locator("#field-attachments").evaluate("e => e.offsetWidth <= 1")
    assert page.locator("#attachment-picks li").count() == 0
    page.locator("#field-attachments").set_input_files([
        {"name": "anh-1.png", "mimeType": "image/png", "buffer": PNG},
        {"name": "anh-2.png", "mimeType": "image/png", "buffer": PNG},
    ])
    assert page.locator("#attachment-picks li span").all_inner_texts() == ["anh-1.png", "anh-2.png"]
    page.locator("#attachment-picks [data-index='0']").click()
    assert page.locator("#attachment-picks li span").all_inner_texts() == ["anh-2.png"]
    page.locator("#modal-form [name=type]").select_option("registration")
    page.locator("#modal-form [name=attachment_links]").wait_for()
    assert page.locator("#attachment-picks li span").all_inner_texts() == ["anh-2.png"]
    page.locator("#modal-form [name=type]").select_option("complaint")
    page.locator("#modal-form [name=attachment_links]").wait_for(state="detached")
    page.locator("#modal-form [name=category]").fill("Tiếng ồn")
    page.locator("#modal-form [name=content]").fill("Ồn về đêm")
    page.locator("#modal-form [type=submit]").click()
    page.wait_for_function("!document.querySelector('#modal')?.open")
    page.locator("[data-action=complaint-edit]").first.wait_for()
    with sqlite3.connect(cluster.db_path) as db:
        identifier, attachments = db.execute("SELECT complaint_id,attachments FROM complaints ORDER BY complaint_id DESC LIMIT 1").fetchone()
    assert "anh-2.png" in attachments and "anh-1.png" not in attachments

    page.locator(f"#page button[data-action=complaint-edit][data-id='{identifier}']").click()
    cancel = page.locator("#modal [data-action=complaint-cancel]")
    cancel.wait_for()
    page.once("dialog", lambda dialog: dialog.accept())
    cancel.click()
    page.wait_for_function("!document.querySelector('#modal')?.open")
    page.locator("#page tr[data-status=cancelled]").wait_for()

    second = page.locator("[data-action=complaint-create]")
    second.click()
    page.locator("#modal-form [name=category]").fill("Vệ sinh")
    page.locator("#modal-form [name=content]").fill("Hành lang bẩn")
    page.locator("#modal-form [type=submit]").click()
    page.wait_for_function("!document.querySelector('#modal')?.open")
    page.locator("#page tr[data-status=pending]").wait_for()
    with sqlite3.connect(cluster.db_path) as db:
        latest = db.execute("SELECT MAX(complaint_id) FROM complaints").fetchone()[0]
        db.execute("UPDATE complaints SET status='processing' WHERE complaint_id=?", (latest,))
    page.locator("[data-action=refresh]").count()
    visit(page, "overview")
    visit(page, "complaints")
    page.locator(f"#page button[data-action=complaint-edit][data-id='{latest}']").click()
    page.locator("#modal .info-box").get_by_text("Đơn đang ở trạng thái đang xử lý không thể huỷ yêu cầu").wait_for()
    assert page.locator("#modal [data-action=complaint-cancel]").count() == 0
    assert not errors, errors


def test_chat_shows_three_questions_from_the_database(browser_page):
    page, cluster, errors = browser_page
    login(page, cluster, "resident")
    page.locator(".support-card [data-route=chatbot]").click(force=True)
    page.locator(".chat-suggestions button").first.wait_for()
    shown = page.locator(".chat-suggestions button").all_inner_texts()
    assert len(shown) == 3 and "Muốn xem hoặc trích xuất camera an ninh thì làm thế nào?" not in shown
    assert not errors, errors


def test_opening_a_notice_updates_the_read_mark_and_the_bell(browser_page):
    page, cluster, errors = browser_page
    login(page, cluster, "admin")
    badge = page.locator("#notification-badge")
    badge.wait_for()
    before = int(badge.inner_text().replace("+", ""))
    visit(page, "notifications")
    card = page.locator(".notice-card:not(.read-mark)").first
    identifier = card.get_attribute("data-id")
    card.click()
    page.locator("#modal[open]").wait_for()
    page.wait_for_function(
        "expected => Number(document.querySelector('#notification-badge').textContent.replace('+','')) === expected",
        arg=before - 1,
    )
    page.locator("#modal .modal-header [data-action=close-modal]").click()
    page.locator(f".notice-card[data-id='{identifier}'].read-mark").wait_for()
    assert not errors, errors


def test_admin_screens_from_the_bug_sheet(browser_page):
    page, cluster, errors = browser_page
    apartment_id, _, _ = new_resident(cluster, "UI-201", "ui.admin.flow")
    vehicle = register_vehicle(cluster, apartment_id, plate="29A1-77777")
    login(page, cluster, "admin")
    icon = page.locator(".nav a.active svg")
    assert icon.evaluate("e => getComputedStyle(e).borderRadius") == "50%"
    assert "gradient" in icon.evaluate("e => getComputedStyle(e).backgroundImage")
    visit(page, "apartments")
    page.locator("[data-action=apartment-create]").click()
    floor = page.locator("#modal-form [name=floor]")
    assert floor.get_attribute("type") == "text"
    for value, valid in (("0", False), ("-1", False), ("12", True)):
        floor.fill(value)
        assert floor.evaluate("e => e.checkValidity()") is valid, value
    area = page.locator("#modal-form [name=area]")
    area.fill("0")
    assert not area.evaluate("e => e.checkValidity()")
    page.locator("#modal .modal-header [data-action=close-modal]").click()
    page.locator("#table-search").fill("UI-201")
    row = page.locator("#page tbody tr:not([hidden])")
    assert "Đã có cư dân" in row.inner_text()
    row.locator("[data-action=apartment-detail]").click()
    page.locator("#modal [data-action=apartment-edit]").click()
    page.locator("#modal-form [name=code]").wait_for()
    assert page.locator("#modal-form [name=code]").input_value() == "UI-201"
    page.locator("#modal .modal-header [data-action=close-modal]").click()

    visit(page, "complaints")
    assert page.locator("[data-action=complaint-create]").count() == 0

    visit(page, "parking")
    page.locator(f"[data-action=vehicle-edit][data-id='{vehicle['vehicle_id']}']").click()
    assert page.locator("#modal-form [name=registration_months]").get_attribute("min") == "2"
    page.locator("#modal .modal-header [data-action=close-modal]").click()
    page.locator(f"[data-action=vehicle-renew][data-id='{vehicle['vehicle_id']}']").click()
    page.locator("#modal-form [name=months]").fill("3")
    page.locator("#modal-form [type=submit]").click()
    page.wait_for_function("!document.querySelector('#modal')?.open")
    page.locator(f"[data-action=vehicle-supplement][data-id='{vehicle['vehicle_id']}']").click()
    page.locator("#modal .info-box").wait_for()
    assert "chưa phát hành" in page.locator("#modal .info-box").inner_text()
    page.locator("#modal .modal-footer [data-action=close-modal]").click()

    page.locator("[data-action=tab][data-tab=guest]").click()
    page.locator("[data-action=guest-create]").wait_for()

    visit(page, "maintenance")
    page.locator("[data-action=ticket-create]").click()
    # Free text for an apartment or a place: no suggestion list, so no dropdown arrow.
    assert page.locator("#modal-form [name=location]").get_attribute("list") is None
    page.locator("#modal-form [name=location]").fill("Sảnh tòa A")
    page.locator("#modal-form [name=description]").fill("Hỏng đèn sảnh")
    page.locator("#modal-form [type=submit]").click()
    page.wait_for_function("!document.querySelector('#modal')?.open")
    page.locator("#table-search").fill("Sảnh tòa A")
    assert "Sảnh tòa A" in page.locator("#page tbody tr:not([hidden])").first.inner_text()

    visit(page, "users")
    assert page.locator("[data-action=user-create]").count() == 0
    assert page.locator("[data-action=technician-create]").count() == 0
    page.locator("[data-action=user-edit]").first.click()
    assert page.locator("#modal-form select").count() == 1
    assert page.locator("#modal-form [name=role]").count() == 1
    assert page.locator("#modal-form [name=password]").count() == 0
    page.locator("#modal .modal-header [data-action=close-modal]").click()
    page.locator("[data-action=tab][data-tab=technicians]").click()
    page.locator("[data-action=technician-edit]").first.wait_for()
    assert page.locator("[data-action=technician-create]").count() == 0
    # The technician's account is shown, never picked from an empty list.
    page.locator("[data-action=technician-edit]").first.click()
    page.locator("#modal-form [name=full_name]").wait_for()
    assert page.locator("#modal-form [name=user_id]").count() == 0
    assert page.locator("#modal-form select").count() == 1  # Specialty only.
    page.locator("#modal .modal-header [data-action=close-modal]").click()
    assert not errors, errors


def test_billing_cards_searches_and_image_receipt(browser_page):
    page, cluster, errors = browser_page
    apartment_id = make_apartment(cluster, "UI-301")
    created = cluster.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": apartment_id, "period": "2097-05", "electricity_fee": 300, "water_fee": 200, "due_date": "2097-06-01"})
    assert created.status_code == 201, created.text
    payment = cluster.call("billing", f"/api/billing/invoices/monthly/{created.json()['invoice_id']}/pay", "POST",
                           json={"payment_method": "cash", "transaction_code": "MA-GD-UI-301"})
    assert payment.status_code == 201, payment.text
    login(page, cluster, "admin")
    visit(page, "billing")
    cards = page.locator("#page .stat-card").all_inner_texts()
    paid_card = next(card for card in cards if "Đã thanh toán (trong tháng)" in card)
    assert "₫" in paid_card.split("\n")[-1] and paid_card.split("\n")[-2].strip().isdigit()
    page.locator("#table-search").fill("UI-301")
    assert page.locator("#page tbody tr:not([hidden])").count() == 1
    page.locator("[data-action=tab][data-tab=payments]").click()
    page.locator("[data-action=receipt]").first.wait_for()
    page.locator("#table-search").fill("ma-gd-ui-301")
    visible = page.locator("#page tbody tr:not([hidden])")
    assert visible.count() == 1
    with page.expect_download() as download:
        visible.locator("[data-action=receipt]").click()
    assert download.value.suggested_filename.endswith(".png")
    with open(download.value.path(), "rb") as handle:
        assert handle.read(8) == bytes.fromhex("89504e470d0a1a0a")
    page.locator("#table-search").fill("UI-301")
    assert page.locator("#page tbody tr:not([hidden])").count() == 1
    assert not errors, errors


def test_technician_service_screen_and_guest_update(browser_page):
    page, cluster, errors = browser_page
    apartment_id, _, _ = new_resident(cluster, "UI-401", "ui.service")
    invoice = overdue_invoice(cluster, apartment_id)
    login(page, cluster, "technician")
    created = cluster.call("parking", "/api/parking/guest-daily", "POST", role="technician",
                           json={"parking_date": "2020-03-04", "daily_revenue": 1000})
    assert created.status_code == 201, created.text
    visit(page, "parking")
    page.locator("#table-search").fill("04/03/2020")
    row = page.locator("#page tbody tr:not([hidden])")
    assert row.count() == 1
    row.locator("[data-action=guest-edit]").click()
    page.locator("#modal-form [name=daily_revenue]").fill("2500")
    page.locator("#modal-form [type=submit]").click()
    page.wait_for_function("!document.querySelector('#modal')?.open")
    page.locator("#page tbody").get_by_text("2.500").first.wait_for()

    visit(page, "services")
    cut = page.locator(f"[data-action=service-cut][data-id='{invoice}'][data-service=electricity]")
    cut.wait_for()
    page.once("dialog", lambda dialog: dialog.accept())
    cut.click()
    page.locator("#page .badge.red").get_by_text("Đã cắt điện").wait_for()
    assert cluster.call("billing", f"/api/billing/invoices/monthly/{invoice}/pay", "POST", json={"payment_method": "cash"}).status_code == 201
    visit(page, "overview")
    visit(page, "services")
    restore = page.locator(f"[data-action=service-restore][data-id='{invoice}'][data-service=electricity]")
    restore.wait_for()
    page.once("dialog", lambda dialog: dialog.accept())
    restore.click()
    page.wait_for_function("id => !document.querySelector(`[data-action=service-restore][data-id='${id}']`)", arg=str(invoice))
    page.locator("[data-action=logout]").click()
    login(page, cluster, "admin")
    visit(page, "billing")
    page.locator("#table-search").fill("UI-401")
    page.locator("#page tbody tr:not([hidden]) [data-action=invoice-detail]").click()
    page.locator("#modal[open] .detail-list").wait_for()
    text = page.locator("#modal .detail-list").inner_text()
    assert "Dịch vụ điện" in text and "Đã cấp lại" in text and "Không bị cắt" in text
    assert not errors, errors


def test_technician_invoice_tab_vehicle_lines_and_immediate_overdue(browser_page):
    page, cluster, errors = browser_page
    apartment_id, _, _ = new_resident(cluster, "UI-501", "ui.vehicle.lines")
    register_vehicle(cluster, apartment_id, plate="29A1-50501", registered="2026-08-15")
    for kind, payload in (
        ("semiannual", {"period": "2026-H2", "service_fee": 1000, "due_date": "2099-01-01"}),
        ("monthly", {"period": "2001-01", "electricity_fee": 300, "water_fee": 200, "due_date": "2001-02-01"}),
    ):
        created = cluster.call("billing", f"/api/billing/invoices/{kind}", "POST", json={"apartment_id": apartment_id, **payload})
        assert created.status_code == 201, created.text
    login(page, cluster, "technician")
    visit(page, "notifications")
    assert page.locator("[data-action=notice-create]").count() == 0
    visit(page, "billing")
    assert page.locator("#page .page-heading h1").inner_text() == "Quản lý hóa đơn"
    # The same management screen as admin's.
    assert page.locator("#page [data-action=invoice-create]").count() == 1
    assert page.locator("[data-action=tab][data-tab=bank-transactions]").count() == 1
    page.locator("#table-search").fill("UI-501")
    assert "Quá hạn" in page.locator("#page tbody tr:not([hidden])").first.inner_text()
    page.locator("[data-action=tab][data-tab=semiannual]").click()
    page.locator("#page [data-action=invoice-detail][data-kind=semiannual]").first.wait_for()
    page.locator("#table-search").fill("UI-501")
    page.locator("#page tbody tr:not([hidden]) [data-action=invoice-detail]").click()
    page.locator("#modal[open] .detail-list").wait_for()
    lines = page.locator("#modal[open] .data-table")
    assert lines.count() == 1, page.locator("#modal").inner_text()
    text = lines.inner_text()
    for part in ("29A1-50501", "4 tháng", "15/08/2026", "15/12/2026", "5 tháng"):
        assert part in text, part
    # A technician records money received, as management does.
    page.locator("#modal [data-action=invoice-cash]").click()
    page.locator("#modal-form [name=transaction_code]").fill("TECH-UI-501")
    page.locator("#modal-form [type=submit]").click()
    page.wait_for_function("!document.querySelector('#modal')?.open")
    rows = cluster.call("billing", "/api/billing/invoices/semiannual").json()["items"]
    assert next(row for row in rows if row["apartment_id"] == apartment_id)["status"] == "paid"
    assert not errors, errors
