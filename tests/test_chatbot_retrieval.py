"""Regression cases for intent-aware retrieval, using the reviewed seed in memory."""
import sqlite3
import unicodedata
from pathlib import Path

import pytest

from shared.chatbot_retrieval import normalize, retrieve


@pytest.fixture
def knowledge():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE faq_knowledge_base(faq_id INTEGER PRIMARY KEY, category TEXT, question TEXT, answer TEXT)")
    db.executemany("INSERT INTO faq_knowledge_base(category, question, answer) VALUES (?, ?, ?)", [
        ("Nội quy", "Có được nuôi thú cưng trong chung cư không?", "Được nuôi thú cưng theo nội quy đã ban hành."),
        ("Gửi xe", "Có chỗ đậu xe cho khách không?", "Khách liên hệ bảo vệ để được hướng dẫn gửi xe."),
        ("Liên hệ", "Giờ làm việc của văn phòng Ban quản lý?", "Xem giờ làm việc trong thông báo hiện hành."),
        ("An toàn", "Khi có cháy phải làm gì?", "Nhấn báo cháy, báo lực lượng cứu hộ và thoát theo lối an toàn."),
        ("An toàn", "Quy định phòng cháy chữa cháy trong chung cư?", "Giữ các lối thoát hiểm thông thoáng."),
    ])
    sql = Path(__file__).resolve().parents[1] / "scripts/sql/chatbot_faq_v3.sql"
    db.executescript(sql.read_text(encoding="utf-8"))
    faqs = [dict(row) for row in db.execute("SELECT * FROM faq_knowledge_base")]
    db.close()
    locations = [
        {"location_id": 1, "name": "Hiệu thuốc", "block": "A", "floor": "1", "description": "Nhà thuốc phục vụ cư dân."},
        {"location_id": 2, "name": "Văn phòng Ban quản lý", "block": "B", "floor": "1", "description": "Nơi tiếp nhận yêu cầu của cư dân."},
        {"location_id": 3, "name": "Bãi gửi xe vãng lai", "block": "B", "floor": "B1", "description": "Khu gửi xe dành cho khách."},
        {"location_id": 4, "name": "Phòng gym", "block": "A", "floor": "2", "description": "Phòng tập thể dục."},
    ]
    return faqs, locations


@pytest.mark.parametrize(("question", "expected"), [
    ("Phí gửi xe bao nhiêu?", "Phí gửi xe tháng và phí làm thẻ là bao nhiêu?"),
    ("Gui xe may gia bao nhieu?", "Phí gửi xe tháng và phí làm thẻ là bao nhiêu?"),
    ("Hóa đơn quá hạn thì sao?", "Nếu thanh toán quá hạn thì sao?"),
    ("Hoa don tre han thi sao?", "Nếu thanh toán quá hạn thì sao?"),
    ("Số điện thoại Ban quản lý?", "Số hotline của chung cư là gì?"),
    ("Hotline?", "Số hotline của chung cư là gì?"),
    ("Thanh toán bằng cách nào?", "Có những hình thức thanh toán nào?"),
    ("Xem lịch sử thanh toán?", "Làm sao để tra cứu lịch sử thanh toán?"),
    ("Hạn thanh toán hóa đơn?", "Hạn thanh toán hoá đơn điện nước hằng tháng là ngày nào?"),
    ("Hóa đơn phát hành khi nào?", "Hoá đơn điện nước được phát hành khi nào?"),
    ("Co duoc nuoi thu cung khong?", "Có được nuôi thú cưng trong chung cư không?"),
])
def test_specific_intent_wins_over_broad_topic(knowledge, question, expected):
    result = retrieve(question, *knowledge)
    assert result["selected"], question
    assert result["selected"][0]["source_title"] == expected
    assert result["selected"][0]["confidence"] >= 0.48


@pytest.mark.parametrize("question", [
    "gửi xe điện hết bao nhiêu tiền",
    "gui xe dien het bao nhieu tien",
    "gửi xe máy điện một tháng tốn mấy tiền",
    "gui xe may dien mot thang ton may tien",
    "gửi xe đạp điện mất nhiêu tiền",
    "gui xe dap dien mat nhieu tien",
    "để xe điện ở đây mỗi tháng hết mấy đồng",
    "mình muốn biết gửi xe đạp điện một tháng tốn bao nhiêu",
    "tiền gửi xe đạp điện một tháng là bao nhiêu",
    "cho em hỏi gửi xe điện hết bao nhiêu tiền với ạ",
    "đỗ xe máy điện ở chung cư hết bao nhiêu tiền",
    "do xe may dien o chung cu het bao nhieu tien",
])
def test_electric_vehicle_price_understands_natural_paraphrases(knowledge, question):
    result = retrieve(question, *knowledge)
    assert result["selected"], question
    selected = result["selected"][0]
    assert selected["source_title"] == "Phí gửi xe tháng và phí làm thẻ là bao nhiêu?"
    assert "xe dien" in normalize(selected["answer"])
    assert "100 000 dong thang" in normalize(selected["answer"])
    assert not result["needs_clarification"]


@pytest.mark.parametrize("question", [
    "xe đạp điện được để ở chung cư không",
    "xe dap dien duoc de o chung cu khong",
    "xe máy điện có được gửi trong hầm không",
    "xe may dien co duoc gui trong ham khong",
    "ở đây có nhận giữ xe đạp điện không",
    "mình có thể gửi xe máy điện ở chung cư được chứ",
    "chung cư có cho gửi ô tô không",
])
def test_vehicle_eligibility_is_distinct_from_price(knowledge, question):
    result = retrieve(question, *knowledge)
    assert result["selected"], question
    selected = result["selected"][0]
    assert selected["source_title"] == "Chung cư nhận gửi những loại xe nào?"
    answer = normalize(selected["answer"])
    assert all(term in answer for term in ("xe may", "xe dien", "xe dap", "khong nhan o to"))
    assert not result["needs_clarification"]


@pytest.mark.parametrize("question", [
    "gửi xe đạp điện hết bao nhiêu tiền",
    "gui xe dap dien het bao nhieu tien",
])
def test_electric_bicycle_does_not_select_ordinary_bicycle_tariff(knowledge, question):
    faqs, locations = knowledge
    faqs = faqs + [{
        "faq_id": 1001,
        "category": "Gửi xe",
        "question": "Phí gửi xe đạp là bao nhiêu?",
        "answer": "Xe đạp thường: 50.000 đồng/tháng.",
    }]
    result = retrieve(question, faqs, locations)
    assert result["selected"], question
    assert result["selected"][0]["source_title"] == "Phí gửi xe tháng và phí làm thẻ là bao nhiêu?"
    assert all(match["source_id"] != 1001 for match in result["matches"])


@pytest.mark.parametrize("question", [
    "mua xe đạp điện hết bao nhiêu tiền",
    "mua xe may dien mot chiec ton may tien",
    "thay pin xe điện mất bao nhiêu tiền",
    "sạc xe điện dưới hầm hết bao nhiêu tiền",
    "độ xe điện hết bao nhiêu tiền",
    "có được chạy xe điện trong chung cư không",
    "co duoc chay xe dien trong chung cu khong",
    "xe điện trong chung cư có được chạy không",
    "xe dien trong chung cu co duoc chay khong",
    "xe điện đó có được không",
    "xe dien do co duoc khong",
])
def test_electric_vehicle_money_question_is_not_always_a_parking_fee(knowledge, question):
    result = retrieve(question, *knowledge)
    assert result["selected"] == []
    assert result["matches"] == []


@pytest.mark.parametrize("question", [
    "xe dien de di cho co duoc khong",
    "xe điện để đi chợ có được không",
    "xe dap dien de tap the duc co duoc khong",
    "xe đạp điện để tập thể dục có được không",
    "co the dung xe dien de di lai khong",
    "có thể dùng xe điện để đi lại không",
])
def test_vehicle_use_purpose_is_not_parking_permission(knowledge, question):
    result = retrieve(question, *knowledge)
    assert result["selected"] == []
    assert result["matches"] == []


@pytest.mark.parametrize("question", [
    "xe dap dien duoc de tren san thuong khong",
    "xe đạp điện được để trên sân thượng không",
    "xe dap dien duoc de o can ho khong",
    "xe đạp điện được để ở căn hộ không",
])
def test_allowed_vehicle_types_do_not_grant_storage_at_other_locations(knowledge, question):
    result = retrieve(question, *knowledge)
    assert result["selected"] == []
    assert result["matches"] == []


@pytest.mark.parametrize("question", [
    "khách đến chơi có chỗ gửi xe không",
    "khach den choi co cho gui xe khong",
])
def test_guest_parking_keeps_visitor_guidance(knowledge, question):
    result = retrieve(question, *knowledge)
    assert result["selected"], question
    assert result["selected"][0]["source_title"] == "Có chỗ đậu xe cho khách không?"


@pytest.mark.parametrize("question", [
    "Tốc độ ánh sáng trong chân không?", "Địa chỉ email Ban quản lý?",
    "Xe máy màu xanh của tôi bao nhiêu mã lực?", "Mua cổ phiếu nào?",
    "Tỷ giá đồng đô la hôm nay?", "Đóng tiền học trường đại học nào?",
])
def test_broad_keywords_do_not_invent_answers(knowledge, question):
    result = retrieve(question, *knowledge)
    assert result["matches"] == []
    assert result["selected"] == []


def test_locations_only_use_location_records(knowledge):
    faqs, locations = knowledge
    faqs.append({"faq_id": 1000, "question": "Hiệu thuốc ở đâu?", "category": "Vị trí", "answer": "Old FAQ says tầng 99."})
    result = retrieve("Hieu thuoc o dau?", faqs, locations)
    assert result["selected"][0]["source"] == "location"
    assert "tầng 1" in result["selected"][0]["answer"]
    assert all(match["source"] == "location" for match in result["matches"])
    assert retrieve("Hồ bơi ở đâu?", faqs, locations)["matches"] == []


def test_application_navigation_is_not_physical_location(knowledge):
    result = retrieve("Xem lịch sử thanh toán ở đâu?", *knowledge)
    assert result["selected"][0]["source"] == "faq"
    assert "lịch sử" in result["selected"][0]["source_title"]


def test_distinct_questions_select_distinct_relevant_answers(knowledge):
    result = retrieve("Phí gửi xe bao nhiêu và số hotline là gì?", *knowledge)
    titles = {match["source_title"] for match in result["selected"]}
    assert titles == {"Phí gửi xe tháng và phí làm thẻ là bao nhiêu?", "Số hotline của chung cư là gì?"}
    assert len(result["matches"]) <= 5


def test_rent_is_not_silently_reinterpreted_as_service_fee(knowledge):
    result = retrieve("Tiền nhà tháng này bao nhiêu?", *knowledge)
    assert result["needs_clarification"]
    assert "thuê" in result["clarification"] and "dịch vụ" in result["clarification"]
    assert result["selected"] == result["matches"] == []


def test_fire_emergency_prioritizes_action_over_policy(knowledge):
    result = retrieve("Có cháy ở hành lang phải làm gì?", *knowledge)
    assert result["emergency"]
    assert result["selected"][0]["source_title"] == "Khi có cháy phải làm gì?"


@pytest.mark.parametrize("question", [
    "Có cháy, tôi còn hóa đơn chưa thanh toán",
    "Có cháy và phí gửi xe bao nhiêu?",
    "Có cháy, tiền nhà tháng này bao nhiêu?",
])
def test_compound_emergency_never_selects_routine_payment_or_parking(knowledge, question):
    result = retrieve(question, *knowledge)
    assert result["emergency"]
    assert not result["needs_clarification"]
    assert {match["source_title"] for match in result["selected"]} == {"Khi có cháy phải làm gì?"}
    assert all(match["source_title"] == "Khi có cháy phải làm gì?" for match in result["matches"])


@pytest.mark.parametrize("question", [
    "Có cháy, tôi còn hóa đơn chưa thanh toán",
    "Có cháy và phí gửi xe bao nhiêu?",
    "Có rò điện và tôi chưa thanh toán hóa đơn",
])
def test_emergency_without_managed_incident_answer_returns_empty_for_safe_fallback(knowledge, question):
    faqs, locations = knowledge
    faqs = [row for row in faqs if row["question"] != "Khi có cháy phải làm gì?"]
    result = retrieve(question, faqs, locations)
    assert result["emergency"]
    assert result["selected"] == result["matches"] == []


def test_electrical_incident_does_not_select_unrelated_fire_guidance(knowledge):
    result = retrieve("Có rò điện, hóa đơn điện nước phát hành khi nào?", *knowledge)
    assert result["emergency"]
    assert result["selected"] == result["matches"] == []


@pytest.mark.parametrize("question", ["Quy định phòng cháy chữa cháy?", "Có được chạy bộ ở đây không?", "Co chay bo o day duoc khong?", "Phòng tránh điện giật như thế nào?", "Số điện thoại Ban quản lý?"])
def test_normal_policy_or_exercise_does_not_trigger_emergency(knowledge, question):
    assert retrieve(question, *knowledge)["emergency"] is False


def test_unicode_combining_accents_and_capitals(knowledge):
    question = unicodedata.normalize("NFD", "SỐ ĐIỆN THOẠI BAN QUẢN LÝ?")
    assert normalize(question) == "so dien thoai ban quan ly"
    assert retrieve(question, *knowledge)["selected"][0]["source_title"] == "Số hotline của chung cư là gì?"
