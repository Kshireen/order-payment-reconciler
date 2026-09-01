"""Bridges the DB-backed Order/Payment models to the pure engine dataclasses.
Kept separate so `engine.py` never imports Django."""

from apps.orders.models import Order
from apps.payments.models import Payment

from .engine import OrderRow, PaymentRow


def order_to_row(o: Order) -> OrderRow:
    return OrderRow(
        order_id=o.order_id,
        order_date=o.order_date_raw,
        customer_email=o.customer_email,
        currency=o.currency,
        gross_amount=o.gross_amount,
        discount=o.discount,
        net_amount=o.net_amount,
        status=o.status,
    )


def payment_to_row(p: Payment) -> PaymentRow:
    return PaymentRow(
        transaction_ref=p.transaction_ref,
        processed_at=p.processed_at_raw,
        order_reference=p.order_reference,
        currency=p.currency,
        amount=p.amount,
        fee=p.fee,
        net_settled=p.net_settled,
        type=p.type,
        status=p.status,
    )


def load_rows_for_user(user):
    orders = [order_to_row(o) for o in Order.objects.filter(owner=user)]
    payments = [payment_to_row(p) for p in Payment.objects.filter(owner=user)]
    return orders, payments
