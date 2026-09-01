from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_ref", "owner", "order_reference", "type", "status", "amount", "currency")
    list_filter = ("type", "status", "currency")
    search_fields = ("transaction_ref", "order_reference")
