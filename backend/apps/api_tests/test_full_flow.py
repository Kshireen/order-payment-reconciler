import os

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "reconciliation", "tests", "fixtures")


@pytest.fixture
def auth_client(db):
    User = get_user_model()
    user = User.objects.create_user(username="tester", password="pw12345!")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_full_flow_upload_run_discrepancies(auth_client):
    with open(os.path.join(FIXTURES, "orders.csv"), "rb") as f:
        resp = auth_client.post("/api/orders/upload/", {"file": f}, format="multipart")
    assert resp.status_code == 201, resp.data
    assert resp.data["created"] > 0

    with open(os.path.join(FIXTURES, "payments.csv"), "rb") as f:
        resp = auth_client.post("/api/payments/upload/", {"file": f}, format="multipart")
    assert resp.status_code == 201, resp.data
    assert resp.data["created"] > 0

    resp = auth_client.post("/api/reconciliation/run/")
    assert resp.status_code == 201, resp.data
    assert resp.data["discrepancy_count"] > 0
    assert float(resp.data["total_value_in_dispute"]) > 0

    resp = auth_client.get("/api/reconciliation/summary/")
    assert resp.status_code == 200
    assert resp.data["discrepancy_count"] > 0

    resp = auth_client.get("/api/reconciliation/discrepancies/?type=MISSING_PAYMENT")
    assert resp.status_code == 200
    assert resp.data["count"] == 4  # ORD-1201..1204

    resp = auth_client.get("/api/reconciliation/discrepancies/?search=ORD-1401")
    assert resp.status_code == 200
    assert resp.data["count"] == 1


@pytest.mark.django_db
def test_data_isolated_per_user(auth_client):
    """A second user with no uploads must see nothing of the first user's data."""
    with open(os.path.join(FIXTURES, "orders.csv"), "rb") as f:
        auth_client.post("/api/orders/upload/", {"file": f}, format="multipart")

    User = get_user_model()
    other = User.objects.create_user(username="other", password="pw12345!")
    other_client = APIClient()
    other_client.force_authenticate(user=other)

    resp = other_client.get("/api/orders/")
    assert resp.status_code == 200
    assert resp.data["count"] == 0


@pytest.mark.django_db
def test_explain_without_api_key_fails_gracefully(auth_client, settings):
    """No GROQ_API_KEY configured -> explain endpoint must degrade, not 500."""
    settings.GROQ_API_KEY = ""

    with open(os.path.join(FIXTURES, "orders.csv"), "rb") as f:
        auth_client.post("/api/orders/upload/", {"file": f}, format="multipart")
    with open(os.path.join(FIXTURES, "payments.csv"), "rb") as f:
        auth_client.post("/api/payments/upload/", {"file": f}, format="multipart")
    auth_client.post("/api/reconciliation/run/")

    resp = auth_client.post("/api/llm/explain/", {"type": "MISSING_PAYMENT"}, format="json")
    assert resp.status_code == 200
    assert resp.data["ok"] is False
    assert resp.data["error"]


@pytest.mark.django_db
def test_upload_rejects_missing_required_columns(auth_client):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile

    bad_csv = SimpleUploadedFile("bad.csv", b"foo,bar\n1,2\n", content_type="text/csv")
    resp = auth_client.post("/api/orders/upload/", {"file": bad_csv}, format="multipart")
    assert resp.status_code == 400
