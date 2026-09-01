"""Parse raw CSV rows (dicts from csv.DictReader) into engine dataclasses.

Kept separate from engine.py so the reconciliation engine has zero knowledge of
CSV/string parsing quirks - it only ever sees clean typed rows.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .engine import OrderRow, PaymentRow


def _dec(value: str | None, default: str = "0") -> Decimal:
    if value is None or value.strip() == "":
        return Decimal(default)
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal(default)


def _str_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def parse_order_row(row: dict) -> OrderRow:
    return OrderRow(
        order_id=row["order_id"].strip(),
        order_date=_str_or_none(row.get("order_date")),
        customer_email=_str_or_none(row.get("customer_email")),
        currency=row["currency"].strip().upper(),
        gross_amount=_dec(row.get("gross_amount")),
        discount=_dec(row.get("discount")),
        net_amount=_dec(row.get("net_amount")),
        status=row["status"].strip().lower(),
    )


def parse_payment_row(row: dict) -> PaymentRow:
    return PaymentRow(
        transaction_ref=row["transaction_ref"].strip(),
        processed_at=_str_or_none(row.get("processed_at")),
        order_reference=row["order_reference"].strip(),
        currency=row["currency"].strip().upper(),
        amount=_dec(row.get("amount")),
        fee=_dec(row.get("fee")),
        net_settled=_dec(row.get("net_settled")),
        type=row["type"].strip().lower(),
        status=row["status"].strip().lower(),
    )


def load_orders_csv(path: str) -> list[OrderRow]:
    import csv

    with open(path, newline="", encoding="utf-8") as f:
        return [parse_order_row(r) for r in csv.DictReader(f)]


def load_payments_csv(path: str) -> list[PaymentRow]:
    import csv

    with open(path, newline="", encoding="utf-8") as f:
        return [parse_payment_row(r) for r in csv.DictReader(f)]
