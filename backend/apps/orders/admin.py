from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "owner", "status", "currency", "net_amount", "uploaded_at")
    list_filter = ("status", "currency")
    search_fields = ("order_id", "customer_email")
