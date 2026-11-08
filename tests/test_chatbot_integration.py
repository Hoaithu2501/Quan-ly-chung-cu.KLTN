"""Invoice privacy through the actual Chatbot -> Billing -> Resident HTTP chain."""


def test_chatbot_looks_up_only_authenticated_residents_invoices(service_cluster, monkeypatch):
    cluster = service_cluster
    monkeypatch.setenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "true")

    def forbidden_provider(*args, **kwargs):
        raise AssertionError("Personal invoices must not be sent to an LLM")

    monkeypatch.setattr(cluster.modules["chatbot"], "rewrite_answer", forbidden_provider)
    first = cluster.call("resident", "/api/residents/me", role="resident", user_id=3).json()
    second = cluster.call("resident", "/api/residents/me", role="resident", user_id=4).json()
    own_apartment = first["apartment_ids"][0]
    other_apartment = next(value for value in second["apartment_ids"] if value not in first["apartment_ids"])
    for apartment, amount in ((own_apartment, 123457), (other_apartment, 876543)):
        created = cluster.call("billing", "/api/billing/invoices/monthly", method="POST", json={
            "apartment_id": apartment, "period": "2099-11", "due_date": "2099-12-01",
            "electricity_fee": amount, "water_fee": 0})
        assert created.status_code == 201, created.text
    reply = cluster.call("chatbot", "/api/chatbot/ask", method="POST", role="resident", user_id=3,
                         json={"question": f"Hoa don cua toi con no bao nhieu? Can ho {other_apartment}."})
    assert reply.status_code == 200, reply.text
    result = reply.json()
    assert result["engine"] == "resident_data" and result["source"] == "billing"
    assert "876.543" not in result["answer"]
    # The reply shows the earliest five debts, so the far-future invoice need
    # not be listed. Compare its total count to Billing's resident-scoped list.
    expected = []
    for kind in ("monthly", "semiannual"):
        response = cluster.call("billing", "/api/billing/invoices/" + kind, role="resident", user_id=3)
        assert response.status_code == 200, response.text
        expected.extend(row for row in response.json()["items"] if row["status"] != "paid")
    assert f"{len(expected)} hóa đơn" in result["answer"]
    assert all(row["apartment_id"] in first["apartment_ids"] for row in expected)
