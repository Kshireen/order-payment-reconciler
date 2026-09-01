from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .adapter import load_rows_for_user
from .engine import reconcile
from .models import Discrepancy, ReconciliationRun
from .serializers import DiscrepancySerializer, ReconciliationRunSerializer


class RunReconciliationView(APIView):
    """POST /api/reconciliation/run/ - reconcile the current user's uploaded
    orders + payments and persist the result, replacing any previous run."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        orders, payments = load_rows_for_user(request.user)
        if not orders and not payments:
            return Response(
                {"detail": "No orders or payments uploaded yet. Upload both CSVs first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = reconcile(orders, payments)
        summary = result.summary()

        ReconciliationRun.objects.filter(owner=request.user).delete()
        run = ReconciliationRun.objects.create(
            owner=request.user,
            total_orders=summary["total_orders"],
            total_payments=summary["total_payments"],
            total_order_value=summary["total_order_value"],
            total_value_reconciled=summary["total_value_reconciled"],
            total_value_in_dispute=summary["total_value_in_dispute"],
            discrepancy_count=summary["discrepancy_count"],
            by_type_json={k: {"count": v["count"], "amount": str(v["amount"])} for k, v in summary["by_type"].items()},
        )

        Discrepancy.objects.bulk_create(
            [
                Discrepancy(
                    run=run,
                    type=d.type.value,
                    order_id=d.order_id,
                    payment_refs_json=d.payment_refs,
                    amount_at_risk=d.amount_at_risk,
                    detail=d.detail,
                )
                for d in result.all_discrepancies
            ]
        )

        return Response(ReconciliationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ReconciliationSummaryView(generics.RetrieveAPIView):
    """GET /api/reconciliation/summary/ - the current user's latest run."""

    serializer_class = ReconciliationRunSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        run = ReconciliationRun.objects.filter(owner=self.request.user).first()
        if run is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("No reconciliation run yet - POST /api/reconciliation/run/ first.")
        return run


class DiscrepancyListView(generics.ListAPIView):
    """GET /api/reconciliation/discrepancies/?type=AMOUNT_OVERPAID&search=ORD-1401
    Filterable, searchable drill-down list backing the dashboard table."""

    serializer_class = DiscrepancySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Discrepancy.objects.filter(run__owner=self.request.user).order_by("-amount_at_risk")
        dtype = self.request.query_params.get("type")
        if dtype:
            qs = qs.filter(type=dtype)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(order_id__icontains=search)
        return qs
