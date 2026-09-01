from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "order_id",
            "order_date_raw",
            "customer_email",
            "currency",
            "gross_amount",
            "discount",
            "net_amount",
            "status",
            "uploaded_at",
        ]
        read_only_fields = fields


class OrderUploadResultSerializer(serializers.Serializer):
    created = serializers.IntegerField()
    skipped_rows = serializers.ListField(child=serializers.CharField(), default=list)
