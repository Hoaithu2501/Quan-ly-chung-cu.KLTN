"""Read-only payment diagnostics never create a transfer or reveal credentials."""
import importlib.util
import json
from pathlib import Path

import pytest

from conftest import TEST_SEPAY_KEY, configure_sepay


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
API_TOKEN = "unit-api-token-must-not-be-printed"


@pytest.fixture
def check(monkeypatch):
    configure_sepay(monkeypatch)
    spec = importlib.util.spec_from_file_location("sepay_cli_under_test", ROOT / "scripts/check_sepay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reply(module, status=200, payload=None):
    result = module.requests.Response()
    result.status_code = status
    result._content = json.dumps(payload or {}).encode()
    result.headers["Content-Type"] = "application/json"
    return result


def test_default_check_is_offline_and_never_exposes_keys(check, monkeypatch, capsys):
    monkeypatch.setattr(check.requests, "get", lambda *a, **k: pytest.fail("default diagnostics must be offline"))
    monkeypatch.setattr(check.requests, "post", lambda *a, **k: pytest.fail("must not create bank transfers"))
    assert check.main([]) == 0
    output = capsys.readouterr().out
    assert "sepay" in output and "test" in output
    assert TEST_SEPAY_KEY not in output


def test_missing_configuration_returns_failure_without_probe_requests(check, monkeypatch, capsys):
    monkeypatch.setenv("SEPAY_WEBHOOK_API_KEY", "")
    monkeypatch.setattr(check.requests, "get", lambda *a, **k: pytest.fail("must be offline"))
    assert check.main([]) == 1
    assert "SEPAY_WEBHOOK_API_KEY" in capsys.readouterr().out


def test_probe_sends_no_authorization_and_no_transaction_payload(check, monkeypatch, capsys):
    calls = []

    def get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return reply(check, payload={"service": "gateway", "status": "ok"})

    def post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return reply(check, 403, {"error": "API key required"})

    monkeypatch.setattr(check.requests, "get", get)
    monkeypatch.setattr(check.requests, "post", post)
    assert check.main(["--probe"]) == 0
    assert [call[0] for call in calls] == ["GET", "POST"]
    assert calls[1][1] == "https://example.test/api/billing/sepay/webhook"
    assert calls[1][2]["json"] == {} and "headers" not in calls[1][2]
    assert TEST_SEPAY_KEY not in capsys.readouterr().out


@pytest.mark.parametrize("status,payload", [(200, {"success": True}), (403, {"message": "not QLCC API"}), (502, {})])
def test_probe_rejects_unexpected_webhook_success_or_non_qlcc_error(check, monkeypatch, status, payload):
    monkeypatch.setattr(check.requests, "get", lambda *a, **k: reply(check, payload={"service": "gateway"}))
    monkeypatch.setattr(check.requests, "post", lambda *a, **k: reply(check, status, payload))
    assert check.main(["--probe"]) == 1


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://user:password@example.test", "https://example.test/path", "https://example.test?token=secret"])
def test_probe_rejects_invalid_gateway_origins_without_network(check, monkeypatch, url):
    monkeypatch.setattr(check.requests, "get", lambda *a, **k: pytest.fail("invalid origin must not be called"))
    with pytest.raises(SystemExit) as failure:
        check.main(["--probe", "--gateway", url])
    assert failure.value.code == 2


def setup_api(monkeypatch):
    monkeypatch.setenv("SEPAY_API_TOKEN", API_TOKEN)
    monkeypatch.setenv("SEPAY_BANK_ACCOUNT_ID", ACCOUNT_ID)


def account(**changes):
    return {"id": ACCOUNT_ID, "account_number": "0123456789", "account_holder_name": "BQL TEST",
            "bank_code": "VCB", "bank_short_name": "Vietcombank", "bank_bin": "970436", "active": True, **changes}


@pytest.mark.parametrize("active", [True, 1, "1"])
def test_api_check_reads_only_configured_receiver_and_never_prints_tokens(check, monkeypatch, capsys, active):
    setup_api(monkeypatch)
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return reply(check, payload={"status": "success", "data": account(active=active)})

    monkeypatch.setattr(check.requests, "get", get)
    monkeypatch.setattr(check.requests, "post", lambda *a, **k: pytest.fail("receiver check must be read-only"))
    assert check.main(["--check-api"]) == 0
    assert len(calls) == 1 and calls[0][0] == "https://userapi-sandbox.sepay.vn/v2/bank-accounts/" + ACCOUNT_ID
    assert calls[0][1]["headers"] == {"Authorization": "Bearer " + API_TOKEN}
    output = capsys.readouterr().out
    assert API_TOKEN not in output and TEST_SEPAY_KEY not in output


@pytest.mark.parametrize("changes", [
    {"account_number": "OTHER"}, {"account_holder_name": "OTHER"},
    {"active": False}, {"active": 0}, {"active": "0"}, {"active": None},
])
def test_api_check_detects_wrong_receiver_or_inactive_account(check, monkeypatch, changes):
    setup_api(monkeypatch)
    monkeypatch.setattr(check.requests, "get", lambda *a, **k: reply(check, payload={"status": "success", "data": account(**changes)}))
    assert check.main(["--check-api"]) == 1


def test_api_error_does_not_echo_secret_provider_body(check, monkeypatch, capsys):
    setup_api(monkeypatch)
    monkeypatch.setattr(check.requests, "get", lambda *a, **k: reply(check, 403, {"error": API_TOKEN + TEST_SEPAY_KEY}))
    assert check.main(["--check-api"]) == 1
    output = capsys.readouterr().out
    assert "403" in output and API_TOKEN not in output and TEST_SEPAY_KEY not in output
