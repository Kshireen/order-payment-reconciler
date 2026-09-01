import os
from decimal import Decimal

import pytest

from apps.reconciliation.engine import DiscrepancyType, reconcile
from apps.reconciliation.loaders import load_orders_csv, load_payments_csv

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="module")
def real_result():
    orders = load_orders_csv(os.path.join(FIXTURES, "orders.csv"))
    payments = load_payments_csv(os.path.join(FIXTURES, "payments.csv"))
    return reconcile(orders, payments)


def _discrepancies_for(result, order_id, dtype=None):
    order_id = order_id.strip().upper()
    out = []
    for r in result.order_results:
        if r.order and r.order.norm_id == order_id:
            out.extend(r.discrepancies)
    for d in result.orphan_payment_discrepancies:
        if d.order_id and d.order_id.strip().upper() == order_id:
            out.append(d)
    if dtype:
        out = [d for d in out if d.type == dtype]
    return out


def test_determinism(real_result):
    """Running reconcile twice on the same input gives the same summary."""
    orders = load_orders_csv(os.path.join(FIXTURES, "orders.csv"))
    payments = load_payments_csv(os.path.join(FIXTURES, "payments.csv"))
    r2 = reconcile(orders, payments)
    assert real_result.summary() == r2.summary()


def test_duplicate_order_row_deduped(real_result):
    assert "ORD-1004" in [oid.strip().upper() for oid in real_result.duplicate_order_ids_skipped]


def test_missing_payment_orders_detected(real_result):
    for oid in ["ORD-1201", "ORD-1202", "ORD-1203", "ORD-1204"]:
        d = _discrepancies_for(real_result, oid, DiscrepancyType.MISSING_PAYMENT)
        assert len(d) == 1, f"expected MISSING_PAYMENT for {oid}"


def test_orphan_payments_detected(real_result):
    orphan_refs = {d.payment_refs[0] for d in real_result.orphan_payment_discrepancies}
    assert {"TXN700161", "TXN700162", "TXN700163"} <= orphan_refs


def test_case_and_whitespace_normalized_refs_matched(real_result):
    """ord-1801 / ord-1802 (lowercase, padded) must still match ORD-1801/1802 -
    i.e. they must NOT show up as orphan payments."""
    orphan_refs = {d.payment_refs[0] for d in real_result.orphan_payment_discrepancies}
    assert "TXN700178" not in orphan_refs
    assert "TXN700179" not in orphan_refs


def test_duplicate_charges_detected(real_result):
    for oid in ["ORD-1501", "ORD-1502"]:
        d = _discrepancies_for(real_result, oid, DiscrepancyType.DUPLICATE_CHARGE)
        assert len(d) == 1, f"expected one DUPLICATE_CHARGE for {oid}"


def test_currency_mismatches_detected(real_result):
    for oid in ["ORD-1601", "ORD-1602"]:
        d = _discrepancies_for(real_result, oid, DiscrepancyType.CURRENCY_MISMATCH)
        assert len(d) == 1, f"expected CURRENCY_MISMATCH for {oid}"


def test_amount_mismatches_detected(real_result):
    over = _discrepancies_for(real_result, "ORD-1401", DiscrepancyType.AMOUNT_OVERPAID)
    assert len(over) == 1
    under = _discrepancies_for(real_result, "ORD-1402", DiscrepancyType.AMOUNT_UNDERPAID)
    assert len(under) == 1
    over2 = _discrepancies_for(real_result, "ORD-1403", DiscrepancyType.AMOUNT_OVERPAID)
    assert len(over2) == 1


def test_small_rounding_diff_within_tolerance_not_flagged(real_result):
    """ORD-1902 differs by $0.02 - inside the $0.05 tolerance, should NOT be an
    amount discrepancy (this is what proves the tolerance isn't hiding real gaps:
    the $18-60 mismatches above ARE flagged)."""
    d = _discrepancies_for(real_result, "ORD-1902")
    types = {x.type for x in d}
    assert DiscrepancyType.AMOUNT_OVERPAID not in types
    assert DiscrepancyType.AMOUNT_UNDERPAID not in types


def test_unsettled_payment_detected(real_result):
    for oid in ["ORD-2001", "ORD-2002"]:
        d = _discrepancies_for(real_result, oid, DiscrepancyType.UNSETTLED_PAYMENT)
        assert len(d) == 1, f"expected UNSETTLED_PAYMENT for {oid}"


def test_cancelled_not_refunded_detected(real_result):
    d = _discrepancies_for(real_result, "ORD-1701", DiscrepancyType.CANCELLED_NOT_REFUNDED)
    assert len(d) == 1


def test_refund_status_drift_detected(real_result):
    d = _discrepancies_for(real_result, "ORD-1703", DiscrepancyType.REFUND_STATUS_DRIFT)
    assert len(d) == 1


def test_partial_refund_is_not_flagged_as_drift_or_missing(real_result):
    """ORD-1702: charged 240, refunded 120 (partial). Status is already 'refunded'
    in the source data, so this should be clean - not a discrepancy."""
    d = _discrepancies_for(real_result, "ORD-1702")
    assert d == []


def test_summary_totals_are_consistent(real_result):
    s = real_result.summary()
    assert s["total_orders"] > 0
    assert s["total_value_in_dispute"] > Decimal("0")
    # every discrepancy type bucket amount must be non-negative
    for bucket in s["by_type"].values():
        assert bucket["amount"] >= Decimal("0")


# --- synthetic edge-case tests (isolated from the real fixture data) ---

from apps.reconciliation.engine import OrderRow, PaymentRow  # noqa: E402


def _order(**kw):
    base = dict(
        order_id="ORD-9001",
        order_date="2025-01-01 00:00:00",
        customer_email="a@example.com",
        currency="USD",
        gross_amount=Decimal("100.00"),
        discount=Decimal("0"),
        net_amount=Decimal("100.00"),
        status="completed",
    )
    base.update(kw)
    return OrderRow(**base)


def _payment(**kw):
    base = dict(
        transaction_ref="TXN9001",
        processed_at="01/01/2025 00:00",
        order_reference="ORD-9001",
        currency="USD",
        amount=Decimal("100.00"),
        fee=Decimal("3.00"),
        net_settled=Decimal("97.00"),
        type="charge",
        status="settled",
    )
    base.update(kw)
    return PaymentRow(**base)


def test_clean_match_has_no_discrepancies():
    result = reconcile([_order()], [_payment()])
    assert result.order_results[0].is_clean_match
    assert result.all_discrepancies == []


def test_boundary_tolerance_exact_edge_not_flagged():
    payment = _payment(amount=Decimal("100.05"))
    result = reconcile([_order()], [payment])
    assert result.all_discrepancies == []


def test_boundary_tolerance_just_over_is_flagged():
    payment = _payment(amount=Decimal("100.06"))
    result = reconcile([_order()], [payment])
    assert len(result.all_discrepancies) == 1
    assert result.all_discrepancies[0].type == DiscrepancyType.AMOUNT_OVERPAID
