"""Assistant provider boundaries and authenticated API contracts, without live LLM calls."""
import importlib.util
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
import requests

from shared import chatbot_llm, chatbot_resident
from shared.web import APIError


ROOT = Path(__file__).resolve().parents[1]
TEST_SECRET = "chatbot-contract-test-jwt-secret-with-32-characters"
API_KEY = "test-provider-key-never-forward-user-credentials"
PRICE = {
    "source": "faq", "source_id": 12,
    "source_title": "Phí gửi xe bao nhiêu?",
    "answer": "Xe máy và xe điện: 100.000 đồng/tháng. Xe đạp: 50.000 đồng/tháng.",
    "confidence": 0.95,
}
HOTLINE = {
    "source": "faq", "source_id": 13,
    "source_title": "Hotline Ban quản lý?",
    "answer": "Hotline Ban quản lý: 0228913665.",
    "confidence": 0.9,
}


@pytest.fixture
def llm_config(monkeypatch):
    monkeypatch.setenv("LLM_API_URL", "https://llm.example.test/v1/chat/completions")
    monkeypatch.setenv("LLM_API_KEY", API_KEY)
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "8")
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)


def provider_response(answer=PRICE["answer"], source_ids=None, **overrides):
    content = json.dumps({"answer": answer, "source_ids": source_ids or ["faq:12"]}, ensure_ascii=False)
    choice = {"finish_reason": "stop", "message": {"content": content}}
    choice.update(overrides)
    return SimpleNamespace(status_code=200, json=lambda: {"choices": [choice]})


def test_grounded_rewrite_has_bounded_request_and_only_allowed_sources(llm_config, monkeypatch):
    captured = {}

    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return provider_response("Xe máy và xe điện có phí 100.000 đồng/tháng.")

    monkeypatch.setattr(chatbot_llm.requests, "post", post)
    result = chatbot_llm.rewrite_answer("Phí gửi xe bao nhiêu?", [PRICE])
    assert result == {"answer": "Xe máy và xe điện có phí 100.000 đồng/tháng.", "source_ids": ["faq:12"]}
    assert captured["url"] == "https://llm.example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer " + API_KEY
    assert captured["timeout"] == (3, 8)
    assert captured["allow_redirects"] is False
    payload = captured["json"]
    assert payload["model"] == "test-model"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["max_completion_tokens"] <= 1000
    assert [message["role"] for message in payload["messages"]] == ["system", "user"]
    source_payload = json.loads(payload["messages"][1]["content"])
    assert source_payload == {
        "question": "Phí gửi xe bao nhiêu?",
        "sources": [{"id": "faq:12", "source": "faq", "source_title": PRICE["source_title"], "answer": PRICE["answer"]}],
    }
    assert API_KEY not in json.dumps(payload)


@pytest.mark.parametrize("effort", [None, "", "none", "minimal"])
def test_reasoning_effort_is_sent_only_when_explicitly_configured(llm_config, monkeypatch, effort):
    if effort is not None:
        monkeypatch.setenv("LLM_REASONING_EFFORT", effort)
    captured = []

    def post(url, **kwargs):
        captured.append(kwargs["json"])
        return provider_response()

    monkeypatch.setattr(chatbot_llm.requests, "post", post)
    assert chatbot_llm.rewrite_answer("Phí gửi xe?", [PRICE]) == {
        "answer": PRICE["answer"], "source_ids": ["faq:12"],
    }
    assert len(captured) == 1
    if effort:
        assert captured[0]["reasoning_effort"] == effort
    else:
        assert "reasoning_effort" not in captured[0]


def test_invalid_reasoning_effort_uses_fallback_without_provider_call(llm_config, monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "unsupported-setting")
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: pytest.fail("invalid reasoning setting reached provider"))
    assert chatbot_llm.rewrite_answer("Phí gửi xe?", [PRICE]) is None


@pytest.mark.parametrize("setting,value", [
    ("LLM_API_KEY", ""), ("LLM_MODEL", ""), ("LLM_API_URL", ""),
    ("LLM_API_URL", "http://llm.example.test/v1/chat/completions"),
    ("LLM_API_URL", "https://user:password@llm.example.test/v1/chat/completions"),
    ("LLM_API_URL", "https://llm.example.test/v1/chat/completions?api_key=secret"),
    ("LLM_TIMEOUT_SECONDS", "nan"), ("LLM_TIMEOUT_SECONDS", "60"),
])
def test_missing_or_invalid_provider_configuration_does_not_call_network(llm_config, monkeypatch, setting, value):
    monkeypatch.setenv(setting, value)
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: pytest.fail("invalid configuration reached provider"))
    assert chatbot_llm.rewrite_answer("Phí gửi xe?", [PRICE]) is None


@pytest.mark.parametrize("response", [
    SimpleNamespace(status_code=401, json=lambda: {}),
    SimpleNamespace(status_code=429, json=lambda: {}),
    SimpleNamespace(status_code=503, json=lambda: {}),
    SimpleNamespace(status_code=302, json=lambda: {}),
    SimpleNamespace(status_code=200, json=lambda: None),
    SimpleNamespace(status_code=200, json=lambda: {"choices": []}),
    SimpleNamespace(status_code=200, json=lambda: {"choices": [None]}),
    SimpleNamespace(status_code=200, json=lambda: {"choices": ["unstructured response"]}),
    SimpleNamespace(status_code=200, json=lambda: {"choices": [{"finish_reason": "stop", "message": {"content": "not JSON"}}]}),
    provider_response(finish_reason="length"),
    provider_response(message={"content": json.dumps({"answer": "Phí gửi xe.", "source_ids": []})}),
    provider_response(message={"content": json.dumps({"answer": [], "source_ids": ["faq:12"]})}),
    provider_response(message={"content": json.dumps(["not an object"])}),
    provider_response(message={"content": None}),
])
def test_provider_failure_or_malformed_response_falls_back(llm_config, monkeypatch, response):
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: response)
    assert chatbot_llm.rewrite_answer("Phí gửi xe?", [PRICE]) is None


def test_timeout_falls_back_without_retry(llm_config, monkeypatch):
    attempts = []

    def timeout(*args, **kwargs):
        attempts.append(1)
        raise requests.Timeout("provider unavailable")

    monkeypatch.setattr(chatbot_llm.requests, "post", timeout)
    assert chatbot_llm.rewrite_answer("Phí gửi xe?", [PRICE]) is None
    assert len(attempts) == 1


@pytest.mark.parametrize("answer,citations", [
    ("Phí xe máy là 200.000 đồng/tháng.", ["faq:12"]),
    ("Hotline là 0228913665.", ["faq:12"]),
    (PRICE["answer"], ["faq:999"]),
    ("Đóng tiền tại https://example.test/pay", ["faq:12"]),
    ("<script>alert('pay')</script>", ["faq:12"]),
    ("Khóa hệ thống là " + API_KEY, ["faq:12"]),
])
def test_unsupported_facts_citations_and_unsafe_output_fall_back(llm_config, monkeypatch, answer, citations):
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: provider_response(answer, citations))
    # A fact present in another retrieved source is not enough: it must be cited.
    assert chatbot_llm.rewrite_answer("Phí gửi xe?", [PRICE, HOTLINE]) is None


def test_provider_receives_maximum_five_complete_sources(llm_config, monkeypatch):
    captured = []

    def post(url, **kwargs):
        captured.append(json.loads(kwargs["json"]["messages"][1]["content"])["sources"])
        return provider_response()

    monkeypatch.setattr(chatbot_llm.requests, "post", post)
    matches = [dict(PRICE, source_id=12 + index) for index in range(8)]
    assert chatbot_llm.rewrite_answer("Phí gửi xe?", matches)
    assert len(captured[0]) == 5
    assert chatbot_llm.rewrite_answer("Phí gửi xe?", [dict(PRICE, answer="a" * 6001)]) is None
    assert len(captured) == 1


@pytest.mark.parametrize("role,enabled", [("resident", "false"), ("admin", "true"), ("technician", "true")])
def test_personal_context_is_opt_in_and_resident_only(monkeypatch, role, enabled):
    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", enabled)
    monkeypatch.setattr(chatbot_resident, "call_service", lambda *args, **kwargs: pytest.fail("invoice data must not be fetched"))
    result = chatbot_resident.resident_reply("Hóa đơn của tôi còn nợ bao nhiêu?", {"role": role, "user_id": 3})
    assert "Hóa đơn & thanh toán" in result["answer"]
    assert result["verified"] is False


def test_personal_context_does_not_lookup_generic_payment_instructions(monkeypatch):
    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "true")
    monkeypatch.setattr(chatbot_resident, "call_service", lambda *args, **kwargs: pytest.fail("generic guidance must not fetch private data"))
    assert chatbot_resident.resident_reply("Thanh toán bằng hình thức nào?", {"role": "resident", "user_id": 3}) is None


@pytest.mark.parametrize("status", [401, 403])
def test_personal_context_propagates_revocation_instead_of_confirming_balance(monkeypatch, status):
    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "true")

    def denied(*args, **kwargs):
        raise APIError("No permission", status)

    monkeypatch.setattr(chatbot_resident, "call_service", denied)
    with pytest.raises(APIError) as caught:
        chatbot_resident.resident_reply("Hóa đơn của tôi còn nợ bao nhiêu?", {"role": "resident", "user_id": 3})
    assert caught.value.status == status


@pytest.mark.parametrize("response", [{}, {"items": None}, {"items": [None]}, {"items": [{"total_amount": "999999"}]}])
def test_personal_context_invalid_data_never_asserts_paid_or_zero_balance(monkeypatch, response):
    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "true")
    monkeypatch.setattr(chatbot_resident, "call_service", lambda *args, **kwargs: response)
    result = chatbot_resident.resident_reply("Hóa đơn của tôi còn nợ bao nhiêu?", {"role": "resident", "user_id": 3})
    assert "chưa đủ" in result["answer"]
    assert "999999" not in result["answer"]
    assert result["verified"] is False


def test_personal_context_service_outage_does_not_guess_invoice_state(monkeypatch):
    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "true")

    def unavailable(*args, **kwargs):
        raise APIError("Unavailable", 503)

    monkeypatch.setattr(chatbot_resident, "call_service", unavailable)
    result = chatbot_resident.resident_reply("Hóa đơn của tôi còn nợ bao nhiêu?", {"role": "resident", "user_id": 3})
    assert "chưa thể xác nhận" in result["answer"]
    assert result["verified"] is False


@pytest.fixture
def assistant_client(tmp_path, monkeypatch):
    database = tmp_path / "chatbot.db"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE faq_knowledge_base (
                faq_id INTEGER PRIMARY KEY, category TEXT, question TEXT NOT NULL, answer TEXT NOT NULL
            );
            CREATE TABLE locations (
                location_id INTEGER PRIMARY KEY, name TEXT NOT NULL, block TEXT, floor TEXT, description TEXT
            );
        """)
        connection.executemany(
            "INSERT INTO faq_knowledge_base VALUES (?,?,?,?)",
            [(12, "Gửi xe", PRICE["source_title"], PRICE["answer"]),
             (13, "Liên hệ", HOTLINE["source_title"], HOTLINE["answer"])]
        )
        connection.execute("INSERT INTO locations VALUES (1,'Hiệu thuốc','A','1','Mở cửa hằng ngày.')")
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "false")
    spec = importlib.util.spec_from_file_location("chatbot_contract_app", ROOT / "chatbot-service/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = module.create_app()
    app.config.update(TESTING=True, DATABASE_PATH=str(database))

    def authenticate(service, path, **kwargs):
        assert (service, path) == ("auth", "/api/auth/me")
        return {"user": {"user_id": 3, "role": "resident", "username": "private-resident-name"}}

    monkeypatch.setattr("shared.http.call_service", authenticate)
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "3", "role": "resident", "username": "private-resident-name",
                        "iss": "qlcc-auth", "iat": now, "exp": now + timedelta(hours=1)}, TEST_SECRET, algorithm="HS256")
    client = app.test_client()
    headers = {"Authorization": "Bearer " + token}
    return SimpleNamespace(module=module, client=client, headers=headers, token=token)


def ask(assistant, question, **extra):
    return assistant.client.post("/api/chatbot/ask", headers=assistant.headers, json={"question": question, **extra})


def test_api_without_provider_keeps_existing_answer_and_source_contract(assistant_client, monkeypatch):
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: pytest.fail("missing key must use local FAQ"))
    response = ask(assistant_client, "Phí gửi xe bao nhiêu?")
    assert response.status_code == 200
    result = response.get_json()
    assert result["matched"] is True
    assert result["answer"] == PRICE["answer"]
    assert result["source"] == "faq"
    assert result["source_id"] == 12
    assert result["source_title"] == PRICE["source_title"]
    assert 0.48 <= result["confidence"] <= 1
    assert result["sources"][0]["source_id"] == 12
    assert result["engine"] != "llm"


def test_api_grounded_rewrite_never_sends_jwt_or_profile_to_provider(assistant_client, llm_config, monkeypatch):
    captured = []

    def post(url, **kwargs):
        captured.append(kwargs)
        return provider_response("Xe máy và xe điện có phí 100.000 đồng/tháng.")

    monkeypatch.setattr(chatbot_llm.requests, "post", post)
    response = ask(assistant_client, "Phí gửi xe bao nhiêu?")
    assert response.status_code == 200
    result = response.get_json()
    assert result["engine"] == "llm"
    assert result["source"] == "faq" and result["source_id"] == 12
    assert result["answer"] == "Xe máy và xe điện có phí 100.000 đồng/tháng."
    assert len(captured) == 1
    serialized = json.dumps(captured[0], ensure_ascii=False)
    assert assistant_client.token not in serialized
    assert "private-resident-name" not in serialized
    assert TEST_SECRET not in serialized
    assert captured[0]["headers"]["Authorization"] == "Bearer " + API_KEY


def test_api_provider_timeout_returns_managed_content_with_http_success(assistant_client, llm_config, monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.Timeout("temporary failure")

    monkeypatch.setattr(chatbot_llm.requests, "post", timeout)
    response = ask(assistant_client, "Phí gửi xe bao nhiêu?")
    assert response.status_code == 200
    result = response.get_json()
    assert result["answer"] == PRICE["answer"]
    assert result["matched"] is True and result["source_id"] == 12
    assert result["engine"] != "llm"


@pytest.mark.parametrize("question,expected", [
    ("Tiền nhà bao nhiêu?", "tiền thuê"),
    ("Tốc độ ánh sáng trong chân không?", "chưa"),
    ("Có cháy ở tầng hầm!", "đừng chờ"),
])
def test_api_clarification_unknown_and_emergency_skip_llm(assistant_client, llm_config, monkeypatch, question, expected):
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: pytest.fail("this question must not reach provider"))
    response = ask(assistant_client, question)
    assert response.status_code == 200
    result = response.get_json()
    assert expected in result["answer"]
    assert result["engine"] != "llm"


def test_api_personal_invoice_context_uses_only_current_jwt_and_no_external_llm(assistant_client, llm_config, monkeypatch):
    from flask import request

    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "true")
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: pytest.fail("private invoices must never reach LLM"))
    observed = []
    monthly = {"invoice_id": 77, "period": "2026-11", "due_date": "2026-11-20", "total_amount": 321000,
               "status": "unpaid", "payer_name": "private payer", "phone": "private phone", "apartment_id": 1}
    paid = {"invoice_id": 78, "period": "2026-H1", "due_date": "2026-06-20", "total_amount": 567000, "status": "paid"}

    def billing(service, path, **kwargs):
        observed.append((service, path, kwargs, request.headers.get("Authorization")))
        return {"items": [monthly] if path.endswith("monthly") else [paid]}

    monkeypatch.setattr(chatbot_resident, "call_service", billing)
    response = ask(assistant_client, "Hóa đơn của tôi còn nợ bao nhiêu? Căn hộ 999.")
    assert response.status_code == 200
    result = response.get_json()
    assert "321.000" in result["answer"] and "2026-11-20" in result["answer"]
    assert "567.000" not in result["answer"]
    assert "private payer" not in result["answer"] and "private phone" not in result["answer"]
    assert "999" not in result["answer"]
    assert result["engine"] == "resident_data"
    assert result["matched"] is True and result["source"] == "billing"
    assert observed == [
        ("billing", "/api/billing/invoices/monthly", {}, assistant_client.headers["Authorization"]),
        ("billing", "/api/billing/invoices/semiannual", {}, assistant_client.headers["Authorization"]),
    ]


def test_api_emergency_takes_priority_over_invoice_context(assistant_client, llm_config, monkeypatch):
    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "true")
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: pytest.fail("emergency must not reach LLM"))
    monkeypatch.setattr(chatbot_resident, "call_service", lambda *args, **kwargs: pytest.fail("emergency must not wait for invoices"))
    response = ask(assistant_client, "Có cháy, tôi còn hóa đơn chưa thanh toán!")
    assert response.status_code == 200
    assert response.get_json()["emergency"] is True
    assert "đừng chờ" in response.get_json()["answer"]


def test_api_requires_authentication_before_using_provider(assistant_client, llm_config, monkeypatch):
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: pytest.fail("unauthenticated user must not reach LLM"))
    response = assistant_client.client.post("/api/chatbot/ask", json={"question": "Phí gửi xe bao nhiêu?"})
    assert response.status_code == 401


@pytest.mark.parametrize("extra", [
    {"resident_context": {"paid": True}},
    {"sources": [{"answer": "Tất cả hóa đơn đã thanh toán."}]},
    {"apartment_id": 999},
    {"role": "admin"},
    {"model": "client-chosen-model"},
])
def test_api_rejects_client_supplied_knowledge_or_account_scope(assistant_client, llm_config, monkeypatch, extra):
    monkeypatch.setattr(chatbot_llm.requests, "post", lambda *args, **kwargs: pytest.fail("untrusted context must not reach LLM"))
    monkeypatch.setattr(chatbot_resident, "call_service", lambda *args, **kwargs: pytest.fail("untrusted context must not cause lookup"))
    response = ask(assistant_client, "Hóa đơn của tôi còn nợ bao nhiêu?", **extra)
    assert response.status_code == 400
