from rest_framework import serializers


class ExplainRequestSerializer(serializers.Serializer):
    discrepancy_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    type = serializers.CharField(required=False)

    def validate(self, data):
        if not data.get("discrepancy_ids") and not data.get("type"):
            raise serializers.ValidationError("Provide either 'discrepancy_ids' or 'type'.")
        return data


class ExplainItemSerializer(serializers.Serializer):
    order_id = serializers.CharField(allow_null=True)
    explanation = serializers.CharField()
    recommended_action = serializers.CharField()


class ExplainResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    overview = serializers.CharField(allow_null=True)
    items = ExplainItemSerializer(many=True)
    error = serializers.CharField(allow_null=True)
