from django.conf import settings
from django.db import models


class Payment(models.Model):
    """One row from the payment processor's export."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")

    transaction_ref = models.CharField(max_length=64)
    processed_at_raw = models.CharField(max_length=64, null=True, blank=True)
    order_reference = models.CharField(max_length=64)
    order_reference_normalized = models.CharField(max_length=64, db_index=True)
    currency = models.CharField(max_length=8)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_settled = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    type = models.CharField(max_length=16)  # charge | refund
    status = models.CharField(max_length=16)  # settled | pending | failed

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["owner", "order_reference_normalized"])]

    def __str__(self):
        return f"{self.transaction_ref} -> {self.order_reference} ({self.type}, {self.status})"

    def save(self, *args, **kwargs):
        self.order_reference_normalized = self.order_reference.strip().upper()
        super().save(*args, **kwargs)
