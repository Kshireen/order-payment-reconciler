from django.conf import settings
from django.db import models


class Order(models.Model):
    """One row from the store's order export. Stored as close to the raw
    export as possible - normalization/matching logic lives in the
    reconciliation engine, not here, so the raw data is always inspectable."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")

    order_id = models.CharField(max_length=64)
    order_id_normalized = models.CharField(max_length=64, db_index=True)

    order_date_raw = models.CharField(max_length=64, null=True, blank=True)
    customer_email = models.CharField(max_length=255, null=True, blank=True)
    currency = models.CharField(max_length=8)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=32)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["owner", "order_id_normalized"])]

    def __str__(self):
        return f"{self.order_id} ({self.status})"

    def save(self, *args, **kwargs):
        self.order_id_normalized = self.order_id.strip().upper()
        super().save(*args, **kwargs)
