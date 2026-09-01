from rest_framework import serializers

from .models import Discrepancy, ReconciliationRun


class ReconciliationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationRun
        fields = [
            "id",
            "created_at",
            "total_orders",
            "total_payments",
            "total_order_value",
            "total_value_reconciled",
            "total_value_in_dispute",
            "discrepancy_count",
            "by_type_json",
        ]
        read_only_fields = fields


class DiscrepancySerializer(serializers.ModelSerializer):
    class Meta:
        model = Discrepancy
        fields = ["id", "type", "order_id", "payment_refs_json", "amount_at_risk", "detail"]
        read_only_fields = fields
