from django.contrib import admin

from .models import Discrepancy, ReconciliationRun


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(admin.ModelAdmin):
    list_display = ("owner", "created_at", "total_orders", "total_payments", "discrepancy_count", "total_value_in_dispute")


@admin.register(Discrepancy)
class DiscrepancyAdmin(admin.ModelAdmin):
    list_display = ("order_id", "type", "amount_at_risk", "run")
    list_filter = ("type",)
    search_fields = ("order_id",)
