from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reconciliation.models import Discrepancy

from .client import explain_discrepancies
from .serializers import ExplainRequestSerializer, ExplainResponseSerializer


class ExplainDiscrepanciesView(APIView):
    """POST /api/llm/explain/
    Body: {"discrepancy_ids": [1,2,3]}  OR  {"type": "AMOUNT_OVERPAID"}

    Explains a specific set of discrepancies, or every discrepancy of one type,
    for the current user's latest reconciliation run. Never touches matching -
    it only reads already-persisted Discrepancy rows and asks the LLM to
    describe them.
    """

    permission_classes = [IsAuthenticated]

    MAX_ITEMS = 25  # keep prompts small and the UI batch reasonable

    def post(self, request):
        req = ExplainRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        data = req.validated_data

        qs = Discrepancy.objects.filter(run__owner=request.user)
        if data.get("discrepancy_ids"):
            qs = qs.filter(id__in=data["discrepancy_ids"])
        elif data.get("type"):
            qs = qs.filter(type=data["type"])

        discrepancies = list(qs.order_by("-amount_at_risk")[: self.MAX_ITEMS])
        if not discrepancies:
            return Response({"detail": "No matching discrepancies found for this user."}, status=404)

        payload = [
            {
                "type": d.type,
                "order_id": d.order_id,
                "amount_at_risk": str(d.amount_at_risk),
                "payment_refs": d.payment_refs_json,
                "detail": d.detail,
            }
            for d in discrepancies
        ]

        result = explain_discrepancies(payload)
        return Response(ExplainResponseSerializer(result).data)
