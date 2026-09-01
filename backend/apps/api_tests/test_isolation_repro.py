"""Full-stack isolation check using real signup + real JWTs end to end
(not force_authenticate) - the exact scenario that matters: does a second,
completely separate account ever see the first account's uploaded data or
reconciliation results."""

import os

import pytest
from rest_framework.test import APIClient

FIXTURES = "apps/reconciliation/tests/fixtures"


@pytest.mark.django_db
def test_two_real_users_full_isolation():
    client_a = APIClient()
    signup_a = client_a.post("/api/auth/signup/", {"username": "alice", "password": "pw12345!!"}, format="json")
    assert signup_a.status_code == 201
    access_a = signup_a.data["access"]

    with open(os.path.join(FIXTURES, "orders.csv"), "rb") as f:
        r = client_a.post(
            "/api/orders/upload/", {"file": f}, format="multipart", HTTP_AUTHORIZATION=f"Bearer {access_a}"
        )
        assert r.status_code == 201
    with open(os.path.join(FIXTURES, "payments.csv"), "rb") as f:
        r = client_a.post(
            "/api/payments/upload/", {"file": f}, format="multipart", HTTP_AUTHORIZATION=f"Bearer {access_a}"
        )
        assert r.status_code == 201
    r = client_a.post("/api/reconciliation/run/", HTTP_AUTHORIZATION=f"Bearer {access_a}")
    assert r.status_code == 201

    client_b = APIClient()
    signup_b = client_b.post("/api/auth/signup/", {"username": "bob", "password": "pw12345!!"}, format="json")
    assert signup_b.status_code == 201
    access_b = signup_b.data["access"]

    r = client_b.get("/api/orders/", HTTP_AUTHORIZATION=f"Bearer {access_b}")
    assert r.data["count"] == 0, f"BOB SEES ALICE'S ORDERS: {r.data}"

    r = client_b.get("/api/payments/", HTTP_AUTHORIZATION=f"Bearer {access_b}")
    assert r.data["count"] == 0, f"BOB SEES ALICE'S PAYMENTS: {r.data}"

    r = client_b.get("/api/reconciliation/summary/", HTTP_AUTHORIZATION=f"Bearer {access_b}")
    assert r.status_code == 404, f"BOB SEES ALICE'S RECONCILIATION RUN: {r.data}"

    r = client_b.get("/api/reconciliation/discrepancies/", HTTP_AUTHORIZATION=f"Bearer {access_b}")
    assert r.data["count"] == 0, f"BOB SEES ALICE'S DISCREPANCIES: {r.data}"
