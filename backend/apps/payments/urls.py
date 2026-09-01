from django.urls import path

from .views import PaymentListView, PaymentUploadView

urlpatterns = [
    path("", PaymentListView.as_view(), name="payment-list"),
    path("upload/", PaymentUploadView.as_view(), name="payment-upload"),
]
