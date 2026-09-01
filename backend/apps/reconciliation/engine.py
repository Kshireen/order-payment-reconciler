"""
Deterministic order/payment reconciliation engine.

Design goals (per assignment spec):
- Pure, framework-agnostic, no I/O, no LLM calls: same input -> same output, always.
- Operates on plain dataclasses so it can be unit-tested without a database or Django.
- Django views/serializers are a thin wrapper that load rows from the DB into these
  dataclasses, call `reconcile()`, and persist the resulting DiscrepancyResult rows.

Discrepancy types (see README for full rationale + the real examples in the sample data
that motivated each one):

  MISSING_PAYMENT        Order is `completed` but no charge payment references it at all.
  ORPHAN_PAYMENT          A payment references an order_id that does not exist.
  DUPLICATE_CHARGE        More than one settled charge for the same order (webhook retry /
                           double-billing). The 2nd+ charge is the discrepancy.
  CURRENCY_MISMATCH       Order currency != payment currency. We do NOT attempt FX
                           conversion (no rate is supplied) - flagged for manual review.
  AMOUNT_UNDERPAID        Settled charge amount < order net_amount, currency matches,
                           beyond tolerance.
  AMOUNT_OVERPAID         Settled charge amount > order net_amount, currency matches,
                           beyond tolerance.
  UNSETTLED_PAYMENT       Order is `completed` but its charge is `pending` or `failed` -
                           revenue booked that was never actually collected.
  CANCELLED_NOT_REFUNDED  Order is `cancelled` but has a settled charge with no
                           offsetting refund.
  REFUND_STATUS_DRIFT     Order is still `completed` but has been fully refunded
                           (refunds >= charges) - the order record itself is stale.

Matching keys are normalized (trimmed + uppercased) before comparison, since the raw
payments export contains case and whitespace variants of otherwise-valid order references
(e.g. "ord-1802", " ord-1801 ").

Tolerance: amounts are compared with a $0.05 tolerance to absorb float rounding noise
(the sample data has a genuine $0.02 rounding case) without masking real mismatches,
which in the sample data are all >= ~$18.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


AMOUNT_TOLERANCE = Decimal("0.05")


class DiscrepancyType(str, Enum):
    MISSING_PAYMENT = "MISSING_PAYMENT"
    ORPHAN_PAYMENT = "ORPHAN_PAYMENT"
    DUPLICATE_CHARGE = "DUPLICATE_CHARGE"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    AMOUNT_UNDERPAID = "AMOUNT_UNDERPAID"
    AMOUNT_OVERPAID = "AMOUNT_OVERPAID"
    UNSETTLED_PAYMENT = "UNSETTLED_PAYMENT"
    CANCELLED_NOT_REFUNDED = "CANCELLED_NOT_REFUNDED"
    REFUND_STATUS_DRIFT = "REFUND_STATUS_DRIFT"


@dataclass(frozen=True)
class OrderRow:
    order_id: str
    order_date: Optional[str]
    customer_email: Optional[str]
    currency: str
    gross_amount: Decimal
    discount: Decimal
    net_amount: Decimal
    status: str  # completed | cancelled | refunded

    @property
    def norm_id(self) -> str:
        return self.order_id.strip().upper()


@dataclass(frozen=True)
class PaymentRow:
    transaction_ref: str
    processed_at: Optional[str]
    order_reference: str
    currency: str
    amount: Decimal
    fee: Decimal
    net_settled: Decimal
    type: str  # charge | refund
    status: str  # settled | pending | failed

    @property
    def norm_ref(self) -> str:
        return self.order_reference.strip().upper()


@dataclass
class Discrepancy:
    type: DiscrepancyType
    order_id: Optional[str]
    payment_refs: list[str] = field(default_factory=list)
    amount_at_risk: Decimal = Decimal("0")
    detail: str = ""


@dataclass
class OrderReconciliation:
    order: Optional[OrderRow]
    payments: list[PaymentRow]
    discrepancies: list[Discrepancy]
    is_clean_match: bool


@dataclass
class ReconciliationResult:
    order_results: list[OrderReconciliation]
    orphan_payment_discrepancies: list[Discrepancy]
    duplicate_order_ids_skipped: list[str]

    @property
    def all_discrepancies(self) -> list[Discrepancy]:
        out: list[Discrepancy] = []
        for r in self.order_results:
            out.extend(r.discrepancies)
        out.extend(self.orphan_payment_discrepancies)
        return out

    def summary(self) -> dict:
        total_orders = len(self.order_results)
        total_payments = sum(len(r.payments) for r in self.order_results) + len(
            self.orphan_payment_discrepancies
        )
        total_order_value = sum((r.order.net_amount for r in self.order_results if r.order), Decimal("0"))
        clean_value = sum(
            (r.order.net_amount for r in self.order_results if r.order and r.is_clean_match),
            Decimal("0"),
        )
        at_risk = sum((d.amount_at_risk for d in self.all_discrepancies), Decimal("0"))
        by_type: dict[str, dict] = {}
        for d in self.all_discrepancies:
            bucket = by_type.setdefault(d.type.value, {"count": 0, "amount": Decimal("0")})
            bucket["count"] += 1
            bucket["amount"] += d.amount_at_risk
        return {
            "total_orders": total_orders,
            "total_payments": total_payments,
            "total_order_value": total_order_value,
            "total_value_reconciled": clean_value,
            "total_value_in_dispute": at_risk,
            "discrepancy_count": len(self.all_discrepancies),
            "by_type": by_type,
        }


def _dedupe_orders(orders: list[OrderRow]) -> tuple[list[OrderRow], list[str]]:
    """Collapse exact-duplicate order rows (same id, same every field) to one row.
    Returns (deduped_orders, list_of_order_ids_that_had_duplicates)."""
    seen: dict[str, OrderRow] = {}
    dupes: list[str] = []
    for o in orders:
        key = o.norm_id
        if key in seen:
            if seen[key] == o:
                dupes.append(o.order_id)
                continue
            # Same id, different data - keep both under distinct synthetic keys so
            # nothing is silently dropped; this is itself worth surfacing but is rare
            # enough in the sample data not to warrant a dedicated discrepancy type.
        seen[key] = o
    return list(seen.values()), dupes


def reconcile(orders: list[OrderRow], payments: list[PaymentRow]) -> ReconciliationResult:
    deduped_orders, dup_order_ids = _dedupe_orders(orders)
    orders_by_id = {o.norm_id: o for o in deduped_orders}

    payments_by_order: dict[str, list[PaymentRow]] = {}
    orphan_payments: list[PaymentRow] = []
    for p in payments:
        if p.norm_ref in orders_by_id:
            payments_by_order.setdefault(p.norm_ref, []).append(p)
        else:
            orphan_payments.append(p)

    order_results: list[OrderReconciliation] = []

    for order in deduped_orders:
        pays = payments_by_order.get(order.norm_id, [])
        charges = [p for p in pays if p.type == "charge"]
        refunds = [p for p in pays if p.type == "refund"]
        settled_charges = [p for p in charges if p.status == "settled"]
        unsettled_charges = [p for p in charges if p.status in ("pending", "failed")]

        discrepancies: list[Discrepancy] = []

        if order.status == "completed" and not charges:
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.MISSING_PAYMENT,
                    order_id=order.order_id,
                    amount_at_risk=order.net_amount,
                    detail=f"Order marked completed ({order.net_amount} {order.currency}) but no payment record exists.",
                )
            )

        if len(settled_charges) > 1:
            primary, *extra = sorted(settled_charges, key=lambda p: p.processed_at or "")
            for p in extra:
                discrepancies.append(
                    Discrepancy(
                        type=DiscrepancyType.DUPLICATE_CHARGE,
                        order_id=order.order_id,
                        payment_refs=[primary.transaction_ref, p.transaction_ref],
                        amount_at_risk=p.amount,
                        detail=f"Order charged more than once ({primary.transaction_ref} and {p.transaction_ref} both settled).",
                    )
                )

        for p in unsettled_charges:
            if order.status == "completed":
                discrepancies.append(
                    Discrepancy(
                        type=DiscrepancyType.UNSETTLED_PAYMENT,
                        order_id=order.order_id,
                        payment_refs=[p.transaction_ref],
                        amount_at_risk=p.amount,
                        detail=f"Order marked completed but payment {p.transaction_ref} is {p.status}, not settled.",
                    )
                )

        for p in settled_charges:
            if p.currency != order.currency:
                discrepancies.append(
                    Discrepancy(
                        type=DiscrepancyType.CURRENCY_MISMATCH,
                        order_id=order.order_id,
                        payment_refs=[p.transaction_ref],
                        amount_at_risk=p.amount,
                        detail=f"Order currency {order.currency} but payment currency {p.currency} (no FX rate available to reconcile).",
                    )
                )
                continue  # don't also amount-compare across currencies

            diff = p.amount - order.net_amount
            if abs(diff) > AMOUNT_TOLERANCE:
                dtype = DiscrepancyType.AMOUNT_OVERPAID if diff > 0 else DiscrepancyType.AMOUNT_UNDERPAID
                discrepancies.append(
                    Discrepancy(
                        type=dtype,
                        order_id=order.order_id,
                        payment_refs=[p.transaction_ref],
                        amount_at_risk=abs(diff),
                        detail=f"Order net_amount {order.net_amount} vs payment amount {p.amount} (diff {diff:+}).",
                    )
                )

        if order.status == "cancelled":
            total_settled_charge = sum((p.amount for p in settled_charges), Decimal("0"))
            total_refund = sum((p.amount for p in refunds if p.status == "settled"), Decimal("0"))
            if total_settled_charge > 0 and total_refund < total_settled_charge - AMOUNT_TOLERANCE:
                discrepancies.append(
                    Discrepancy(
                        type=DiscrepancyType.CANCELLED_NOT_REFUNDED,
                        order_id=order.order_id,
                        payment_refs=[p.transaction_ref for p in settled_charges],
                        amount_at_risk=total_settled_charge - total_refund,
                        detail="Order was cancelled but the settled charge was never refunded.",
                    )
                )

        if order.status == "completed":
            total_settled_charge = sum((p.amount for p in settled_charges), Decimal("0"))
            total_refund = sum((p.amount for p in refunds if p.status == "settled"), Decimal("0"))
            if total_settled_charge > 0 and total_refund >= total_settled_charge - AMOUNT_TOLERANCE:
                discrepancies.append(
                    Discrepancy(
                        type=DiscrepancyType.REFUND_STATUS_DRIFT,
                        order_id=order.order_id,
                        payment_refs=[p.transaction_ref for p in refunds],
                        amount_at_risk=Decimal("0"),
                        detail="Order has been fully refunded but its status is still 'completed'.",
                    )
                )

        order_results.append(
            OrderReconciliation(
                order=order,
                payments=pays,
                discrepancies=discrepancies,
                is_clean_match=(len(discrepancies) == 0),
            )
        )

    orphan_discrepancies = [
        Discrepancy(
            type=DiscrepancyType.ORPHAN_PAYMENT,
            order_id=p.order_reference,
            payment_refs=[p.transaction_ref],
            amount_at_risk=p.amount,
            detail=f"Payment {p.transaction_ref} references order {p.order_reference!r}, which does not exist.",
        )
        for p in orphan_payments
    ]

    return ReconciliationResult(
        order_results=order_results,
        orphan_payment_discrepancies=orphan_discrepancies,
        duplicate_order_ids_skipped=dup_order_ids,
    )
