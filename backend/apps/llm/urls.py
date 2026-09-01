from django.urls import path

from .views import ExplainDiscrepanciesView

urlpatterns = [
    path("explain/", ExplainDiscrepanciesView.as_view(), name="llm-explain"),
]
