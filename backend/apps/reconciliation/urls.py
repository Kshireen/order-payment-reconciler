from django.urls import path

from .views import DiscrepancyListView, ReconciliationSummaryView, RunReconciliationView

urlpatterns = [
    path("run/", RunReconciliationView.as_view(), name="reconciliation-run"),
    path("summary/", ReconciliationSummaryView.as_view(), name="reconciliation-summary"),
    path("discrepancies/", DiscrepancyListView.as_view(), name="discrepancy-list"),
]
