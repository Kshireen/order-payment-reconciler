from django.conf import settings
from django.db import models

from .engine import DiscrepancyType


class ReconciliationRun(models.Model):
    """One execution of the engine for a user. Only the latest run per user is
    kept (re-running replaces the previous one) - this is a reconciliation
    dashboard, not an audit trail across historical runs, per the assignment
    scope."""

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reconciliation_run")
    created_at = models.DateTimeField(auto_now_add=True)

    total_orders = models.IntegerField()
    total_payments = models.IntegerField()
    total_order_value = models.DecimalField(max_digits=14, decimal_places=2)
    total_value_reconciled = models.DecimalField(max_digits=14, decimal_places=2)
    total_value_in_dispute = models.DecimalField(max_digits=14, decimal_places=2)
    discrepancy_count = models.IntegerField()
    by_type_json = models.JSONField(default=dict)

    def __str__(self):
        return f"Run for {self.owner} at {self.created_at:%Y-%m-%d %H:%M}"


class Discrepancy(models.Model):
    TYPE_CHOICES = [(t.value, t.value) for t in DiscrepancyType]

    run = models.ForeignKey(ReconciliationRun, on_delete=models.CASCADE, related_name="discrepancies")
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, db_index=True)
    order_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    payment_refs_json = models.JSONField(default=list)
    amount_at_risk = models.DecimalField(max_digits=12, decimal_places=2)
    detail = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["run", "type"])]

    def __str__(self):
        return f"{self.type} - {self.order_id}"
