from django.urls import path

from .views import OrderListView, OrderUploadView

urlpatterns = [
    path("", OrderListView.as_view(), name="order-list"),
    path("upload/", OrderUploadView.as_view(), name="order-upload"),
]
