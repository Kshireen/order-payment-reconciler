from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "transaction_ref",
            "processed_at_raw",
            "order_reference",
            "currency",
            "amount",
            "fee",
            "net_settled",
            "type",
            "status",
            "uploaded_at",
        ]
        read_only_fields = fields
