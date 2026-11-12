import threading

import requests
from flask import has_request_context, request
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shared.config import service_url, secret
from shared.web import APIError

_local = threading.local()


def pooled_session(retry_reads=True):
    """One keep-alive session per worker thread; opening a TCP connection per hop is wasteful."""
    attribute = "retrying" if retry_reads else "plain"
    session = getattr(_local, attribute, None)
    if session is None:
        session = requests.Session()
        if retry_reads:
            # Only read requests can be retried automatically; mutation idempotency is domain-owned.
            session.mount(
                "http://",
                HTTPAdapter(
                    max_retries=Retry(
                        total=2,
                        backoff_factor=0.15,
                        allowed_methods=frozenset({"GET", "HEAD"}),
                        status_forcelist=[502, 503, 504],
                    )
                ),
            )
        setattr(_local, attribute, session)
    return session


def call_service(service, path, method="GET", json=None, params=None, internal=False):
    headers = {}
    if internal:
        headers["X-Service-Token"] = secret("SERVICE_TOKEN")
    elif has_request_context():
        headers["Authorization"] = request.headers.get("Authorization", "")
    try:
        response = pooled_session().request(
            method, service_url(service) + path, json=json, params=params, headers=headers, timeout=(3, 12)
        )
        result = response.json()
    except (requests.RequestException, ValueError):
        raise APIError(f"Dịch vụ {service} tạm thời không khả dụng.", 503)
    if not response.ok:
        raise APIError(result.get("error", f"Lỗi dịch vụ {service}"), response.status_code)
    return result
