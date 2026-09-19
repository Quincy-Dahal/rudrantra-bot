"""
products/urls.py
"""

from django.urls import path

from .views import TriggerSyncView

urlpatterns = [
    path(
        "internal/sync-products/",
        TriggerSyncView.as_view(),
        name="trigger-sync-products",
    ),
]